"""Provider-free definitions and analysis for the authorized5x5 control."""
from collections import Counter
from dataclasses import replace
import math
import numpy as np
from qiskit import QuantumCircuit
from cuprate_2d_hubbard_pipeline import Cuprate2DConfig
from cuprate_2d_fermionic_mapping import prepare_state,pair_model
from cuprate_2d_tflo import initial_occupations,flo_reference,physical_observables

CAP=5
SHOTS=512
TOTAL=6144
T=.4
BOOTSTRAP=2000
SCREEN=np.array([.05,.05,.03])


def configurations():
    common=dict(steps=2,dt=.2,hopping_t=1.,t_prime_over_t=-.25,
                u_over_t=8.,chemical_potential=0.,shots=SHOTS)
    return (Cuprate2DConfig(lx=5,ly=5,holes=3,**common),
            Cuprate2DConfig(lx=6,ly=6,holes=4,**common))


def preparation(cfg,mask):
    mask=np.asarray(mask)
    if mask.shape!=(cfg.qubits,) or not np.all((mask==0)|(mask==1)):
        raise ValueError('Invalid preparation mask')
    circuit=QuantumCircuit(cfg.qubits)
    prepare_state(circuit,cfg)
    for q in np.flatnonzero(mask): circuit.x(int(q))
    return circuit


def records(layout72,masks):
    if len(layout72)!=72 or len(set(layout72))!=72:
        raise ValueError('Need original72-wire layout')
    if np.asarray(masks).shape!=(4,50): raise ValueError('Need four50-bit masks')
    def rec(setting,variant,width,mask,**extra):
        return dict(setting_id=setting,twirl_id=variant,width=width,shots=SHOTS,
                    readout_mask_little_endian=list(map(int,mask)),
                    physical_layout=list(layout72[:width]),**extra)
    targets=[]
    for setting,width,particles in [('prep5',50,22),('prep6',72,32)]:
        for v in (0,1):
            targets.append(rec(setting,v,width,[v]*width,role='preparation',
                               ideal_N=particles,T=0.,evolution=False))
    for v in range(4):
        targets.append(rec('flo5_T04',v,50,masks[v],role='dynamics',ideal_N=22,
                           T=T,U=0.,evolution=True,twirl_seed=202609060700+v))
    order=np.random.default_rng(202609060701).permutation(len(targets))
    calibrations=lambda block:[rec(f'cal{state}_{block}',0,72,[0]*72,
        role='calibration',state=state,block=block) for state in (0,1)]
    result=calibrations('start')+[targets[int(i)] for i in order]+calibrations('end')
    validate_records(result)
    return result


def validate_records(rows):
    if len(rows)!=12 or sum(r['shots'] for r in rows)!=TOTAL:
        raise ValueError('Wrong allocation')
    if any(r['shots']!=SHOTS for r in rows): raise ValueError('Shots changed')
    if Counter(r['role'] for r in rows)!=dict(calibration=4,preparation=4,dynamics=4):
        raise ValueError('Wrong roles')
    if len({(r['setting_id'],r['twirl_id']) for r in rows})!=12:
        raise ValueError('Duplicate record')
    for r in rows:
        w=r['width']; mask=np.asarray(r['readout_mask_little_endian'])
        if w not in (50,72) or mask.shape!=(w,) or not np.all((mask==0)|(mask==1)):
            raise ValueError('Width/mask mismatch')
        if len(r['physical_layout'])!=w or len(set(r['physical_layout']))!=w:
            raise ValueError('Invalid physical layout')
        if r['role']=='dynamics' and (w!=50 or r['U']!=0 or r['T']!=T or r['ideal_N']!=22):
            raise ValueError('Only U0 dynamics authorized')
        if r['role']=='preparation':
            if r['setting_id'] not in ('prep5','prep6') or r['evolution'] or r['T']!=0:
                raise ValueError('Preparation contains evolution')
            if r['ideal_N']!={50:22,72:32}[w] or r['twirl_id'] not in (0,1):
                raise ValueError('Wrong preparation target')
            if not np.all(mask==r['twirl_id']): raise ValueError('Changed preparation readout')
        if r['role']=='calibration' and (w!=72 or r['state'] not in (0,1) or np.any(mask)):
            raise ValueError('Invalid calibration')
    if [r['setting_id'] for r in rows[:2]+rows[-2:]]!=['cal0_start','cal1_start','cal0_end','cal1_end']:
        raise ValueError('Calibration bookends changed')
    for setting,count in [('prep5',2),('prep6',2),('flo5_T04',4)]:
        selected=[r for r in rows if r['setting_id']==setting]
        if sorted(r['twirl_id'] for r in selected)!=list(range(count)):
            raise ValueError('Missing variant')


