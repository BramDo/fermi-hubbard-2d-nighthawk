"""Offline equal-512-bitshot comparison, with shared factor1 prefix."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import shutil
import time
import unittest
import numpy as np
from qiskit import qpy
from qiskit_aer import AerSimulator
from qiskit_ibm_runtime.models import BackendProperties
import aer_cuprate_cz_zne as z
from cuprate_2d_tflo import decode_bitstrings, pauli_samples

PARENT=z.c.a.RESULTS/'aer_nighthawk_cz_gatefold_zne_T04_v2'
COUNTS=(64,9,18)
ALLOCATION=(37,9,18)
BASES=(2027100000,2027200000,2027300000)
SOURCES=['aer_cuprate_cz_zne_bitshots.py','analyze_aer_cuprate_cz_zne_bitshots.py',
 'test_aer_cuprate_cz_zne_bitshots.py','verify_aer_cuprate_cz_zne_bitshots.py',
 'AER_CZ_ZNE_BITSHOTS_512_PROTOCOL.md','aer_cuprate_cz_zne.py',
 'aer_cuprate_cz_half_v2.py','aer_cuprate_cz_half.py','aer_cuprate_noise_components.py',
 'aer_cuprate_nighthawk_smoke.py','aer_cuprate_gate_split.py',
 'analyze_aer_noise_components.py','cuprate_2d_tflo.py','test_aer_cuprate_cz_zne.py',
 'analyze_aer_cuprate_cz_zne.py','verify_aer_noise_components.py']

def seed_for(group,twirl):
    if group not in range(3) or twirl not in range(8):
        raise ValueError('Invalid group/twirl')
    return BASES[group]+1000*twirl

def check_measured(circuit):
    if circuit.num_qubits!=circuit.num_clbits or circuit.count_ops().get('measure',0)!=circuit.num_qubits:
        raise ValueError('Require full identity-mapped measurements')
    seen=set()
    for item in circuit.data:
        if item.operation.name.startswith('save_'):
            raise ValueError('No saves in production bitshot circuit')
        if item.operation.name=='measure':
            q=circuit.find_bit(item.qubits[0]).index
            b=circuit.find_bit(item.clbits[0]).index
            if q!=b or q in seen:
                raise ValueError('Measurement mapping changed')
            seen.add(q)
        elif seen and item.operation.name!='barrier':
            raise ValueError('Nonterminal measurement')
    if seen!=set(range(circuit.num_qubits)):
        raise ValueError('Missing measured qubit')

def binary_memory(raw,width):
    result=[]
    for value in raw['results'][0]['data']['memory']:
        if not isinstance(value,str) or not value.startswith('0x'):
            raise ValueError('Require raw hexadecimal Aer memory')
        integer=int(value,16)
        if integer<0 or integer>=2**width:
            raise ValueError('Memory exceeds width')
        result.append(format(integer,f'0{width}b'))
    return result

def canonical_measured(measured):
    """Match the previous pilot's global order without retaining Aer saves."""
    check_measured(measured)
    prepared=z.prepare_base(measured)
    out=measured.copy_empty_like()
    out.global_phase=prepared.global_phase
    for item in prepared.data:
        if not item.operation.name.startswith('save_'):
            out.append(item.operation.copy(),
                       [prepared.find_bit(q).index for q in item.qubits],
                       [prepared.find_bit(c).index for c in item.clbits])
    for item in measured.data:
        if item.operation.name=='measure':
            out.append(item.operation.copy(),
                       [measured.find_bit(q).index for q in item.qubits],
                       [measured.find_bit(c).index for c in item.clbits])
    rows=lambda q:[r for r in z.instruction_rows(q) if r[0] in z.c.a.NATIVE]
    old,new=rows(measured),rows(out)
    for qubit in range(measured.num_qubits):
        assert [r for r in old if qubit in r[1]]==[r for r in new if qubit in r[1]]
    assert rows(out)==rows(prepared)
    check_measured(out)
    return out

def check_saved_counts(raw,memory,width):
    expected={format(int(k,16),f'0{width}b'):int(v)
              for k,v in raw['results'][0]['data']['counts'].items()}
    if Counter(memory)!=expected:
        raise AssertionError('Counts differ from memory')

