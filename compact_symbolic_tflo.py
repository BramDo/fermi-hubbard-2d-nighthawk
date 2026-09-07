"""Exact structural native cleanup, independent of all bound physics values."""
import math
import numpy as np
from qiskit.synthesis import OneQubitEulerDecomposer

MATS={'x':np.array([[0,1],[1,0]],complex),
      'sx':.5*np.array([[1+1j,1-1j],[1-1j,1+1j]],complex),'id':np.eye(2,dtype=complex)}
DECOMPOSER=OneQubitEulerDecomposer('ZSXX')

def symbolic(op): return any(getattr(p,'parameters',set()) for p in op.params)
def constant_key(op):
    if symbolic(op) or op.name not in ('rz','sx','x','id'): raise ValueError('Not a constant native1q gate')
    return op.name,tuple(float(p) for p in op.params)
def matrix(key):
    name,params=key
    if name=='rz': return np.diag([np.exp(-.5j*params[0]),np.exp(.5j*params[0])])
    return MATS[name]
def wire_indices(c,item): return tuple(c.find_bit(q).index for q in item.qubits)
def classical_indices(c,item): return tuple(c.find_bit(q).index for q in item.clbits)

def affine_phase(phase,extra=0.):
    params=list(getattr(phase,'parameters',[]))
    constant=float(phase.bind({p:0. for p in params})) if params else float(phase)
    coefficients={p:float(phase.gradient(p)) for p in params}
    for k in range(3):
        values={p:(j+1)*(.13+k*.17) for j,p in enumerate(params)}
        actual=float(phase.bind(values)) if params else float(phase)
        predicted=constant+math.fsum(coefficients[p]*values[p] for p in params)
        if abs(actual-predicted)>1e-9: raise ValueError('Nonaffine phase')
    result=math.fsum([constant,extra])%(2*math.pi)
    for p,coefficient in coefficients.items(): result=result+coefficient*p
    return result

def segments(c):
    buffers=[np.eye(2,dtype=complex) for _ in c.qubits]; out=[[] for _ in c.qubits]
    for inst in c.data:
        op=inst.operation; wires=wire_indices(c,inst)
        if op.name in ('rz','sx','x','id') and not symbolic(op):
            if len(wires)!=1: raise ValueError('Unexpected arity')
            buffers[wires[0]]=matrix(constant_key(op))@buffers[wires[0]]
        else:
            if op.name not in ('cz','rz','measure','barrier'): raise ValueError('Unsupported structural anchor '+op.name)
            tag=(op.name,wires,tuple(map(str,op.params)),classical_indices(c,inst))
            for q in wires:
                out[q].append((tag,buffers[q])); buffers[q]=np.eye(2,dtype=complex)
    for q in range(c.num_qubits): out[q].append((('end',),buffers[q]))
    return out

def verify_constant_cleanup(before,after):
    a,b=segments(before),segments(after); phases=[]; worst=0.; count=0
    for lhs,rhs in zip(a,b):
        if len(lhs)!=len(rhs): raise AssertionError('Anchor count changed')
        for (tag,u),(other,v) in zip(lhs,rhs):
            if tag!=other: raise AssertionError('Symbolic/CZ/measurement anchor changed')
            scalar=np.vdot(v,u)/2
            error=float(np.max(abs(u-scalar*v))); worst=max(worst,error)
            if abs(abs(scalar)-1)>1e-10 or error>1e-10: raise AssertionError('Constant segment mismatch')
            phases.append(float(np.angle(scalar))); count+=1
    phase=before.global_phase-after.global_phase
    params=list(getattr(phase,'parameters',[]))
    residuals=[]
    for k in range(4):
        values={p:(j+1)*(.037+k*.19) for j,p in enumerate(params)}
        delta=float(phase.bind(values)) if params else float(phase)
        residuals.append(float(abs(np.exp(1j*math.fsum([delta,*phases]))-1)))
    if max(residuals)>1e-7: raise AssertionError('Global phase mismatch')
    return dict(segments=count,max_segment_error=worst,max_global_phase_error=max(residuals),
        symbolic_and_CZ_wire_anchors_unchanged=True)

