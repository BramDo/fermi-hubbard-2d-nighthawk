"""Submit-free one-qubit cleanup and calibration-only TFLO filter selection.

Never mutate the original compiled bundle, primary analysis, or job lock.
Refitted uncertainty does not include transfer bias. Retention is not fidelity.
"""
from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit
from qiskit.transpiler import PassManager
from qiskit.transpiler.passes import Optimize1qGatesDecomposition

from cuprate_2d_tflo import sector_mask,pauli_samples,fit_tflo,apply_tflo


def cz_trace(circuit):
    """CZ ordering on every wire; disjoint commuting CZs may be reordered."""
    trace=[[] for _ in range(circuit.num_qubits)]
    for inst in circuit.data:
        if len(inst.qubits)!=2:
            continue
        if inst.operation.name!='cz':
            raise ValueError('Non-CZ two-qubit operation')
        pair=tuple(sorted(circuit.find_bit(q).index for q in inst.qubits))
        for q in pair:
            trace[q].append(pair)
    return trace


def measurement_map(circuit):
    return sorted((circuit.find_bit(i.qubits[0]).index,circuit.find_bit(i.clbits[0]).index)
                  for i in circuit.data if i.operation.name=='measure')


def compact_phase(circuit):
    phase=circuit.global_phase
    if not hasattr(phase,'parameters'):
        return
    parameters=sorted(phase.parameters,key=lambda p:p.name)
    canonical=float(phase.bind({p:0. for p in parameters}))
    for p in parameters:
        coefficient=float(phase.gradient(p))  # rejects nonlinear phases
        if coefficient:
            canonical=canonical+coefficient*p
    errors=[]
    for k in range(5):
        values={p:(j+1)*(k-.7)/3 for j,p in enumerate(parameters)}
        before=float(phase.bind(values))
        after=float(canonical.bind({p:values[p] for p in canonical.parameters})) if hasattr(canonical,'parameters') else canonical
        errors.append(float(abs(np.exp(1j*before)-np.exp(1j*after))))
    if max(errors)>1e-8:
        raise ValueError('Phase canonicalization not equivalent')
    circuit.global_phase=canonical
    circuit.metadata={**(circuit.metadata or {}),'phase_compaction_max_error':max(errors)}


def cleanup_one_qubit(template):
    """Only optimize 1q runs in an UNBOUND template, never specialize U or T."""
    if not template.parameters:
        raise ValueError('Expected unbound parameters; do not specialize training circuits')
    result=PassManager([Optimize1qGatesDecomposition(basis=['rz','sx','x'])]).run(template)
    if cz_trace(result)!=cz_trace(template):
        raise AssertionError('Two-qubit partial ordering changed')
    if measurement_map(result)!=measurement_map(template):
        raise AssertionError('Measurement mapping changed')
    if result.parameters!=template.parameters:
        raise AssertionError('Parameter set changed')
    if any(i.operation.name not in ('rz','sx','x','cz','measure') for i in result.data):
        raise AssertionError('Operation outside the frozen native basis')
    result.metadata={**(template.metadata or {}),'one_qubit_cleanup':True,
                     'cleanup_before_binding':True,'hardware_tested':False}
    compact_phase(result)
    return result


def active_circuit(circuit,layout):
    """Drop terminal measurements and unused physical wires for ideal tests."""
    inverse={p:q for q,p in enumerate(layout)}
    out=QuantumCircuit(len(layout))
    out.global_phase=circuit.global_phase
    measured=set()
    for inst in circuit.data:
        wires=[circuit.find_bit(q).index for q in inst.qubits]
        if inst.operation.name=='measure':
            measured.update(wires)
            continue
        if measured.intersection(wires):
            raise ValueError('Non-terminal measurement')
        if inst.clbits or any(q not in inverse for q in wires):
            raise ValueError('Unexpected classical operation or wire outside layout')
        out.append(inst.operation,[inverse[q] for q in wires])
    return out


def block_means(settings,raw,nup,ndown,tolerance,minimum=32):
    means,counts=[],[]
    for setting in settings:
        blocks=raw[setting['id']]
        bits=np.concatenate([blocks[t] for t in sorted(blocks)])
        keep=sector_mask(bits,nup,ndown,tolerance)
        counts.append(int(keep.sum()))
        if counts[-1]<minimum:
            raise ValueError('Insufficient retained shots')
        means.append(pauli_samples(bits[keep]).mean(axis=0))
    return np.asarray(means),counts


