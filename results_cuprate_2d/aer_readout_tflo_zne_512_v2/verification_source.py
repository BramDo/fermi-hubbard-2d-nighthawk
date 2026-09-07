"""Independent bit-level, matrix-inverse, cost and fit audit; no resampling."""
import argparse
import json
from pathlib import Path
import shutil
import numpy as np
from qiskit import qpy
import aer_readout_tflo_zne as r

def physical_bits(folder):
    record=r.a.read(folder/'record.json')
    raw=r.a.read(folder/'aer_result.json')
    strings=raw['results'][0]['data']['memory']
    ints=np.array([int(x,16) for x in strings],dtype=np.uint32)
    bits=((ints[:,None]>>np.arange(18))&1).astype(float)
    printed=[format(int(x),'018b') for x in ints]
    assert printed==record['bitstrings']
    unique,counts=np.unique(ints,return_counts=True)
    actual={int(k,16):v for k,v in raw['results'][0]['data']['counts'].items()}
    assert dict(zip(unique.tolist(),counts.tolist()))==actual
    return bits

def direct_weights(bits,mask,errors=None):
    z=1-2*bits
    if errors is not None:
        for q in range(18):
            e0,e1=errors[:,q]
            assignment=np.array([[1-e0,e1],[e0,1-e1]])
            weights=np.array([1.,-1.])@np.linalg.inv(assignment)
            z[:,q]=weights[bits[:,q].astype(int)]
    z*=1-2*np.asarray(mask,dtype=float)
    return np.c_[z,z[:,::2]*z[:,1::2]]

def fit_independent(training,refs,times,target):
    output=[]
    beta=[]
    for q in range(27):
        design=np.c_[training[:,q],times/np.ptp(times),np.ones(6)]
        # Normal equations independent of production's augmented-design SVD fit.
        coeff=np.linalg.solve(design.T@design+.001*np.eye(3),design.T@refs[:,q]+.001*np.array([1,0,0]))
        beta.append(coeff)
        output.append(coeff@np.array([target[q],.4/np.ptp(times),1]))
    return np.array(output),np.array(beta)

