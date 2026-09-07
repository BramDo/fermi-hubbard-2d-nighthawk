"""Independent offline verification of the frozen 6x6 hardware results.
No provider calls. Native readout inversion precedes terminal-mask decoding.
"""
import argparse
from datetime import datetime
import io
import json
from pathlib import Path
import shutil
import unittest
import numpy as np
from qiskit import qpy
from qiskit_ibm_runtime import RuntimeDecoder
import run_hardware_6x6_rocz_once as h

def independent_pair_probabilities(bits,mask,errors=None):
    """P(up,down) ordered00,01,10,11, from native shot bits."""
    result=[]
    for site in range(36):
        q0,q1=2*site,2*site+1
        counts=np.bincount(2*bits[:,q0]+bits[:,q1],minlength=4)/len(bits)
        if errors is not None:
            matrices=[]
            for q in (q0,q1):
                e0,e1=errors[:,q]
                matrices.append(np.array([[1-e0,e1],[e0,1-e1]]))
            counts=np.linalg.solve(np.kron(*matrices),counts)
        permutation=np.arange(4)^(2*int(mask[q0])+int(mask[q1]))
        result.append(counts[permutation])
    return np.asarray(result)

def pair_observables(probs):
    return np.stack([probs[...,1]+probs[...,2]+2*probs[...,3],
        probs[...,2]-probs[...,1],probs[...,3]],axis=-1)

