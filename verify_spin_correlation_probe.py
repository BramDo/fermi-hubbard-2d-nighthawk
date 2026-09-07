"""Independent site-probability and Quimb-operator checks of the probe."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key]='1'
import hashlib,json,time
from pathlib import Path
import numpy as np
import quimb.tensor as qtn
from verify_classical_chi64_continuation import load_arrays

ROOT=Path(__file__).resolve().parent
RUN=ROOT/'results_cuprate_2d/spin_correlations_T04_2026-09-06_v1'
def read(path): return json.loads(path.read_text())
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):
    with path.open('x',encoding='utf-8') as f:
        json.dump(value,f,indent=2,allow_nan=False); f.write('\n')

def main():
    begun=time.perf_counter()
    if (RUN/'independent_verification.json').exists(): raise FileExistsError('Preserve previous verification')
    archive=read(RUN/'analysis_sha256.json'); plan=read(RUN/'plan.json')
    for name,h in archive.items(): assert digest(RUN/name)==h,name
    for name,h in plan['inputs_sha256'].items(): assert digest(ROOT/name)==h,name
    with np.load(RUN/'exact_3x3_state.npz',allow_pickle=False) as packed: state=packed['state']
    probability=abs(state)**2; probability/=probability.sum()
    bits=((np.arange(len(state))[:,None]>>np.arange(18))&1).astype(float)
    m=bits[:,::2]-bits[:,1::2]
    mean=probability@m; second=(m.T*probability)@m
    exact=read(RUN/'3x3_exact.json')
    exact_error=float(np.max(abs(second-np.outer(mean,mean)-np.array(exact['connected']))))
    assert exact_error<1e-12
    folder=ROOT/'results_cuprate_2d/classical_full_6x6_mps_T04_chi64_v1/6x6_chi64_threads1'
    arrays=load_arrays(folder)
    raw=[arrays[0][0,:,:]]+arrays[1:-1]+[arrays[-1][:,0,:]]
    psi=qtn.MatrixProductState(raw,shape='lrp')
    M=np.diag([0.,-1.,1.,0.]); MM=np.kron(M,M)
    selected=[(0,1),(0,2),(0,3),(7,14),(14,21)]
    sites=sorted({i for pair in selected for i in pair})
    terms={(2*i,2*i+1):M for i in sites}
    terms.update({(2*i,2*i+1,2*j,2*j+1):MM for i,j in selected})
    values=psi.compute_local_expectation_canonical(terms,return_all=True,normalized=True,inplace=False)
    stored=read(RUN/'6x6_chi64.json'); independent=[]; qerror=0.
    for i,j in selected:
        a=complex(values[2*i,2*i+1]); b=complex(values[2*j,2*j+1])
        p=complex(values[2*i,2*i+1,2*j,2*j+1]); value=p-a*b
        assert max(abs(a.imag),abs(b.imag),abs(p.imag))<1e-11
        qerror=max(qerror,abs(value.real-stored['connected'][i][j]))
        independent.append(dict(site_i=i,site_j=j,connected=value.real))
    assert qerror<1e-10
    mixture_error=0.; between_time={}
    for size in (3,6):
        data=read(RUN/f'{size}x{size}_FLO.json')
        means=np.array([r['spin_mean'] for r in data['training']])
        conditional=np.mean([r['connected'] for r in data['training']],axis=0)
        between=(means-means.mean(0)).T@(means-means.mean(0))/6
        mixture_error=max(mixture_error,float(np.max(abs(conditional+between-np.array(data['mean']['connected'])))))
        between_time[f'{size}x{size}_max_abs_between_time_covariance']=float(np.max(abs(between)))
    assert mixture_error<1e-12
    report=dict(status='PASS',exact_3x3_direct_site_probability_max_abs=exact_error,
        six_by_six_Quimb_four_mode_operator_max_abs=qerror,independent_pairs=independent,
        total_covariance_mixture_identity_max_abs=mixture_error,between_time_covariance=between_time,
        old_inputs_sha256_verified=len(plan['inputs_sha256']),analysis_hashes_verified=len(archive),
        source_sha256=digest(Path(__file__)),verification_seconds=time.perf_counter()-begun,
        note='Verifies extraction and mixture arithmetic, NOT chi64 accuracy or quantum advantage.')
    save(RUN/'independent_verification.json',report)
    print(json.dumps(report),flush=True)

if __name__=='__main__': main()
