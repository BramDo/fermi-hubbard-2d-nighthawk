"""Exhaustive finite-count diagnostics, conditional on frozen model and readout."""
from pathlib import Path
import argparse,hashlib,io,itertools,json,math,shutil,sys,time,unittest
import numpy as np
from scipy.special import gammaln,xlogy
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
PARENT=ROOT/'results_cuprate_2d/lmpf_3x3_twirl1_noise_model_2026-09-09_v2'
HARDWARE=ROOT/'results_cuprate_2d/lmpf_3x3_twirl1_hardware_2026-09-09_v1'
ARCHIVE=ROOT/'results_cuprate_2d/hardware_readout_cz_folding_3x3_2026-09-06'
BITS=np.array([[0,0],[1,0],[0,1],[1,1]])
PLUS=np.column_stack([BITS[:,0]==0,BITS[:,1]==0,BITS[:,0]==BITS[:,1]])

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,value):
    with p.open('x',encoding='utf-8') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n')

def probabilities(p):
    q=np.asarray(p,dtype=float)
    if q.ndim!=1 or len(q) not in (2,4) or not np.isfinite(q).all() or np.any(q<0) or np.any(q>1):
        raise ValueError('Invalid probabilities; no clipping')
    if not np.isclose(q.sum(),1,atol=1e-12,rtol=0):raise ValueError('Unnormalized probabilities')
    return q

def joint_probabilities(paulis):
    z,d,zz=np.asarray(paulis,dtype=float)
    return probabilities(np.array([1+z+d+zz,1-z+d-zz,1+z-d-zz,1-z-d+zz])/4)

def measured_probabilities(paulis,mask,errors):
    p=joint_probabilities(paulis);m=np.asarray(mask);e=np.asarray(errors,dtype=float)
    if m.shape!=(2,) or not np.isin(m,[0,1]).all():raise ValueError('Invalid mask')
    if e.shape!=(2,2) or not np.isfinite(e).all() or np.any(e<0) or np.any(e>1):
        raise ValueError('Invalid calibration')
    true=BITS ^ m.astype(int)
    one=np.where(true==0,e[0],1-e[1])
    assignment=np.prod(np.where(BITS[None,:,:]==1,one[:,None,:],1-one[:,None,:]),axis=2)
    return probabilities(p@assignment)

def count_vectors(n,k=4):
    if isinstance(n,bool) or not isinstance(n,(int,np.integer)) or not 1<=n<=64 or k not in (2,4):
        raise ValueError('Count enumeration guard: n in1..64, k2/4')
    separators=np.array(list(itertools.combinations(range(n+k-1),k-1)),dtype=int)
    return np.diff(np.column_stack([np.full(len(separators),-1),separators,
                                   np.full(len(separators),n+k-1)]),axis=1)-1

def checked_counts(counts,p):
    c=np.asarray(counts)
    if c.ndim!=2 or c.shape[1]!=len(p) or not len(c) or not np.isfinite(c).all() or np.any(c<0) or np.any(c!=np.floor(c)):
        raise ValueError('Invalid integer count matrix')
    n=c.sum(1)
    if np.any(n<1) or np.any(n!=n[0]):raise ValueError('Changed exposure')
    return c,n[0]

def multinomial_logmass(counts,p):
    q=probabilities(p);c,n=checked_counts(counts,q)
    return gammaln(n+1)-gammaln(c+1).sum(1)+xlogy(c,q).sum(1)

def deviance(counts,p):
    q=probabilities(p);c,n=checked_counts(counts,q)
    return 2*(xlogy(c,c)-xlogy(c,n*q)).sum(1)

def tail_probability(stat,mass,observed,tolerance=1e-10):
    if math.isnan(observed) or observed< -1e-10:raise ValueError('Invalid statistic')
    selected=np.isinf(stat) if np.isinf(observed) else stat>=observed-tolerance*max(1,abs(observed))
    value=float(math.fsum(np.asarray(mass)[selected]))
    if not -1e-12<=value<=1+1e-12:raise ValueError('Invalid tail mass')
    return value

