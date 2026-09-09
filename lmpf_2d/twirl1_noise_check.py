"""Post-hoc frozen-model prediction check using saved operators and archived shots."""
from pathlib import Path
import argparse,io,json,shutil,sys,time,unittest
import numpy as np
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from lmpf_2d.twirl1_hardware import CASES,checked_bundle,TESTS as OLD_TESTS
from lmpf_2d.single_twirl import read,write,moment_table,physical,pair_probabilities
from lmpf_2d.chain_contract import chain_expectation_zero
from lmpf_2d.tn_storage import load_tn
from lmpf_2d.model import digest
PARENT=ROOT/'results_cuprate_2d/lmpf_3x3_twirl1_hardware_2026-09-09_v1'
TESTS=OLD_TESTS+('test_lmpf_twirl1_noise_check',)
SHOTS=np.array([64,7,14])

def merge_strata(counts):
    c=np.asarray(counts)
    if c.ndim!=3 or c.shape[1:]!=(4,4) or not np.isfinite(c).all() or np.any(c<0):
        raise ValueError('Expected saved four-stratum counts')
    if not np.all(c.sum(2)==[43,21,7,14]) or not np.all(c==np.floor(c)):
        raise ValueError('Changed source bootstrap strata')
    return np.stack([c[:,0]+c[:,1],c[:,2],c[:,3]],axis=1)

def arm_means(counts,errors,masks):
    c=np.asarray(counts);m=np.asarray(masks)
    if c.ndim!=3 or c.shape[1:]!=(3,4) or not np.isfinite(c).all() or np.any(c<0):
        raise ValueError('Expected full-arm counts')
    if not np.all(c.sum(2)==SHOTS) or not np.all(c==np.floor(c)):
        raise ValueError('Wrong64/7/14 exposure')
    if m.shape!=(3,2) or not np.isin(m,[0,1]).all():raise ValueError('Invalid arm masks')
    e=np.broadcast_to(errors,(len(c),2,2))
    if not np.isfinite(e).all() or np.any(e<0) or np.any(e>=1):raise ValueError('Invalid calibration')
    return np.stack([np.einsum('rp,rpo->ro',c[:,a]/SHOTS[a],moment_table(e,m[a]))
                     for a in range(3)],axis=1)

def outside_marginal(interval,point):
    interval=np.asarray(interval);point=np.asarray(point)
    if interval.shape!=(2,*point.shape):raise ValueError('Wrong interval shape')
    return (point<interval[0])|(point>interval[1])

