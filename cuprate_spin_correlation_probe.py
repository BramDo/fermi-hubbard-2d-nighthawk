"""Offline connected-spin probe; no provider imports or hardware path."""
import os,time
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key]='1'
import numpy as np
from verify_classical_chi64_continuation import left_step,load_arrays

Z=np.array([1.,-1.])

def spin_from_z(single,second):
    single=np.asarray(single,float); second=np.asarray(second,float)
    width=len(single)
    if width%2 or second.shape!=(width,width): raise ValueError('Even mode count and square Z moments required')
    weights=np.zeros((width//2,width))
    for i in range(width//2): weights[i,2*i:2*i+2]=(-.5,.5)
    mean=weights@single; moment=weights@second@weights.T
    connected=moment-np.outer(mean,mean)
    onsite=second[np.arange(0,width,2),np.arange(1,width,2)]
    physical=np.stack((1-(single[::2]+single[1::2])/2,mean,
        (1-single[::2]-single[1::2]+onsite)/4),axis=-1)
    return mean,moment,connected,physical

def mps_moments(arrays,deadline=None,progress=None):
    n=len(arrays); left=[np.ones((1,1),complex)]
    for a in arrays: left.append(left_step(left[-1],a))
    norm=left[-1][0,0]
    if abs(norm.imag)>1e-10 or norm.real<=0: raise ValueError('Invalid norm')
    right=[None]*(n+1); right[-1]=np.ones((1,1),complex)
    for i in reversed(range(n)):
        a=arrays[i]
        right[i]=np.einsum('arp,bsp,rs->ab',a,a.conj(),right[i+1],optimize=True)
    singles=np.empty(n,complex); pairs=np.eye(n,dtype=complex)
    for i in range(n):
        if deadline is not None and time.perf_counter()>deadline: raise TimeoutError('Correlation deadline')
        inserted=left_step(left[i],arrays[i],Z)
        singles[i]=np.sum(inserted*right[i+1])/norm
        propagated=inserted
        for j in range(i+1,n):
            pair=left_step(propagated,arrays[j],Z)
            pairs[i,j]=pairs[j,i]=np.sum(pair*right[j+1])/norm
            propagated=left_step(propagated,arrays[j])
        if progress and (i+1)%12==0: progress(i+1,n)
    if max(np.max(abs(singles.imag)),np.max(abs(pairs.imag)))>1e-9: raise ValueError('Complex diagonal moments')
    return float(norm.real),singles.real,pairs.real

def dense_z_moments(state,little_endian=True):
    state=np.asarray(state,complex).reshape(-1)
    n=int(round(np.log2(len(state))))
    if len(state)!=2**n or n>18: raise ValueError('Dense check restricted to at most 18 qubits')
    norm=float(np.vdot(state,state).real)
    p=abs(state)**2/norm
    powers=np.arange(n) if little_endian else np.arange(n-1,-1,-1)
    bits=((np.arange(len(state))[:,None]>>powers)&1).astype(float)
    z=1-2*bits
    return norm,p@z,(z.T*p)@z

def flo_spin_moments(cfg,T):
    from cuprate_2d_tflo import flo_reference,physical_observables
    paulis,cov=flo_reference(cfg,T)
    density=cov.diagonal().real
    occupancy_cov=np.diag(density)-abs(cov)**2
    weights=np.zeros((cfg.sites,cfg.qubits))
    for i in range(cfg.sites): weights[i,2*i:2*i+2]=(1.,-1.)
    mean=weights@density; connected=weights@occupancy_cov@weights.T
    second=connected+np.outer(mean,mean)
    return mean,second,connected,physical_observables(paulis)

def mixture(rows):
    means=np.mean([r[0] for r in rows],axis=0)
    seconds=np.mean([r[1] for r in rows],axis=0)
    physical=np.mean([r[3] for r in rows],axis=0)
    return means,seconds,seconds-np.outer(means,means),physical

def invariant_checks(row):
    mean,second,cov,physical=row
    checks={'symmetry_max_abs':float(np.max(abs(cov-cov.T))),
        'minimum_covariance_eigenvalue':float(np.linalg.eigvalsh(cov).min()),
        'total_spin_variance':float(cov.sum()),
        'fixed_spin_row_sum_max_abs':float(np.max(abs(cov.sum(axis=1)))),
        'onsite_variance_identity_max_abs':float(np.max(abs(np.diag(cov)-(physical[:,0]-2*physical[:,2]-mean**2)))),
        'N':float(physical[:,0].sum()),'total_spin':float(mean.sum())}
    if checks['symmetry_max_abs']>1e-9 or checks['minimum_covariance_eigenvalue'] < -1e-8 or checks['onsite_variance_identity_max_abs']>1e-9:
        raise ArithmeticError('Spin moment identity/positivity failure')
    return checks

def distances(lx,ly):
    n=lx*ly
    return np.array([[abs(i%lx-j%lx)+abs(i//lx-j//lx) for j in range(n)] for i in range(n)])

def compare(left,right,lx,ly):
    delta=np.asarray(left)-np.asarray(right); distance=distances(lx,ly)
    upper=np.triu(np.ones_like(delta,dtype=bool),1)
    masks={'all_offdiagonal':upper,**{f'distance_{d}':upper&(distance==d) for d in (1,2,3)}}
    result={}
    for name,mask in masks.items():
        values=delta[mask]
        if not len(values): continue
        result[name]={'pairs':int(mask.sum()),'rms':float(np.sqrt(np.mean(values**2))),
            'max_abs':float(np.max(abs(values))),'mean_signed':float(np.mean(values))}
    return result

def serialize(row):
    return dict(spin_mean=row[0].tolist(),spin_second=row[1].tolist(),connected=row[2].tolist(),
        physical_charge_spin_doublon=row[3].tolist(),invariants=invariant_checks(row))
