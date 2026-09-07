"""Provider-free circuit, timing and fit definitions for one 6x6 TFLO/DD job."""
import hashlib
import json
import math
import numpy as np
from qiskit.transpiler import PassManager
from qiskit.transpiler.passes import ALAPScheduleAnalysis,ConstrainedReschedule,PadDelay,PadDynamicalDecoupling
from qiskit.circuit.library import XGate

CAP=15
SHOTS=512
TWIRLS=4
TOTAL=38912
PUBS=76
RIDGE=.001
BOOTSTRAP=400
TRAIN=(.04,.08,.12,.24,.32,.48)
HOLDOUT=(.2,.4)
DD_LABEL='tflo_dd_echo_x'


def settings():
    return ([{'id':f'train{i}','role':'train','T':t,'U':0.} for i,t in enumerate(TRAIN)]
        +[{'id':f'holdout{i}','role':'holdout','T':t,'U':0.} for i,t in enumerate(HOLDOUT)]
        +[{'id':'target','role':'target','T':.4,'U':8.}])


def records(layout,masks):
    out=[]
    for block in ('start','end'):
        for state in (0,1):
            out.append({'setting_id':f'cal{state}_{block}','role':'calibration','block':block,
                'state':state,'dd':False,'twirl_id':0,'shots':SHOTS,'width':72,
                'physical_layout':layout,'readout_mask_little_endian':[0]*72})
    targets=[]
    pairs=[(s,t) for s in settings() for t in range(TWIRLS)]
    rng=np.random.default_rng(202609061601); rng.shuffle(pairs)
    for s,t in pairs:
        order=[False,True]; rng.shuffle(order)
        for dd in order:
            targets.append({'setting_id':s['id'],'role':s['role'],'T':s['T'],'U':s['U'],
                'dd':dd,'twirl_id':t,'shots':SHOTS,'width':72,'physical_layout':layout,
                'readout_mask_little_endian':list(map(int,masks[t]))})
    return out[:2]+targets+out[2:]


def validate_records(rows):
    if len(rows)!=PUBS or sum(r['shots'] for r in rows)!=TOTAL:
        raise ValueError('Wrong fixed exposure')
    expected={(s['id'],d,t) for s in settings() for d in (False,True) for t in range(TWIRLS)}
    seen=set()
    for r in rows:
        if r['shots']!=SHOTS or r['width']!=72 or len(r['physical_layout'])!=72:
            raise ValueError('Wrong PUB shape')
        if len(set(r['physical_layout']))!=72 or min(r['physical_layout'])<0 or max(r['physical_layout'])>=120:
            raise ValueError('Invalid layout')
        if len(r['readout_mask_little_endian'])!=72 or set(r['readout_mask_little_endian'])-{0,1}:
            raise ValueError('Invalid mask')
        if r['role']!='calibration':
            key=(r['setting_id'],r['dd'],r['twirl_id'])
            if key in seen: raise ValueError('Duplicate setting')
            seen.add(key)
            s=next(s for s in settings() if s['id']==r['setting_id'])
            if any(r[k]!=s[k] for k in ('role','U','T')): raise ValueError('Changed physics')
    if seen!=expected: raise ValueError('Missing settings')
    if [r['setting_id'] for r in rows[:2]+rows[-2:]]!=['cal0_start','cal1_start','cal0_end','cal1_end']:
        raise ValueError('Calibration bookends changed')


def fingerprint(target,layout):
    rows=[]
    for name in ('rz','sx','x','cz','measure','reset'):
        for wires,prop in target[name].items():
            if wires is not None and set(wires).issubset(set(layout)):
                if prop is None or prop.duration is None: raise ValueError('Missing duration')
                rows.append([name,list(wires),float(prop.duration)])
    payload={'dt':target.dt,'pulse_alignment':target.pulse_alignment,
        'acquire_alignment':target.acquire_alignment,'granularity':target.granularity,
        'min_length':target.min_length,'durations':sorted(rows,key=str)}
    return hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest(),payload


def clocks(circuit,target):
    """Independent exact dt clock, including explicit delays and barriers."""
    now=np.zeros(circuit.num_qubits,dtype=np.int64)
    original=[]
    for inst in circuit.data:
        op=inst.operation; wires=tuple(circuit.find_bit(q).index for q in inst.qubits)
        if not wires: continue
        start=int(max(now[list(wires)]))
        if op.name=='barrier': now[list(wires)]=start; continue
        if op.name=='delay':
            if op.unit!='dt': raise ValueError('Expected integral dt delay')
            dt=float(op.duration)
        else:
            prop=target[op.name].get(wires)
            if prop is None or prop.duration is None: raise ValueError('Missing timing')
            dt=float(prop.duration)/target.dt
        if not math.isfinite(dt) or dt<0 or abs(dt-round(dt))>1e-6:
            raise ValueError('Nonintegral or negative gate timing')
        if op.name not in ('delay',) and op.label!=DD_LABEL:
            align=target.acquire_alignment if op.name=='measure' else target.pulse_alignment
            if start%max(int(align or 1),1): raise ValueError('Gate start alignment')
            original.append((op.name,wires,start,tuple(str(p) for p in op.params)))
        now[list(wires)]=start+int(round(dt))
    return int(max(now)),original


