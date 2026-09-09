"""Independent assignment/KKT/seed audit of the matched twirl1 hardware analysis."""
from pathlib import Path
import argparse,json,sys,time
import numpy as np
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from lmpf_2d.model import digest
from lmpf_2d.verify_single_twirl import inverse_means,occupation_values,central_bits
from lmpf_2d.verify_shot_aware import inverse_penalties,direct_weights,independent_paulis

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def estimates(counts,errors,masks,weights):
    # Only the three matching baselines are used from the historical oracle.
    baseline=inverse_means(counts,errors,masks,np.eye(3))[:,:3]
    lm=independent_paulis(counts,errors,masks,weights)
    return np.concatenate([baseline,lm[:,None,:]],axis=1)

def verify(out):
    start=time.monotonic();dest=out/'verification';dest.mkdir(exist_ok=False)
    plan,summary,inputs,frozen=[read(out/name) for name in
        ('plan.json','summary.json','selected_inputs.json','frozen_weights.json')]
    methods=['raw64','readout64','zne_matched','lmpf_shot_aware']
    if plan['twirl']!=1 or plan['observables']!=[8,9,22] or plan['methods']!=methods:
        raise ValueError('Wrong analysis scope')
    if (plan['replicates'],plan['subset_seed'],plan['bootstrap_seed'])!=(10000,2026090917,2026090918):
        raise ValueError('Changed predefined seeds/replicates')
    if frozen['eta']!=1. or frozen['target_shots']!=[43,7,14] or frozen['target_means_or_reference_used']:
        raise ValueError('Target-tuned estimator or changed rule')
    if not frozen['calibration_dependent_weights_in_primary_bootstrap']:
        raise ValueError('Calibration dependence omitted')
    if digest(out/'frozen_weights.json')!=plan['frozen_weights_sha256']:raise ValueError('Changed frozen weights')
    for name,h in read(out/'sha256.json').items():
        if digest(out/name)!=h:raise ValueError('Changed output '+name)
    for name,h in plan['source_sha256'].items():
        if digest(ROOT/name)!=h or digest(out/'source_snapshot'/Path(name).name)!=h:
            raise ValueError('Changed source '+name)
    for name,h in plan['input_sha256'].items():
        if digest(ROOT/name)!=h:raise ValueError('Changed input '+name)
    grams=[];low=[];source_weights=[]
    for record in frozen['source_operators']:
        obs=record['observable'];folder=ROOT/record['folder'];lo,hi=record['levels']
        op_plan=read(out/'operator_inputs'/f'obs{obs:02d}_plan.json')
        op_summary=read(out/'operator_inputs'/f'obs{obs:02d}_summary.json')
        audit=read(out/'operator_inputs'/f'obs{obs:02d}_verification_verification.json')
        if op_plan['twirl']!=1 or op_plan['observable']!=obs or op_plan['job_id']!=plan['job_id']:
            raise ValueError('Wrong operator binding')
        if not (op_summary['stability']['exact_norm_local_flags_pass'] and audit['exact_norm_local_flags_pass']):
            raise ValueError('Unpassed operator gate')
        for rel in ('plan.json','summary.json','sha256.json',f'chi{lo}.json',f'chi{hi}.json','verification/verification.json'):
            if digest(folder/rel)!=digest(out/'operator_inputs'/f'obs{obs:02d}_{rel.replace("/","_")}'):
                raise ValueError('Changed operator input copy')
        g=read(folder/f'chi{hi}.json');l=read(folder/f'chi{lo}.json')
        grams.append(g['exact_norm_gram']);low.append(l['exact_norm_gram']);source_weights.append(g['weights'])
    grams=np.array(grams);low=np.array(low)
    np.testing.assert_array_equal(grams,frozen['grams'])
    np.testing.assert_array_equal(low,frozen['low_grams'])
    archive=ROOT/'results_cuprate_2d/hardware_readout_cz_folding_3x3_2026-09-06'
    raw,hp,receipt=[read(archive/name) for name in ('raw_bitstrings.json','plan.json','job_receipt.json')]
    if raw['job_id']!=plan['job_id'] or hp['backend']!=plan['backend'] or receipt['plan_sha256']!=digest(archive/'plan.json'):
        raise ValueError('Wrong hardware archive')
    for r in inputs['target_records']+inputs['calibration_records']:
        candidates=[x for x in raw['records'] if (x['setting_id'],x['twirl_id'])==(r['setting_id'],r['twirl_id'])]
        if len(candidates)!=1 or candidates[0]!=r:raise ValueError('Copied record differs from archive')
    targets=inputs['target_records']
    for r,f,index,n in zip(targets,(1,2,3),(25,19,2),(64,7,14)):
        if r['twirl_id']!=1 or r['factor']!=f or len(r['bitstrings'])!=n:
            raise ValueError('Wrong target exposure')
        qpy=archive/'provider_inputs'/f'circuit_{index:03d}.qpy'
        for record in frozen['source_operators']:
            op=read(ROOT/record['folder']/'plan.json')
            native=next(x for x in op['inputs'] if x['factor']==f)
            if native['record_index']!=index or digest(qpy)!=native['qpy_sha256'] or r['readout_mask_little_endian']!=native['mask']:
                raise ValueError('Target/Gram channel mismatch')
    order=np.random.default_rng(2026090917).permutation(64)
    np.testing.assert_array_equal(order[:43],frozen['shared_factor1_indices'])
    np.testing.assert_array_equal(order[43:],frozen['extra_factor1_indices'])
    bits=[central_bits(r) for r in targets]
    groups=[bits[0][order[:43]],bits[0][order[43:]],bits[1],bits[2]]
    patterns=np.array([[0,0],[1,0],[0,1],[1,1]])
    counts=np.array([[np.all(g==p,axis=1).sum() for p in patterns] for g in groups])
    np.testing.assert_array_equal(counts,inputs['stratum_counts'])
    masks=np.array([r['readout_mask_little_endian'][8:10] for r in targets])[[0,0,1,2]]
    np.testing.assert_array_equal(masks,inputs['stratum_masks'])
    np.testing.assert_array_equal(masks,frozen['masks'])
    cal=inputs['calibration_records']
    if [len(r['bitstrings']) for r in cal]!=[64,64] or [r['state'] for r in cal]!=[0,1]:
        raise ValueError('Wrong calibration budget')
    cal_bits=[central_bits(r) for r in cal]
    cal_counts=np.array([cal_bits[0].sum(0),(1-cal_bits[1]).sum(0)])
    errors=(cal_counts+.5)/65
    np.testing.assert_array_equal(cal_counts,inputs['calibration_error_counts'])
    np.testing.assert_array_equal(errors,frozen['calibration_errors'])
    penalties=inverse_penalties(errors[None],masks)
    weights=direct_weights(grams,penalties)[0];low_weights=direct_weights(low,penalties)[0]
    point_weight_error=float(np.max(abs(weights-frozen['weights'])))
    np.testing.assert_allclose(weights,frozen['weights'],atol=1e-11,rtol=0)
    np.testing.assert_allclose(weights,source_weights,atol=1e-11,rtol=0)
    np.testing.assert_allclose(low_weights,frozen['low_weights'],atol=1e-11,rtol=0)
    np.testing.assert_allclose(penalties[0],frozen['penalties'],atol=1e-12,rtol=0)
    changes=abs(weights-low_weights).sum(1)
    np.testing.assert_allclose(changes,frozen['chi_coefficient_l1_changes'],atol=1e-11)
    if np.any(changes>.05):raise ValueError('Coefficient gate changed')
    if (plan['primary_total_shots'],plan['selected_union_shots'],plan['shared_calibration_shots'])!=(192,213,128):
        raise ValueError('Changed budget claims')
    if plan['primary_target_shots']!={'readout64':[64,0,0],'zne_matched':[43,7,14],'lmpf_shot_aware':[43,7,14]}:
        raise ValueError('Unmatched comparison')
    n=10000;rng=np.random.default_rng(2026090918)
    draws=rng.beta(cal_counts+.5,64-cal_counts+.5,size=(n,2,2))
    sampled=np.stack([rng.multinomial(size,counts[g]/size,size=n) for g,size in enumerate((43,21,7,14))],axis=1)
    pd=inverse_penalties(draws,masks);wd=direct_weights(grams,pd)
    pauli=estimates(sampled,draws,masks,wd);boot=occupation_values(pauli)
    fixed=occupation_values(estimates(sampled,errors[None],masks,weights))
    frozen_boot=occupation_values(estimates(sampled,draws,masks,weights))
    discrepancy={}
    with np.load(out/'bootstrap.npz',allow_pickle=False) as saved:
        np.testing.assert_array_equal(draws,saved['calibration_errors'])
        np.testing.assert_array_equal(sampled,saved['sampled_counts'])
        for key,value in (('penalties',pd),('weights',wd),('pauli',pauli),('physical',boot),
                          ('physical_fixed_calibration',fixed),('physical_frozen_weights',frozen_boot)):
            discrepancy['maximum_'+key+'_error']=float(np.max(abs(value-saved[key])))
            np.testing.assert_allclose(value,saved[key],atol=1e-10,rtol=0)
    point_pauli=estimates(counts[None],errors[None],masks,weights)[0]
    point=occupation_values(point_pauli)
    reference=np.array(hp['target']['reference'])[[8,9,22]];target=occupation_values(reference)
    np.testing.assert_allclose(target,summary['reference_physical'],atol=1e-12)
    for j,name in enumerate(methods):
        rec=summary['methods'][name]
        for key,value in (('paulis',point_pauli[j]),('physical',point[j]),
            ('signed_errors',point[j]-target),('absolute_errors',abs(point[j]-target)),
            ('bootstrap_sd',boot[:,j].std(0,ddof=1)),
            ('fixed_calibration_bootstrap_sd',fixed[:,j].std(0,ddof=1)),
            ('frozen_weight_bootstrap_sd',frozen_boot[:,j].std(0,ddof=1)),
            ('percentile_interval',np.quantile(boot[:,j],[.025,.975],axis=0))):
            np.testing.assert_allclose(value,rec[key],atol=1e-10,rtol=0)
        z,d,zz=point_pauli[j]
        pairs=np.array([1+z+d+zz,1-z+d-zz,1+z-d-zz,1-z-d+zz])/4
        np.testing.assert_allclose(pairs,rec['pair_probabilities_00_10_01_11'],atol=1e-10)
        if rec['clipped'] or abs(pairs.min()-rec['minimum_pair_probability'])>1e-10:
            raise ValueError('Probability clipping or reporting failure')
        np.testing.assert_allclose(abs(point_pauli[j]).max(),rec['maximum_absolute_pauli'],atol=1e-10)
    for name,j in (('readout64',1),('zne_matched',2)):
        rec=summary['comparisons'][name]
        np.testing.assert_allclose(abs(point[j]-target)-abs(point[3]-target),rec['absolute_error_improvement'],atol=1e-10)
        interval=np.quantile(abs(boot[:,j]-target)-abs(boot[:,3]-target),[.025,.975],axis=0)
        np.testing.assert_allclose(interval,rec['paired_percentile_interval'],atol=1e-10)
        np.testing.assert_allclose(np.quantile(abs(fixed[:,j]-target)-abs(fixed[:,3]-target),[.025,.975],axis=0),
                                   rec['fixed_calibration_paired_interval'],atol=1e-10)
        if bool(np.all(interval[0]>0))!=rec['all_three_lower_bounds_positive']:
            raise ValueError('Improvement flag wrong')
    report={'status':'TWIRL1_HARDWARE_ASSIGNMENT_KKT_AUDIT_PASSED',
        'methods_checked':4,'bootstrap_replicates_replayed':10000,
        'operator_sources_verified':3,'maximum_point_weight_error':point_weight_error,**discrepancy,
        'matched_shot_budget_verified':True,'calibration_dependent_weights_verified':True,
        'paired_intervals_verified':True,'no_clipping_verified':True,
        'new_qpu_seconds':0,'hardware_accuracy_validated':False,'seconds':time.monotonic()-start}
    with (dest/'verification.json').open('x') as f:
        json.dump(report,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(report),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path)
    with threadpool_limits(limits=1):verify(p.parse_args().output)