def run(out):
    start=time.monotonic()
    if out.exists():raise FileExistsError('Preserve previous diagnostic')
    out.mkdir(parents=True);(out/'source_snapshot').mkdir()
    names=['twirl1_noise_check.py','verify_twirl1_noise_check.py','twirl1_hardware.py',
        'single_twirl.py','verify_single_twirl.py','chain_contract.py','tn_storage.py','model.py']
    sources=[ROOT/'lmpf_2d'/name for name in names]+[ROOT/(name+'.py') for name in TESTS]
    sources += [PARENT/'NEXT_NOISE_MODEL_CHECK.md']
    for path in sources:shutil.copyfile(path,out/'source_snapshot'/path.name)
    stream=io.StringIO();suite=unittest.TestSuite()
    for name in TESTS:suite.addTests(unittest.defaultTestLoader.loadTestsFromName(name))
    tests=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    (out/'tests.txt').write_text(stream.getvalue(),encoding='utf-8')
    if not tests.wasSuccessful():raise RuntimeError('Tests failed')
    print('TESTS_PASSED',tests.testsRun,flush=True)
    parent_plan=read(PARENT/'plan.json');parent_manifest=read(PARENT/'sha256.json')
    for name,h in parent_manifest.items():
        if digest(PARENT/name)!=h:raise ValueError('Changed parent analysis artifact')
    audit=read(PARENT/'verification/verification.json')
    if audit['status']!='TWIRL1_HARDWARE_ASSIGNMENT_KKT_AUDIT_PASSED':
        raise ValueError('Parent audit missing')
    if parent_plan['twirl']!=1 or parent_plan['replicates']!=10000:
        raise ValueError('Wrong parent scope')
    predictions=np.empty((4,3));state_records=[];input_hashes={}
    for name in ('plan.json','sha256.json','selected_inputs.json','summary.json',
                 'bootstrap.npz','frozen_weights.json','verification/verification.json'):
        path=PARENT/name;input_hashes[str(path.relative_to(ROOT))]=digest(path)
    for column,(obs,name,low,high) in enumerate(CASES):
        folder=ROOT/'results_cuprate_2d'/name
        op,_,_=checked_bundle(folder)
        if (op['twirl'],op['observable'],op['job_id'])!=(1,obs,parent_plan['job_id']):
            raise ValueError('Wrong saved operator')
        for rel in ('plan.json','sha256.json',f'chi{high}.json','verification/verification.json'):
            input_hashes[str((folder/rel).relative_to(ROOT))]=digest(folder/rel)
        for arm in range(4):
            prefix=folder/'states'/f'obs{obs:02d}_chi{high}_arm{arm}'
            meta=read(folder/f'state_chi{high}_arm{arm}.json')
            if digest(prefix.with_suffix('.npz'))!=meta['npz_sha256'] or digest(prefix.with_suffix('.json'))!=meta['metadata_sha256']:
                raise ValueError('Changed model state')
            native=next(r for r in op['inputs'] if r['factor']==max(arm,1))
            sign=int(np.prod([1-2*native['mask'][int(q)] for q in op['support']]))
            if sign!=meta['unmask_sign']:raise ValueError('Operator mask mismatch')
            t0=time.monotonic();tn=load_tn(prefix)
            value=chain_expectation_zero(tn)
            predictions[arm,column]=value
            state_records.append({'observable':obs,'chi':high,'arm':arm,'factor':max(arm,1),
                'prefix':str(prefix.relative_to(ROOT)),'npz_sha256':meta['npz_sha256'],
                'metadata_sha256':meta['metadata_sha256'],'unmask_sign':sign,
                'mean':value,'contraction_and_load_seconds':time.monotonic()-t0})
            del tn
    model_pairs=np.stack([pair_probabilities(row) for row in predictions])
    model={'arms':['ideal_factor1','noisy_factor1','noisy_factor2','noisy_factor3'],
        'pauli_order':['Z_up','Z_down','ZZ'],'pauli_means':predictions.tolist(),
        'physical_means':physical(predictions).tolist(),'joint_probabilities_00_10_01_11':model_pairs.tolist(),
        'minimum_joint_probability_by_arm':model_pairs.min(1).tolist(),
        'maximum_absolute_pauli_by_arm':abs(predictions).max(1).tolist(),
        'local_probability_valid_by_arm':((model_pairs.min(1)>=-1e-10)&(model_pairs.max(1)<=1+1e-10)).tolist(),
        'operator_rescaled':False,'exact_F00_substituted_into_expectation':False,
        'state_preparation_applied_again':False,'noise_parameters_fitted':False,
        'records':state_records}
    write(out/'model_predictions.json',model)
    print('FROZEN_MODEL_PREDICTIONS_SAVED_BEFORE_COMPARISON',flush=True)
    # Keep the parent's paired strata/calibration draws, only aggregate43+21.
    inputs=read(PARENT/'selected_inputs.json');parent_summary=read(PARENT/'summary.json')
    counts=merge_strata(np.asarray(inputs['stratum_counts'])[None])
    errors=np.array(inputs['calibration_errors_posterior_mean'])
    masks=np.array(inputs['stratum_masks'])[[0,2,3]]
    point=arm_means(counts,errors[None],masks)[0]
    np.testing.assert_allclose(point[0],parent_summary['methods']['readout64']['paulis'],atol=1e-12)
    with np.load(PARENT/'bootstrap.npz',allow_pickle=False) as previous:
        sampled=merge_strata(previous['sampled_counts'])
        draws=previous['calibration_errors']
    boot=arm_means(sampled,draws,masks)
    fixed=arm_means(sampled,errors[None],masks)
    boot_phys=physical(boot);observed_phys=physical(point)
    delta=boot-predictions[None,1:,:]
    np.savez_compressed(out/'arm_bootstrap.npz',sampled_counts=sampled.astype(np.int16),
        calibration_errors=draws,pauli=boot,physical=boot_phys,
        pauli_fixed_calibration=fixed,pauli_minus_model=delta)
    interval=np.quantile(boot,[.025,.975],axis=0)
    outside=outside_marginal(interval,predictions[1:])
    physical_interval=np.quantile(boot_phys,[.025,.975],axis=0)
    phys_outside=outside_marginal(physical_interval,physical(predictions[1:]))
    arms=[]
    for a in range(3):
        arms.append({'factor':a+1,'shots':int(SHOTS[a]),'mask':masks[a].tolist(),
            'model_paulis':predictions[a+1].tolist(),'observed_readout_paulis':point[a].tolist(),
            'observed_pauli_sd':boot[:,a].std(0,ddof=1).tolist(),
            'pauli_percentile_interval':interval[:,a].tolist(),
            'observed_minus_model_paulis':(point[a]-predictions[a+1]).tolist(),
            'difference_percentile_interval':np.quantile(delta[:,a],[.025,.975],axis=0).tolist(),
            'model_outside_nominal_pauli_margins':outside[a].tolist(),
            'model_physical':physical(predictions[a+1]).tolist(),'observed_physical':observed_phys[a].tolist(),
            'observed_physical_sd':boot_phys[:,a].std(0,ddof=1).tolist(),
            'physical_percentile_interval':physical_interval[:,a].tolist(),
            'model_outside_nominal_physical_margins':phys_outside[a].tolist()})
    ref=np.array(parent_summary['reference_paulis'])
    plan={'schema':'twirl1-frozen-noise-arm-check-v1','job_id':parent_plan['job_id'],
        'backend':parent_plan['backend'],'twirl':1,'observables':[8,9,22],
        'shots':[64,7,14],'calibration_shots':128,'target_union':85,
        'replicates':10000,'bootstrap_seed':parent_plan['bootstrap_seed'],
        'reuse_existing_bootstrap':True,'factor1_bootstrap':'sum of saved43+21 strata, not a newly pooled resample',
        'posthoc_reused_data':True,'process_timeout_seconds':120,'new_qpu_seconds':0,'new_tn_states':0,
        'source_sha256':{str(p.relative_to(ROOT)):digest(p) for p in sources},
        'input_sha256':input_hashes}
    write(out/'plan.json',plan)
    summary={'status':'FROZEN_MODEL_ARM_DIAGNOSTIC_COMPLETE','arms':arms,
        'ideal_tn_paulis':predictions[0].tolist(),'exact_circuit_reference_paulis':ref.tolist(),
        'ideal_tn_minus_exact':(predictions[0]-ref).tolist(),
        'ideal_tn_physical':physical(predictions[0]).tolist(),'exact_reference_physical':physical(ref).tolist(),
        'model_joint_probability_valid':model['local_probability_valid_by_arm'],
        'noisy_pauli_margins_outside_count':int(outside.sum()),
        'noisy_physical_margins_outside_count':int(phys_outside.sum()),
        'shared_bootstrap_pauli_covariance':np.cov(boot.reshape(10000,9),rowvar=False,ddof=1).tolist(),
        'fixed_calibration_pauli_sd':fixed.std(0,ddof=1).tolist(),
        'tests_run':tests.testsRun,'seconds':time.monotonic()-start,
        'new_qpu_seconds':0,'new_tn_states':0,'model_fitted':False,
        'noise_model_validated':False,'causal_error_source_identified':False,'six_by_six_go':False,
        'uncertainty_scope':'Reused paired stratified bootstrap plus shared readout calibration. Unadjusted marginal95% intervals, not simultaneous tests; no guarantee at7 shots. Model/TN/coherent/drift/correlated-readout error not included.'}
    write(out/'summary.json',summary)
    write(out/'sha256.json',{str(p.relative_to(out)):digest(p) for p in sorted(out.rglob('*')) if p.is_file()})
    print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    if args.output.exists():p.error('Preserve earlier diagnostic')
    try:
        with threadpool_limits(limits=1):run(args.output)
    except Exception as error:
        if args.output.exists():write(args.output/'failure.json',{'type':type(error).__name__,'reason':str(error),'new_qpu_seconds':0})
        raise
