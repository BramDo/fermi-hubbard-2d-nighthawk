"""Independent nested-loop, combinatorial-mass and assignment-matrix audit."""
from pathlib import Path
import argparse,hashlib,json,math,sys,time
import numpy as np
from scipy.stats import multinomial,binom
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1]

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n')

def score(row,p):
    n=sum(row)
    return 2*math.fsum(k*(math.log(k/n)-math.log(q)) for k,q in zip(row,p) if k)

def oracle(n,p):
    if len(p)==4:
        rows=np.array([[a,b,c,n-a-b-c] for a in range(n,-1,-1)
                        for b in range(n-a,-1,-1) for c in range(n-a-b,-1,-1)],dtype=int)
    else:rows=np.array([[k,n-k] for k in range(n,-1,-1)])
    mass=[];stat=[]
    for row in rows:
        remaining=n;coefficient=1
        for k in row:
            coefficient*=math.comb(remaining,int(k));remaining-=int(k)
        mass.append(coefficient*math.prod(float(q)**int(k) for k,q in zip(row,p)))
        stat.append(score(row,p))
    return rows,np.array(mass),np.array(stat)

def independent_tail(stat,mass,observed,tol):
    return math.fsum(float(p) for g,p in zip(stat,mass) if g+tol*max(1,abs(observed))>=observed)

