"""Offline matched-shot covariance and saved-circuit timing budget; no provider API."""
from pathlib import Path
import argparse,io,json,math,shutil,sys,time,unittest
import numpy as np
from qiskit import qpy
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from lmpf_2d.exact_counts import read,write,digest,measured_probabilities
from lmpf_2d.single_twirl import moment_table
from lmpf_2d.shot_aware import variance_penalties,solve_weights
ARCHIVE=ROOT/'results_cuprate_2d/hardware_readout_cz_folding_3x3_2026-09-06'
MODEL=ROOT/'results_cuprate_2d/lmpf_3x3_twirl1_noise_model_2026-09-09_v2'
WEIGHTS=ROOT/'results_cuprate_2d/lmpf_3x3_twirl1_hardware_2026-09-09_v1'
PARENT=ROOT/'results_cuprate_2d/lmpf_3x3_exact_counts_2026-09-09_v1'
L=np.array([[-.5,-.5,0],[-.5,.5,0],[-.25,-.25,.25]])
OFFSET=np.tile([1.,0.,.25],4)
BITS=np.array([[0,0],[1,0],[0,1],[1,1]])
NAMES=['raw','readout','zne','lmpf']
INDICES=[0,1,25,19,2]

def seconds(value,unit):
    scales={'s':1.,'ms':1e-3,'us':1e-6,'ns':1e-9,'ps':1e-12}
    if unit not in scales or not np.isfinite(value) or value<0:raise ValueError('Invalid duration')
    return float(value)*scales[unit]

def duration_map(props):
    values={}
    for gate in props['gates']:
        length=[r for r in gate['parameters'] if r['name']=='gate_length']
        if length:values[(gate['gate'],tuple(gate['qubits']))]=seconds(length[0]['value'],length[0]['unit'])
    for q,records in enumerate(props['qubits']):
        item=next(r for r in records if r['name']=='readout_length')
        values['measure',(q,)]=seconds(item['value'],item['unit'])
        values['rz',(q,)]=0.
    return values

def critical_path(circuit,durations):
    clocks=np.zeros(circuit.num_qubits)
    for inst in circuit.data:
        name=inst.operation.name;w=tuple(circuit.find_bit(q).index for q in inst.qubits)
        if name not in ('rz','x','sx','cz','measure','barrier') or not w:raise ValueError('Unexpected operation')
        d=0. if name=='barrier' else durations.get((name,w))
        if d is None and name=='cz':d=durations.get((name,w[::-1]))
        if d is None:raise ValueError('Missing duration')
        clocks[list(w)]=max(clocks[list(w)])+d
    return float(clocks.max())

def exposure(n,m=256):
    if n not in (64,128,256,512) or m!=256:raise ValueError('Changed budget choices')
    return np.array([n,2*n,n,n]),5*n+2*m

def estimator_scores(n,errors,masks,grams):
    tables=np.array([moment_table(errors[None],m)[0] for m in masks])
    rawz=1-2*(BITS^masks[0])
    raw=np.column_stack([rawz,rawz[:,0]*rawz[:,1]])
    p=variance_penalties(errors[None],masks[[0,0,1,2]],np.full(3,n))
    weights=solve_weights(grams,p)[0]
    b=np.zeros((4,4,12))
    for s,f in ((0,1/3),(1,2/3)):
        b[s,:,:3]=f*raw@L.T
        b[s,:,3:6]=f*tables[0]@L.T
    for a,s in enumerate((0,2,3)):
        b[s,:,6:9]=[4/3,1/3,-2/3][a]*tables[a]@L.T
        b[s,:,9:12]=(tables[a]*weights[:,a])@L.T
    return b,weights,p[0]

def forecast_mean(n,errors,masks,grams,q):
    scores,_,_=estimator_scores(n,errors,masks,grams)
    return OFFSET+np.einsum('sx,sxo->o',q[[0,0,1,2]],scores)

def covariance_from_scores(scores,q,sizes):
    covariance=np.zeros((scores.shape[-1],scores.shape[-1]))
    for b,p,n in zip(scores,q,sizes):
        mean=p@b
        covariance+=((b.T*p)@b-np.outer(mean,mean))/n
    return covariance

def jacobian(n,errors,masks,grams,q,h):
    columns=[]
    for i in range(4):
        plus=errors.copy();minus=errors.copy();plus.flat[i]+=h;minus.flat[i]-=h
        columns.append((forecast_mean(n,plus,masks,grams,q)-forecast_mean(n,minus,masks,grams,q))/(2*h))
    return np.column_stack(columns)

