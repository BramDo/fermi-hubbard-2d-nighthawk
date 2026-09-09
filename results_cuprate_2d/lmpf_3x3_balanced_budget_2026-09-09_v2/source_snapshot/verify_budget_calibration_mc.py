"""Audit finite calibration mixtures via the independent scalar KKT oracle."""
from pathlib import Path
import argparse,json,sys,time
import numpy as np
from qiskit import qpy
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from lmpf_2d.verify_balanced_budget import read,digest,oracle,offline_target

def verify(out):
    start=time.monotonic();dest=out/'verification';dest.mkdir(exist_ok=False)
    plan,summary,inp=[read(out/n) for n in ('plan.json','summary.json','forecast_inputs.json')]
    if (plan['schema'],plan['calibration_draws'],plan['seed'])!=('offline-balanced-budget-finite-calibration-v2',8192,2026090921):
        raise ValueError('Wrong finite calibration plan')
    for name,h in read(out/'sha256.json').items():
        if digest(out/name)!=h:raise ValueError('Changed output')
    for name,h in plan['source_sha256'].items():
        if digest(ROOT/name)!=h or digest(out/'source_snapshot'/Path(name).name)!=h:raise ValueError('Changed source')
    for name,h in plan['input_sha256'].items():
        if digest(ROOT/name)!=h:raise ValueError('Changed input')
    truth=np.array(inp['assumed_true_calibration_errors']);q=np.array(inp['noise_model_measured_probabilities'])
    masks=np.array(inp['masks']);grams=np.array(inp['grams']);low=np.array(inp['low_grams'])
    k=np.random.default_rng(2026090921).binomial(256,truth,size=(8192,2,2))
    unique,inverse,frequencies=np.unique(k.reshape(8192,4),axis=0,return_inverse=True,return_counts=True)
    errors=(unique.reshape(-1,2,2)+.5)/257
    archive=ROOT/'results_cuprate_2d/hardware_readout_cz_folding_3x3_2026-09-06'
    target=offline_target(read(archive/'live_backend_properties.json'));dur=[]
    for r,i in zip(inp['timing'],(0,1,25,19,2)):
        p=archive/'provider_inputs'/f'circuit_{i:03d}.qpy'
        if digest(p)!=r['qpy_sha256']:raise ValueError('Changed actual circuit')
        with p.open('rb') as f:c=qpy.load(f)[0]
        elapsed=c.estimate_duration(target,unit='s');dur.append(float(elapsed))
        np.testing.assert_allclose(elapsed,r['circuit_seconds'],atol=1e-12,rtol=0)
    maximum={'weights':0.,'means':0.,'covariance':0.};candidates=[];checked=[]
    with np.load(out/'calibration_forecast.npz',allow_pickle=False) as data:
        np.testing.assert_array_equal(data['calibration_error_counts'],k)
        np.testing.assert_array_equal(data['calibration_errors'],(k+.5)/257)
        for rec,n in zip(summary['cases'],(64,128,256,512)):
            if rec['n_per_folded_factor']!=n or rec['total_union_shots']!=5*n+512 or rec['primary_target_shots']!=3*n:
                raise ValueError('Wrong matched budget')
            unique_mean=[];unique_shot=[];unique_w=[];unique_l=[]
            for e in errors:
                mean,shot,w,_,_=oracle(n,e,masks,grams,q)
                unique_mean.append(mean);unique_shot.append(shot);unique_w.append(w)
                unique_l.append(oracle(n,e,masks,low,q)[2])
            mu=np.array(unique_mean)[inverse];w=np.array(unique_w)[inverse];lw=np.array(unique_l)[inverse]
            us=np.array(unique_shot);shot=np.einsum('r,rop->op',frequencies/8192,us)
            cal=np.cov(mu,rowvar=False,ddof=1);total=shot+cal
            for key,value in (('means',mu),('weights',w),('low_weights',lw),('conditional_average_covariance',shot),
                ('calibration_mean_covariance',cal),('total_covariance',total)):
                got=data[f'n{n}_{key}'];error=float(abs(value-got).max())
                group='weights' if 'weights' in key else 'means' if key=='means' else 'covariance'
                maximum[group]=max(maximum[group],error)
                np.testing.assert_allclose(value,got,atol=1e-10,rtol=0)
            np.testing.assert_allclose(mu.mean(0).reshape(4,3),rec['projected_model_physical_means'],atol=1e-10,rtol=0)
            for cov,key in ((shot,'conditional_sampling_sd'),(cal,'finite_calibration_sd'),(total,'sampling_plus_finite_calibration_sd')):
                np.testing.assert_allclose(np.sqrt(np.diag(cov)).reshape(4,3),rec[key],atol=1e-10,rtol=0)
            halves=[]
            for sel in (slice(0,4096),slice(4096,None)):
                freq=np.bincount(inverse[sel],minlength=len(errors))/4096
                hshot=np.einsum('r,rop->op',freq,us);hcal=np.cov(mu[sel],rowvar=False,ddof=1)
                halves.append(np.sqrt(np.diag(hshot+hcal)))
            np.testing.assert_allclose(halves,data[f'n{n}_half_sample_sd'],atol=1e-10,rtol=0)
            np.testing.assert_allclose(np.array(halves).reshape(2,4,3),rec['half_sample_total_sd'],atol=1e-10,rtol=0)
            changes=abs(w-lw).sum(2);passed=float(np.mean(np.all(changes<=.05,axis=1)))
            np.testing.assert_allclose(passed,rec['calibration_draw_fraction_passing_local_coefficient_flag'],atol=0,rtol=0)
            np.testing.assert_allclose(np.quantile(changes,[.025,.5,.975],axis=0),rec['coefficient_l1_change_quantiles'],atol=1e-10,rtol=0)
            for name,idx in (('readout',1),('zne',2)):
                a=slice(9,12);b=slice(3*idx,3*idx+3)
                paired=total[a,a]+total[b,b]-total[a,b]-total[b,a]
                np.testing.assert_allclose(np.sqrt(np.diag(paired)),rec['paired_lmpf_minus_baseline_sd'][name],atol=1e-10,rtol=0)
            center=(256*truth+.5)/257;cw=oracle(n,center,masks,grams,q)[2];cl=oracle(n,center,masks,low,q)[2]
            np.testing.assert_allclose(cw,rec['weights'],atol=1e-10,rtol=0)
            np.testing.assert_allclose(cl,rec['low_weights'],atol=1e-10,rtol=0)
            flag=bool(np.all(abs(cw-cl).sum(1)<=.05))
            if flag!=rec['archived_coefficient_flag_pass']:raise ValueError('Changed center flag')
            for delay,key,ekey in ((inp['rep_delay_seconds'],'shot_execution_seconds','estimated_qpu_seconds_by_subjobs'),
                                   (250e-6,'execution_seconds_rep250us_sensitivity','rep250us_qpu_seconds_by_subjobs')):
                cost=sum(v*(t+inp['reset_seconds']+delay) for v,t in zip((256,256,3*n,n,n),dur))
                np.testing.assert_allclose(cost,rec[key],atol=1e-12,rtol=0)
                for s in (1,2,3):np.testing.assert_allclose(2*s+cost,rec[ekey][str(s)],atol=1e-12,rtol=0)
            if flag and rec['estimated_qpu_seconds_by_subjobs']['2']<5 and rec['rep250us_qpu_seconds_by_subjobs']['2']<5:candidates.append(n)
            checked.append({'n':n,'future_calibration_flag_pass_fraction':passed})
    if summary['candidate_n_under_planning_rule']!=(max(candidates) if candidates else None):raise ValueError('Wrong candidate')
    if any(summary[x] for x in ('new_qpu_seconds','hardware_submission_ready','authorization','six_by_six_go')):
        raise ValueError('Unsupported hardware authority')
    report={'status':'FINITE_CALIBRATION_KKT_COVARIANCE_AND_QISKIT_AUDIT_PASSED',
        'calibration_draws_replayed':8192,'unique_calibration_outcomes_checked':len(errors),
        'cases_checked':4,'qpy_circuits_checked':5,'maximum_differences':maximum,'checked_cases':checked,
        'new_qpu_seconds':0,'authorization':False,'seconds':time.monotonic()-start}
    with (dest/'verification.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path)
    with threadpool_limits(limits=1):verify(p.parse_args().output)