def wire_sequences(circuit,drop_echo=False):
    output=[[] for _ in circuit.qubits]
    pairs=0
    pending=[0]*circuit.num_qubits
    for inst in circuit.data:
        op=inst.operation
        if op.name in ('delay','barrier'): continue
        wires=tuple(circuit.find_bit(b).index for b in inst.qubits)
        for q in wires:
            if op.label==DD_LABEL:
                if op.name!='x': raise ValueError('Non-X DD insertion')
                pending[q]+=1
                if pending[q]==2: pairs+=1; pending[q]=0
                if drop_echo: continue
            elif pending[q]:
                raise ValueError('DD pair interrupted by an original gate')
            output[q].append((op.name,wires,tuple(str(p) for p in op.params),
                tuple(circuit.find_bit(b).index for b in inst.clbits)))
    if any(pending): raise ValueError('Unpaired echo gate')
    return output,pairs


def schedule_pair(circuit,target,layout):
    def base():
        return [ALAPScheduleAnalysis(target=target),ConstrainedReschedule(target=target)]
    off=PassManager(base()+[PadDelay(target=target)]).run(circuit)
    on=PassManager(base()+[PadDynamicalDecoupling(target=target,
        dd_sequence=[XGate(label=DD_LABEL),XGate(label=DD_LABEL)],qubits=layout,
        pulse_alignment=max(int(target.pulse_alignment or 1),1),skip_reset_qubits=True)]).run(circuit)
    seq,_=wire_sequences(circuit)
    seqoff,_=wire_sequences(off)
    seqon,pairs=wire_sequences(on,drop_echo=True)
    if seq!=seqoff or seq!=seqon: raise ValueError('DD changed ideal gate order')
    t0,starts0=clocks(off,target); t1,starts1=clocks(on,target)
    # Scheduling may interleave independent gates differently; compare per-wire starts.
    if t0!=t1 or sorted(starts0,key=str)!=sorted(starts1,key=str):
        raise ValueError('DD changed original gate timing')
    if pairs==0: raise ValueError('No DD pairs inserted')
    if off.count_ops().get('cz',0)!=on.count_ops().get('cz',0): raise ValueError('CZ changed')
    return off,on,{'echo_pairs':pairs,'duration_dt':t0,'duration_seconds':t0*target.dt,
        'off_operations':dict(off.count_ops()),'on_operations':dict(on.count_ops()),
        'original_gate_starts_equal':True,'ideal_per_wire_equivalence':True}


def fit_affine(noisy,exact,ridge=RIDGE):
    x,y=np.asarray(noisy,float),np.asarray(exact,float)
    if x.shape!=y.shape or x.ndim!=2 or x.shape[0]<4 or not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError('Invalid training arrays')
    if ridge<=0: raise ValueError('Invalid ridge')
    n=x.shape[0]; sx=x.sum(0); sy=y.sum(0)
    a=(x*x).sum(0)+ridge; b=sx; d=n+ridge
    rhs0=(x*y).sum(0)+ridge; rhs1=sy
    det=a*d-b*b
    if np.any(det<=0): raise ValueError('Singular regularized fit')
    slope=(d*rhs0-b*rhs1)/det
    offset=(a*rhs1-b*rhs0)/det
    return np.stack([slope,offset],axis=-1)


def apply_affine(beta,noisy):
    return beta[:,0]*np.asarray(noisy)+beta[:,1]


def budget(execution):
    if not math.isfinite(execution) or execution<=0: raise ValueError('Invalid execution duration')
    estimates={str(n):2*n+execution for n in range(1,9)}
    return {'shot_execution_seconds':execution,'estimates_by_internal_subjobs':estimates,
        'planning_subjobs':4,'headroom_seconds':.75,'cap_seconds':CAP,
        'internal_subjob_count_known':False,'completion_guaranteed':False,
        'pass':estimates['4']<=CAP-.75}


def quota(raw):
    keys=('usage_limit_seconds','usage_allocation_seconds','usage_consumed_seconds','usage_remaining_seconds')
    out={k:float(raw[k]) for k in keys if isinstance(raw.get(k),(int,float)) and not isinstance(raw[k],bool)}
    if any(not math.isfinite(v) or v<0 for v in out.values()): raise ValueError('Invalid quota')
    if 'usage_remaining_seconds' not in out:
        limit=out.get('usage_limit_seconds',out.get('usage_allocation_seconds'))
        if limit is not None and 'usage_consumed_seconds' in out:
            out['usage_remaining_seconds']=max(0,limit-out['usage_consumed_seconds'])
    if out.get('usage_remaining_seconds',CAP)<CAP: raise ValueError('Insufficient reported quota')
    return {**out,'remaining_reported':'usage_remaining_seconds' in out,'unknown_is_not_unlimited':True}
