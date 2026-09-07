"""Fermionic routing on a path, with explicit mode-order bookkeeping.

The adaptive route preserves the reference product formula exactly. The
parallel network uses another palindromic ordering of the same full t-t'-U
Hamiltonian; its Trotter error must be checked separately.
"""
from __future__ import annotations

import math
from qiskit import QuantumCircuit
from qiskit.circuit.library import XXPlusYYGate

from cuprate_2d_hubbard_pipeline import Cuprate2DConfig, initial_site_rows, SPINS, mode_qubit, validate_config
from cuprate_2d_fermionic_dynamics import hopping_operations

NETWORK_FAMILY = 'fermionic_fswap_network'
ADAPTIVE_FAMILY = 'fermionic_fswap_adaptive'


def add_fswap(qc, a, b, hopping_angle=0.0, interaction_angle=0.0):
    """F = P(pi/2) x P(pi/2) x XXPlusYY(pi) = SWAP x CZ.

    The hopping rotation commutes with F and is fused into its angle. The
    onsite controlled phase also commutes with F. Only adjacent slots occur.
    """
    if abs(a-b) != 1:
        raise ValueError('The routing primitive requires adjacent slots')
    qc.append(XXPlusYYGate(math.pi+hopping_angle), [a,b])
    qc.p(math.pi/2,a); qc.p(math.pi/2,b)
    if interaction_angle:
        qc.cp(interaction_angle,a,b)


def prepare_state(qc,cfg):
    for row in initial_site_rows(cfg):
        for spin in SPINS:
            if int(row[f'n_{spin}_initial']):
                qc.x(mode_qubit(int(row['site']),spin))


def pair_model(cfg):
    hops={tuple(sorted((p,q))):c for p,q,c in hopping_operations(cfg)}
    onsite={(2*s,2*s+1):cfg.interaction_u for s in range(cfg.sites)}
    return hops,onsite


def network_schedule(width):
    """Odd/even reversal network: every pair of modes meets exactly once."""
    order=list(range(width)); layers=[]; seen=set()
    for layer in range(width):
        records=[]
        for a in range(layer%2,width-1,2):
            b=a+1; modes=tuple(sorted((order[a],order[b])))
            if modes in seen:
                raise AssertionError('A mode pair met twice')
            seen.add(modes); records.append((a,b,modes))
            order[a],order[b]=order[b],order[a]
        layers.append(records)
    assert order == list(reversed(range(width)))
    assert len(seen) == width*(width-1)//2
    return layers


def build_network(cfg: Cuprate2DConfig, *, measured=False, prepare=True):
    validate_config(cfg)
    qc=QuantumCircuit(cfg.qubits)
    if prepare: prepare_state(qc,cfg)
    hops,onsite=pair_model(cfg)
    layers=network_schedule(cfg.qubits)
    for _ in range(cfg.steps):
        order=list(range(cfg.qubits)); covered={}
        for schedule in (layers,list(reversed(layers))):
            for layer in schedule:
                for a,b,modes in layer:
                    assert tuple(sorted((order[a],order[b]))) == modes
                    coefficient=hops.get(modes,0.0)
                    interaction=onsite.get(modes,0.0)
                    # dt/2 of each term on each outward/return pass.
                    add_fswap(qc,a,b,hopping_angle=coefficient*cfg.dt,
                              interaction_angle=-interaction*cfg.dt/2)
                    if coefficient or interaction:
                        covered[modes]=covered.get(modes,0)+1
                    order[a],order[b]=order[b],order[a]
        assert order == list(range(cfg.qubits))
        assert all(covered[k] == 2 for k,c in {**hops,**onsite}.items() if c)
        if cfg.chemical_potential:
            for q in range(cfg.qubits): qc.p(cfg.chemical_potential*cfg.dt,q)
    qc.metadata={'circuit_family':NETWORK_FAMILY,'model':'full_2d_fermi_hubbard',
                 'trotter_order':2,'trotter_ordering':'parallel_swap_network_palindrome',
                 'exact_reference_step_equivalence':False,'mode_order_final':list(range(cfg.qubits)),
                 'mode_order_restored':True,'steps':cfg.steps,'dt':cfg.dt,'time':cfg.total_time,
                 'fswaps_per_step':cfg.qubits*(cfg.qubits-1),'only_adjacent_two_qubit_gates':True}
    if measured: qc.measure_all()
    return qc


