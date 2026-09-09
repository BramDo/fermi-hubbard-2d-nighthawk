"""Apply the pre-dispatch floor64 contract to the one fresh archived hardware job."""
from pathlib import Path
import argparse,io,json,shutil,sys,time,unittest
import numpy as np
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from lmpf_2d import floor_hardware as hw
from lmpf_2d.single_twirl import moment_table,physical,pair_probabilities
from lmpf_2d.shot_aware import variance_penalties,solve_weights
from lmpf_2d.exact_counts import read,write,digest
METHODS=['raw','readout','zne','lmpf_original','lmpf_floor']
ROLES=['shared_factor1','baseline_only_factor1','factor2','factor3']
SIZES=np.array([512,1024,512,512])

def bits(record):
    return np.array([[(int(s,2)>>8)&1,(int(s,2)>>9)&1] for s in record['bitstrings']])

def counts4(record):
    b=bits(record);return np.bincount(b[:,0]+2*b[:,1],minlength=4)

def combine(pub_counts,roles):
    counts=np.asarray(pub_counts)
    if counts.ndim!=3 or counts.shape[1:]!=(16,4) or len(roles)!=16:raise ValueError('Wrong16 PUB count shape')
    if any(role not in ROLES for role in roles):raise ValueError('Unknown target role')
    result=np.stack([counts[:,[i for i,r in enumerate(roles) if r==role]].sum(1) for role in ROLES],axis=1)
    if not np.all(result.sum(2)==SIZES):raise ValueError('Wrong full-shot exposure')
    return result

def fit_pair(errors,masks,grams,low):
    masks4=masks[[0,0,1,2]]
    penalty_floor=variance_penalties(errors,masks4,np.full(3,64))
    penalty_original=variance_penalties(errors,masks4,np.full(3,512))
    return {'floor':solve_weights(grams,penalty_floor),'original':solve_weights(grams,penalty_original),
        'low_floor':solve_weights(low,penalty_floor),'floor_penalties':penalty_floor,'original_penalties':penalty_original}

def estimates(counts,errors,masks,weights):
    c=np.asarray(counts);r=len(c)
    if c.shape!=(r,4,4) or not np.all(c.sum(2)==SIZES):raise ValueError('Wrong actual-shot counts')
    e=np.broadcast_to(errors,(r,2,2))
    tables=[moment_table(e,m) for m in masks]
    means=[np.einsum('rx,rxo->ro',c[:,s]/SIZES[s],tables[a]) for s,a in ((0,0),(1,0),(2,1),(3,2))]
    patterns=np.array([[0,0],[1,0],[0,1],[1,1]]);z=1-2*(patterns^masks[0])
    raw=(c[:,0]+c[:,1])/1536@np.column_stack([z,z[:,0]*z[:,1]])
    ro=(means[0]+2*means[1])/3;zne=(4*means[0]+means[2]-2*means[3])/3
    arms=np.stack([means[0],means[2],means[3]],axis=1)
    old=np.einsum('roa,rao->ro',np.broadcast_to(weights['original'],(r,3,3)),arms)
    floor=np.einsum('roa,rao->ro',np.broadcast_to(weights['floor'],(r,3,3)),arms)
    return np.stack([raw,ro,zne,old,floor],axis=1)