def exact_test(observed,p):
    q=probabilities(p);c,n=checked_counts(np.asarray(observed)[None],q)
    rows=count_vectors(int(n),len(q));logmass=multinomial_logmass(rows,q);mass=np.exp(logmass)
    stat=deviance(rows,q);obs=float(deviance(c,q)[0])
    mean=mass@rows;centered=rows-n*q
    covariance=(centered.T*mass)@centered
    expected=n*(np.diag(q)-np.outer(q,q))
    np.testing.assert_allclose(mass.sum(),1,atol=1e-11,rtol=0)
    np.testing.assert_allclose(mean,n*q,atol=1e-9,rtol=0)
    np.testing.assert_allclose(covariance,expected,atol=1e-9,rtol=0)
    result={'count_vectors':len(rows),'statistic':obs,
        'p_value':tail_probability(stat,mass,obs),'p_value_tight_ties':tail_probability(stat,mass,obs,1e-12),
        'total_mass':float(mass.sum()),'mean_max_error':float(abs(mean-n*q).max()),
        'covariance_max_error':float(abs(covariance-expected).max())}
    return result,{'counts':rows.astype(np.int16),'probability':mass,'deviance':stat}

def run(out):
    started=time.monotonic();out.mkdir(exist_ok=False);(out/'source_snapshot').mkdir()
    sources=[ROOT/'lmpf_2d'/n for n in ('exact_counts.py','verify_exact_counts.py','PLAN_EXACT_COUNTS.md')]
    sources+=[ROOT/'test_lmpf_exact_counts.py']
    for p in sources:shutil.copyfile(p,out/'source_snapshot'/p.name)
    for name,h in read(PARENT/'sha256.json').items():
        if digest(PARENT/name)!=h:raise ValueError('Changed parent result')
    parent_plan=read(PARENT/'plan.json')
    if read(PARENT/'verification/verification.json')['status']!='FROZEN_MODEL_RAW_TN_AND_ASSIGNMENT_AUDIT_PASSED':
        raise ValueError('Missing independent parent verification')
    if (parent_plan['twirl'],parent_plan['shots'],parent_plan['observables'])!=(1,[64,7,14],[8,9,22]):
        raise ValueError('Changed parent scope')
    source_inputs=[PARENT/n for n in ('plan.json','summary.json','model_predictions.json','sha256.json','verification/verification.json')]
    source_inputs+=[HARDWARE/'selected_inputs.json',HARDWARE/'plan.json',ARCHIVE/'raw_bitstrings.json',ARCHIVE/'plan.json']
    plan={'schema':'twirl1-exact-finite-counts-v1','job_id':parent_plan['job_id'],'backend':parent_plan['backend'],
        'twirl':1,'central_modes':[8,9],'shots':[64,7,14],'calibration_shots':128,
        'primary_statistic':'multinomial likelihood-ratio deviance','tail':'inclusive deviance at least observed',
        'tie_relative_tolerance':1e-10,'secondary_tie_tolerance':1e-12,
        'primary_family_size':3,'secondary_family_size':9,'adjustment':'Bonferroni','alpha':.05,
        'fixed_readout':'archived shared posterior mean','calibration_uncertainty_integrated':False,
        'iid_shots_assumed':True,'posthoc_reused_data':True,'model_fitted':False,'ideal_reference_used':False,
        'source_sha256':{str(p.relative_to(ROOT)):digest(p) for p in sources},
        'input_sha256':{str(p.relative_to(ROOT)):digest(p) for p in source_inputs},
        'process_limit_seconds':120,'new_qpu_seconds':0,'new_tn_states':0}
    write(out/'plan.json',plan)
    stream=io.StringIO();tests=unittest.TextTestRunner(stream=stream,verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromName('test_lmpf_exact_counts'))
    (out/'tests.txt').write_text(stream.getvalue(),encoding='utf-8')
    if not tests.wasSuccessful():raise RuntimeError('Tests failed')
    print('EXACT_COUNT_TESTS_PASSED',tests.testsRun,flush=True)
    inputs=read(HARDWARE/'selected_inputs.json');raw=read(ARCHIVE/'raw_bitstrings.json')
    if raw['job_id']!=plan['job_id']:raise ValueError('Wrong archived job')
    for r in inputs['target_records']+inputs['calibration_records']:
        matches=[v for v in raw['records'] if (v['setting_id'],v['twirl_id'])==(r['setting_id'],r['twirl_id'])]
        if len(matches)!=1 or matches[0]!=r:raise ValueError('Changed original record')
    model=read(PARENT/'model_predictions.json')
    if any(model[k] for k in ('operator_rescaled','noise_parameters_fitted')):raise ValueError('Modified model')
    errors=np.asarray(inputs['calibration_errors_posterior_mean'])
    records=[];arrays={};selected=[]
    for a,(r,n) in enumerate(zip(inputs['target_records'],(64,7,14))):
        if (r['factor'],r['twirl_id'],len(r['bitstrings']))!=(a+1,1,n):raise ValueError('Wrong arm')
        bitpairs=np.array([[(int(s,2)>>8)&1,(int(s,2)>>9)&1] for s in r['bitstrings']])
        counts=np.bincount(bitpairs[:,0]+2*bitpairs[:,1],minlength=4)
        mask=r['readout_mask_little_endian'][8:10];paulis=model['pauli_means'][a+1]
        q=measured_probabilities(paulis,mask,errors)
        test,dist=exact_test(counts,q)
        for key,val in dist.items():arrays[f'factor{a+1}_{key}']=val
        binary=[]
        for j,name in enumerate(('Z_up','Z_down','ZZ')):
            k=int(counts@PLUS[:,j]);pplus=float(q@PLUS[:,j])
            rec,table=exact_test([k,n-k],[pplus,1-pplus])
            rec.update({'observable':name,'plus_count':k,'n':n,'model_plus_probability':pplus,
                        'p_value_bonferroni9':min(1.,9*rec['p_value'])})
            binary.append(rec)
            for key,val in table.items():arrays[f'factor{a+1}_{name}_{key}']=val
        test.update({'factor':a+1,'shots':n,'mask':mask,'observed_counts_00_10_01_11':counts.tolist(),
            'model_physical_probabilities':joint_probabilities(paulis).tolist(),
            'model_measured_probabilities':q.tolist(),'observed_frequencies':(counts/n).tolist(),
            'p_value_bonferroni3':min(1.,3*test['p_value']),'secondary_binary_tests':binary})
        records.append(test);selected.append({'target_record':r,'counts':counts.tolist(),'mask':mask})
    write(out/'selected_inputs.json',{'targets':selected,'calibration_records':inputs['calibration_records'],
        'calibration_errors':errors.tolist(),'model_paulis':model['pauli_means'][1:]})
    np.savez_compressed(out/'enumeration.npz',**arrays)
    summary={'status':'EXACT_FINITE_COUNT_DIAGNOSTIC_COMPLETE','arms':records,
        'primary_count_vectors_total':sum(r['count_vectors'] for r in records),
        'primary_conditional_rejections_at_05':[r['factor'] for r in records if r['p_value_bonferroni3']<=.05],
        'secondary_conditional_rejections_at_05':[[r['factor'],b['observable']] for r in records for b in r['secondary_binary_tests'] if b['p_value_bonferroni9']<=.05],
        'tests_run':tests.testsRun,'seconds':time.monotonic()-started,
        'calibration_uncertainty_integrated':False,'noise_model_validated':False,'shot_noise_only_proven':False,
        'six_by_six_go':False,'new_qpu_seconds':0,'new_tn_states':0,
        'scope':'Post-hoc finite-count tail probabilities conditional on frozen approximate model, fixed shared readout and IID shots; not posterior model probabilities or held-out validation.'}
    write(out/'summary.json',summary)
    write(out/'sha256.json',{str(p.relative_to(out)):digest(p) for p in sorted(out.rglob('*')) if p.is_file()})
    print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    if args.output.exists():ap.error('Preserve existing results')
    try:
        with threadpool_limits(limits=1):run(args.output)
    except Exception as e:
        if args.output.exists():write(args.output/'failure.json',{'type':type(e).__name__,'reason':str(e),'new_qpu_seconds':0})
        raise