def main(out):
    if (out/'VERIFICATION.json').exists(): raise ValueError('Refuse overwrite')
    nfiles=r.stats.verify_files(out,'final_sha256.json')
    parent_files=r.stats.verify_files(r.PARENT,'final_archive_sha256.json')
    plan=r.a.read(out/'plan.json'); result=r.a.read(out/'analysis/results.json')
    r.verify_inputs(plan)
    cal0=physical_bits(out/'blocks/cal_0'); cal1=physical_bits(out/'blocks/cal_1')
    counts=np.array([cal0.sum(axis=0),(1-cal1).sum(axis=0)])
    np.testing.assert_array_equal(counts,result['calibration']['error_counts'])
    errors=(counts+.5)/65
    masks=plan['masks']
    target={}; raw={}
    actual_selected_cz=0
    for g,n in enumerate([27,7,14]):
        target[g]=[]; raw[g]=[]
        for t in range(8):
            bits=physical_bits(r.PARENT/'blocks'/f'{g}_{t}')
            target[g].append(direct_weights(bits,masks[t],errors))
            raw[g].append(direct_weights(bits,masks[t]))
            with (r.PARENT/'circuits'/f'{g}_{t}.qpy').open('rb') as f:
                qc=qpy.load(f)[0]
            assert qc.count_ops()['cz']==1008*(g+1)
            actual_selected_cz+=n*qc.count_ops()['cz']
    assert actual_selected_cz==669312==plan['cz_applications']['readout_zne']
    train=[]; train_raw=[]; train_cz=0
    for s in range(6):
        blocks=[]; rawblocks=[]
        assert plan['settings'][s]['role']=='train' and plan['settings'][s]['u_over_t']==0
        for t in range(8):
            bits=physical_bits(out/'blocks'/f'train_{s}_{t}')
            assert len(bits)==4
            blocks.append(direct_weights(bits,masks[t],errors).mean(axis=0))
            rawblocks.append(direct_weights(bits,masks[t]).mean(axis=0))
            with (out/'circuits'/f'train_{s}_{t}.qpy').open('rb') as f:
                qc=qpy.load(f)[0]
            train_cz+=4*qc.count_ops()['cz']
        train.append(np.mean(blocks,axis=0)); train_raw.append(np.mean(rawblocks,axis=0))
    train,train_raw=np.array(train),np.array(train_raw)
    assert train_cz+192*1008==387072
    mean=lambda data,n:np.mean([x[:n].mean(axis=0) for x in data],axis=0)
    refs=np.array([s['reference'] for s in plan['settings']]); times=np.array([s['time'] for s in plan['settings']])
    tflo,coef=fit_independent(train,refs,times,mean(target[0],24))
    tflo_raw,_=fit_independent(train_raw,refs,times,mean(raw[0],24))
    design=np.c_[np.ones(3),[1,2,3]]
    zne=np.linalg.lstsq(design,np.array([mean(target[g],n) for g,n in enumerate([27,7,14])]),rcond=None)[0][0]
    zne_raw=np.linalg.lstsq(design,np.array([mean(raw[g],n) for g,n in enumerate([27,7,14])]),rcond=None)[0][0]
    methods=np.array([mean(raw[0],64),mean(target[0],48),tflo,zne,tflo_raw,zne_raw,refs[4]])
    error=float(np.max(np.abs(methods-result['method_moments'])))
    coeff_error=float(np.max(np.abs(coef-result['tflo_fit']['coefficients'])))
    assert error<1e-10 and coeff_error<1e-10
    # Density/product construction independent of the production physical_observables function.
    up=(1-methods[:,:18:2])/2; down=(1-methods[:,1:18:2])/2
    doublon=(methods[:,18:]-1+2*up+2*down)/4
    physical=np.stack([up+down,up-down,doublon],axis=-1)
    p_error=float(np.max(np.abs(physical-result['physical_means'])))
    assert p_error<1e-10
    boot=np.load(out/'analysis/bootstrap.npz')['hybrid']
    exact=np.array(plan['target']['reference'])
    target_spin=(exact[1:18:2]-exact[:18:2])/2
    spin=(boot[:,:,1:18:2]-boot[:,:,:18:2])/2
    rmse=np.sqrt(np.mean((spin-target_spin)**2,axis=-1))
    interval=np.quantile(rmse[:,3]-rmse[:,2],[.025,.975])
    np.testing.assert_allclose(interval,[result['primary_hybrid_interval95']['low'],result['primary_hybrid_interval95']['high']],atol=1e-14)
    checks=r.a.read(out/'preflight.json')
    assert len(checks['checks'])==48
    max_ideal=max(x['noise_off_error'] for x in checks['checks'])
    assert max_ideal<1e-9
    report={'status':'PASS_INDEPENDENT_AUDIT','parent_files_verified':parent_files,'run_files_verified':nfiles,
        'independent_method_moment_error':error,'independent_ridge_coefficient_error':coeff_error,
        'independent_physical_observable_error':p_error,'primary_interval_independently_reproduced':interval.tolist(),
        'noise_off_checks':48,'maximum_noise_off_error':max_ideal,'model_audit':checks['model_audit'],
        'new_measured_aer_shots':320,'equal_main_arm_shots':512,'equal_gate_time_budget':False,
        'readout_tflo_cz':387072,'readout_zne_cz':669312,'new_qpu_seconds':0,
        'first_preflight_failure_preserved':'aer_readout_tflo_zne_512_v1: zero sampled shots',
        'budget_test_correction_before_sampling':'28/7/13 corrected to actual discrete optimum27/7/14',
        'uncertainty_scope':'Exploratory hybrid bootstrap/calibration-posterior interval, not certified CI.'}
    r.a.write(out/'VERIFICATION.json',report)
    shutil.copyfile(Path(__file__),out/'verification_source.py')
    (out/'VERIFICATION.md').write_text('# Independent verification\n\nExecuted bit-level inverse-matrix and normal-equation checks (NumPy).\n\n```json\n'+json.dumps(report,indent=2)+'\n```\n',encoding='utf-8')
    r.a.write(out/'completed_sha256.json',{str(p.relative_to(out)):r.a.digest(p) for p in out.rglob('*') if p.is_file()})
    print(json.dumps(report),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('output',type=Path)
    main(parser.parse_args().output.resolve())