def compact_constants(c):
    out=c.copy_empty_like(); buffers=[[] for _ in c.qubits]; cache={}; phases=[]; worst=0.
    def flush(q):
        nonlocal worst
        key=tuple(buffers[q])
        if not key: return
        if key not in cache:
            u=np.eye(2,dtype=complex)
            for gate in key: u=matrix(gate)@u
            native=DECOMPOSER(u,simplify=True,atol=1e-12)
            v=np.eye(2,dtype=complex)
            for gate in native.data: v=matrix(constant_key(gate.operation))@v
            err=float(np.max(abs(u-np.exp(1j*float(native.global_phase))*v)))
            if err>1e-11: raise AssertionError('1q synthesis mismatch')
            cache[key]=(native,err)
        native,err=cache[key]; worst=max(worst,err)
        for inst in native.data: out.append(inst.operation,[q])
        phases.append(float(native.global_phase)); buffers[q]=[]
    for inst in c.data:
        op=inst.operation; wires=wire_indices(c,inst)
        if op.name in ('rz','sx','x','id') and not symbolic(op):
            buffers[wires[0]].append(constant_key(op))
        else:
            if op.name not in ('rz','cz','measure','barrier'): raise ValueError('Unsupported operation '+op.name)
            for q in wires: flush(q)
            out.append(op,wires,classical_indices(c,inst))
    for q in range(c.num_qubits): flush(q)
    out.global_phase=affine_phase(c.global_phase,math.fsum(phases))
    out.metadata=dict(c.metadata or {})
    check=verify_constant_cleanup(c,out)
    return out,dict(**check,unique_synthesized_segments=len(cache),synthesis_max_abs=worst)

def cancel_diagonal_cz_pairs(c):
    pending={}; touching=[set() for _ in c.qubits]; removed=set(); records=[]
    for index,inst in enumerate(c.data):
        op=inst.operation; wires=wire_indices(c,inst)
        if op.name=='cz':
            pair=tuple(sorted(wires))
            if pair in pending:
                previous=pending.pop(pair); removed.update((previous,index))
                records.append(dict(first=previous,second=index,wires=list(pair)))
                for q in pair: touching[q].discard(pair)
            else:
                pending[pair]=index
                for q in pair: touching[q].add(pair)
        elif op.name not in ('rz','id'):
            for q in wires:
                for pair in list(touching[q]):
                    pending.pop(pair,None)
                    for endpoint in pair: touching[endpoint].discard(pair)
    # Independent proof on ORIGINAL operation positions for every removed pair.
    for record in records:
        first,last=record['first'],record['second']; pair=set(record['wires'])
        for index in (first,last):
            inst=c.data[index]
            if inst.operation.name!='cz' or set(wire_indices(c,inst))!=pair: raise AssertionError('CZ witness changed')
        for inst in c.data[first+1:last]:
            if pair.intersection(wire_indices(c,inst)) and inst.operation.name not in ('rz','cz','id'):
                raise AssertionError('Illegal cancellation through a non-diagonal operation')
    out=c.copy_empty_like()
    for index,inst in enumerate(c.data):
        if index not in removed: out.append(inst.operation,wire_indices(c,inst),classical_indices(c,inst))
    out.global_phase=c.global_phase; out.metadata=dict(c.metadata or {})
    if c.count_ops().get('cz',0)-out.count_ops().get('cz',0)!=2*len(records): raise AssertionError('Wrong CZ removal count')
    return out,dict(pairs_cancelled=len(records),CZ_removed=2*len(records),
        exact_diagonal_commutation_witnesses=records,only_recorded_gates_removed=True)

def optimize(c,rounds=3,progress=None):
    current=c; checks=[]
    for i in range(rounds):
        compact,one=compact_constants(current)
        reduced,two=cancel_diagonal_cz_pairs(compact)
        checks.append(dict(round=i,constant_cleanup=one,cancellation=two,counts=dict(reduced.count_ops())))
        if progress: progress(i,checks[-1])
        current=reduced
        if not two['pairs_cancelled']: break
    current,last=compact_constants(current)
    return current,dict(rounds=checks,final_cleanup=last)