def main(extra):
    out=h.RUN
    if (out/'VERIFICATION.json').exists(): raise FileExistsError('Do not overwrite verification')
    manifests=['frozen_inputs_sha256.json','implementation_revision2_sha256.json',
        'preflight_sha256.json','hardware_archive_sha256.json','analysis_archive_sha256.json']
    for manifest in manifests: h.verify_files(out,manifest)
    h.verify_files(h.CLASSICAL,'sha256.json')
    plan=h.safe.read(out/'plan.json')
    for name,digest in plan['input_sha256'].items():
        h.require(h.safe.digest(h.ROOT/name)==digest,'Source or classical input changed')
    for name in ('run_hardware_6x6_rocz_checked.py','test_hardware_6x6_quota.py'):
        h.require(h.safe.digest(h.ROOT/name)==h.safe.digest(out/'source_snapshot'/name),'Revision changed')
    provider=json.loads((out/'provider_result_complete.json').read_text(),cls=RuntimeDecoder)
    raw=h.safe.read(out/'raw_bitstrings.json'); result=h.safe.read(out/'analysis/results.json')
    receipt=h.safe.read(out/'job_receipt.json'); retrieval=h.safe.read(out/'retrieval_verification.json')
    h.require(raw['job_id']==receipt['job_id']==result['job_id']==retrieval['job_id'],'Wrong job')
    h.require(len(provider)==len(raw['records'])==26,'Wrong record count')
    h.validate_records(raw['records'])
    blocks={}; total=0; cz_applications=0; native_bits={}; semantic_fallback=[]
    for i,rec in enumerate(raw['records']):
        bitarray=provider[i].data.meas
        h.require(bitarray.shape==() and bitarray.num_bits==72 and bitarray.num_shots==512,'Wrong BitArray shape')
        strings=bitarray.get_bitstrings()
        h.require(strings==rec['bitstrings'] and len(strings)==512,'Bitstring archive mismatch')
        h.require(all(len(s)==72 and set(s)<={'0','1'} for s in strings),'Invalid strings')
        bits=np.array([[ord(c)-48 for c in s[::-1]] for s in strings],dtype=np.int64)
        native_bits[rec['setting_id'],rec['twirl_id']]=bits
        meta=provider[i].metadata['circuit_metadata']
        h.require(meta['hardware_rocz_index']==i and meta['hardware_rocz_plan_sha256']==receipt['plan_sha256'],'Result metadata mismatch')
        expected=out/'bound_inputs'/f'circuit_{i:03d}.qpy'
        actual=out/'provider_inputs'/f'circuit_{i:03d}.qpy'
        if h.safe.digest(expected)!=h.safe.digest(actual):
            with expected.open('rb') as f: wanted=qpy.load(f)[0]
            with actual.open('rb') as f: received=qpy.load(f)[0]
            h.require(received==wanted,'Actual provider circuit differs')
            semantic_fallback.append(i)
        total+=len(bits)
        cz_applications+=len(bits)*(15400*rec['factor'] if rec['role']=='target' else 0)
    h.require(total==13312 and cz_applications==378470400,'Wrong total exposure')
    counts=np.array([native_bits['readout_all0',0].sum(axis=0),
        (1-native_bits['readout_all1',0]).sum(axis=0)])
    errors=(counts+.5)/513
    np.testing.assert_allclose(errors,result['readout_error_rates_Jeffreys'],atol=0,rtol=0)
    original=[]; corrected=[]; sectors=[]
    lookup={(r['setting_id'],r['twirl_id']):r for r in raw['records']}
    for factor in (1,2,3):
        rp=[]; cp=[]; retained=0
        for t in range(8):
            key=f'U8_T04_factor{factor}',t
            bits=native_bits[key]; mask=np.array(lookup[key]['readout_mask_little_endian'])
            rp.append(independent_pair_probabilities(bits,mask))
            cp.append(independent_pair_probabilities(bits,mask,errors))
            decoded=bits^mask
            retained+=int(np.sum((decoded[:,::2].sum(axis=1)==16)&(decoded[:,1::2].sum(axis=1)==16)))
        original.append(np.mean(rp,axis=0)); corrected.append(np.mean(cp,axis=0))
        sectors.append({'factor':factor,'Nup16_Ndown16_fraction':retained/4096,'postselection_applied':False})
    original=np.array(original); corrected=np.array(corrected)
    design=np.c_[np.ones(3),[1,2,3]]
    fitted=np.linalg.lstsq(design,corrected.reshape(3,-1),rcond=None)[0][0].reshape(36,4)
    fitted_raw=np.linalg.lstsq(design,original.reshape(3,-1),rcond=None)[0][0].reshape(36,4)
    independent=pair_observables(np.array([original[0],corrected[0],fitted,fitted_raw]))
    reported=np.array([r['physical_charge_spin_doublon'] for r in result['arms']])
    max_error=float(np.max(np.abs(independent-reported)))
    h.require(max_error<1e-12,'Independent native-inverse and OLS mismatch')
    with np.load(out/'analysis/bootstrap.npz') as archive:
        boot=np.array(archive['physical'])
        h.require(boot.shape==(2000,4,36,3) and np.all(np.isfinite(boot)),'Invalid bootstrap output')
    for i,row in enumerate(result['arms']):
        np.testing.assert_allclose(np.quantile(boot[:,i],[.025,.975],axis=0),
            row['physical_95pct_intervals'],rtol=0,atol=1e-13)
    references=h.safe.read(h.CLASSICAL/'summary.json')['results']
    extra_hashes={}
    for path in extra:
        path=path.resolve()
        h.require(path.is_file() and path.is_relative_to(h.ROOT),'Extra reference must be in project')
        extra_root=path.parent.parent
        h.verify_files(extra_root,'sha256.json')
        # This manifest deliberately links its verifier two levels up in ROOT.
        for name,digest in h.safe.read(extra_root/'verification_sha256.json').items():
            referenced=(extra_root/name).resolve()
            h.require(referenced.is_relative_to(h.ROOT) and h.safe.digest(referenced)==digest,
                'Extra classical verification hash mismatch')
        independent_check=h.safe.read(extra_root/'INDEPENDENT_VERIFICATION.json')
        h.require(independent_check['status']=='PASS','Extra classical verification failed')
        ref=h.safe.read(path)
        h.require(ref['config']==plan['config'] and ref['status']=='COMPLETE','Extra reference config/status mismatch')
        references.append({**ref,'profile':str(path.relative_to(h.ROOT))})
        extra_hashes[str(path.relative_to(h.ROOT))]=h.safe.digest(path)
    comparisons=[]
    for ref in references:
        if ref['config']['lx']!=6: continue
        reference=np.asarray(ref['physical_means'])
        rms=np.sqrt(np.mean((independent-reference)**2,axis=1))
        boot_rms=np.sqrt(np.mean((boot-reference)**2,axis=2))
        gain=boot_rms[:,0]-boot_rms[:,2]
        comparisons.append({'classical_profile':ref['profile'],'chi':ref['chi'],
            'classical_kernel_seconds':ref['kernel_seconds'],
            'RMS_discrepancies_charge_spin_doublon_by_arm':rms.tolist(),
            'raw_minus_readoutZNE_discrepancy':(rms[0]-rms[2]).tolist(),
            'raw_minus_readoutZNE_discrepancy_hybrid95':np.quantile(gain,[.025,.975],axis=0).tolist(),
            'reference_certified':False})
    metrics=h.safe.read(out/'provider_metrics.json')
    qpu=metrics['usage']['qpu_charge_time_seconds']
    h.require(metrics['usage']['status']=='complete' and qpu<=15,'Usage mismatch')
    times=metrics['timestamps']
    service_seconds=(datetime.fromisoformat(times['finished'].replace('Z','+00:00'))-
        datetime.fromisoformat(times['created'].replace('Z','+00:00'))).total_seconds()
    log=io.StringIO()
    tests=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(
        ['test_hardware_6x6_rocz','test_hardware_6x6_quota','test_benchmark_fermionic_6x6_mps',
         'test_continue_fermionic_6x6_chi64']))
    h.require(tests.wasSuccessful() and tests.testsRun==41,'Regression tests failed')
    audit={'status':'PASS_INDEPENDENT_6X6_RESULT_AUDIT','job_id':receipt['job_id'],'actual_shots':total,
        'provider_circuits_verified':26,'QPY_byte_identical_count':26-len(semantic_fallback),
        'QPY_semantic_fallback_indices':semantic_fallback,'shot_weighted_CZ_applications':cz_applications,
        'independent_native_readout_inverse_and_OLS_max_error':max_error,'regression_tests':41,
        'qpu_charge_seconds':qpu,'qpu_cap_seconds':15,'provider_created_to_finished_seconds':service_seconds,
        'local_prepare_seconds':h.safe.read(out/'local_verification.json')['local_prepare_seconds'],
        'classical_comparisons':comparisons,'extra_reference_sha256':extra_hashes,
        'observed_sector_fractions_diagnostic_only':sectors,
        'calibration_max_error':float(errors.max()),'calibration_min_inverse_denominator':float((1-errors.sum(axis=0)).min()),
        'no_postselection_or_clipping':True,'quantum_advantage_demonstrated':False,
        'uncertainty_scope':result['uncertainty_scope'],
        'notes':'All-reference discrepancies are not exact-reference errors. Do not select a classical chi based on agreement with hardware. Timing definitions differ and classical convergence is assessed separately.'}
    h.safe.exclusive_json(out/'VERIFICATION.json',audit)
    (out/'regression_tests.txt').write_text(log.getvalue(),encoding='utf-8')
    shutil.copyfile(Path(__file__),out/'verification_source.py')
    h.safe.exclusive_json(out/'verified_archive_sha256.json',{str(p.relative_to(out)):h.safe.digest(p)
        for p in out.rglob('*') if p.is_file() and p.name!='status_history.jsonl'})
    print(json.dumps({'status':audit['status'],'shots':total,'qpu_seconds':qpu,'tests':41,
        'independent_max_error':max_error,'comparisons':comparisons}),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--classical-extra',type=Path,action='append',default=[])
    main(parser.parse_args().classical_extra)
