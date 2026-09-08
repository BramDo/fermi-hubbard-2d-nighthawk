"""Independent saved-data audit of the native 3x3 application and its no-go gate."""
from pathlib import Path
import argparse,json,sys,time,io,unittest
import numpy as np
from qiskit import qpy
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from lmpf_2d.model import digest,FrozenSurrogate
from lmpf_2d.operators import compile_steps,fuse_steps,evolve_tn
from lmpf_2d.archive_3x3 import active_circuit

def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def verify(folder):
    dest=folder/'verification'
    if dest.exists():raise FileExistsError('Preserve earlier verification')
    dest.mkdir();started=time.monotonic();plan=read(folder/'plan.json');summary=read(folder/'summary.json')
    for relative,h in read(folder/'sha256.json').items():
        if digest(folder/relative)!=h:raise ValueError(f'Changed result: {relative}')
    for relative,h in plan['source_sha256'].items():
        if digest(ROOT/relative)!=h or digest(folder/'source_snapshot'/Path(relative).name)!=h:raise ValueError('Changed implementation or snapshot')
    for relative,h in plan['input_sha256'].items():
        if digest(ROOT/relative)!=h:raise ValueError('Changed hardware input')
    archive=ROOT/plan['archive'];original=read(archive/'plan.json');raw=read(archive/'raw_bitstrings.json')
    native=read(folder/'native_inputs.json');overlaps=read(folder/'overlaps.json');fits=read(folder/'coefficients.json')
    maximum_gram_error=0.;maximum_gradient=0.;state_count=0;max_bound=0.;min_gap=1.
    def state(index,scale):
        nonlocal max_bound,min_gap
        with np.load(folder/'states'/f'record_{index:02d}_rate_{scale:.1f}.npz') as data:
            factors=data['local'];amp=data['amplitude'];bound=data['truncation_bound'];gap=data['minimum_schmidt_gap']
        np.testing.assert_allclose(np.linalg.norm(factors,axis=2),1.,atol=1e-12)
        if not np.isfinite(amp).all():raise ValueError('Invalid saved amplitudes')
        max_bound=max(max_bound,float(bound.max()));min_gap=min(min_gap,float(gap.min()))
        return factors,amp
    for scale in (.7,1.,1.3):
        groups=[[item for item in native if item['factor']==1]]+[[item for item in native if item['factor']==f] for f in (1,2,3)]
        states=[state(item['record_index'],0. if group==0 else scale) for group,items in enumerate(groups) for item in items]
        local=np.array([s[0] for s in states]);amp=np.array([s[1] for s in states]);average=np.kron(np.eye(4),np.ones((1,8))/8)
        alt=[]
        for observable in range(27):
            gram=np.outer(amp[:,observable],amp[:,observable])
            for q in range(18):gram*=local[:,observable,q,:]@local[:,observable,q,:].T
            alt.append(average@gram@average.T)
        alt=np.array(alt);f=np.array(overlaps[str(scale)])
        maximum_gram_error=max(maximum_gram_error,float(np.max(abs(alt-f))))
        np.testing.assert_allclose(alt,f,atol=1e-12)
    for name,records in fits.items():
        scale=.7 if name.endswith('0.7') else 1.3 if name.endswith('1.3') else 1.
        for i,fit in enumerate(records):
            f=np.array(overlaps[str(scale)][i]);c=np.array(fit['coefficients'])
            if abs(c.sum()-1)>1e-9:raise ValueError('Coefficient sum not one')
            if np.linalg.eigvalsh(f).min() < -1e-9:raise ValueError('Non-PSD Gram')
            gradient=f[1:,1:]@c-f[1:,0]+fit['ridge']*c
            error=float(np.max(abs(gradient-gradient.mean())));maximum_gradient=max(maximum_gradient,error)
            if error>1e-7:raise ValueError('Optimizer stationarity failed')
    # Reconstruct moments with explicit bit-order/readout equations, without
    # calling the production feature or physical-transform routines.
    keyed={(r['setting_id'],r['twirl_id']):r for r in raw['records']}
    def bits(record):return np.array([[int(s[17-q]) for q in range(18)] for s in record['bitstrings']])
    cal0=bits(keyed['readout_all0',0]);cal1=bits(keyed['readout_all1',0])
    e0=(cal0.sum(0)+.5)/65;e1=((1-cal1).sum(0)+.5)/65;alpha=1-e0-e1;beta=e1-e0
    arms=[];baseline=np.zeros(27)
    for factor in (1,2,3):
        avg=np.zeros(27)
        for twirl in range(8):
            r=keyed[f'U8_T04_factor{factor}',twirl];z=(1-2*bits(r)-beta)/alpha;z*=1-2*np.array(r['readout_mask_little_endian'])
            values=np.concatenate([z,z[:,::2]*z[:,1::2]],axis=1)
            if factor==1:baseline+=values.mean(0)/8;values=values[:43]
            avg+=values.mean(0)/8
        arms.append(avg)
    maximum_sample_error=0.;names=list(summary['methods'])
    with np.load(folder/'bootstrap_rmse.npz') as data:boot=data['rmse']
    for name,item in summary['methods'].items():
        if name=='readout':value=baseline
        else:
            if name=='zne_linear':weights=np.tile([4/3,1/3,-2/3],(27,1))
            elif name=='zne_richardson':weights=np.tile([3.,-3.,1.],(27,1))
            else:weights=np.array([fit['coefficients'] for fit in fits[name]])
            value=sum(weights[:,arm]*arms[arm] for arm in range(3))
        maximum_sample_error=max(maximum_sample_error,float(np.max(abs(value-item['pauli_means']))))
        np.testing.assert_allclose(value,item['pauli_means'],atol=1e-12)
        zu=value[:18:2];zd=value[1:18:2];zz=value[18:]
        physical=np.r_[1-(zu+zd)/2,(zd-zu)/2,(1-zu-zd+zz)/4]
        np.testing.assert_allclose(physical,item['physical_means'],atol=1e-12)
        error=np.sqrt(np.mean((physical-np.array(summary['ideal_physical'])).reshape(3,9)**2,axis=1))
        np.testing.assert_allclose(error,item['rmse_charge_spin_doublon'],atol=1e-12)
    for base,comparison in summary['comparisons'].items():
        difference=boot[:,names.index(base)]-boot[:,names.index('lmpf_ridge')]
        np.testing.assert_allclose(np.quantile(difference,[.025,.975],axis=0),comparison['paired_interval'],atol=1e-12)
    # Native-scale cross-check: quimb D2BP chi=1, independent of the batched
    # SVD implementation, for the first Z operator of the actual 18-wire circuit.
    index=next(item['record_index'] for item in native if item['factor']==1 and item['twirl']==0)
    with (archive/'provider_inputs'/f'circuit_{index:03d}.qpy').open('rb') as f:qc=active_circuit(qpy.load(f)[0],plan['physical_layout'])
    profile=FrozenSurrogate(archive/'live_backend_properties.json',plan['physical_layout'])
    steps=fuse_steps(compile_steps(qc,profile.rate));edges=sorted({tuple(sorted(step.qubits)) for step in steps if len(step.qubits)==2})
    tn,info=evolve_tn(18,edges,{0:'Z'},steps,1.,chi=1,deadline=time.monotonic()+300)
    local,amp=state(index,1.);left=local[0];right=[];qamp=10**float(tn.exponent)
    for q in range(18):
        tensor=tn[f'I{q}'];vec=tensor.data.reshape(4)
        # All internal axes have dimension one at chi=1.
        norm=np.linalg.norm(vec);qamp*=norm;right.append(vec/norm)
    qamp*=1-2*original['records'][index]['readout_mask_little_endian'][0]
    right=np.array(right);inner=float(amp[0]*qamp*np.prod(np.sum(left*right,axis=1)))
    squared_distance=float(amp[0]**2+qamp**2-2*inner)
    if abs(squared_distance)>1e-10:raise ValueError(f'Native chi=1 quimb disagreement: norm-squared {squared_distance}')
    if info['bp_nonconverged_updates']:raise ValueError('Native chi=1 BP failed convergence')
    report={'status':'VERIFIED_3X3_EXPLORATORY_APPLICATION_NOT_ACCEPTED_FOR_6X6',
        'maximum_gram_reconstruction_error':maximum_gram_error,'maximum_optimizer_projected_gradient':maximum_gradient,
        'maximum_raw_sample_reconstruction_error':maximum_sample_error,'native_quimb_chi1_squared_distance':squared_distance,
        'native_quimb_bp_nonconverged_updates':info['bp_nonconverged_updates'],
        'maximum_accumulated_truncation_bound':max_bound,'minimum_schmidt_relative_gap':min_gap,
        'states_saved':len(list((folder/'states').glob('*.npz'))),'physical_observables':27,
        'six_by_six_started':False,'new_qpu_seconds':0,'verification_source_sha256':digest(Path(__file__)),
        'seconds':time.monotonic()-started,'scope':'Software, native-chi1 and saved-evidence checks; not a noise-model or higher-bond convergence certificate.'}
    (dest/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('folder',type=Path);args=p.parse_args()
    with threadpool_limits(limits=1):verify(args.folder)
