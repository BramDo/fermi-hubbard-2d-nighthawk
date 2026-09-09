"""Matched archived twirl1 central hardware comparison, with no new QPU."""
from pathlib import Path
import argparse,io,json,shutil,sys,time,unittest
import numpy as np
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from lmpf_2d.archive_3x3 import ARCHIVE
from lmpf_2d.hardware_inputs import decode
from lmpf_2d.model import digest
from lmpf_2d.single_twirl import (moment_table,physical,pair_probabilities,counts4,
    subset_indices,SIZES,REPLICATES,SUBSET_SEED,BOOT_SEED,read,write)
from lmpf_2d.shot_aware import variance_penalties,solve_weights,apply_weights
from lmpf_2d.resume_twirl1_zz import TESTS as OLD_TESTS
from scripts.restore_archives import safe_path,run as restore_run

CASES=[(8,'lmpf_3x3_twirl1_zup_2026-09-09_v1',64,128),
       (9,'lmpf_3x3_twirl1_zdown_2026-09-09_v1',64,128),
       (22,'lmpf_3x3_twirl1_zz_completed_2026-09-09_v1',128,256)]
METHODS=['raw64','readout64','zne_matched','lmpf_shot_aware']
TESTS=OLD_TESTS+('test_lmpf_twirl1_hardware',)

def baseline_batch(counts,errors,masks):
    counts=np.asarray(counts)
    if counts.ndim!=3 or counts.shape[1:]!=(4,4) or not np.isfinite(counts).all() or np.any(counts<0):
        raise ValueError('Expected nonnegative replicate/stratum/outcome counts')
    if not np.all(counts.sum(2)==SIZES) or not np.all(counts==np.floor(counts)):
        raise ValueError('Changed integer shot budget')
    masks=np.asarray(masks)
    if masks.shape!=(4,2) or not np.isin(masks,[0,1]).all() or not np.array_equal(masks[0],masks[1]):
        raise ValueError('Invalid masks or different factor1 stratum masks')
    errors=np.broadcast_to(errors,(len(counts),2,2))
    if not np.isfinite(errors).all() or np.any(errors<0) or np.any(errors>=1):
        raise ValueError('Invalid readout probabilities')
    moments=[np.einsum('rp,rpo->ro',counts[:,g]/SIZES[g],moment_table(errors,masks[g]))
             for g in range(4)]
    baseline=(43*moments[0]+21*moments[1])/64
    raw=((counts[:,0]+counts[:,1])/64)@moment_table(np.zeros((1,2,2)),masks[0])[0]
    zne=(4*moments[0]+moments[2]-2*moments[3])/3
    return np.stack([raw,baseline,zne],axis=1)

def combine(counts,errors,masks,weights):
    base=baseline_batch(counts,errors,masks)
    lm=apply_weights(counts,errors,masks,weights)
    result=np.concatenate([base,lm[:,None,:]],axis=1)
    if not np.isfinite(result).all():raise ValueError('Nonfinite moment estimate')
    return result

def checked_bundle(folder):
    manifest=read(folder/'sha256.json')
    absent=[name for name in manifest if not safe_path(folder,name).is_file()]
    if absent:
        archive=read(folder/'archive/manifest.json')
        if not set(absent)<={r['path'] for r in archive['original_files']}:
            raise FileNotFoundError('Missing nonarchived operator evidence')
        restore_run(folder,restore=True)
    for name,h in manifest.items():
        if digest(safe_path(folder,name))!=h:raise ValueError('Changed operator evidence: '+name)
    plan=read(folder/'plan.json')
    for name,h in plan['source_sha256'].items():
        if digest(ROOT/name)!=h or digest(folder/'source_snapshot'/Path(name).name)!=h:
            raise ValueError('Changed operator source: '+name)
    for name,h in plan['input_sha256'].items():
        if digest(ROOT/name)!=h:raise ValueError('Changed operator input: '+name)
    audit=read(folder/'verification/verification.json');summary=read(folder/'summary.json')
    if not (audit['exact_norm_local_flags_pass'] and summary['stability']['exact_norm_local_flags_pass']):
        raise ValueError('Operator prerequisite not passed')
    return plan,summary,audit