def route_trial(order,p,q,meeting):
    order=list(order); a,b=sorted((order.index(p),order.index(q))); swaps=[]
    for k in range(a,meeting):
        order[k],order[k+1]=order[k+1],order[k]; swaps.append(k)
    for k in range(b-1,meeting,-1):
        order[k],order[k+1]=order[k+1],order[k]; swaps.append(k)
    return order,swaps


def choose_route(order,p,q,future,strategy):
    a,b=sorted((order.index(p),order.index(q)))
    if strategy=='left': meetings=[a]
    elif strategy=='right': meetings=[b-1]
    elif strategy.startswith('look'):
        meetings=range(a,b)
    else: raise ValueError(f'Unknown routing strategy: {strategy}')
    best=None
    for meeting in meetings:
        trial,swaps=route_trial(order,p,q,meeting)
        positions={m:i for i,m in enumerate(trial)}
        score=sum((abs(positions[u]-positions[v])-1)/(i+1) for i,(u,v,_) in enumerate(future))
        candidate=(score,meeting,trial,swaps)
        if best is None or candidate[:2] < best[:2]: best=candidate
    return best[2],best[3]


def build_adaptive(cfg: Cuprate2DConfig, *, measured=False, prepare=True, strategy='look12'):
    validate_config(cfg)
    qc=QuantumCircuit(cfg.qubits)
    if prepare: prepare_state(qc,cfg)
    hops=hopping_operations(cfg)
    horizon=int(strategy[4:]) if strategy.startswith('look') else 0
    step_swaps=0
    for _ in range(cfg.steps):
        order=list(range(cfg.qubits)); records=[]
        for i,(p,q,c) in enumerate(hops):
            order,swaps=choose_route(order,p,q,hops[i+1:i+1+horizon],strategy)
            for a in swaps: add_fswap(qc,a,a+1)
            a,b=order.index(p),order.index(q)
            assert abs(a-b)==1
            qc.append(XXPlusYYGate(c*cfg.dt),[a,b])
            records.append((a,b,c,swaps))
        # Bring onsite partners together without imposing an arbitrary site
        # ordering; undo this permutation after the commuting U terms.
        onsite_swaps=[]
        for a in range(0,cfg.qubits,2):
            partner=order[a]^1; b=order.index(partner)
            assert b>a
            for k in range(b-1,a,-1):
                add_fswap(qc,k,k+1); order[k],order[k+1]=order[k+1],order[k]
                onsite_swaps.append(k)
            if cfg.interaction_u: qc.cp(-cfg.interaction_u*cfg.dt,a,a+1)
        if cfg.chemical_potential:
            for q in range(cfg.qubits): qc.p(cfg.chemical_potential*cfg.dt,q)
        for a in reversed(onsite_swaps):
            add_fswap(qc,a,a+1); order[a],order[a+1]=order[a+1],order[a]
        for a,b,c,swaps in reversed(records):
            qc.append(XXPlusYYGate(c*cfg.dt),[a,b])
            for k in reversed(swaps):
                add_fswap(qc,k,k+1); order[k],order[k+1]=order[k+1],order[k]
        assert order == list(range(cfg.qubits))
        step_swaps=2*(sum(len(r[3]) for r in records)+len(onsite_swaps))
    qc.metadata={'circuit_family':ADAPTIVE_FAMILY,'routing_strategy':strategy,
                 'model':'full_2d_fermi_hubbard','trotter_order':2,
                 'exact_reference_step_equivalence':True,'mode_order_final':list(range(cfg.qubits)),
                 'mode_order_restored':True,'steps':cfg.steps,'dt':cfg.dt,'time':cfg.total_time,
                 'fswaps_per_step':step_swaps,'only_adjacent_two_qubit_gates':True}
    if measured: qc.measure_all()
    return qc