def paulis_from_covariance(covariance):
    z=1-2*np.diag(covariance).real
    zz=z[::2]*z[1::2]-4*np.abs(covariance[::2,1::2].diagonal())**2
    return np.concatenate([z,zz])


def references(cfg5,cfg6):
    output={}
    for name,cfg in [('prep5',cfg5),('prep6',cfg6)]:
        occ=initial_occupations(cfg).astype(float); z=1-2*occ
        p=np.concatenate([z,z[::2]*z[1::2]])
        output[name]={'paulis':p.tolist(),'physical':physical_observables(p).tolist(),
            'N':int(occ.sum()),'N_up':int(occ[::2].sum()),'N_down':int(occ[1::2].sum()),
            'initial_bits_little_endian':occ.astype(int).tolist(),'exact_for':'product_preparation'}
    p,cov=flo_reference(cfg5,T)
    assert np.max(np.abs(cov@cov-cov))<1e-11 and abs(np.trace(cov).real-22)<1e-10
    h1=np.zeros((50,50),complex)
    for (a,b),c in pair_model(cfg5)[0].items(): h1[a,b]=h1[b,a]=c
    energies,vectors=np.linalg.eigh(h1)
    evolution=(vectors*np.exp(-1j*T*energies))@vectors.conj().T
    continuous=evolution@np.diag(initial_occupations(cfg5))@evolution.conj().T
    exact_p=paulis_from_covariance(continuous)
    convergence=[]
    for steps in (2,4,8,16):
        trial,_=flo_reference(replace(cfg5,steps=steps,dt=T/steps),T)
        delta=physical_observables(trial)-physical_observables(exact_p)
        convergence.append({'steps':steps,'RMS_charge_spin_doublon':np.sqrt(np.mean(delta**2,axis=0)).tolist()})
    output['flo5_T04']={'paulis':p.tolist(),'physical':physical_observables(p).tolist(),
        'N':22,'N_up':11,'N_down':11,'exact_for':'ideal_finite_two_step_U0_circuit',
        'continuous_paulis':exact_p.tolist(),'continuous_physical':physical_observables(exact_p).tolist(),
        'Trotter_convergence':convergence,'projector_error':float(np.max(np.abs(cov@cov-cov)))}
    return output


def corrected_paulis(means,mask,errors):
    means=np.asarray(means,float); mask=np.asarray(mask); errors=np.asarray(errors,float)
    width=len(mask)
    if means.shape[-1]!=width*3//2 or width%2 or errors.shape[-2:]!=(2,width):
        raise ValueError('Readout dimensions disagree')
    if not np.all((mask==0)|(mask==1)) or np.any(~np.isfinite(errors)) or np.any((errors<0)|(errors>1)):
        raise ValueError('Invalid readout model')
    e0,e1=errors[...,0,:],errors[...,1,:]
    a=(1-2*mask)*(e1-e0); b=1-e0-e1
    if np.any(b<=.1): raise ValueError('Ill-conditioned readout inverse')
    z=(means[...,:width]-a)/b
    zz=(means[...,width:]-a[...,::2]*means[...,1:width:2]
        -a[...,1::2]*means[...,:width:2]+a[...,::2]*a[...,1::2])/(b[...,::2]*b[...,1::2])
    return np.concatenate([z,zz],axis=-1)


def quota_summary(raw):
    keys=('usage_limit_seconds','usage_allocation_seconds','usage_consumed_seconds','usage_remaining_seconds')
    values={k:float(raw[k]) for k in keys if isinstance(raw.get(k),(int,float)) and not isinstance(raw.get(k),bool)}
    if any(not math.isfinite(v) or v<0 for v in values.values()): raise ValueError('Invalid quota values')
    if 'usage_remaining_seconds' not in values:
        limit=values.get('usage_limit_seconds',values.get('usage_allocation_seconds'))
        consumed=values.get('usage_consumed_seconds')
        if limit is not None and consumed is not None: values['usage_remaining_seconds']=max(0,limit-consumed)
    remaining=values.get('usage_remaining_seconds')
    if remaining is not None and remaining<CAP: raise ValueError('Reported remaining quota below5s')
    return {**values,'remaining_quota_reported':remaining is not None,
            'unknown_is_not_unlimited':True,'authorized_job_cap_seconds':CAP}


def budget_summary(execution):
    if not math.isfinite(execution) or execution<=0: raise ValueError('Invalid timing')
    result={'shot_execution_seconds':execution,'one_subjob_seconds':2+execution,
        'two_subjob_seconds':4+execution,'three_subjob_seconds':6+execution,
        'internal_subjob_count_known':False,'completion_guaranteed':False,
        'cap_seconds':CAP,'planning_headroom_seconds':.25}
    result['pass']=4+execution<=CAP-.25
    return result