def make_case(n,truth,masks,grams,low,q,timing,reset,rep,m=256):
    sizes,union=exposure(n,m);center=(m*truth+.5)/(m+1);var=m*truth*(1-truth)/(m+1)**2
    scores,w,penalties=estimator_scores(n,center,masks,grams)
    loww=solve_weights(low,penalties[None])[0];changes=abs(w-loww).sum(1)
    mean=forecast_mean(n,center,masks,grams,q)
    shot=covariance_from_scores(scores,q[[0,0,1,2]],sizes)
    j=jacobian(n,center,masks,grams,q,1e-5);j2=jacobian(n,center,masks,grams,q,5e-6)
    delta_error=float(abs(j-j2).max())
    if delta_error>2e-6:raise ValueError('Unstable calibration derivative')
    cal=(j*var.ravel())@j.T;total=shot+cal
    if np.linalg.eigvalsh(total).min() < -1e-10:raise ValueError('Non-PSD forecast covariance')
    paired={}
    for name,idx in (('readout',1),('zne',2)):
        contrast=np.zeros((3,12));contrast[:,9:12]=np.eye(3);contrast[:,3*idx:3*idx+3]=-np.eye(3)
        cov=contrast@total@contrast.T
        paired[name]=np.sqrt(np.diag(cov)).tolist()
    counts=np.array([m,m,3*n,n,n]);dur=np.array([r['circuit_seconds'] for r in timing])
    def cost(delay):return float(counts@(dur+reset+delay))
    core=cost(rep);slow=cost(250e-6)
    return {'n_per_folded_factor':n,'calibration_per_state':m,'factor1_total':3*n,
        'strata_shots':sizes.tolist(),'target_union_shots':5*n,'total_union_shots':union,
        'primary_target_shots':3*n,'primary_with_calibration':3*n+2*m,
        'weights':w.tolist(),'low_weights':loww.tolist(),'penalties':penalties.tolist(),
        'chi_coefficient_l1_changes':changes.tolist(),'archived_coefficient_flag_pass':bool(np.all(changes<=.05)),
        'projected_model_physical_means':mean.reshape(4,3).tolist(),
        'shot_only_sd':np.sqrt(np.diag(shot)).reshape(4,3).tolist(),
        'calibration_delta_sd':np.sqrt(np.diag(cal)).reshape(4,3).tolist(),
        'shot_plus_first_order_calibration_sd':np.sqrt(np.diag(total)).reshape(4,3).tolist(),
        'paired_lmpf_minus_baseline_sd':paired,
        'maximum_derivative_step_change':delta_error,
        'shot_execution_seconds':core,'execution_seconds_rep250us_sensitivity':slow,
        'estimated_qpu_seconds_by_subjobs':{str(k):2*k+core for k in (1,2,3)},
        'rep250us_qpu_seconds_by_subjobs':{str(k):2*k+slow for k in (1,2,3)}}, {
        'scores':scores,'jacobian':j,'shot_covariance':shot,'calibration_covariance':cal,'total_covariance':total}