def run(out):
    started=time.monotonic()
    if out.exists():raise FileExistsError('Preserve prior hardware analysis')
    out.mkdir(parents=True);(out/'source_snapshot').mkdir();(out/'operator_inputs').mkdir()
    dependencies=['twirl1_hardware.py','verify_twirl1_hardware.py','single_twirl.py',
        'verify_single_twirl.py','shot_aware.py','verify_shot_aware.py','hardware_inputs.py',
        'fit.py','model.py','archive_3x3.py','PLAN_TWIRL1_HARDWARE.md']
    sources=[ROOT/'lmpf_2d'/name for name in dependencies]+[ROOT/(name+'.py') for name in TESTS]
    for path in sources:shutil.copyfile(path,out/'source_snapshot'/path.name)
    stream=io.StringIO();suite=unittest.TestSuite()
    for name in TESTS:suite.addTests(unittest.defaultTestLoader.loadTestsFromName(name))
    tests=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    (out/'tests.txt').write_text(stream.getvalue(),encoding='utf-8')
    if not tests.wasSuccessful():raise RuntimeError('Tests failed')
    print('TESTS_PASSED',tests.testsRun,flush=True)
    operator_started=time.monotonic()
    grams=[];low_grams=[];saved_weights=[];input_hashes={};provenance=[];common=None
    for obs,name,low,high in CASES:
        folder=ROOT/'results_cuprate_2d'/name
        plan,summary,audit=checked_bundle(folder)
        if plan['twirl']!=1 or plan['observable']!=obs or plan['chi']!=[low,high] or plan['eta']!=1.:
            raise ValueError('Wrong matching operator')
        if common is None:common=plan
        for key in ('job_id','backend','layout','calibration_errors','stratum_masks','inputs','noise'):
            if plan[key]!=common[key]:raise ValueError('Operators do not share native channel/calibration: '+key)
        lo,hi=read(folder/f'chi{low}.json'),read(folder/f'chi{high}.json')
        grams.append(hi['exact_norm_gram']);low_grams.append(lo['exact_norm_gram']);saved_weights.append(hi['weights'])
        files=['plan.json','summary.json','sha256.json',f'chi{low}.json',f'chi{high}.json','verification/verification.json']
        for rel in files:
            path=folder/rel;h=digest(path);input_hashes[str(path.relative_to(ROOT))]=h
            shutil.copyfile(path,out/'operator_inputs'/f'obs{obs:02d}_{rel.replace("/","_")}')
        provenance.append({'observable':obs,'folder':str(folder.relative_to(ROOT)),
            'levels':[low,high],'source_file':f'chi{high}.json',
            'raw_flags_pass':summary['stability']['raw_flags_pass'],
            'exact_norm_local_flags_pass':True})
    grams=np.array(grams);low_grams=np.array(low_grams)
    errors=np.array(common['calibration_errors']);masks=np.array(common['stratum_masks'])
    penalties=variance_penalties(errors[None],masks)
    weights=solve_weights(grams,penalties)[0];low_weights=solve_weights(low_grams,penalties)[0]
    np.testing.assert_allclose(weights,saved_weights,atol=1e-12,rtol=0)
    changes=np.abs(weights-low_weights).sum(1)
    if np.any(changes>.05):raise ValueError('Coefficient stability changed')
    shared,extra=subset_indices()
    frozen={'twirl':1,'observables':[8,9,22],'source_operators':provenance,
        'grams':grams.tolist(),'low_grams':low_grams.tolist(),'weights':weights.tolist(),
        'low_weights':low_weights.tolist(),'chi_coefficient_l1_changes':changes.tolist(),
        'penalties':penalties[0].tolist(),'calibration_errors':errors.tolist(),'masks':masks.tolist(),
        'eta':1.,'target_shots':[43,7,14],'shared_factor1_indices':shared.tolist(),
        'extra_factor1_indices':extra.tolist(),'subset_seed':SUBSET_SEED,'bootstrap_seed':BOOT_SEED,
        'bootstrap_replicates':REPLICATES,'target_means_or_reference_used':False,
        'calibration_dependent_weights_in_primary_bootstrap':True}
    write(out/'frozen_weights.json',frozen)
    print('MATCHING_WEIGHTS_FROZEN_BEFORE_TARGET_SCORING',flush=True)
    prerequisite_seconds=time.monotonic()-operator_started
    analysis_started=time.monotonic()
    original,raw,receipt=[read(ARCHIVE/name) for name in ('plan.json','raw_bitstrings.json','job_receipt.json')]
    if receipt['plan_sha256']!=digest(ARCHIVE/'plan.json') or raw['job_id']!=receipt['job_id']:
        raise ValueError('Hardware archive identity failure')
    if raw['job_id']!=common['job_id'] or original['backend']!=common['backend'] or raw['width']!=18 or original['layout']!=common['layout']:
        raise ValueError('Hardware/operator mismatch')
    keyed={(r['setting_id'],r['twirl_id']):r for r in raw['records']}
    if len(keyed)!=len(raw['records']):raise ValueError('Duplicate archive record')
    selected=[];target_bits=[];selected_masks=[]
    for factor,index,n in ((1,25,64),(2,19,7),(3,2,14)):
        rec=keyed[(f'U8_T04_factor{factor}',1)];expected=original['records'][index]
        for key in ('setting_id','twirl_id','role','factor','shots','source_qpy','readout_mask_little_endian'):
            if rec[key]!=expected[key]:raise ValueError('Native target record mismatch')
        circuit=ARCHIVE/'provider_inputs'/f'circuit_{index:03d}.qpy'
        op=next(r for r in common['inputs'] if r['factor']==factor)
        if index!=op['record_index'] or digest(circuit)!=op['qpy_sha256'] or digest(circuit)!=digest(ARCHIVE/'bound_inputs'/circuit.name):
            raise ValueError('Target circuit/Gram mismatch')
        bits=decode(rec['bitstrings'],18)
        if len(bits)!=n or rec['shots']!=n:raise ValueError('Changed target shots')
        selected.append(rec);target_bits.append(bits[:,[8,9]])
        selected_masks.append(np.array(rec['readout_mask_little_endian'])[[8,9]])
    np.testing.assert_array_equal(np.array(selected_masks)[[0,0,1,2]],masks)
    calibration=[keyed[(f'readout_all{i}',0)] for i in (0,1)]
    cbits=[]
    for state,rec in enumerate(calibration):
        if rec['state']!=state or rec['shots']!=64 or any(rec['readout_mask_little_endian']):
            raise ValueError('Unexpected calibration record')
        bits=decode(rec['bitstrings'],18)
        if len(bits)!=64:raise ValueError('Changed calibration shots')
        cbits.append(bits[:,[8,9]])
    cal_counts=np.array([cbits[0].sum(0),(1-cbits[1]).sum(0)])
    np.testing.assert_array_equal((cal_counts+.5)/65,errors)
    groups=[target_bits[0][shared],target_bits[0][extra],target_bits[1],target_bits[2]]
    counts=np.array([counts4(g) for g in groups])
    write(out/'selected_inputs.json',{'job_id':raw['job_id'],'width':18,'twirl':1,
        'central_modes':[8,9],'target_records':selected,'calibration_records':calibration,
        'stratum_counts':counts.tolist(),'stratum_masks':masks.tolist(),
        'calibration_error_counts':cal_counts.tolist(),'calibration_errors_posterior_mean':errors.tolist()})
    for name in ('plan.json','raw_bitstrings.json','job_receipt.json'):
        path=ARCHIVE/name;input_hashes[str(path.relative_to(ROOT))]=digest(path)
    plan={'schema':'central-twirl1-shot-aware-hardware-v1','job_id':raw['job_id'],
        'backend':common['backend'],'twirl':1,'observables':[8,9,22],'methods':METHODS,
        'replicates':REPLICATES,'subset_seed':SUBSET_SEED,'bootstrap_seed':BOOT_SEED,
        'primary_target_shots':{'readout64':[64,0,0],'zne_matched':[43,7,14],'lmpf_shot_aware':[43,7,14]},
        'shared_calibration_shots':128,'primary_total_shots':192,'selected_union_shots':213,
        'raw64_calibration_shots_used':0,'new_qpu_seconds':0,'new_tn_states':0,
        'new_six_by_six_work':False,'exploratory_reused_data':True,
        'source_sha256':{str(p.relative_to(ROOT)):digest(p) for p in sources},
        'input_sha256':input_hashes,'frozen_weights_sha256':digest(out/'frozen_weights.json')}
    write(out/'plan.json',plan)
    # Only now access the target reference and score the frozen estimator.
    reference=np.array(original['target']['reference'])[[8,9,22]];target=physical(reference)
    point_pauli=combine(counts[None],errors[None],masks,weights)[0];point=physical(point_pauli)
    rng=np.random.default_rng(BOOT_SEED)
    draws=rng.beta(cal_counts+.5,64-cal_counts+.5,size=(REPLICATES,2,2))
    sampled=np.stack([rng.multinomial(int(n),counts[g]/n,size=REPLICATES) for g,n in enumerate(SIZES)],axis=1)
    pd=variance_penalties(draws,masks);wd=solve_weights(grams,pd)
    boot_pauli=combine(sampled,draws,masks,wd);boot=physical(boot_pauli)
    fixed=physical(combine(sampled,errors[None],masks,weights))
    frozen_boot=physical(combine(sampled,draws,masks,weights))
    np.savez_compressed(out/'bootstrap.npz',calibration_errors=draws,sampled_counts=sampled.astype(np.int16),
        penalties=pd,weights=wd,pauli=boot_pauli,physical=boot,
        physical_fixed_calibration=fixed,physical_frozen_weights=frozen_boot)
    methods={}
    for j,name in enumerate(METHODS):
        pairs=pair_probabilities(point_pauli[j])
        methods[name]={'paulis':point_pauli[j].tolist(),'physical':point[j].tolist(),
            'signed_errors':(point[j]-target).tolist(),'absolute_errors':abs(point[j]-target).tolist(),
            'bootstrap_sd':boot[:,j].std(0,ddof=1).tolist(),
            'fixed_calibration_bootstrap_sd':fixed[:,j].std(0,ddof=1).tolist(),
            'frozen_weight_bootstrap_sd':frozen_boot[:,j].std(0,ddof=1).tolist(),
            'percentile_interval':np.quantile(boot[:,j],[.025,.975],axis=0).tolist(),
            'pair_probabilities_00_10_01_11':pairs.tolist(),'minimum_pair_probability':float(pairs.min()),
            'maximum_absolute_pauli':float(abs(point_pauli[j]).max()),'clipped':False}
    comparisons={}
    for name in ('readout64','zne_matched'):
        j=METHODS.index(name);delta=abs(boot[:,j]-target)-abs(boot[:,3]-target)
        interval=np.quantile(delta,[.025,.975],axis=0)
        comparisons[name]={'absolute_error_improvement':(abs(point[j]-target)-abs(point[3]-target)).tolist(),
            'paired_percentile_interval':interval.tolist(),
            'fixed_calibration_paired_interval':np.quantile(abs(fixed[:,j]-target)-abs(fixed[:,3]-target),[.025,.975],axis=0).tolist(),
            'all_three_lower_bounds_positive':bool(np.all(interval[0]>0))}
    summary={'status':'CENTRAL_TWIRL1_MATCHED_HARDWARE_REANALYSIS',
        'physical_order':['central_charge','central_spin','central_doublon'],
        'reference_paulis':reference.tolist(),'reference_physical':target.tolist(),
        'methods':methods,'comparisons':comparisons,'tests_run':tests.testsRun,
        'operator_input_verification_seconds':prerequisite_seconds,
        'analysis_seconds':time.monotonic()-analysis_started,'seconds':time.monotonic()-started,
        'new_qpu_seconds':0,'new_tn_states':0,'hardware_accuracy_validated':False,
        'full_profile_or_eight_twirl_validation':False,'six_by_six_go':False,
        'raw_ZZ_stability_failed_and_preserved':not provenance[2]['raw_flags_pass'],
        'uncertainty_scope':'Heuristic paired stratified bootstrap plus shared Jeffreys readout calibration and calibration-dependent coefficients; no coverage guarantee at 7 shots or model/TN/drift/correlated-readout bias coverage.'}
    write(out/'summary.json',summary)
    write(out/'sha256.json',{str(p.relative_to(out)):digest(p) for p in sorted(out.rglob('*')) if p.is_file()})
    print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    if args.output.exists():p.error('Output exists; preserve prior evidence')
    try:
        with threadpool_limits(limits=1):run(args.output)
    except Exception as error:
        if args.output.exists():write(args.output/'failure.json',{'type':type(error).__name__,'reason':str(error),'new_qpu_seconds':0})
        raise
