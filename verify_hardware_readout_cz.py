"""Independent offline hardware audit from provider BitArrays and inverse matrices."""
import argparse
import io
import json
from pathlib import Path
import shutil
import unittest
import numpy as np
from qiskit import qpy
import run_hardware_readout_cz_once as h

def weighted_samples(bits,mask,errors=None):
    z=1-2*bits.astype(float)
    if errors is not None:
        for q in range(18):
            e0,e1=errors[:,q]
            assignment=np.array([[1-e0,e1],[e0,1-e1]])
            weights=np.array([1.,-1.])@np.linalg.inv(assignment)
            z[:,q]=weights[bits[:,q]]
    z*=1-2*np.asarray(mask,dtype=float)
    return np.c_[z,z[:,::2]*z[:,1::2]]

def main():
    out=h.RUN
    if (out/'VERIFICATION.json').exists(): raise FileExistsError('Refuse overwrite')
    verified=h.r.stats.verify_files(out,'analysis_archive_sha256.json')
    plan,pubs=h.frozen(); raw=h.safe.read(out/'raw_bitstrings.json')
    provider=h.r.a.read(out/'provider_result_complete.json')
    result=h.safe.read(out/'analysis/results.json')
    receipt=h.safe.read(out/'job_receipt.json')
    assert raw['job_id']==receipt['job_id']==result['job_id']
    assert len(provider)==len(raw['records'])==26
    physical={}; total=0; actual_cz=0
    for i,rec in enumerate(raw['records']):
        strings=provider[i].data.meas.get_bitstrings()
        assert strings==rec['bitstrings'] and len(strings)==plan['records'][i]['shots']
        ints=np.array([int(x,2) for x in strings],dtype=np.uint32)
        bits=((ints[:,None]>>np.arange(18))&1).astype(int)
        physical[rec['setting_id'],rec['twirl_id']]=bits
        total+=len(bits)
        with (out/'provider_inputs'/f'circuit_{i:03d}.qpy').open('rb') as f: circuit=qpy.load(f)[0]
        assert circuit==pubs[i].circuit
        count=circuit.count_ops().get('cz',0)
        expected=1008*rec['factor'] if rec['role']=='target' else 0
        assert count==expected
        actual_cz+=len(bits)*count
        mapping=[(circuit.find_bit(x.qubits[0]).index,circuit.find_bit(x.clbits[0]).index)
            for x in circuit.data if x.operation.name=='measure']
        assert mapping==list(zip(plan['layout'],range(18)))
    assert total==808 and actual_cz==967680
    counts=np.array([physical['readout_all0',0].sum(axis=0),(1-physical['readout_all1',0]).sum(axis=0)])
    np.testing.assert_array_equal(counts,result['calibration']['counts'])
    errors=(counts+.5)/65
    lookup={(x['setting_id'],x['twirl_id']):x for x in plan['records']}
    groups={}; uncorrected={}
    for f in [1,2,3]:
        groups[f]=[]; uncorrected[f]=[]
        for t in range(8):
            key=f'U8_T04_factor{f}',t; mask=lookup[key]['readout_mask_little_endian']
            bits=physical[key]
            groups[f].append(weighted_samples(bits,mask,errors))
            uncorrected[f].append(weighted_samples(bits,mask))
    mean=lambda group,n:np.mean([x[:n].mean(axis=0) for x in group],axis=0)
    design=np.c_[np.ones(3),[1,2,3]]
    factors=np.array([mean(groups[f],n) for f,n in zip([1,2,3],[27,7,14])])
    raw_factors=np.array([mean(uncorrected[f],n) for f,n in zip([1,2,3],[27,7,14])])
    methods=np.array([mean(uncorrected[1],64),mean(groups[1],48),
        np.linalg.lstsq(design,factors,rcond=None)[0][0],np.linalg.lstsq(design,raw_factors,rcond=None)[0][0]])
    moment_error=float(np.max(np.abs(methods-result['method_moments'])))
    assert moment_error<1e-12
    up=(1-methods[:,:18:2])/2; down=(1-methods[:,1:18:2])/2
    pair=(methods[:,18:]-1+2*up+2*down)/4
    obs=np.stack([up+down,up-down,pair],axis=-1)
    physical_error=float(np.max(np.abs(obs-result['physical_means'])))
    assert physical_error<1e-12
    boot=np.load(out/'analysis/bootstrap.npz')['hybrid']
    exact=np.array(plan['target']['reference']); target_spin=(exact[1:18:2]-exact[:18:2])/2
    spin=(boot[:,:,1:18:2]-boot[:,:,:18:2])/2
    rmse=np.sqrt(np.mean((spin-target_spin)**2,axis=-1))
    gain=rmse[:,0]-rmse[:,2]; interval=np.quantile(gain,[.025,.975])
    np.testing.assert_allclose(interval,[result['primary_reduction_hybrid95']['low'][1],result['primary_reduction_hybrid95']['high'][1]],atol=1e-14)
    relative=(result['metrics'][0][1]-result['metrics'][2][1])/result['metrics'][0][1]
    relative_interval=np.quantile(gain/rmse[:,0],[.025,.975])
    log=io.StringIO()
    tests=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(
        ['test_hardware_readout_cz','test_aer_readout_tflo_zne','test_aer_cuprate_cz_zne_bitshots','test_aer_cuprate_cz_zne']))
    assert tests.wasSuccessful() and tests.testsRun==74
    metrics=h.safe.read(out/'provider_metrics.json')
    usage=metrics['usage']['qpu_charge_time_seconds']; assert usage<=5
    checks=h.safe.read(out/'local_verification.json')['noise_off_checks']
    report={'status':'PASS_INDEPENDENT_HARDWARE_AUDIT','job_id':receipt['job_id'],
        'actual_qpu_seconds':usage,'cap_seconds':5,'provider_pub_bitarrays_and_QPY_verified':26,
        'new_hardware_shots':total,'total_executed_CZ_applications':actual_cz,
        'independent_inverse_matrix_and_OLS_error':moment_error,'independent_physical_error':physical_error,
        'primary_spin_gain_interval_independently_reproduced':interval.tolist(),
        'relative_spin_rmse_reduction':relative,'relative_spin_reduction_hybrid95':relative_interval.tolist(),
        'maximum_noise_off_error':max(x['max_error'] for x in checks),'noise_off_checks':len(checks),
        'prior_archive_files_verified':verified,'tests':74,'resubmission_performed':False,
        'scope':'Single 3x3 hardware pilot, matched shot budgets but not gate/time budgets.'}
    h.safe.exclusive_json(out/'VERIFICATION.json',report)
    (out/'regression_tests.txt').write_text(log.getvalue(),encoding='utf-8')
    (out/'VERIFICATION.md').write_text('# Independent hardware verification\n\nExecuted from provider BitArrays using separate inverse matrices and an OLS solve.\n\n```json\n'+json.dumps(report,indent=2)+'\n```\n',encoding='utf-8')
    shutil.copyfile(Path(__file__),out/'verification_source.py')
    h.safe.exclusive_json(out/'verified_archive_sha256.json',{str(p.relative_to(out)):h.safe.digest(p)
        for p in out.rglob('*') if p.is_file() and p.name!='status_history.jsonl'})
    print(json.dumps(report),flush=True)