def verify(out):
    started=time.monotonic();dest=out/'verification';dest.mkdir(exist_ok=False)
    plan=read(out/'plan.json');summary=read(out/'summary.json');selected=read(out/'selected_inputs.json')
    if (plan['schema'],plan['shots'],plan['central_modes'],plan['twirl'])!=(
            'twirl1-exact-finite-counts-v1',[64,7,14],[8,9],1):raise ValueError('Wrong scope')
    if (plan['primary_family_size'],plan['secondary_family_size'],plan['adjustment'],plan['alpha'])!=(3,9,'Bonferroni',.05):
        raise ValueError('Changed test families')
    if (plan['tie_relative_tolerance'],plan['secondary_tie_tolerance'])!=(1e-10,1e-12):raise ValueError('Changed tie rule')
    if not plan['posthoc_reused_data'] or not plan['iid_shots_assumed']:raise ValueError('Unsupported inference scope')
    if any(plan[k] for k in ('calibration_uncertainty_integrated','model_fitted','ideal_reference_used','new_qpu_seconds','new_tn_states')):
        raise ValueError('Changed model or resource scope')
    for name,h in read(out/'sha256.json').items():
        if digest(out/name)!=h:raise ValueError('Changed output '+name)
    for name,h in plan['source_sha256'].items():
        if digest(ROOT/name)!=h or digest(out/'source_snapshot'/Path(name).name)!=h:raise ValueError('Changed source')
    for name,h in plan['input_sha256'].items():
        if digest(ROOT/name)!=h:raise ValueError('Changed parent input')
    parent=ROOT/'results_cuprate_2d/lmpf_3x3_twirl1_noise_model_2026-09-09_v2'
    model=read(parent/'model_predictions.json')
    if read(parent/'verification/verification.json')['status']!='FROZEN_MODEL_RAW_TN_AND_ASSIGNMENT_AUDIT_PASSED':
        raise ValueError('Missing parent verification')
    np.testing.assert_array_equal(selected['model_paulis'],model['pauli_means'][1:])
    archive=ROOT/'results_cuprate_2d/hardware_readout_cz_folding_3x3_2026-09-06'
    raw=read(archive/'raw_bitstrings.json');hp=read(archive/'plan.json')
    if (raw['job_id'],hp['backend'])!=(plan['job_id'],plan['backend']):raise ValueError('Changed backend or job')
    bits=lambda r:np.array([[int(s[::-1][8]),int(s[::-1][9])] for s in r['bitstrings']])
    cal=selected['calibration_records']
    if [r['state'] for r in cal]!=[0,1] or [len(r['bitstrings']) for r in cal]!=[64,64]:raise ValueError('Wrong calibration')
    errors=np.stack([bits(cal[0]).sum(0),(1-bits(cal[1])).sum(0)])
    e=(errors+.5)/65
    np.testing.assert_array_equal(e,selected['calibration_errors'])
    onebit=[np.array([[1-e[0,q],e[1,q]],[e[0,q],1-e[1,q]]]) for q in range(2)]
    assignment=np.kron(onebit[1],onebit[0])
    for r in cal+[r['target_record'] for r in selected['targets']]:
        matches=[v for v in raw['records'] if (v['setting_id'],v['twirl_id'])==(r['setting_id'],r['twirl_id'])]
        if len(matches)!=1 or matches[0]!=r:raise ValueError('Changed raw record')
    maxima={'mass':0.,'deviance':0.,'p_value':0.,'normalization':0.,'scipy_mass':0.}
    checked=[];primary_reject=[];secondary_reject=[]
    def compare_table(saved,prefix,n,p,observed,rec):
        rows,mass,stat=oracle(n,p);lookup={tuple(row):i for i,row in enumerate(rows)}
        positions=[lookup[tuple(row)] for row in saved[prefix+'_counts']]
        np.testing.assert_array_equal(rows[positions],saved[prefix+'_counts'])
        if len(positions)!=len(rows) or len(set(positions))!=len(rows):raise ValueError('Missing count vectors')
        maxima['mass']=max(maxima['mass'],float(abs(mass[positions]-saved[prefix+'_probability']).max()))
        maxima['deviance']=max(maxima['deviance'],float(abs(stat[positions]-saved[prefix+'_deviance']).max()))
        np.testing.assert_allclose(mass[positions],saved[prefix+'_probability'],atol=1e-12,rtol=1e-11)
        np.testing.assert_allclose(stat[positions],saved[prefix+'_deviance'],atol=1e-10,rtol=1e-12)
        scipy_mass=multinomial.pmf(rows,n,p) if len(p)==4 else binom.pmf(rows[:,0],n,p[0])
        maxima['scipy_mass']=max(maxima['scipy_mass'],float(abs(mass-scipy_mass).max()))
        np.testing.assert_allclose(mass,scipy_mass,atol=1e-12,rtol=1e-11)
        total=math.fsum(mass);maxima['normalization']=max(maxima['normalization'],abs(total-1))
        np.testing.assert_allclose(total,1,atol=1e-11,rtol=0)
        np.testing.assert_allclose(total,rec['total_mass'],atol=1e-11,rtol=0)
        mean=mass@rows;centered=rows-n*np.asarray(p)
        covariance=(centered.T*mass)@centered
        np.testing.assert_allclose(mean,n*np.asarray(p),atol=1e-9,rtol=0)
        np.testing.assert_allclose(covariance,n*(np.diag(p)-np.outer(p,p)),atol=1e-9,rtol=0)
        observed_stat=score(observed,p)
        np.testing.assert_allclose(observed_stat,rec['statistic'],atol=1e-10,rtol=0)
        value=independent_tail(stat,mass,observed_stat,1e-10)
        tight=independent_tail(stat,mass,observed_stat,1e-12)
        maxima['p_value']=max(maxima['p_value'],abs(value-rec['p_value']),abs(tight-rec['p_value_tight_ties']))
        np.testing.assert_allclose([value,tight],[rec['p_value'],rec['p_value_tight_ties']],atol=1e-11,rtol=0)
        if rec['count_vectors']!=len(rows):raise ValueError('Wrong enumeration count')
        return value,tight
    with np.load(out/'enumeration.npz',allow_pickle=False) as saved:
        for a,(target,rec,n) in enumerate(zip(selected['targets'],summary['arms'],(64,7,14))):
            r=target['target_record']
            if (r['factor'],r['twirl_id'],len(r['bitstrings']))!=(a+1,1,n):raise ValueError('Wrong target exposure')
            mask=r['readout_mask_little_endian'][8:10]
            counts=np.array([np.all(bits(r)==[i%2,i//2],axis=1).sum() for i in range(4)])
            np.testing.assert_array_equal(counts,target['counts'])
            np.testing.assert_array_equal(counts,rec['observed_counts_00_10_01_11'])
            np.testing.assert_array_equal(mask,target['mask']);np.testing.assert_array_equal(mask,rec['mask'])
            z,d,zz=model['pauli_means'][a+1]
            signs=np.array([[1-2*(i%2),1-2*(i//2)] for i in range(4)])
            physical=(1+signs[:,0]*z+signs[:,1]*d+np.prod(signs,axis=1)*zz)/4
            if np.any(physical<0) or np.any(physical>1):raise ValueError('Invalid model probability')
            q=assignment@physical[np.arange(4)^(int(mask[0])+2*int(mask[1]))]
            np.testing.assert_allclose(q,rec['model_measured_probabilities'],atol=1e-14,rtol=0)
            np.testing.assert_allclose(physical,rec['model_physical_probabilities'],atol=1e-14,rtol=0)
            np.testing.assert_allclose(counts/n,rec['observed_frequencies'],atol=1e-14,rtol=0)
            value,tight=compare_table(saved,f'factor{a+1}',n,q,counts,rec)
            np.testing.assert_allclose(min(1,3*value),rec['p_value_bonferroni3'],atol=1e-11,rtol=0)
            if min(1,3*value)<=.05:primary_reject.append(a+1)
            binary=[]
            for b,name,indices in zip(rec['secondary_binary_tests'],('Z_up','Z_down','ZZ'),([0,2],[0,1],[0,3])):
                count=int(counts[indices].sum());prob=float(q[indices].sum())
                if b['observable']!=name or b['plus_count']!=count or b['n']!=n:raise ValueError('Wrong binary event')
                np.testing.assert_allclose(prob,b['model_plus_probability'],atol=1e-14,rtol=0)
                bv,_=compare_table(saved,f'factor{a+1}_{name}',n,[prob,1-prob],[count,n-count],b)
                np.testing.assert_allclose(min(1,9*bv),b['p_value_bonferroni9'],atol=1e-11,rtol=0)
                if min(1,9*bv)<=.05:secondary_reject.append([a+1,name])
                binary.append({'observable':name,'p_value':bv})
            checked.append({'factor':a+1,'p_value':value,'p_value_tight_ties':tight,'binary':binary})
    if summary['primary_count_vectors_total']!=48705 or len(checked)!=3:raise ValueError('Wrong number of tests')
    if primary_reject!=summary['primary_conditional_rejections_at_05'] or secondary_reject!=summary['secondary_conditional_rejections_at_05']:
        raise ValueError('Wrong reported flags')
    if any(summary[k] for k in ('calibration_uncertainty_integrated','noise_model_validated','shot_noise_only_proven','six_by_six_go','new_qpu_seconds','new_tn_states')):
        raise ValueError('Unsupported validation claim')
    report={'status':'EXACT_COUNTS_COMBINATORIAL_AND_SCIPY_AUDIT_PASSED','primary_count_vectors_verified':48705,
        'primary_tests_verified':3,'secondary_tests_verified':9,'source_input_and_output_hashes_verified':True,
        'original_bitstrings_and_fixed_readout_verified':True,
        'maximum_differences':maxima,'independent_results':checked,'new_qpu_seconds':0,
        'noise_model_validated':False,'seconds':time.monotonic()-started}
    write(dest/'verification.json',report);print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('output',type=Path)
    with threadpool_limits(limits=1):verify(ap.parse_args().output)