def run(out):
    start=time.monotonic();out.mkdir(exist_ok=False);(out/'source_snapshot').mkdir()
    sources=[ROOT/'lmpf_2d'/x for x in ('balanced_budget.py','verify_balanced_budget.py','PLAN_BALANCED_BUDGET.md',
             'exact_counts.py','single_twirl.py','shot_aware.py','fit.py','model.py')]
    sources += [ROOT/'test_lmpf_balanced_budget.py']
    for p in sources:shutil.copyfile(p,out/'source_snapshot'/p.name)
    for parent in (MODEL,WEIGHTS,PARENT):
        for name,h in read(parent/'sha256.json').items():
            if digest(parent/name)!=h:raise ValueError('Changed verified parent')
    if read(PARENT/'verification/verification.json')['status']!='EXACT_COUNTS_COMBINATORIAL_AND_SCIPY_AUDIT_PASSED':
        raise ValueError('Missing exact-count audit')
    frozen=read(WEIGHTS/'frozen_weights.json');mp=read(MODEL/'model_predictions.json')
    archive_plan=read(ARCHIVE/'plan.json');dispatch=read(ARCHIVE/'dispatch_live_check.json')
    props=read(ARCHIVE/'live_backend_properties.json');metrics=read(ARCHIVE/'provider_metrics.json')
    for name,h in read(ARCHIVE/'preflight_sha256.json').items():
        if digest(ARCHIVE/name)!=h:raise ValueError('Changed timing snapshot')
    duration_lookup=duration_map(props);timing=[];paths=[]
    for i in INDICES:
        p=ARCHIVE/'provider_inputs'/f'circuit_{i:03d}.qpy'
        bound=ARCHIVE/'bound_inputs'/p.name
        if digest(p)!=digest(bound) or digest(bound)!=read(ARCHIVE/'frozen_inputs_sha256.json')[f'bound_inputs/{p.name}']:
            raise ValueError('Changed actual provider circuit')
        with p.open('rb') as f:circuits=qpy.load(f)
        if len(circuits)!=1 or circuits[0].num_parameters:raise ValueError('Invalid saved circuit')
        c=circuits[0];r=archive_plan['records'][i]
        duration=critical_path(c,duration_lookup)
        saved=dispatch['timing_by_pub'][i]
        np.testing.assert_allclose(duration,saved['aligned_duration'],atol=1e-12,rtol=0)
        if i in (25,19,2):
            if r['twirl_id']!=1:raise ValueError('Wrong native twirl')
            for op in frozen['source_operators']:
                plan=read(ROOT/op['folder']/'plan.json')
                native=next(x for x in plan['inputs'] if x['factor']==r['factor'])
                if native['qpy_sha256']!=digest(p) or native['record_index']!=i:raise ValueError('Operator/circuit mismatch')
        timing.append({'provider_index':i,'role':r['role'],'setting_id':r['setting_id'],
            'circuit_seconds':duration,'saved_aligned_seconds':saved['aligned_duration'],
            'cz':int(c.count_ops().get('cz',0)),'depth':c.depth(),'qpy_sha256':digest(p)})
        paths += [p,bound]
    truth=np.array(frozen['calibration_errors']);masks=np.array(frozen['masks'])[[0,2,3]]
    grams=np.array(frozen['grams']);low=np.array(frozen['low_grams'])
    q=np.array([measured_probabilities(mp['pauli_means'][a+1],masks[a],truth) for a in range(3)])
    reset=dispatch['reset_seconds'];rep=dispatch['options']['execution']['rep_delay']
    paths += [ARCHIVE/n for n in ('plan.json','dispatch_live_check.json','provider_metrics.json',
        'live_backend_properties.json','preflight_sha256.json','frozen_inputs_sha256.json')]
    paths += [MODEL/'model_predictions.json',MODEL/'sha256.json',WEIGHTS/'frozen_weights.json',WEIGHTS/'sha256.json',
              PARENT/'summary.json',PARENT/'verification/verification.json']
    plan={'schema':'offline-balanced-3x3-budget-v1','backend':'ibm_phoenix','archived_job_id':'daem7r642tqs73autong',
        'twirl':1,'n_candidates':[64,128,256,512],'calibration_per_state':256,'method_order':NAMES,
        'physical_order':['charge','spin','D'],'proposed_cap_seconds':5,'authorization':False,
        'fresh_backend_verified':False,'new_qpu_seconds':0,'new_tn_states':0,'process_limit_seconds':120,
        'source_sha256':{str(p.relative_to(ROOT)):digest(p) for p in sources},
        'input_sha256':{str(p.relative_to(ROOT)):digest(p) for p in paths},
        'public_usage_source':'https://quantum.cloud.ibm.com/docs/en/guides/estimate-job-run-time',
        'public_usage_source_checked':'2026-09-09'}
    write(out/'plan.json',plan)
    write(out/'forecast_inputs.json',{'noise_model_measured_probabilities':q.tolist(),'assumed_true_calibration_errors':truth.tolist(),
        'future_calibration_expansion_center':((256*truth+.5)/257).tolist(),'grams':grams.tolist(),'low_grams':low.tolist(),
        'masks':masks.tolist(),'timing':timing,'reset_seconds':reset,'rep_delay_seconds':rep})
    stream=io.StringIO();tests=unittest.TextTestRunner(stream=stream,verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromName('test_lmpf_balanced_budget'))
    (out/'tests.txt').write_text(stream.getvalue())
    if not tests.wasSuccessful():raise RuntimeError('Budget tests failed')
    records=[];arrays={}
    for n in (64,128,256,512):
        rec,data=make_case(n,truth,masks,grams,low,q,timing,reset,rep)
        records.append(rec)
        for key,value in data.items():arrays[f'n{n}_{key}']=value
    np.savez_compressed(out/'forecast_covariance.npz',**arrays)
    candidates=[r['n_per_folded_factor'] for r in records if r['archived_coefficient_flag_pass']
                and r['estimated_qpu_seconds_by_subjobs']['2']<5
                and r['rep250us_qpu_seconds_by_subjobs']['2']<5]
    summary={'status':'OFFLINE_SHOT_BUDGET_COMPLETE_NOT_AUTHORIZED','cases':records,
        'candidate_n_under_planning_rule':max(candidates) if candidates else None,
        'historical_timing':{'old_total_shots':archive_plan['total_new_shots'],
            'old_local_execution_seconds':dispatch['execution_seconds'],
            'old_provider_execution_seconds':metrics['circuits_execution_time_ns']*1e-9,
            'old_registered_qpu_seconds':metrics['usage']['qpu_charge_time_seconds'],
            'provider_vs_local_execution_ratio':metrics['circuits_execution_time_ns']*1e-9/dispatch['execution_seconds'],
            'provider_timestamps':metrics['timestamps']},
        'tests_run':tests.testsRun,'seconds':time.monotonic()-start,
        'new_qpu_seconds':0,'hardware_submission_ready':False,'authorization':False,'six_by_six_go':False,
        'uncertainty_scope':'Conditional model sampling covariance plus first-order independent readout-calibration covariance, including weight dependence. Not accuracy or coverage guarantees; no TN/model/drift/correlated-readout uncertainty.',
        'timing_scope':'Archived circuit snapshot plus approximate2s per unknown internal subjob; not a live quote, guarantee, or wall-clock prediction.'}
    write(out/'summary.json',summary)
    write(out/'sha256.json',{str(p.relative_to(out)):digest(p) for p in sorted(out.rglob('*')) if p.is_file()})
    print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    if args.output.exists():p.error('Preserve previous budget')
    try:
        with threadpool_limits(limits=1):run(args.output)
    except Exception as e:
        if args.output.exists():write(args.output/'failure.json',{'type':type(e).__name__,'reason':str(e),'new_qpu_seconds':0})
        raise