def run(out,resume=False):
    started=time.perf_counter()
    z.analysis.verify_files(PARENT,'final_archive_sha256.json')
    parent=z.c.a.read(PARENT/'plan.json')
    old_folds={(r['group'],r['twirl']):r for r in z.c.a.read(PARENT/'preflight.json')['checks']}
    inputs=[z.c.a.ROOT/name for name in SOURCES]+[PARENT/'plan.json',PARENT/'preflight.json',
        PARENT/'full_noise.json',PARENT/'final_archive_sha256.json',
        z.c.BASELINE/'restricted_backend_properties.json',z.h.PARENT/'decomposition.json']
    inputs += [z.c.BASELINE/'circuits'/f'twirl_{t}.qpy' for t in range(8)]
    hashes={str(p.relative_to(z.c.a.ROOT)):z.c.a.digest(p) for p in inputs}
    if out.exists():
        if not resume or (out/'run_summary.json').exists():
            raise ValueError('Refuse overwrite/resampling')
        if z.c.a.read(out/'plan.json')['input_sha256']!=hashes:
            raise ValueError('Resume input mismatch')
    else:
        if resume:
            raise ValueError('Cannot resume missing output')
        out.mkdir(parents=True)
        for folder in ['source_snapshot','circuits','blocks']:
            (out/folder).mkdir()
        for name in SOURCES:
            shutil.copyfile(z.c.a.ROOT/name,out/'source_snapshot'/name)
        z.c.a.write(out/'plan.json',{'schema':'equal512-bitshot-cz-zne-v1',
            'setting':parent['setting'],'layout':parent['layout'],'records':parent['records'],
            'run_shots_per_twirl':COUNTS,'zne_shots_per_twirl':ALLOCATION,
            'raw_arm_shots':512,'zne_arm_shots':512,'union_new_bitshots':728,
            'shared_factor1_prefix_per_twirl':37,'seed_bases':BASES,'seed_stride':1000,
            'bootstrap_seed':2027400000,'bootstrap_repetitions':2000,
            'linear_weights':[4/3,1/3,-2/3],'quadratic_secondary_weights':[3,-3,1],
            'readout_sampled_by_aer':True,'analytic_readout_applied':False,
            'conditional_expectations_used_in_production':False,
            'raw_cz_applications':516096,'zne_cz_applications':878976,'cz_cost_ratio':1.703125,
            'not_equal_gate_or_time_budget':True,'max_runner_seconds':1800,
            'method':'statevector','precision':'double','max_parallel_threads':2,
            'qiskit':z.c.a.qiskit.__version__,'aer':z.c.a.qiskit_aer.__version__,
            'new_qpu_seconds':0,'input_sha256':hashes,
            'created_utc':datetime.now(timezone.utc).isoformat()})
    plan=z.c.a.read(out/'plan.json')
    log=io.StringIO()
    suite=unittest.defaultTestLoader.loadTestsFromNames(['test_aer_cuprate_cz_zne_bitshots','test_aer_cuprate_cz_zne'])
    tests=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    if not tests.wasSuccessful():
        raise AssertionError(log.getvalue())
    if not (out/'preflight_unit_tests.txt').exists():
        (out/'preflight_unit_tests.txt').write_text(log.getvalue(),encoding='utf-8')
    props=BackendProperties.from_dict(z.c.a.read(z.c.BASELINE/'restricted_backend_properties.json'))
    noise,_=z.h.scaled_full_model(props,z.c.a.read(z.h.PARENT/'decomposition.json'),1.)
    model_audit=z.h.validate_saved_control(noise,z.c.a.read(PARENT/'full_noise.json'))
    if not (out/'noise_model.json').exists():
        z.c.a.write(out/'noise_model.json',noise.to_dict(serializable=True))
    labels=[seed_for(g,t)+s for g in range(3) for t in range(8) for s in range(COUNTS[g])]
    assert len(labels)==len(set(labels))==728
    ideal=AerSimulator(method='statevector',precision='double',max_parallel_threads=1,enable_truncation=False)
    exact=np.asarray(plan['setting']['reference'])
    checks,circuits=[],{}
    for t in range(8):
        with (z.c.BASELINE/'circuits'/f'twirl_{t}.qpy').open('rb') as handle:
            base=canonical_measured(qpy.load(handle)[0])
        for g in range(3):
            circuit,audit=z.fold_cz(base,g+1,2026300000+1000*t)
            check_measured(circuit)
            assert circuit.num_qubits==18 and audit['folded_cz']==1008*(g+1)
            if g:
                assert audit['selected_original_indices']==old_folds[g,t]['folding']['selected_original_indices']
            result=ideal.run(z.c.expectation_circuit(circuit),shots=1).result()
            p=z.c.unmask_paulis(z.c.extract_expectations(result,18,1),plan['records'][t]['readout_mask_little_endian'])
            error=float(np.max(np.abs(p[0]-exact)))
            assert result.success and error<1e-9
            target=out/'circuits'/f'{g}_{t}.qpy'
            if not target.exists():
                with target.open('wb') as handle:
                    qpy.dump(circuit,handle)
            with target.open('rb') as handle:
                loaded=qpy.load(handle)[0]
            check_measured(loaded)
            assert z.instruction_rows(loaded)==z.instruction_rows(circuit)
            circuits[g,t]=loaded
            checks.append({'group':g,'twirl':t,'noise_off_error':error,'folding':audit})
    if not (out/'preflight.json').exists():
        z.c.a.write(out/'preflight.json',{'status':'PASS','tests':tests.testsRun,'model_audit':model_audit,
            'unique_run_seed_labels':len(set(labels)),'checks':checks})
    print(json.dumps({'stage':'PREFLIGHT_PASS','tests':tests.testsRun,
        'max_noise_off_error':max(x['noise_off_error'] for x in checks),'new_bitshots':728}),flush=True)
    sim=AerSimulator(method='statevector',precision='double',noise_model=noise,
        max_parallel_threads=2,max_parallel_shots=2,enable_truncation=False)
    for g in range(3):
        for t in range(8):
            if time.perf_counter()-started>1800:
                raise TimeoutError('Runner time limit; partial results preserved')
            block=out/'blocks'/f'{g}_{t}'
            if (block/'sha256.json').exists():
                z.analysis.verify_files(block,'sha256.json')
                rec=z.c.a.read(block/'record.json')
                assert rec['seed']==seed_for(g,t) and rec['shots']==COUNTS[g]
                continue
            if block.exists():
                raise ValueError('Partial block exists; inspect before retry')
            tick=time.perf_counter()
            result=sim.run(circuits[g,t],shots=COUNTS[g],memory=True,seed_simulator=seed_for(g,t)).result()
            elapsed=time.perf_counter()-tick
            raw=result.to_dict()
            memory=result.get_memory(0)
            meta=result.results[0].metadata
            assert result.success and len(memory)==COUNTS[g]
            assert meta['num_qubits']==18 and meta['noise']=='kraus' and not meta['measure_sampling']
            assert binary_memory(raw,18)==memory
            check_saved_counts(raw,memory,18)
            bits=decode_bitstrings(memory,18,plan['records'][t]['readout_mask_little_endian'])
            block.mkdir()
            z.c.a.write(block/'record.json',{'group':g,'factor':g+1,'twirl':t,'seed':seed_for(g,t),
                'shots':COUNTS[g],'bitstrings':memory,'decoded_bits':bits.tolist(),
                'pauli_samples':pauli_samples(bits).tolist(),'run_wall_seconds':elapsed})
            z.c.a.write(block/'aer_result.json',raw)
            z.c.a.write(block/'sha256.json',{p.name:z.c.a.digest(p) for p in block.iterdir() if p.is_file()})
            print(json.dumps({'factor':g+1,'completed_twirls':t+1,
                'completed_factor_bitshots':(t+1)*COUNTS[g],'seconds':elapsed}),flush=True)
    z.verify_inputs(plan)
    z.c.a.write(out/'run_summary.json',{'status':'COMPLETE_EQUAL512_BITSHOTS',
        'new_qpu_seconds':0,'new_bitshots':728,'raw_arm_shots':512,'zne_arm_shots':512,
        'group_run_seconds':{str(g+1):sum(z.c.a.read(out/'blocks'/f'{g}_{t}'/'record.json')
            ['run_wall_seconds'] for t in range(8)) for g in range(3)},
        'runner_elapsed_seconds':time.perf_counter()-started})
    z.c.a.write(out/'run_archive_sha256.json',{str(p.relative_to(out)):z.c.a.digest(p)
        for p in out.rglob('*') if p.is_file()})
    print(json.dumps(z.c.a.read(out/'run_summary.json')),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--resume',action='store_true')
    args=parser.parse_args()
    run(args.output.resolve(),args.resume)
