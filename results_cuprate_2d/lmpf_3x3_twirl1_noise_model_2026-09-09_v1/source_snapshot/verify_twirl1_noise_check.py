"""Independent raw-TN, assignment-inverse and seed audit of frozen arm predictions."""
from pathlib import Path
import argparse,json,sys,time
import numpy as np
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from lmpf_2d.model import digest
from lmpf_2d.tn_storage import load_tn,expectation_zero
from lmpf_2d.verify_single_twirl import central_bits,occupation_values

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def assignment_means(counts,errors,masks):
    n=len(counts);e=np.broadcast_to(errors,(n,2,2))
    bits=np.array([[i%2,i//2] for i in range(4)])
    assignment=np.ones((n,4,4))
    for true in range(4):
        for measured in range(4):
            for q in range(2):
                p=e[:,0,q] if bits[true,q]==0 else 1-e[:,1,q]
                assignment[:,true,measured]*=p if bits[measured,q] else 1-p
    probabilities=counts/np.array([64,7,14])[None,:,None]
    corrected=np.linalg.solve(assignment.transpose(0,2,1),probabilities.transpose(0,2,1))
    means=[]
    for arm in range(3):
        z=1-2*(bits ^ np.asarray(masks[arm],dtype=int))
        means.append(corrected[:,:,arm]@np.column_stack([z,z[:,0]*z[:,1]]))
    return np.stack(means,axis=1)

def pairs(paulis):
    z,d,zz=np.asarray(paulis).T
    return np.stack([1+z+d+zz,1-z+d-zz,1+z-d-zz,1-z-d+zz],axis=-1)/4

def verify(out):
    start=time.monotonic();dest=out/'verification';dest.mkdir(exist_ok=False)
    plan,summary,model=[read(out/name) for name in ('plan.json','summary.json','model_predictions.json')]
    if (plan['schema'],plan['twirl'],plan['observables'],plan['shots'])!=(
            'twirl1-frozen-noise-arm-check-v1',1,[8,9,22],[64,7,14]):
        raise ValueError('Wrong diagnostic scope')
    if (plan['replicates'],plan['bootstrap_seed'],plan['new_qpu_seconds'],plan['new_tn_states'])!=(10000,2026090918,0,0):
        raise ValueError('Changed bootstrap or computation scope')
    if not (plan['reuse_existing_bootstrap'] and plan['posthoc_reused_data']):
        raise ValueError('This is not independent held-out data')
    if any(model[k] for k in ('operator_rescaled','exact_F00_substituted_into_expectation',
                              'state_preparation_applied_again','noise_parameters_fitted')):
        raise ValueError('Modified model functional')
    for name,h in read(out/'sha256.json').items():
        if digest(out/name)!=h:raise ValueError('Changed result '+name)
    for name,h in plan['source_sha256'].items():
        if digest(ROOT/name)!=h or digest(out/'source_snapshot'/Path(name).name)!=h:
            raise ValueError('Changed source '+name)
    for name,h in plan['input_sha256'].items():
        if digest(ROOT/name)!=h:raise ValueError('Changed source input '+name)
    parent=ROOT/'results_cuprate_2d/lmpf_3x3_twirl1_hardware_2026-09-09_v1'
    inputs=read(parent/'selected_inputs.json')
    parent_audit=read(parent/'verification/verification.json')
    if parent_audit['status']!='TWIRL1_HARDWARE_ASSIGNMENT_KKT_AUDIT_PASSED':
        raise ValueError('Missing parent verification')
    archive=ROOT/'results_cuprate_2d/hardware_readout_cz_folding_3x3_2026-09-06'
    raw=read(archive/'raw_bitstrings.json');hp=read(archive/'plan.json')
    if raw['job_id']!=plan['job_id'] or hp['backend']!=plan['backend']:
        raise ValueError('Wrong hardware job')
    for rec in inputs['target_records']+inputs['calibration_records']:
        candidates=[r for r in raw['records'] if (r['setting_id'],r['twirl_id'])==(rec['setting_id'],rec['twirl_id'])]
        if len(candidates)!=1 or candidates[0]!=rec:raise ValueError('Changed original bitstrings')
    targets=inputs['target_records']
    for rec,f,n in zip(targets,(1,2,3),(64,7,14)):
        if rec['factor']!=f or rec['twirl_id']!=1 or len(rec['bitstrings'])!=n:
            raise ValueError('Wrong target arm')
    model_values=np.empty((4,3));seen=set();contractions=[]
    folders={8:'lmpf_3x3_twirl1_zup_2026-09-09_v1',
             9:'lmpf_3x3_twirl1_zdown_2026-09-09_v1',
             22:'lmpf_3x3_twirl1_zz_completed_2026-09-09_v1'}
    for rec in model['records']:
        obs,arm=rec['observable'],rec['arm'];key=(obs,arm)
        if obs not in folders or arm not in range(4) or key in seen:raise ValueError('Duplicate/wrong model state')
        seen.add(key);column=[8,9,22].index(obs);chi=256 if obs==22 else 128
        folder=ROOT/'results_cuprate_2d'/folders[obs]
        expected=folder/'states'/f'obs{obs:02d}_chi{chi}_arm{arm}'
        prefix=ROOT/rec['prefix']
        if prefix!=expected or rec['chi']!=chi or rec['factor']!=max(arm,1):
            raise ValueError('Wrong state binding')
        op=read(folder/'plan.json');meta=read(folder/f'state_chi{chi}_arm{arm}.json')
        if (op['twirl'],op['observable'],op['job_id'])!=(1,obs,plan['job_id']):
            raise ValueError('Wrong operator scope')
        native=next(r for r in op['inputs'] if r['factor']==max(arm,1))
        target=targets[max(arm,1)-1]
        if target['readout_mask_little_endian']!=native['mask']:raise ValueError('Target mask mismatch')
        sign=int(np.prod([1-2*native['mask'][q] for q in op['support']]))
        if sign!=rec['unmask_sign'] or sign!=meta['unmask_sign']:raise ValueError('Wrong mask sign')
        for suffix,keyname in (('.npz','npz_sha256'),('.json','metadata_sha256')):
            if digest(prefix.with_suffix(suffix))!=rec[keyname] or rec[keyname]!=meta[keyname]:
                raise ValueError('Changed saved operator')
        t0=time.monotonic()
        value=expectation_zero(load_tn(prefix)) # Generic raw TN + local[1,0,0,1], not chain implementation.
        model_values[arm,column]=value
        np.testing.assert_allclose(value,rec['mean'],atol=1e-10,rtol=0)
        contractions.append({'observable':obs,'arm':arm,'value':value,'seconds':time.monotonic()-t0})
    if len(seen)!=12:raise ValueError('Incomplete model arms')
    np.testing.assert_allclose(model_values,model['pauli_means'],atol=1e-10,rtol=0)
    model_phys=occupation_values(model_values);joint=pairs(model_values)
    for name,value in (('physical_means',model_phys),('joint_probabilities_00_10_01_11',joint),
            ('minimum_joint_probability_by_arm',joint.min(1)),
            ('maximum_absolute_pauli_by_arm',abs(model_values).max(1))):
        np.testing.assert_allclose(value,model[name],atol=1e-10,rtol=0)
    valid=(joint.min(1)>=-1e-10)&(joint.max(1)<=1+1e-10)
    np.testing.assert_array_equal(valid,model['local_probability_valid_by_arm'])
    np.testing.assert_array_equal(valid,summary['model_joint_probability_valid'])
    order=np.random.default_rng(2026090917).permutation(64)
    bits=[central_bits(r) for r in targets]
    groups=[bits[0][order[:43]],bits[0][order[43:]],bits[1],bits[2]]
    patterns=np.array([[i%2,i//2] for i in range(4)])
    strata=np.array([[np.all(g==p,axis=1).sum() for p in patterns] for g in groups])
    full=np.array([[np.all(g==p,axis=1).sum() for p in patterns] for g in bits])
    np.testing.assert_array_equal(strata,inputs['stratum_counts'])
    np.testing.assert_array_equal(full,np.stack([strata[0]+strata[1],strata[2],strata[3]]))
    masks=np.array([r['readout_mask_little_endian'][8:10] for r in targets])
    np.testing.assert_array_equal(masks[[0,0,1,2]],inputs['stratum_masks'])
    cal=inputs['calibration_records']
    if [r['state'] for r in cal]!=[0,1] or [len(r['bitstrings']) for r in cal]!=[64,64]:
        raise ValueError('Wrong calibration')
    cal0,cal1=[central_bits(r) for r in cal]
    cal_counts=np.array([cal0.sum(0),(1-cal1).sum(0)])
    errors=(cal_counts+.5)/65
    np.testing.assert_array_equal(cal_counts,inputs['calibration_error_counts'])
    np.testing.assert_array_equal(errors,inputs['calibration_errors_posterior_mean'])
    n=10000;rng=np.random.default_rng(2026090918)
    draws=rng.beta(cal_counts+.5,64-cal_counts+.5,size=(n,2,2))
    old_counts=np.stack([rng.multinomial(size,strata[g]/size,size=n) for g,size in enumerate((43,21,7,14))],axis=1)
    with np.load(parent/'bootstrap.npz',allow_pickle=False) as previous:
        np.testing.assert_array_equal(old_counts,previous['sampled_counts'])
        np.testing.assert_array_equal(draws,previous['calibration_errors'])
    sampled=np.stack([old_counts[:,0]+old_counts[:,1],old_counts[:,2],old_counts[:,3]],axis=1)
    boot=assignment_means(sampled,draws,masks);boot_phys=occupation_values(boot)
    fixed=assignment_means(sampled,errors[None],masks)
    point=assignment_means(full[None],errors[None],masks)[0];point_phys=occupation_values(point)
    delta=boot-model_values[None,1:,:];discrepancy={}
    with np.load(out/'arm_bootstrap.npz',allow_pickle=False) as saved:
        np.testing.assert_array_equal(sampled,saved['sampled_counts'])
        np.testing.assert_array_equal(draws,saved['calibration_errors'])
        for key,value in (('pauli',boot),('physical',boot_phys),('pauli_fixed_calibration',fixed),('pauli_minus_model',delta)):
            discrepancy['maximum_'+key+'_error']=float(abs(value-saved[key]).max())
            np.testing.assert_allclose(value,saved[key],atol=1e-10,rtol=0)
    pi=np.quantile(boot,[.025,.975],axis=0);qi=np.quantile(boot_phys,[.025,.975],axis=0)
    po=(model_values[1:]<pi[0])|(model_values[1:]>pi[1])
    qo=(model_phys[1:]<qi[0])|(model_phys[1:]>qi[1])
    for a,rec in enumerate(summary['arms']):
        if rec['factor']!=a+1 or rec['shots']!=[64,7,14][a]:raise ValueError('Wrong arm summary')
        np.testing.assert_array_equal(rec['mask'],masks[a])
        for key,value in (
            ('model_paulis',model_values[a+1]),('observed_readout_paulis',point[a]),
            ('observed_pauli_sd',boot[:,a].std(0,ddof=1)),('pauli_percentile_interval',pi[:,a]),
            ('observed_minus_model_paulis',point[a]-model_values[a+1]),
            ('difference_percentile_interval',np.quantile(delta[:,a],[.025,.975],axis=0)),
            ('model_physical',model_phys[a+1]),('observed_physical',point_phys[a]),
            ('observed_physical_sd',boot_phys[:,a].std(0,ddof=1)),('physical_percentile_interval',qi[:,a])):
            np.testing.assert_allclose(value,rec[key],atol=1e-10,rtol=0)
        np.testing.assert_array_equal(po[a],rec['model_outside_nominal_pauli_margins'])
        np.testing.assert_array_equal(qo[a],rec['model_outside_nominal_physical_margins'])
    ref=np.array(hp['target']['reference'])[[8,9,22]]
    for key,value in (('ideal_tn_paulis',model_values[0]),('exact_circuit_reference_paulis',ref),
            ('ideal_tn_minus_exact',model_values[0]-ref),('ideal_tn_physical',model_phys[0]),
            ('exact_reference_physical',occupation_values(ref)),
            ('shared_bootstrap_pauli_covariance',np.cov(boot.reshape(n,9),rowvar=False,ddof=1)),
            ('fixed_calibration_pauli_sd',fixed.std(0,ddof=1))):
        np.testing.assert_allclose(value,summary[key],atol=1e-10,rtol=0)
    if (summary['noisy_pauli_margins_outside_count'],summary['noisy_physical_margins_outside_count'])!=(int(po.sum()),int(qo.sum())):
        raise ValueError('Wrong marginal flags')
    if any(summary[k] for k in ('new_qpu_seconds','new_tn_states','model_fitted','noise_model_validated',
                               'causal_error_source_identified','six_by_six_go')):
        raise ValueError('Unsupported causal or validation claim')
    report={'status':'FROZEN_MODEL_RAW_TN_AND_ASSIGNMENT_AUDIT_PASSED',
        'saved_operator_means_verified':12,'bootstrap_replicates_replayed':10000,
        'maximum_model_contraction_difference':float(abs(model_values-model['pauli_means']).max()),
        **discrepancy,'full64_7_14_arm_counts_verified':True,'source_and_input_hashes_verified':True,
        'shared_calibration_verified':True,'no_model_rescaling_or_clipping':True,
        'contractions':contractions,'new_qpu_seconds':0,'new_tn_states':0,
        'noise_model_validated':False,'seconds':time.monotonic()-start}
    with (dest/'verification.json').open('x') as f:
        json.dump(report,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(report),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path)
    with threadpool_limits(limits=1):verify(p.parse_args().output)
