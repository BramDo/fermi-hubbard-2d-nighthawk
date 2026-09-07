"""Exact shared-parity synthesis for the two commuting Paulis in a PA hop.

This reduces repeated parity computation; it is not the full XYZ paper schedule.
Hopping = S*(a A_p B_q + b A'_p B'_q), where S acts on spectators.
Local S gates convert the endpoint axes to XX +/- YY. Dressing either endpoint
with the same spectator parity S gives an exact XXPlusYY implementation.
"""
from qiskit import QuantumCircuit
from qiskit.circuit.library import XXPlusYYGate
from cuprate_2d_hubbard_pipeline import validate_config


def paired_hop(circuit,mapping,p,q,angle):
    first,second=mapping.hopping(p,q)
    qp,qq=mapping.data[p],mapping.data[q]
    if first.support!=second.support or first.x!=second.x:
        raise AssertionError('Expected shared spectator parity and endpoint XY axes')
    if first.z^second.z != (1<<qp)|(1<<qq):
        raise AssertionError('Hop terms must differ only at the two endpoints')
    if abs(first.phase.imag)>1e-14 or abs(second.phase.imag)>1e-14:
        raise AssertionError('Real hopping coefficients required')
    if not all(first.x>>end&1 for end in (qp,qq)):
        raise AssertionError('Endpoint axes must be X or Y')
    spectators=[wire for wire in first.support if wire not in (qp,qq)]
    # Local Clifford endpoint phases turn the first endpoint product into XX.
    yends=[wire for wire in (qp,qq) if first.z>>wire&1]
    for wire in yends: circuit.sdg(wire)
    for wire in spectators:
        if first.x>>wire&1:
            if first.z>>wire&1: circuit.sdg(wire)
            circuit.h(wire)
    # Select an endpoint only by the PA drawing distance; never change physics.
    width=3*mapping.lx
    def distance(a,b): return abs(a%width-b%width)+abs(a//width-b//width)
    anchor=min((qp,qq),key=lambda end:sum(distance(end,s) for s in spectators))
    for wire in spectators: circuit.cz(wire,anchor)
    first_coefficient=first.phase.real
    second_coefficient=second.phase.real*(-1)**len(yends)
    if abs(abs(first_coefficient)-.5)>1e-14: raise AssertionError('Unexpected coefficient')
    flip=abs(second_coefficient+first_coefficient)<1e-14
    if not flip and abs(second_coefficient-first_coefficient)>1e-14:
        raise AssertionError('Unsupported hopping pair')
    if flip: circuit.x(qq)
    circuit.append(XXPlusYYGate(4*angle*first_coefficient),[qp,qq])
    if flip: circuit.x(qq)
    for wire in reversed(spectators): circuit.cz(wire,anchor)
    for wire in reversed(spectators):
        if first.x>>wire&1:
            circuit.h(wire)
            if first.z>>wire&1: circuit.s(wire)
    for wire in reversed(yends): circuit.s(wire)


def evolution(mapping,cfg,ordering='layered'):
    validate_config(cfg)
    if (cfg.lx,cfg.ly)!=(mapping.lx,mapping.ly): raise ValueError('Size mismatch')
    circuit=QuantumCircuit(mapping.n)
    for event in mapping.events(cfg,ordering):
        p,q=event['p'],event['q']
        if event['kind']=='onsite':
            circuit.cp(-event['angle'],mapping.data[p],mapping.data[q])
        else: paired_hop(circuit,mapping,p,q,event['angle'])
    for wire in mapping.data.values():
        if cfg.chemical_potential: circuit.p(cfg.chemical_potential*cfg.total_time,wire)
    circuit.metadata={'family':'PA_shared_parity_pair','ordering':ordering,
        'same_old_finite_circuit':ordering=='network','steps':cfg.steps,'dt':cfg.dt,
        'time':cfg.total_time,'paper_XYZ_schedule_reproduced':False}
    return circuit