def run(out):
    start=time.monotonic()
    hw.verify_files(hw.RUN,'hardware_archive_sha256.json');hw.verify_files(hw.RUN,'analysis_contract_sha256.json')
    contract=read(hw.RUN/'analysis_inputs.json');plan=read(hw.RUN/'plan.json');receipt=read(hw.RUN/'job_receipt.json')
    retrieved=read(hw.RUN/'retrieval_verification.json')
    if retrieved['status']!='DONE_ARCHIVED_VERIFIED' or retrieved['shots']!=3072 or receipt['job_id']!=retrieved['job_id']:
        raise ValueError('Wrong/incomplete hardware retrieval')
    if contract['method_order']!=METHODS or contract['floor_penalty_denominator']!=64 or contract['bootstrap_seed']!=2026090922:
        raise ValueError('Changed pre-dispatch contract')
    out.mkdir(exist_ok=False);(out/'source_snapshot').mkdir()
    sources=[ROOT/'lmpf_2d'/n for n in ('analyze_floor_hardware.py','verify_floor_hardware_analysis.py',
        'floor_hardware.py','freeze_floor_analysis.py','single_twirl.py','shot_aware.py','fit.py','model.py','exact_counts.py')]
    sources += [ROOT/'test_lmpf_floor_analysis.py']
    for p in sources:shutil.copyfile(p,out/'source_snapshot'/p.name)
    stream=io.StringIO();tests=unittest.TextTestRunner(stream=stream,verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromName('test_lmpf_floor_analysis'))
    (out/'tests.txt').write_text(stream.getvalue())
    if not tests.wasSuccessful():raise RuntimeError('Analysis tests failed')
    raw=read(hw.RUN/'raw_bitstrings.json')
    if raw['job_id']!=receipt['job_id'] or raw['width']!=18 or len(raw['records'])!=20:raise ValueError('Wrong raw archive')
    for r,p in zip(raw['records'],plan['records']):
        if {k:v for k,v in r.items() if k!='bitstrings'}!=p or len(r['bitstrings'])!=p['shots']:
            raise ValueError('Changed raw provenance or shots')
    # Only calibration records enter the fit. Freeze weights before decoding targets.
    cal=[r for r in raw['records'] if r['role']=='calibration']
    cal_counts=np.stack([sum((bits(r).sum(0) if s==0 else (1-bits(r)).sum(0)) for r in cal if r['state']==s) for s in (0,1)])
    errors=(cal_counts+.5)/257
    masks=np.array(contract['masks']);grams=np.array(contract['grams']);low=np.array(contract['low_grams'])
    point_weights=fit_pair(errors[None],masks,grams,low);changes=abs(point_weights['floor']-point_weights['low_floor']).sum(2)[0]
    frozen={'actual_shots':[512,512,512],'floor_denominator':64,'eta':1,'calibration_error_counts':cal_counts.tolist(),
        'calibration_errors':errors.tolist(),'masks':masks.tolist(),'weights':{k:v[0].tolist() for k,v in point_weights.items()},
        'chi_coefficient_l1_changes':changes.tolist(),'all_local_coefficient_flags_pass':bool(np.all(changes<=.05)),
        'target_or_reference_used_to_fit':False,'raw_target_scoring_started':False}
    write(out/'frozen_weights.json',frozen)
    print('CALIBRATION_ONLY_WEIGHTS_FROZEN',flush=True)
    targets=[r for r in raw['records'] if r['role']!='calibration'];roles=[r['role'] for r in targets]
    for r in targets:
        a={'shared_factor1':0,'baseline_only_factor1':0,'factor2':1,'factor3':2}[r['role']]
        if r['readout_mask_little_endian'][8:10]!=masks[a].tolist():raise ValueError('Changed target mask')
    pub_counts=np.array([counts4(r) for r in targets]);counts=combine(pub_counts[None],roles)
    point_pauli=estimates(counts,errors[None],masks,point_weights)[0];point=physical(point_pauli)
    rng=np.random.default_rng(2026090922);draws=rng.beta(cal_counts+.5,256-cal_counts+.5,size=(10000,2,2))
    sampled=np.stack([rng.multinomial(r['shots'],c/r['shots'],size=10000) for r,c in zip(targets,pub_counts)],axis=1)
    combined=combine(sampled,roles);draw_weights=fit_pair(draws,masks,grams,low)
    pauli=estimates(combined,draws,masks,draw_weights);boot=physical(pauli)
    fixed=physical(estimates(combined,errors[None],masks,point_weights))
    write(out/'selected_inputs.json',{'target_records':targets,'calibration_records':cal,'pub_counts':pub_counts.tolist(),
        'roles':roles,'combined_counts':counts[0].tolist(),'calibration_error_counts':cal_counts.tolist()})
    np.savez_compressed(out/'bootstrap.npz',calibration_errors=draws,sampled_pub_counts=sampled.astype(np.int16),
        combined_counts=combined.astype(np.int16),floor_weights=draw_weights['floor'],original_weights=draw_weights['original'],
        low_floor_weights=draw_weights['low_floor'],paulis=pauli,physical=boot,physical_fixed_calibration=fixed)
    ref=np.array(contract['reference_paulis']);reference=physical(ref);methods={}
    for i,name in enumerate(METHODS):
        p=pair_probabilities(point_pauli[i])
        methods[name]={'paulis':point_pauli[i].tolist(),'physical':point[i].tolist(),
            'signed_error':(point[i]-reference).tolist(),'absolute_error':abs(point[i]-reference).tolist(),
            'bootstrap_sd':boot[:,i].std(0,ddof=1).tolist(),'percentile_interval':np.quantile(boot[:,i],[.025,.975],axis=0).tolist(),
            'fixed_calibration_sd':fixed[:,i].std(0,ddof=1).tolist(),'joint_probabilities_00_10_01_11':p.tolist(),
            'valid_point_probabilities':bool(p.min()>=-1e-10 and p.max()<=1+1e-10),'clipped':False}
    comparisons={}
    for name,i in (('readout',1),('zne',2),('lmpf_original',3)):
        delta=abs(boot[:,i]-reference)-abs(boot[:,4]-reference)
        interval=np.quantile(delta,[.025,.975],axis=0)
        comparisons[name]={'absolute_error_improvement':(abs(point[i]-reference)-abs(point[4]-reference)).tolist(),
            'paired_percentile_interval':interval.tolist(),'all_three_lower_bounds_positive':bool(np.all(interval[0]>0))}
    prepost={}
    for phase in ('pre','post'):
        selected=[r for r in cal if r['id'].startswith('cal_'+phase)]
        errors_phase=np.stack([sum((bits(r).sum(0) if s==0 else (1-bits(r)).sum(0)) for r in selected if r['state']==s) for s in (0,1)])
        prepost[phase]={'shots_per_state':128,'error_counts':errors_phase.tolist(),'posterior_mean':((errors_phase+.5)/129).tolist()}
    draw_change=abs(draw_weights['floor']-draw_weights['low_floor']).sum(2)
    summary={'status':'FRESH_FLOOR64_HARDWARE_ANALYZED','job_id':receipt['job_id'],'backend':plan['backend'],
        'reference_paulis':ref.tolist(),'reference_physical':reference.tolist(),'methods':methods,'comparisons':comparisons,
        'calibration_pre_post':prepost,'point_coefficient_flags_pass':frozen['all_local_coefficient_flags_pass'],
        'bootstrap_coefficient_pass_fraction':float(np.mean(np.all(draw_change<=.05,axis=1))),
        'data_union_shots':3072,'primary_target_shots_each':1536,'calibration_shots':512,
        'usage':read(hw.RUN/'provider_metrics.json').get('usage'),'tests_run':tests.testsRun,'seconds':time.monotonic()-start,
        'equal_qpu_time_budget':False,'six_by_six_go':False,'quantum_advantage_proven':False,
        'uncertainty_scope':'Paired16-stratum empirical target bootstrap with shared independent Beta readout calibration and refitted weights. Marginal descriptive95% intervals, not simultaneous/certified coverage; no model/TN/coherent/drift/correlated-readout bias included.'}
    write(out/'summary.json',summary)
    write(out/'plan.json',{'job_id':receipt['job_id'],'contract_sha256':digest(hw.RUN/'analysis_inputs.json'),
        'source_sha256':{str(p.relative_to(ROOT)):digest(p) for p in sources},
        'input_sha256':{str((hw.RUN/n).relative_to(ROOT)):digest(hw.RUN/n) for n in
            ('plan.json','raw_bitstrings.json','analysis_inputs.json','analysis_contract_sha256.json','job_receipt.json',
             'retrieval_verification.json','hardware_archive_sha256.json','provider_metrics.json')}})
    write(out/'sha256.json',{str(p.relative_to(out)):digest(p) for p in sorted(out.rglob('*')) if p.is_file()})
    print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=hw.RUN/'analysis');args=ap.parse_args()
    if args.output.exists():ap.error('Preserve earlier analysis')
    with threadpool_limits(limits=1):run(args.output)
