"""Submit-free, exact-target shallow candidates for the full network circuit."""
from collections import Counter
import math
import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import XXPlusYYGate
from qiskit.transpiler import PassManager
from qiskit.transpiler.passes import Optimize1qGatesDecomposition
from cuprate_2d_fermionic_mapping import (
    network_schedule,pair_model,prepare_state,choose_route,add_fswap)
from cuprate_2d_hubbard_pipeline import validate_config
from cuprate_2d_tflo_refinement import cz_trace,measurement_map

def network_events(cfg):
    """Exactly the original network's physical interaction order; no regrouping."""
    hops,onsite=pair_model(cfg)
    schedule=network_schedule(cfg.qubits)
    events=[]
    for step in range(cfg.steps):
        for direction,layers in enumerate((schedule,list(reversed(schedule)))):
            for layer_id,layer in enumerate(layers):
                for _,_,modes in layer:
                    c=float(hops.get(modes,0)); u=float(onsite.get(modes,0))
                    if c or u:
                        events.append({'step':step,'direction':direction,'layer':layer_id,
                            'modes':list(modes),'hopping_angle':c*cfg.dt,
                            'onsite_angle':-u*cfg.dt/2})
    return events

def restore_order(circuit,order):
    order=list(order); swaps=0
    for wanted in range(len(order)):
        position=order.index(wanted)
        while position>wanted:
            add_fswap(circuit,position-1,position)
            order[position-1],order[position]=order[position],order[position-1]
            position-=1; swaps+=1
    if order!=list(range(len(order))): raise AssertionError('Restoration failed')
    return swaps

def build_sparse(cfg,*,strategy='look12',prepare=True,restore=False):
    """Reroute the SAME ordered even-fermion interactions, keeping a mode ledger.

    If restore=False, the final fermionic permutation is retained and logical
    output bits MUST be measured from slot_for_mode. It is not an ordinary
    bosonic relabeling of the state amplitudes.
    """
    validate_config(cfg)
    if strategy not in ('left','right','look4','look12'): raise ValueError('Unsupported strategy')
    circuit=QuantumCircuit(cfg.qubits)
    if prepare: prepare_state(circuit,cfg)
    order=list(range(cfg.qubits)); events=network_events(cfg); routing=0; ledger=[]
    horizon=int(strategy[4:]) if strategy.startswith('look') else 0
    for i,event in enumerate(events):
        p,q=event['modes']
        future=[(*e['modes'],1.) for e in events[i+1:i+1+horizon]]
        changed,swaps=choose_route(order,p,q,future,strategy)
        for slot in swaps:
            add_fswap(circuit,slot,slot+1)
            order[slot],order[slot+1]=order[slot+1],order[slot]
        if order!=changed: raise AssertionError('Routing ledger differs')
        a,b=order.index(p),order.index(q)
        if abs(a-b)!=1: raise AssertionError('Modes not adjacent')
        if event['hopping_angle']:
            circuit.append(XXPlusYYGate(event['hopping_angle']),[a,b])
        if event['onsite_angle']:
            circuit.cp(event['onsite_angle'],a,b)
        ledger.append({**event,'slots':[a,b]})
        routing+=len(swaps)
    # Uniform chemical potential commutes with every term and mode permutation.
    if cfg.chemical_potential:
        for q in range(cfg.qubits): circuit.p(cfg.chemical_potential*cfg.total_time,q)
    if restore:
        routing+=restore_order(circuit,order); order=list(range(cfg.qubits))
    slot_for_mode=[order.index(q) for q in range(cfg.qubits)]
    if [{k:v for k,v in e.items() if k!='slots'} for e in ledger]!=events:
        raise AssertionError('Physics event order changed')
    circuit.metadata={'family':'sparse_exact_original_network_order','strategy':strategy,
        'mode_order_final':order,'slot_for_mode':slot_for_mode,'routing_fswaps':routing,
        'event_count':len(events),'final_permutation_restored':restore,
        'same_original_event_order':True,'hardware_tested':False}
    return circuit,ledger