def select_u0(settings,raw,nup,ndown,protocol):
    """This API REFUSES U!=0 input, including references or target bitstrings."""
    ids={s['id'] for s in settings}
    if set(raw)!=ids or any(s['u_over_t']!=0 for s in settings):
        raise ValueError('Selection accepts U=0 settings and their bitstrings ONLY')
    train=[i for i,s in enumerate(settings) if s['role']=='train']
    valid=[i for i,s in enumerate(settings) if s['role']=='flo_holdout']
    if len(train)!=6 or len(valid)!=2:
        raise ValueError('Expected six original training and two U=0 validation settings')
    if not all('reference' in s for s in settings):
        raise ValueError('Missing exact FLO references')
    exact=np.asarray([s['reference'] for s in settings])
    times=[s['time'] for s in settings]
    unfiltered,raw_counts=block_means(settings,raw,nup,ndown,18,1)
    raw_score=float(np.mean((unfiltered[valid]-exact[valid])**2))
    winner={'id':'raw','tolerance':18,'score':raw_score,'model':None,
            'counts':raw_counts,'uses_TFLO':False}
    candidates=[{'id':'raw','feasible':True,'U0_validation_pauli_MSE':raw_score,'counts':raw_counts}]
    minimum=protocol['minimum_retained_per_U0_setting']
    # Descending tolerance makes exact ties prefer weaker filtering.
    for tolerance in sorted(protocol['candidate_tolerances'],reverse=True):
        cid=f'tflo_k{tolerance}'
        try:
            means,counts=block_means(settings,raw,nup,ndown,tolerance,minimum)
        except ValueError:
            candidates.append({'id':cid,'feasible':False,'reason':'below frozen 32-shot minimum'})
            continue
        model=fit_tflo(means[train],exact[train],[times[i] for i in train],ridge=protocol['ridge'])
        predicted=np.array([apply_tflo(model,p,t) for p,t in zip(means,times)])
        score=float(np.mean((predicted[valid]-exact[valid])**2))
        candidates.append({'id':cid,'tolerance':tolerance,'feasible':True,
                           'counts':counts,'U0_validation_pauli_MSE':score,
                           'PS_only_U0_validation_pauli_MSE':float(np.mean((means[valid]-exact[valid])**2))})
        if score<winner['score']-1e-12:
            winner={'id':cid,'tolerance':tolerance,'score':score,'model':model,'counts':counts,'uses_TFLO':True}
    return winner,candidates


def refit_locked_u0(winner,settings,raw,nup,ndown,protocol):
    if any(s['u_over_t']!=0 for s in settings) or set(raw)!={s['id'] for s in settings}:
        raise ValueError('Locked refit also accepts U=0 only')
    if not winner['uses_TFLO']:
        return dict(winner)
    train=[s for s in settings if s['role']=='train']
    means,_=block_means(train,raw,nup,ndown,winner['tolerance'],32)
    model=fit_tflo(means,[s['reference'] for s in train],[s['time'] for s in train],ridge=protocol['ridge'])
    return {**winner,'model':model}


def evaluate_target(winner,settings,raw,nup,ndown):
    """No target references are read here. This is prediction, not fitting."""
    if any(s['u_over_t']!=8 for s in settings):
        raise ValueError('This pilot uses the frozen U=8 target settings')
    unfiltered,_=block_means(settings,raw,nup,ndown,18,1)
    selected,counts=block_means(settings,raw,nup,ndown,winner['tolerance'],32)
    predicted=(np.array([apply_tflo(winner['model'],p,s['time']) for p,s in zip(selected,settings)])
               if winner['uses_TFLO'] else selected.copy())
    return {'raw':unfiltered,'postselected':selected,'corrected':predicted,'counts':counts}


def resample_paired(raw,rng):
    keys=sorted(next(iter(raw.values())))
    if any(sorted(blocks)!=keys for blocks in raw.values()):
        raise ValueError('Twirl IDs are not matched')
    chosen=rng.choice(keys,len(keys),replace=True)
    output={}
    for sid,blocks in raw.items():
        output[sid]={}
        for slot,key in enumerate(chosen):
            bits=blocks[int(key)]
            output[sid][slot]=bits[rng.integers(len(bits),size=len(bits))]
    return output
