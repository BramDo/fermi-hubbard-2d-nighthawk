"""Finite future-calibration mixture for offline budget forecasts; no derivatives."""
from pathlib import Path
import argparse,copy,io,json,shutil,sys,time,unittest
import numpy as np
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from lmpf_2d.balanced_budget import L,OFFSET,BITS,read,write,digest,moment_table,variance_penalties,solve_weights
PARENT=ROOT/'results_cuprate_2d/lmpf_3x3_balanced_budget_2026-09-09_v1'
DRAWS=8192;SEED=2026090921

def mixture(n,errors,masks,grams,low,q):
    r=len(errors);h=[moment_table(errors,m) for m in masks]
    penalties=variance_penalties(errors,masks[[0,0,1,2]],np.full(3,n))
    weights=solve_weights(grams,penalties);low_weights=solve_weights(low,penalties)
    z=1-2*(BITS^masks[0]);raw=np.column_stack([z,z[:,0]*z[:,1]])
    b=np.zeros((r,4,4,12))
    for s,f in ((0,1/3),(1,2/3)):
        b[:,s,:,:3]=f*raw@L.T;b[:,s,:,3:6]=f*h[0]@L.T
    for a,s in enumerate((0,2,3)):
        b[:,s,:,6:9]=[4/3,1/3,-2/3][a]*h[a]@L.T
        b[:,s,:,9:12]=(h[a]*weights[:,:,a][:,None,:])@L.T
    def moments(block):
        size=len(block);mean=OFFSET+np.einsum('sx,rsxo->ro',q[[0,0,1,2]],block)
        shot=np.zeros((12,12))
        for s,p,count in zip(range(4),q[[0,0,1,2]],(n,2*n,n,n)):
            score=block[:,s];mu=np.einsum('x,rxo->ro',p,score)
            shot+=(np.einsum('rxo,x,rxp->op',score,p,score)/size-mu.T@mu/size)/count
        cal=np.cov(mean,rowvar=False,ddof=1)
        return mean,shot,cal
    means,shot,cal=moments(b);total=shot+cal
    first=moments(b[:r//2]);second=moments(b[r//2:])
    half=np.array([np.sqrt(np.diag(x[1]+x[2])) for x in (first,second)])
    if np.linalg.eigvalsh(total).min()<-1e-10:raise ValueError('Non-PSD covariance')
    return {'means':means,'weights':weights,'low_weights':low_weights,
        'conditional_average_covariance':shot,'calibration_mean_covariance':cal,
        'total_covariance':total,'half_sample_sd':half}

def run(out):
    start=time.monotonic();out.mkdir(exist_ok=False);(out/'source_snapshot').mkdir()
    for name,h in read(PARENT/'sha256.json').items():
        if digest(PARENT/name)!=h:raise ValueError('Changed preserved budget')
    old_plan=read(PARENT/'plan.json');old_summary=read(PARENT/'summary.json');inp=read(PARENT/'forecast_inputs.json')
    sources=[ROOT/'lmpf_2d'/n for n in ('budget_calibration_mc.py','verify_budget_calibration_mc.py',
        'balanced_budget.py','verify_balanced_budget.py','PLAN_BALANCED_BUDGET.md','PLAN_BUDGET_CALIBRATION_MC.md',
        'single_twirl.py','shot_aware.py','fit.py','model.py','exact_counts.py')]
    sources += [ROOT/'test_lmpf_budget_calibration_mc.py',ROOT/'test_lmpf_balanced_budget.py']
    for p in sources:shutil.copyfile(p,out/'source_snapshot'/p.name)
    plan={**old_plan,'schema':'offline-balanced-budget-finite-calibration-v2','calibration_draws':DRAWS,
        'seed':SEED,'first_order_delta_replaced':True,'source_sha256':{str(p.relative_to(ROOT)):digest(p) for p in sources},
        'input_sha256':{**old_plan['input_sha256'],**{str((PARENT/n).relative_to(ROOT)):digest(PARENT/n)
            for n in ('plan.json','forecast_inputs.json','summary.json','sha256.json','verification/failure.json')}}}
    write(out/'plan.json',plan);write(out/'forecast_inputs.json',inp)
    stream=io.StringIO();suite=unittest.TestSuite()
    for name in ('test_lmpf_balanced_budget','test_lmpf_budget_calibration_mc'):
        suite.addTests(unittest.defaultTestLoader.loadTestsFromName(name))
    tests=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    (out/'tests.txt').write_text(stream.getvalue())
    if not tests.wasSuccessful():raise RuntimeError('Tests failed')
    truth=np.array(inp['assumed_true_calibration_errors']);q=np.array(inp['noise_model_measured_probabilities'])
    masks=np.array(inp['masks']);grams=np.array(inp['grams']);low=np.array(inp['low_grams'])
    k=np.random.default_rng(SEED).binomial(256,truth,size=(DRAWS,2,2));errors=(k+.5)/257
    arrays={'calibration_error_counts':k.astype(np.int16),'calibration_errors':errors};records=[]
    for old in old_summary['cases']:
        n=old['n_per_folded_factor'];data=mixture(n,errors,masks,grams,low,q)
        changes=abs(data['weights']-data['low_weights']).sum(2)
        rec={key:value for key,value in old.items() if key not in ('calibration_delta_sd',
            'shot_plus_first_order_calibration_sd','maximum_derivative_step_change',
            'paired_lmpf_minus_baseline_sd','projected_model_physical_means','shot_only_sd')}
        rec['point_calibration_model_mean']=old['projected_model_physical_means']
        rec['point_calibration_shot_sd']=old['shot_only_sd']
        rec['projected_model_physical_means']=data['means'].mean(0).reshape(4,3).tolist()
        rec['conditional_sampling_sd']=np.sqrt(np.diag(data['conditional_average_covariance'])).reshape(4,3).tolist()
        rec['finite_calibration_sd']=np.sqrt(np.diag(data['calibration_mean_covariance'])).reshape(4,3).tolist()
        rec['sampling_plus_finite_calibration_sd']=np.sqrt(np.diag(data['total_covariance'])).reshape(4,3).tolist()
        rec['calibration_draw_fraction_passing_local_coefficient_flag']=float(np.mean(np.all(changes<=.05,axis=1)))
        rec['coefficient_l1_change_quantiles']=np.quantile(changes,[.025,.5,.975],axis=0).tolist()
        rec['half_sample_total_sd']=data['half_sample_sd'].reshape(2,4,3).tolist()
        rec['maximum_half_sample_total_sd_difference']=float(abs(data['half_sample_sd'][0]-data['half_sample_sd'][1]).max())
        rec['paired_lmpf_minus_baseline_sd']={}
        for name,i in (('readout',1),('zne',2)):
            contrast=np.zeros((3,12));contrast[:,9:12]=np.eye(3);contrast[:,3*i:3*i+3]=-np.eye(3)
            rec['paired_lmpf_minus_baseline_sd'][name]=np.sqrt(np.diag(contrast@data['total_covariance']@contrast.T)).tolist()
        records.append(rec)
        for key,value in data.items():arrays[f'n{n}_{key}']=value
    np.savez_compressed(out/'calibration_forecast.npz',**arrays)
    summary={**old_summary,'status':'OFFLINE_FINITE_CALIBRATION_BUDGET_COMPLETE_NOT_AUTHORIZED',
        'cases':records,'tests_run':tests.testsRun,'seconds':time.monotonic()-start,
        'calibration_draws':DRAWS,'seed':SEED,'first_order_delta_replaced':True,
        'uncertainty_scope':'Exact conditional categorical sampling covariance averaged over8192 simulated future calibrations plus covariance of their conditional means. Discrete Jeffreys estimates and reweighted L-MPF included. Finite Monte Carlo approximation; no TN/model/drift/correlated-readout uncertainty or accuracy guarantee.'}
    write(out/'summary.json',summary)
    write(out/'sha256.json',{str(p.relative_to(out)):digest(p) for p in sorted(out.rglob('*')) if p.is_file()})
    print(json.dumps({'status':summary['status'],'candidate_n':summary['candidate_n_under_planning_rule'],
        'tests':tests.testsRun,'seconds':summary['seconds'],'cases':[{
            'n':r['n_per_folded_factor'],'lmpf_sd':r['sampling_plus_finite_calibration_sd'][3],
            'lmpf_model_mean':r['projected_model_physical_means'][3],
            'calibration_flag_pass_fraction':r['calibration_draw_fraction_passing_local_coefficient_flag'],
            'mc_half_sd_difference':r['maximum_half_sample_total_sd_difference']} for r in records]},indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    if args.output.exists():p.error('Preserve previous results')
    try:
        with threadpool_limits(limits=1):run(args.output)
    except Exception as e:
        if args.output.exists():write(args.output/'failure.json',{'type':type(e).__name__,'reason':str(e),'new_qpu_seconds':0})
        raise