def embed_with_logical_readout(local,layout,slot_for_mode,mask=None,physical_width=120):
    width=local.num_qubits
    if local.num_clbits or len(layout)!=width or len(set(layout))!=width:
        raise ValueError('Invalid input layout')
    if sorted(slot_for_mode)!=list(range(width)) or min(layout)<0 or max(layout)>=physical_width:
        raise ValueError('Invalid output permutation')
    out=QuantumCircuit(physical_width)
    out.compose(local,qubits=layout,inplace=True)
    from qiskit import ClassicalRegister
    meas=ClassicalRegister(width,'meas'); out.add_register(meas)
    output_layout=[layout[slot] for slot in slot_for_mode]
    out.measure(output_layout,meas)
    mask=np.zeros(width,dtype=int) if mask is None else np.asarray(mask)
    if mask.shape!=(width,) or not np.all((mask==0)|(mask==1)):
        raise ValueError('Invalid terminal mask')
    logical_mask=mask[slot_for_mode].astype(int).tolist()
    out.metadata={**(local.metadata or {}),'input_layout':list(layout),
        'logical_output_layout':output_layout,'readout_mask_little_endian':logical_mask}
    return out

def wire_segments(circuit):
    """Local 2x2 unitary segments anchored at each unchanged entangling event."""
    current=[np.eye(2,dtype=complex) for _ in range(circuit.num_qubits)]
    segments=[[] for _ in range(circuit.num_qubits)]
    for item in circuit.data:
        name=item.operation.name; qs=[circuit.find_bit(q).index for q in item.qubits]
        if name in ('rz','sx','x','id'):
            current[qs[0]]=item.operation.to_matrix()@current[qs[0]]
        elif name=='cz':
            anchor=('cz',tuple(sorted(qs)))
            for q in qs:
                segments[q].append((anchor,current[q]))
                current[q]=np.eye(2,dtype=complex)
        elif name=='measure':
            q=qs[0]; anchor=('measure',circuit.find_bit(item.clbits[0]).index)
            segments[q].append((anchor,current[q])); current[q]=np.eye(2,dtype=complex)
        else: raise ValueError('Unexpected operation: '+name)
    for q in range(circuit.num_qubits): segments[q].append((('end',),current[q]))
    return segments

def verify_cleanup(before,after):
    if cz_trace(before)!=cz_trace(after) or measurement_map(before)!=measurement_map(after):
        raise AssertionError('Two-qubit order or readout changed')
    lhs,rhs=wire_segments(before),wire_segments(after)
    phases=[float(before.global_phase-after.global_phase)]; worst=0.; count=0
    for old,new in zip(lhs,rhs):
        if len(old)!=len(new): raise AssertionError('Segment count changed')
        for (tag,a),(other,b) in zip(old,new):
            if tag!=other: raise AssertionError('Segment anchor changed')
            scalar=np.vdot(b,a)/2
            if abs(abs(scalar)-1)>1e-10: raise AssertionError('Local block changed')
            worst=max(worst,float(np.max(np.abs(a-scalar*b))))
            phases.append(float(np.angle(scalar))); count+=1
    global_error=float(abs(np.exp(1j*math.fsum(phases))-1))
    if worst>1e-10 or global_error>1e-7: raise AssertionError('Unitary cleanup mismatch')
    return {'local_2x2_segments':count,'max_segment_error':worst,
        'global_phase_error':global_error,'CZ_partial_order_preserved':True}

def compact_bound(circuit):
    if circuit.num_parameters: raise ValueError('This path is for bound fixed-physics circuits')
    out=PassManager([Optimize1qGatesDecomposition(basis=['rz','sx','x'])]).run(circuit)
    check=verify_cleanup(circuit,out)
    out.metadata={**(circuit.metadata or {}),'one_qubit_only_cleanup':True,'hardware_tested':False}
    return out,check
