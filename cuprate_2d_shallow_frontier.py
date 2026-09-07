"""Reorder only disjoint EVEN fermionic interactions; preserve each mode's order."""
import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import XXPlusYYGate
from cuprate_2d_fermionic_mapping import prepare_state,choose_route,add_fswap
from cuprate_2d_hubbard_pipeline import validate_config
from cuprate_2d_shallow_network import network_events,restore_order

def mode_trace(events,ids,width):
    return [[i for i in ids if mode in events[i]['modes']] for mode in range(width)]

def build_frontier(cfg,*,policy='distance',prepare=True,restore=False):
    validate_config(cfg)
    if policy not in ('distance','critical','asap'): raise ValueError('Unknown policy')
    events=network_events(cfg); count=len(events)
    predecessors=[set() for _ in events]; successors=[set() for _ in events]
    last={}
    for i,event in enumerate(events):
        for mode in event['modes']:
            if mode in last: predecessors[i].add(last[mode])
            last[mode]=i
        for previous in predecessors[i]: successors[previous].add(i)
    height=np.ones(count,dtype=int)
    for i in reversed(range(count)):
        if successors[i]: height[i]+=max(height[j] for j in successors[i])
    remaining=[set(p) for p in predecessors]
    ready={i for i,p in enumerate(remaining) if not p}
    circuit=QuantumCircuit(cfg.qubits)
    if prepare: prepare_state(circuit,cfg)
    order=list(range(cfg.qubits)); clocks=np.zeros(cfg.qubits,dtype=int)
    ledger=[]; execution=[]; swaps_used=0
    while ready:
        positions={mode:slot for slot,mode in enumerate(order)}
        def score(i):
            p,q=events[i]['modes']; a,b=positions[p],positions[q]
            distance=abs(a-b)-1
            if policy=='distance': return distance,i
            if policy=='critical': return distance,-int(height[i]),i
            return max(clocks[a],clocks[b])+2*distance,-int(height[i]),distance,i
        i=min(ready,key=score); ready.remove(i)
        event=events[i]; p,q=event['modes']
        pending=set(range(count))-set(execution)-{i}
        upcoming=sorted(ready)+[j for j in range(i+1,count) if j in pending and j not in ready]
        future=[(*events[j]['modes'],1.) for j in upcoming[:12]]
        changed,swaps=choose_route(order,p,q,future,'look12')
        for slot in swaps:
            add_fswap(circuit,slot,slot+1)
            order[slot],order[slot+1]=order[slot+1],order[slot]
            clocks[slot]=clocks[slot+1]=max(clocks[slot],clocks[slot+1])+1
        if order!=changed: raise AssertionError('Routing ledger changed')
        a,b=order.index(p),order.index(q)
        if abs(a-b)!=1: raise AssertionError('Nonadjacent physical interaction')
        if event['hopping_angle']: circuit.append(XXPlusYYGate(event['hopping_angle']),[a,b])
        if event['onsite_angle']: circuit.cp(event['onsite_angle'],a,b)
        clocks[a]=clocks[b]=max(clocks[a],clocks[b])+1
        ledger.append({'original_event_id':i,**event,'slots':[a,b]})
        execution.append(i); swaps_used+=len(swaps)
        for j in successors[i]:
            remaining[j].discard(i)
            if not remaining[j]: ready.add(j)
    if sorted(execution)!=list(range(count)): raise AssertionError('Incomplete dependency traversal')
    if mode_trace(events,execution,cfg.qubits)!=mode_trace(events,range(count),cfg.qubits):
        raise AssertionError('Overlapping fermionic interaction order changed')
    if cfg.chemical_potential:
        for q in range(cfg.qubits): circuit.p(cfg.chemical_potential*cfg.total_time,q)
    if restore:
        swaps_used+=restore_order(circuit,order); order=list(range(cfg.qubits))
    circuit.metadata={'family':'commuting_frontier_original_network','policy':policy,
        'mode_order_final':order,'slot_for_mode':[order.index(q) for q in range(cfg.qubits)],
        'routing_fswaps':swaps_used,'event_count':count,'final_permutation_restored':restore,
        'every_mode_event_order_preserved':True,'only_disjoint_even_terms_reordered':True,
        'hardware_tested':False}
    return circuit,ledger

