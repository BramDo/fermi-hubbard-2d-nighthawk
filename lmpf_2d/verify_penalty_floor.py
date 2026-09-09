"""Independent actual-shot KKT and block-covariance audit of penalty floors."""
from pathlib import Path
import argparse,json,sys,time
import numpy as np
from scipy.linalg import block_diag
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from lmpf_2d.verify_balanced_budget import read,digest,oracle
PARENT=ROOT/'results_cuprate_2d/lmpf_3x3_balanced_budget_2026-09-09_v2'

def probability_vectors(v):
    charge,spin,d=np.asarray(v).T
    up=(charge+spin)/2;down=(charge-spin)/2
    return np.array([1-up-down+d,up-d,down-d,d]).T

def verify(out):
    start=time.monotonic();dest=out/'verification';dest.mkdir(exist_ok=False)
    plan,summary,inp=[read(out/name) for name in ('plan.json','summary.json','forecast_inputs.json')]
    if (plan['schema'],plan['actual_shots'],plan['caps'],plan['draws'],plan['seed'])!=(
        'exploratory-penalty-floor-v1',[256,512],[64,128],8192,2026090921):raise ValueError('Wrong experiment')
    if plan['measured_target_or_exact_reference_used'] or not plan['exploratory_changed_estimator']:
        raise ValueError('Unsupported estimator scope')
    for name,h in read(out/'sha256.json').items():
        if digest(out/name)!=h:raise ValueError('Changed result '+name)
    for name,h in plan['source_sha256'].items():
        if digest(ROOT/name)!=h or digest(out/'source_snapshot'/Path(name).name)!=h:raise ValueError('Changed source')
    for name,h in plan['input_sha256'].items():
        if digest(ROOT/name)!=h:raise ValueError('Changed parent input')
    if read(PARENT/'verification/verification.json')['status']!='FINITE_CALIBRATION_KKT_COVARIANCE_AND_QISKIT_AUDIT_PASSED':
        raise ValueError('Missing independent parent audit')
    if inp!=read(PARENT/'forecast_inputs.json'):raise ValueError('Changed forecast inputs')
    truth=np.array(inp['assumed_true_calibration_errors']);q=np.array(inp['noise_model_measured_probabilities'])
    masks=np.array(inp['masks']);grams=np.array(inp['grams']);low=np.array(inp['low_grams'])
    k=np.random.default_rng(2026090921).binomial(256,truth,size=(8192,2,2))
    unique,inverse,freq=np.unique(k.reshape(8192,4),axis=0,return_inverse=True,return_counts=True)
    e=(unique.reshape(-1,2,2)+.5)/257
    cache={};low_cache={}
    for d in (64,128,256,512):
        values=[oracle(d,x,masks,grams,q) for x in e]
        cache[d]={'mean':np.array([x[0] for x in values]),'weight':np.array([x[2] for x in values]),
                  'transfer':np.array([x[4] for x in values])}
        if d in (64,128):low_cache[d]=np.array([oracle(d,x,masks,low,q)[2] for x in e])
    psummary=read(PARENT/'summary.json');previous={r['n_per_folded_factor']:r for r in psummary['cases']}
    maximum={'weights':0.,'means':0.,'covariance':0.};screens=[];seen=set();checks=[]
    with np.load(out/'joint_forecasts.npz',allow_pickle=False) as saved:
        np.testing.assert_array_equal(saved['calibration_error_counts'],k)
        np.testing.assert_array_equal(saved['calibration_errors'],(k+.5)/257)
        for rec in summary['cases']:
            n,cap=rec['actual_n_per_folded_factor'],rec['penalty_cap'];d=min(n,cap);key=f'n{n}_cap{cap}'
            if (n,cap) in seen or n not in (256,512) or cap not in (64,128):raise ValueError('Wrong/duplicate candidate')
            seen.add((n,cap))
            if rec['effective_denominator']!=d or rec['total_union_with_calibration']!=5*n+512 or rec['primary_target_shots']!=3*n:
                raise ValueError('Wrong actual exposure or denominator')
            # Actual n, not d, determines the independent count covariance.
            fcov=block_diag(*[(np.diag(p)-np.outer(p,p))/size for p,size in zip(q[[0,0,1,2]],(n,2*n,n,n))])
            transfers=np.concatenate([cache[n]['transfer'],cache[d]['transfer'][:,9:12]],axis=1)
            conditional=transfers@fcov@transfers.transpose(0,2,1)
            unique_mean=np.column_stack([cache[n]['mean'],cache[d]['mean'][:,9:12]])
            means=unique_mean[inverse];shot=np.einsum('r,rop->op',freq/8192,conditional)
            cal=np.cov(means,rowvar=False,ddof=1);total=shot+cal
            weights=cache[d]['weight'][inverse];low_weights=low_cache[d][inverse]
            for name,value in (('floor_weights',weights),('floor_low_weights',low_weights),('means',means),
                ('conditional_average_covariance',shot),('calibration_mean_covariance',cal),('total_covariance',total)):
                error=float(abs(value-saved[f'{key}_{name}']).max())
                group='weights' if 'weights' in name else 'means' if name=='means' else 'covariance'
                maximum[group]=max(maximum[group],error)
                np.testing.assert_allclose(value,saved[f'{key}_{name}'],atol=1e-10,rtol=0)
            mean=means.mean(0).reshape(5,3);sd=np.sqrt(np.diag(total)).reshape(5,3)
            np.testing.assert_allclose(mean,rec['mean_model_forecasts'],atol=1e-10,rtol=0)
            np.testing.assert_allclose(sd,rec['sd_forecasts'],atol=1e-10,rtol=0)
            pairs=probability_vectors(mean);per_draw=probability_vectors(means[:,12:15])
            np.testing.assert_allclose(pairs,rec['joint_probabilities_of_mean_forecasts'],atol=1e-12,rtol=0)
            np.testing.assert_allclose(per_draw,saved[f'{key}_floor_conditional_probabilities'],atol=1e-12,rtol=0)
            np.testing.assert_allclose(pairs.sum(1),1,atol=1e-12,rtol=0)
            valid=(pairs.min(1)>=-1e-10)&(pairs.max(1)<=1+1e-10)
            np.testing.assert_array_equal(valid,rec['valid_mean_probability_by_method'])
            probability_fraction=float(np.mean((per_draw.min(1)>=-1e-10)&(per_draw.max(1)<=1+1e-10)))
            np.testing.assert_allclose(probability_fraction,rec['floor_valid_conditional_probability_fraction'],atol=0,rtol=0)
            np.testing.assert_allclose(per_draw.min(),rec['minimum_floor_conditional_probability'],atol=1e-12,rtol=0)
            changes=abs(weights-low_weights).sum(2);flag=float(np.mean(np.all(changes<=.05,axis=1)))
            np.testing.assert_allclose(flag,rec['coefficient_flag_pass_fraction'],atol=0,rtol=0)
            np.testing.assert_allclose(np.quantile(changes,[.025,.5,.975],axis=0),rec['coefficient_change_quantiles'],atol=1e-10,rtol=0)
            np.testing.assert_allclose(sd[4]/sd[3],rec['floor_sd_ratio_to_original'],atol=1e-10,rtol=0)
            for name,i in (('readout',1),('zne',2),('lmpf_original',3)):
                a=slice(12,15);b=slice(3*i,3*i+3)
                diff=total[a,a]+total[b,b]-total[a,b]-total[b,a]
                np.testing.assert_allclose(np.sqrt(np.diag(diff)),rec['paired_floor_minus_method_sd'][name],atol=1e-10,rtol=0)
            half=[]
            for s in (slice(0,4096),slice(4096,None)):
                freqhalf=np.bincount(inverse[s],minlength=len(e))/4096
                hs=np.einsum('r,rop->op',freqhalf,conditional);hc=np.cov(means[s],rowvar=False,ddof=1)
                half.append(np.sqrt(np.diag(hs+hc)))
            np.testing.assert_allclose(half,saved[f'{key}_half_sample_sd'],atol=1e-10,rtol=0)
            np.testing.assert_allclose(abs(np.array(half)[0]-half[1]).max(),rec['maximum_half_sample_sd_difference'],atol=1e-10,rtol=0)
            for field,value in rec['archived_time_scenarios'].items():
                if value!=previous[n][field]:raise ValueError('Changed archived cost forecast')
            screened=bool(flag>=.99 and valid[4])
            if screened!=rec['descriptive_screen_pass']:raise ValueError('Wrong screen flag')
            if screened:screens.append([n,cap])
            checks.append({'n':n,'cap':cap,'weight_stability_fraction':flag,'conditional_physical_fraction':probability_fraction})
    if seen!={(256,64),(256,128),(512,64),(512,128)} or screens!=summary['descriptive_screen_candidates']:
        raise ValueError('Incomplete/changed comparison family')
    if any(summary[x] for x in ('new_qpu_seconds','new_tn_states','hardware_submission_ready','authorization','six_by_six_go','accuracy_improvement_proven')):
        raise ValueError('Unsupported claim or authority')
    report={'status':'PENALTY_FLOOR_ACTUAL_SHOT_KKT_AUDIT_PASSED','cases_checked':4,
        'calibration_draws_replayed':8192,'unique_calibration_outcomes':len(e),'joint_covariance_dimensions':[15,15],
        'maximum_differences':maximum,'candidate_checks':checks,'new_qpu_seconds':0,
        'accuracy_improvement_proven':False,'seconds':time.monotonic()-start}
    with (dest/'verification.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('output',type=Path)
    with threadpool_limits(limits=1):verify(ap.parse_args().output)
