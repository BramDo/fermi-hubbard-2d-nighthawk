"""Independent assignment-inverse/KKT replay of the fresh3072-shot pilot."""
from pathlib import Path
import argparse,json,sys,time
import numpy as np
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from lmpf_2d.verify_single_twirl import occupation_values
from lmpf_2d.exact_counts import read,digest
from lmpf_2d import floor_hardware as hw

def inverse_estimates(counts,errors,masks,grams,low):
    r=len(counts);e=np.broadcast_to(errors,(r,2,2));bits=np.array([[i%2,i//2] for i in range(4)])
    a=np.ones((r,4,4))
    for true in range(4):
        for measured in range(4):
            for q in range(2):
                p=e[:,0,q] if bits[true,q]==0 else 1-e[:,1,q]
                a[:,true,measured]*=p if bits[measured,q] else 1-p
    frequencies=counts/np.array([512,1024,512,512])[None,:,None]
    probabilities=np.linalg.solve(a.transpose(0,2,1),frequencies.transpose(0,2,1))
    features=[];bounds=[]
    for mask in masks:
        z=1-2*(bits^mask);f=np.column_stack([z,z[:,0]*z[:,1]]);features.append(f)
        score=np.linalg.solve(a,np.broadcast_to(f,(r,4,3)))
        bounds.append((score.max(1)-score.min(1))**2/4)
    bounds=np.stack(bounds,axis=2)
    def kkt(g,n):
        matrix=np.zeros((r,3,4,4));matrix[:,:,:3,:3]=g[None,:,1:,1:]
        for i in range(3):matrix[:,:,i,i]+=bounds[:,:,i]/n
        matrix[:,:,:3,3]=1;matrix[:,:,3,:3]=1
        rhs=np.ones((r,3,4));rhs[:,:,:3]=g[None,:,1:,0]
        return np.linalg.solve(matrix,rhs[...,None])[...,:3,0]
    floor=kkt(grams,64);old=kkt(grams,512);low_floor=kkt(low,64)
    groups=[np.einsum('rx,xo->ro',probabilities[:,:,s],features[i]) for s,i in ((0,0),(1,0),(2,1),(3,2))]
    raw=(counts[:,0]+counts[:,1])/1536@features[0]
    ro=(groups[0]+2*groups[1])/3;zne=(4*groups[0]+groups[2]-2*groups[3])/3
    arms=np.stack([groups[0],groups[2],groups[3]],axis=1)
    original=np.einsum('roa,rao->ro',old,arms);candidate=np.einsum('roa,rao->ro',floor,arms)
    return np.stack([raw,ro,zne,original,candidate],axis=1),{'floor':floor,'original':old,'low_floor':low_floor,
        'floor_penalties':bounds/64,'original_penalties':bounds/512}

def central_bits(record):
    return np.array([[int(s[::-1][8]),int(s[::-1][9])] for s in record['bitstrings']])

def verify(out):
    start=time.monotonic();dest=out/'verification';dest.mkdir(exist_ok=False)
    plan=read(out/'plan.json');summary=read(out/'summary.json');frozen=read(out/'frozen_weights.json')
    contract=read(hw.RUN/'analysis_inputs.json');selected=read(out/'selected_inputs.json')
    for name,h in read(out/'sha256.json').items():
        if digest(out/name)!=h:raise ValueError('Changed analysis output')
    for name,h in plan['source_sha256'].items():
        if digest(ROOT/name)!=h or digest(out/'source_snapshot'/Path(name).name)!=h:raise ValueError('Changed source')
    for name,h in plan['input_sha256'].items():
        if digest(ROOT/name)!=h:raise ValueError('Changed hardware input')
    if digest(hw.RUN/'analysis_inputs.json')!=plan['contract_sha256']:raise ValueError('Changed pre-dispatch analysis')
    if (contract['bootstrap_seed'],contract['bootstrap_replicates'],contract['floor_penalty_denominator'])!=(2026090922,10000,64):
        raise ValueError('Wrong predeclared analysis')
    raw=read(hw.RUN/'raw_bitstrings.json');p=read(hw.RUN/'plan.json')
    if raw['job_id']!=plan['job_id'] or summary['job_id']!=raw['job_id'] or summary['backend']!=p['backend']:
        raise ValueError('Wrong fresh job')
    for rec in selected['target_records']+selected['calibration_records']:
        matches=[r for r in raw['records'] if r['id']==rec['id']]
        if len(matches)!=1 or matches[0]!=rec:raise ValueError('Changed selected record')
    targets=selected['target_records'];cal=selected['calibration_records']
    patterns=np.array([[i%2,i//2] for i in range(4)])
    pc=np.array([[np.all(central_bits(r)==b,axis=1).sum() for b in patterns] for r in targets])
    np.testing.assert_array_equal(pc,selected['pub_counts'])
    roles=[r['role'] for r in targets];names=['shared_factor1','baseline_only_factor1','factor2','factor3']
    indices=[[i for i,r in enumerate(roles) if r==name] for name in names]
    counts=np.array([pc[x].sum(0) for x in indices])
    np.testing.assert_array_equal(counts,selected['combined_counts'])
    np.testing.assert_array_equal(counts.sum(1),[512,1024,512,512])
    errors_count=np.array([sum((central_bits(r).sum(0) if s==0 else (1-central_bits(r)).sum(0)) for r in cal if r['state']==s) for s in (0,1)])
    np.testing.assert_array_equal(errors_count,selected['calibration_error_counts'])
    e=(errors_count+.5)/257;m=np.asarray(contract['masks']);g=np.asarray(contract['grams']);low=np.asarray(contract['low_grams'])
    point,weights=inverse_estimates(counts[None],e[None],m,g,low)
    for key,value in weights.items():np.testing.assert_allclose(value[0],frozen['weights'][key],atol=1e-10,rtol=0)
    np.testing.assert_allclose(e,frozen['calibration_errors'],atol=1e-15,rtol=0)
    if frozen['target_or_reference_used_to_fit'] or frozen['raw_target_scoring_started']:raise ValueError('Wrong fit boundary')
    change=abs(weights['floor']-weights['low_floor']).sum(2)[0]
    np.testing.assert_allclose(change,frozen['chi_coefficient_l1_changes'],atol=1e-10,rtol=0)
    rng=np.random.default_rng(2026090922);draws=rng.beta(errors_count+.5,256-errors_count+.5,size=(10000,2,2))
    sampled=np.stack([rng.multinomial(r['shots'],c/r['shots'],size=10000) for r,c in zip(targets,pc)],axis=1)
    combined=np.stack([sampled[:,i].sum(1) for i in indices],axis=1)
    pauli,wd=inverse_estimates(combined,draws,m,g,low);boot=occupation_values(pauli)
    fixed=occupation_values(inverse_estimates(combined,e[None],m,g,low)[0])
    maximum={}
    with np.load(out/'bootstrap.npz',allow_pickle=False) as saved:
        np.testing.assert_array_equal(sampled,saved['sampled_pub_counts']);np.testing.assert_array_equal(draws,saved['calibration_errors'])
        np.testing.assert_array_equal(combined,saved['combined_counts'])
        for key,value in (('paulis',pauli),('physical',boot),('physical_fixed_calibration',fixed),
                          ('floor_weights',wd['floor']),('original_weights',wd['original']),('low_floor_weights',wd['low_floor'])):
            maximum[key]=float(abs(value-saved[key]).max());np.testing.assert_allclose(value,saved[key],atol=1e-10,rtol=0)
    ref=np.array(p['target']['reference'])[[8,9,22]];target=occupation_values(ref);physical=occupation_values(point)[0]
    np.testing.assert_allclose(ref,contract['reference_paulis'],atol=1e-12,rtol=0)
    np.testing.assert_allclose(target,summary['reference_physical'],atol=1e-12,rtol=0)
    methods=['raw','readout','zne','lmpf_original','lmpf_floor']
    for i,name in enumerate(methods):
        rec=summary['methods'][name]
        for key,value in (('paulis',point[0,i]),('physical',physical[i]),('signed_error',physical[i]-target),
            ('absolute_error',abs(physical[i]-target)),('bootstrap_sd',boot[:,i].std(0,ddof=1)),
            ('percentile_interval',np.quantile(boot[:,i],[.025,.975],axis=0)),('fixed_calibration_sd',fixed[:,i].std(0,ddof=1))):
            np.testing.assert_allclose(value,rec[key],atol=1e-10,rtol=0)
        z,d,zz=point[0,i];pairs=np.array([1+z+d+zz,1-z+d-zz,1+z-d-zz,1-z-d+zz])/4
        np.testing.assert_allclose(pairs,rec['joint_probabilities_00_10_01_11'],atol=1e-10,rtol=0)
        if rec['clipped'] or bool(pairs.min()>=-1e-10 and pairs.max()<=1+1e-10)!=rec['valid_point_probabilities']:
            raise ValueError('Wrong physicality/clipping report')
    for name,i in (('readout',1),('zne',2),('lmpf_original',3)):
        rec=summary['comparisons'][name]
        np.testing.assert_allclose(abs(physical[i]-target)-abs(physical[4]-target),rec['absolute_error_improvement'],atol=1e-10,rtol=0)
        interval=np.quantile(abs(boot[:,i]-target)-abs(boot[:,4]-target),[.025,.975],axis=0)
        np.testing.assert_allclose(interval,rec['paired_percentile_interval'],atol=1e-10,rtol=0)
        if bool(np.all(interval[0]>0))!=rec['all_three_lower_bounds_positive']:raise ValueError('Wrong paired-improvement flag')
    for phase in ('pre','post'):
        records=[r for r in cal if r['id'].startswith('cal_'+phase)]
        count=np.array([sum((central_bits(r).sum(0) if s==0 else (1-central_bits(r)).sum(0)) for r in records if r['state']==s) for s in (0,1)])
        np.testing.assert_array_equal(count,summary['calibration_pre_post'][phase]['error_counts'])
        np.testing.assert_allclose((count+.5)/129,summary['calibration_pre_post'][phase]['posterior_mean'],atol=1e-15,rtol=0)
    fraction=float(np.mean(np.all(abs(wd['floor']-wd['low_floor']).sum(2)<=.05,axis=1)))
    np.testing.assert_allclose(fraction,summary['bootstrap_coefficient_pass_fraction'],atol=0,rtol=0)
    if (summary['data_union_shots'],summary['primary_target_shots_each'],summary['calibration_shots'])!=(3072,1536,512):
        raise ValueError('Wrong matched shot budget')
    if summary['six_by_six_go'] or summary['quantum_advantage_proven'] or summary['equal_qpu_time_budget']:raise ValueError('Unsupported claim')
    report={'status':'FRESH_FLOOR64_ASSIGNMENT_KKT_BOOTSTRAP_AUDIT_PASSED','job_id':raw['job_id'],
        'methods_checked':5,'bootstrap_replicates_replayed':10000,'maximum_differences':maximum,
        'same_shot_comparison_verified':True,'calibration_only_fit_verified':True,'no_clipping_verified':True,
        'seconds':time.monotonic()-start}
    with (dest/'verification.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path)
    with threadpool_limits(limits=1):verify(p.parse_args().output)