def finalize():
    out=h.RUN
    if (out/'delivery_sha256.json').exists(): raise FileExistsError('Refuse overwrite')
    h.r.stats.verify_files(out,'verified_archive_sha256.json')
    h.frozen()
    result=h.safe.read(out/'analysis/results.json')
    audit=h.safe.read(out/'VERIFICATION.json')
    assert (out/'BEVINDINGEN.md').is_file()
    completion={'status':'COMPLETE_HARDWARE_PILOT_SPIN_IMPROVED_SITE_CHARGE_WORSENED',
        'job_id':audit['job_id'],'actual_qpu_seconds':audit['actual_qpu_seconds'],'cap_seconds':5,
        'hardware_shots':808,'provider_circuits_verified':26,'tests':74,
        'relative_spin_rmse_reduction':audit['relative_spin_rmse_reduction'],
        'relative_spin_reduction_hybrid95':audit['relative_spin_reduction_hybrid95'],
        'charge_rmse_increased':True,'doublon_improvement_resolved':False,
        'no_repetition':True,'equal_gate_or_time_budget':False,'quantum_advantage_claim':False}
    h.safe.exclusive_json(out/'COMPLETION.json',completion)
    shutil.copyfile(Path(__file__),out/'finalization_source.py')
    h.safe.exclusive_json(out/'delivery_sha256.json',{str(p.relative_to(out)):h.safe.digest(p)
        for p in out.rglob('*') if p.is_file() and p.name!='status_history.jsonl'})
    completion['verified_delivery_files']=h.r.stats.verify_files(out,'delivery_sha256.json')
    print(json.dumps(completion),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--finalize',action='store_true')
    (finalize if parser.parse_args().finalize else main)()
