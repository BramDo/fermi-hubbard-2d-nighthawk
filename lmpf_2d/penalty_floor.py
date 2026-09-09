"""Penalty-floor forecast with same-sample comparisons; no hardware calls."""
from pathlib import Path
import argparse,io,json,shutil,sys,time,unittest
import numpy as np
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from lmpf_2d.balanced_budget import L,BITS,read,write,digest,moment_table
PARENT=ROOT/'results_cuprate_2d/lmpf_3x3_balanced_budget_2026-09-09_v2'
METHODS=['raw','readout','zne','lmpf_original','lmpf_floor']

def effective_denominator(actual,cap):
    if actual not in (64,128,256,512) or cap not in (64,128,256,512):raise ValueError('Invalid denominator')
    return min(actual,cap)

def local_probabilities(values):
    v=np.asarray(values)
    if v.shape[-1]!=3 or not np.isfinite(v).all():raise ValueError('Invalid physical vector')
    q,s,d=np.moveaxis(v,-1,0)
    return np.stack([1-q+d,(q+s)/2-d,(q-s)/2-d,d],axis=-1)

def joint_forecast(n,errors,masks,q,original_weights,floor_weights):
    r=len(errors)
    if r<4 or np.shape(errors)!=(r,2,2) or np.shape(masks)!=(3,2) or np.shape(q)!=(3,4):
        raise ValueError('Wrong calibration/mask/probability shape')
    for w in (original_weights,floor_weights):
        if np.shape(w)!=(r,3,3) or not np.isfinite(w).all():raise ValueError('Wrong weight array')
        np.testing.assert_allclose(np.asarray(w).sum(-1),1,atol=1e-10,rtol=0)
    if n<=0 or int(n)!=n or not np.isfinite(q).all() or np.any(q<0):raise ValueError('Invalid n/q')
    np.testing.assert_allclose(np.asarray(q).sum(1),1,atol=1e-12,rtol=0)
    h=[moment_table(errors,m) for m in masks];z=1-2*(BITS^masks[0])
    raw=np.column_stack([z,z[:,0]*z[:,1]])
    b=np.zeros((r,4,4,15))
    for s,f in ((0,1/3),(1,2/3)):
        b[:,s,:,:3]=f*raw@L.T;b[:,s,:,3:6]=f*h[0]@L.T
    for a,s in enumerate((0,2,3)):
        b[:,s,:,6:9]=[4/3,1/3,-2/3][a]*h[a]@L.T
        for offset,w in ((9,original_weights),(12,floor_weights)):
            b[:,s,:,offset:offset+3]=(h[a]*w[:,:,a][:,None,:])@L.T
    def evaluate(scores):
        size=len(scores);means=np.tile([1,0,.25],5)+np.einsum('sx,rsxo->ro',q[[0,0,1,2]],scores)
        shot=np.zeros((15,15))
        for s,p,count in zip(range(4),q[[0,0,1,2]],(n,2*n,n,n)):
            x=scores[:,s];mu=np.einsum('x,rxo->ro',p,x)
            shot+=(np.einsum('rxo,x,rxp->op',x,p,x)/size-mu.T@mu/size)/count
        cal=np.cov(means,rowvar=False,ddof=1)
        return means,shot,cal
    means,shot,cal=evaluate(b);total=shot+cal
    if np.linalg.eigvalsh(total).min()<-1e-10:raise ValueError('Non-PSD joint forecast')
    halves=[evaluate(b[:r//2]),evaluate(b[r//2:])]
    return {'means':means,'conditional_average_covariance':shot,'calibration_mean_covariance':cal,
        'total_covariance':total,'half_sample_sd':np.array([np.sqrt(np.diag(a+c)) for _,a,c in halves])}

def run(out):
    start=time.monotonic();out.mkdir(exist_ok=False);(out/'source_snapshot').mkdir()
    for name,h in read(PARENT/'sha256.json').items():
        if digest(PARENT/name)!=h:raise ValueError('Changed verified forecast')
    audit=read(PARENT/'verification/verification.json')
    if audit['status']!='FINITE_CALIBRATION_KKT_COVARIANCE_AND_QISKIT_AUDIT_PASSED':
        raise ValueError('Missing independent parent audit')
    parent_plan=read(PARENT/'plan.json');parent_summary=read(PARENT/'summary.json');inp=read(PARENT/'forecast_inputs.json')
    sources=[ROOT/'lmpf_2d'/n for n in ('penalty_floor.py','verify_penalty_floor.py','PLAN_PENALTY_FLOOR.md',
        'balanced_budget.py','verify_balanced_budget.py','single_twirl.py','shot_aware.py','fit.py','model.py',
        'exact_counts.py','budget_calibration_mc.py')]
    sources += [ROOT/(n+'.py') for n in ('test_lmpf_penalty_floor','test_lmpf_balanced_budget','test_lmpf_budget_calibration_mc')]
    for p in sources:shutil.copyfile(p,out/'source_snapshot'/p.name)
    plan={'schema':'exploratory-penalty-floor-v1','backend':'ibm_phoenix','archived_job_id':'daem7r642tqs73autong',
        'twirl':1,'actual_shots':[256,512],'caps':[64,128],'method_order':METHODS,'physical_order':['charge','spin','D'],
        'calibration_shots_per_state':256,'draws':8192,'seed':2026090921,
        'exploratory_changed_estimator':True,'measured_target_or_exact_reference_used':False,
        'source_sha256':{str(p.relative_to(ROOT)):digest(p) for p in sources},
        'input_sha256':{str((PARENT/n).relative_to(ROOT)):digest(PARENT/n) for n in
            ('plan.json','summary.json','forecast_inputs.json','calibration_forecast.npz','sha256.json','verification/verification.json')},
        'model_or_accuracy_validated':False,'authorization':False,'new_qpu_seconds':0,'new_tn_states':0,'process_limit_seconds':120}
    write(out/'plan.json',plan);write(out/'forecast_inputs.json',inp)
    stream=io.StringIO();suite=unittest.TestSuite()
    for name in ('test_lmpf_balanced_budget','test_lmpf_budget_calibration_mc','test_lmpf_penalty_floor'):
        suite.addTests(unittest.defaultTestLoader.loadTestsFromName(name))
    tests=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    (out/'tests.txt').write_text(stream.getvalue())
    if not tests.wasSuccessful():raise RuntimeError('Tests failed')
    rows={r['n_per_folded_factor']:r for r in parent_summary['cases']}
    q=np.asarray(inp['noise_model_measured_probabilities']);masks=np.asarray(inp['masks'])
    records=[];arrays={}
    with np.load(PARENT/'calibration_forecast.npz',allow_pickle=False) as old:
        errors=old['calibration_errors'];k=old['calibration_error_counts']
        arrays.update(calibration_errors=errors,calibration_error_counts=k)
        for n in (256,512):
            for cap in (64,128):
                d=effective_denominator(n,cap);key=f'n{n}_cap{cap}'
                w=old[f'n{d}_weights'];low=old[f'n{d}_low_weights']
                data=joint_forecast(n,errors,masks,q,old[f'n{n}_weights'],w)
                select=list(range(9))+[12,13,14]
                np.testing.assert_allclose(data['means'][:,select],old[f'n{d}_means'],atol=1e-12,rtol=0)
                np.testing.assert_allclose(data['means'][:,:12],old[f'n{n}_means'],atol=1e-12,rtol=0)
                np.testing.assert_allclose(data['conditional_average_covariance'][np.ix_(select,select)],
                    old[f'n{d}_conditional_average_covariance']*d/n,atol=1e-12,rtol=0)
                np.testing.assert_allclose(data['calibration_mean_covariance'][np.ix_(select,select)],
                    old[f'n{d}_calibration_mean_covariance'],atol=1e-12,rtol=0)
                np.testing.assert_allclose(data['total_covariance'][:12,:12],old[f'n{n}_total_covariance'],atol=1e-12,rtol=0)
                means=data['means'].mean(0).reshape(5,3);sd=np.sqrt(np.diag(data['total_covariance'])).reshape(5,3)
                probs=local_probabilities(means);per_draw=local_probabilities(data['means'][:,12:15])
                changes=abs(w-low).sum(2);flag=float(np.mean(np.all(changes<=.05,axis=1)))
                valid=(probs.min(1)>=-1e-10)&(probs.max(1)<=1+1e-10)
                paired={}
                for name,i in (('readout',1),('zne',2),('lmpf_original',3)):
                    contrast=np.zeros((3,15));contrast[:,12:15]=np.eye(3);contrast[:,3*i:3*i+3]=-np.eye(3)
                    paired[name]=np.sqrt(np.diag(contrast@data['total_covariance']@contrast.T)).tolist()
                rec={'actual_n_per_folded_factor':n,'penalty_cap':cap,'effective_denominator':d,
                    'target_union_shots':5*n,'total_union_with_calibration':5*n+512,'primary_target_shots':3*n,
                    'mean_model_forecasts':means.tolist(),'sd_forecasts':sd.tolist(),
                    'joint_probabilities_of_mean_forecasts':probs.tolist(),'valid_mean_probability_by_method':valid.tolist(),
                    'floor_valid_conditional_probability_fraction':float(np.mean((per_draw.min(1)>=-1e-10)&(per_draw.max(1)<=1+1e-10))),
                    'minimum_floor_conditional_probability':float(per_draw.min()),'coefficient_flag_pass_fraction':flag,
                    'coefficient_change_quantiles':np.quantile(changes,[.025,.5,.975],axis=0).tolist(),
                    'floor_sd_ratio_to_original':(sd[4]/sd[3]).tolist(),'paired_floor_minus_method_sd':paired,
                    'descriptive_screen_pass':bool(flag>=.99 and valid[4]),
                    'maximum_half_sample_sd_difference':float(abs(data['half_sample_sd'][0]-data['half_sample_sd'][1]).max()),
                    'archived_time_scenarios':{x:rows[n][x] for x in ('shot_execution_seconds','estimated_qpu_seconds_by_subjobs','rep250us_qpu_seconds_by_subjobs')}}
                records.append(rec)
                for name,val in data.items():arrays[f'{key}_{name}']=val
                arrays[f'{key}_floor_weights']=w;arrays[f'{key}_floor_low_weights']=low
                arrays[f'{key}_floor_conditional_probabilities']=per_draw
    np.savez_compressed(out/'joint_forecasts.npz',**arrays)
    summary={'status':'PENALTY_FLOOR_FORECAST_COMPLETE','cases':records,'tests_run':tests.testsRun,
        'calibration_draws':8192,'seconds':time.monotonic()-start,
        'descriptive_screen_candidates':[[r['actual_n_per_folded_factor'],r['penalty_cap']] for r in records if r['descriptive_screen_pass']],
        'new_qpu_seconds':0,'new_tn_states':0,'hardware_submission_ready':False,'authorization':False,'six_by_six_go':False,
        'accuracy_improvement_proven':False,
        'scope':'New exploratory estimator forecast under a frozen approximate noise model and finite calibration mixture, not measured hardware or certified error bars. Stable coefficients and valid conditional model means do not establish accuracy or finite-shot physicality.'}
    write(out/'summary.json',summary)
    write(out/'sha256.json',{str(p.relative_to(out)):digest(p) for p in sorted(out.rglob('*')) if p.is_file()})
    print(json.dumps({'status':summary['status'],'tests':tests.testsRun,'seconds':summary['seconds'],
        'cases':[{'n':r['actual_n_per_folded_factor'],'cap':r['penalty_cap'],'floor_mean':r['mean_model_forecasts'][4],
        'floor_sd':r['sd_forecasts'][4],'sd_ratio_to_original':r['floor_sd_ratio_to_original'],
        'coefficient_pass_fraction':r['coefficient_flag_pass_fraction'],
        'conditional_physical_fraction':r['floor_valid_conditional_probability_fraction'],
        'minimum_conditional_probability':r['minimum_floor_conditional_probability'],
        'screen_pass':r['descriptive_screen_pass']} for r in records]},indent=2),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    if args.output.exists():ap.error('Preserve earlier output')
    try:
        with threadpool_limits(limits=1):run(args.output)
    except Exception as e:
        if args.output.exists():write(args.output/'failure.json',{'type':type(e).__name__,'reason':str(e),'new_qpu_seconds':0})
        raise
