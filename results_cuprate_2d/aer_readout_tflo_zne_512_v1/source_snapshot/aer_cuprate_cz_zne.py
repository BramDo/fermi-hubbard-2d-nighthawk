"""Offline CZ gate-folding ZNE pilot; no provider or hardware submission."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import shutil
import time
import unittest
import numpy as np
from qiskit import qpy
from qiskit.quantum_info import SuperOp
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, ReadoutError
from qiskit_ibm_runtime.models import BackendProperties
import aer_cuprate_noise_components as c
import aer_cuprate_cz_half_v2 as h
import analyze_aer_noise_components as analysis

PARENT = c.a.RESULTS/'aer_nighthawk_full_cz_half_T04_v2_disjoint_seeds'
GROUPS = ['factor1_reused', 'factor2_folded', 'factor3_folded', 'cz_noise_off_diagnostic']
BASES = [2026100000,2026400000,2026500000,2026600000]
N = 16
SOURCES = ['aer_cuprate_cz_zne.py','analyze_aer_cuprate_cz_zne.py',
           'test_aer_cuprate_cz_zne.py','AER_CZ_ZNE_PROTOCOL.md',
           'aer_cuprate_cz_half_v2.py','aer_cuprate_cz_half.py',
           'aer_cuprate_noise_components.py','aer_cuprate_nighthawk_smoke.py',
           'aer_cuprate_gate_split.py','analyze_aer_noise_components.py',
           'verify_aer_noise_components.py','cuprate_2d_tflo.py']

def seed_for(group, twirl):
    if group not in range(4) or twirl not in range(8):
        raise ValueError('Invalid group/twirl')
    return BASES[group]+1000*twirl

def instruction_rows(circuit):
    return [(i.operation.name, tuple(circuit.find_bit(q).index for q in i.qubits),
             tuple(circuit.find_bit(b).index for b in i.clbits),
             repr(i.operation.params)) for i in circuit.data]

def prepare_base(measured):
    if measured.count_ops().get('measure',0) != measured.num_qubits:
        raise ValueError('Require original terminally measured source circuit')
    circuit=c.expectation_circuit(measured)
    if circuit.count_ops().get('measure',0) or circuit.num_clbits:
        raise ValueError('Only terminal measurements supported')
    return circuit

def fold_cz(circuit, factor, seed):
    if factor not in (1,2,3):
        raise ValueError('Only exact factors 1,2,3 supported')
    positions = defaultdict(list)
    for index, item in enumerate(circuit.data):
        if item.operation.name == 'cz':
            positions[tuple(circuit.find_bit(q).index for q in item.qubits)].append(index)
    if not positions:
        raise ValueError('No CZ gates')
    selected = set()
    if factor == 3:
        selected = {i for group in positions.values() for i in group}
    elif factor == 2:
        rng = np.random.default_rng(seed)
        for support, indices in sorted(positions.items()):
            if len(indices) % 2:
                raise ValueError(f'Odd CZ count on support {support}')
            selected.update(int(i) for i in rng.choice(indices, len(indices)//2, replace=False))
    folded = circuit.copy_empty_like()
    for index, item in enumerate(circuit.data):
        qs = [circuit.find_bit(q).index for q in item.qubits]
        cs = [circuit.find_bit(b).index for b in item.clbits]
        folded.append(item.operation.copy(), qs, cs)
        if index in selected:
            folded.cz(*qs)
            folded.cz(*qs)
    counts = Counter(tuple(folded.find_bit(q).index for q in i.qubits)
                     for i in folded.data if i.operation.name == 'cz')
    assert counts == Counter({k:len(v)*factor for k,v in positions.items()})
    # Replay the recorded insertion positions against the entire instruction sequence.
    original_rows = instruction_rows(circuit)
    actual_rows = instruction_rows(folded)
    cursor = 0
    for index, row in enumerate(original_rows):
        assert actual_rows[cursor] == row
        cursor += 1
        if index in selected:
            assert actual_rows[cursor][0:2] == ('cz', row[1])
            assert actual_rows[cursor+1][0:2] == ('cz', row[1])
            cursor += 2
    assert cursor == len(actual_rows)
    assert folded.global_phase == circuit.global_phase
    return folded, {'factor':factor,'placement_seed':seed,'selected_original_indices':sorted(selected),
        'original_cz':sum(map(len,positions.values())), 'folded_cz':sum(counts.values()),
        'per_support':[{'qubits':k,'original':len(v),'folded':counts[k]} for k,v in positions.items()],
        'original_instruction_replay':True,'no_postfold_transpilation':True}

def without_cz_noise(full):
    model = NoiseModel(basis_gates=sorted(c.a.NATIVE))
    original = h.qerrors(full)
    for (name,qs), error in original.items():
        if name != 'cz':
            model.add_quantum_error(error, name, qs)
    for qs, matrix in h.readout_entries(full).items():
        model.add_readout_error(ReadoutError(matrix),qs)
    remaining = h.qerrors(model)
    assert set(remaining) == {k for k in original if k[0] != 'cz'}
    maximum = max(float(np.max(np.abs(SuperOp(remaining[k]).data-SuperOp(original[k]).data)))
                  for k in remaining)
    assert maximum < 1e-12
    for qs,matrix in h.readout_entries(full).items():
        np.testing.assert_array_equal(matrix,h.readout_entries(model)[qs])
    return model, {'non_cz_channel_max_error':maximum,'cz_channels_removed':sum(k[0]=='cz' for k in original),
                   'ideal_cz_gates_retained':True,'readout_identical':True}

def verify_inputs(plan):
    for name, digest in plan['input_sha256'].items():
        if c.a.digest(c.a.ROOT/name) != digest:
            raise ValueError(f'Changed frozen input {name}')

def run(out, resume=False):
    started = time.perf_counter()
    verified = analysis.verify_files(PARENT,'final_archive_sha256.json')
    parent = c.a.read(PARENT/'plan.json')
    sources = [c.a.ROOT/name for name in SOURCES]
    inputs = sources+[PARENT/'plan.json',PARENT/'final_archive_sha256.json',
        PARENT/'full_calibrated_noise.json',PARENT/'readout_matrices.json',
        c.BASELINE/'restricted_backend_properties.json', h.PARENT/'decomposition.json']
    inputs += [PARENT/'circuits'/f'twirl_{t}.qpy' for t in range(8)]
    inputs += [c.BASELINE/'circuits'/f'twirl_{t}.qpy' for t in range(8)]
    inputs += [PARENT/'blocks'/f'0_{t}'/'record.json' for t in range(8)]
    hashes = {str(p.relative_to(c.a.ROOT)):c.a.digest(p) for p in inputs}
    if out.exists():
        if not resume or (out/'run_summary.json').exists():
            raise ValueError('Refuse overwrite or resampling')
        if c.a.read(out/'plan.json')['input_sha256'] != hashes:
            raise ValueError('Resume input mismatch')
    else:
        if resume:
            raise ValueError('Cannot resume missing run')
        out.mkdir(parents=True)
        for folder in ['source_snapshot','circuits','blocks']:
            (out/folder).mkdir()
        for name in SOURCES:
            shutil.copyfile(c.a.ROOT/name,out/'source_snapshot'/name)
        c.a.write(out/'plan.json',{'schema':'cz-gatefolding-zne-v1',
            'setting':parent['setting'],'layout':parent['layout'],'records':parent['records'],
            'groups':GROUPS,'factors':[1,2,3], 'trajectories_per_group':128,
            'new_trajectories':384,'reused_control_trajectories':128,
            'seed_bases':BASES,'seed_stride':1000,'bootstrap_seed':2026700000,
            'fold_placement_seed_base':2026300000,'bootstrap_repetitions':2000,
            'linear_intercept_weights':[4/3,1/3,-2/3],'quadratic_secondary_weights':[3,-3,1],
            'primary_readout_on':True,'conditional_expectations_not_bitshots':True,
            'qiskit':c.a.qiskit.__version__,'aer':c.a.qiskit_aer.__version__,
            'method':'statevector','precision':'double','max_parallel_threads':2,
            'new_qpu_seconds':0,'max_runner_seconds':1800,'parent_files_verified':verified,
            'created_utc':datetime.now(timezone.utc).isoformat(),'input_sha256':hashes,
            'logical_zne_cost_vs_raw128':{'trajectory_factor':3,'cz_application_factor':6},
            'not_equal_cost_comparison':True})
    plan = c.a.read(out/'plan.json')
    log = io.StringIO()
    tests = unittest.TextTestRunner(stream=log,verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromName('test_aer_cuprate_cz_zne'))
    if not tests.wasSuccessful():
        raise AssertionError(log.getvalue())
    if not (out/'preflight_unit_tests.txt').exists():
        (out/'preflight_unit_tests.txt').write_text(log.getvalue(),encoding='utf-8')
    props = BackendProperties.from_dict(c.a.read(c.BASELINE/'restricted_backend_properties.json'))
    full,_ = h.scaled_full_model(props,c.a.read(h.PARENT/'decomposition.json'),1.)
    control_audit = h.validate_saved_control(full,c.a.read(PARENT/'full_calibrated_noise.json'))
    czoff,off_audit = without_cz_noise(full)
    matrices = np.asarray(c.a.read(PARENT/'readout_matrices.json'))
    if not (out/'full_noise.json').exists():
        c.a.write(out/'full_noise.json',full.to_dict(serializable=True))
        c.a.write(out/'cz_noise_off.json',czoff.to_dict(serializable=True))
        c.a.write(out/'readout_matrices.json',matrices.tolist())
    seeds = [seed_for(g,t)+s for g in range(4) for t in range(8) for s in range(N)]
    assert len(set(seeds)) == 512
    circuits, checks = {}, []
    exact = np.asarray(plan['setting']['reference'])
    ideal = AerSimulator(method='statevector',max_parallel_threads=1,
                         precision='double',enable_truncation=False)
    for tid in range(8):
        with (c.BASELINE/'circuits'/f'twirl_{tid}.qpy').open('rb') as handle:
            base = prepare_base(qpy.load(handle)[0])
        with (PARENT/'circuits'/f'twirl_{tid}.qpy').open('rb') as handle:
            old_saved = qpy.load(handle)[0]
        # QPY restores generic save_expval Instructions without Aer _subtype.
        # Recreate saves through the public API; native physics must be identical.
        native=lambda q:[row for row in instruction_rows(q) if row[0] in c.a.NATIVE]
        assert native(base)==native(old_saved)
        for group,factor in [(1,2),(2,3),(3,1)]:
            circuit,folding = fold_cz(base,factor,2026300000+1000*tid)
            assert folding['folded_cz'] == 1008*factor
            result = ideal.run(circuit,shots=1).result()
            values = c.extract_expectations(result,18,1)
            decoded = c.unmask_paulis(values,plan['records'][tid]['readout_mask_little_endian'])
            error = float(np.max(np.abs(decoded[0]-exact)))
            if not result.success or error > 1e-9:
                raise AssertionError('Folded noise-off circuit mismatch')
            circuits[group,tid] = circuit
            checks.append({'group':group,'twirl':tid,'max_noise_off_error':error,'folding':folding})
            target = out/'circuits'/f'{group}_{tid}.qpy'
            if not target.exists():
                with target.open('wb') as handle:
                    qpy.dump(circuit,handle)
    if not (out/'preflight.json').exists():
        c.a.write(out/'preflight.json',{'status':'PASS','unit_tests':tests.testsRun,
            'model_audit':control_audit,'czoff_audit':off_audit,'unique_seed_labels':len(set(seeds)),
            'checks':checks})
    print(json.dumps({'stage':'PREFLIGHT_PASS','tests':tests.testsRun,
        'noise_off_max_error':max(x['max_noise_off_error'] for x in checks),
        'new_trajectories':384}),flush=True)
    for group in (1,2,3):
        sim = AerSimulator(method='statevector',precision='double',
            noise_model=czoff if group==3 else full,max_parallel_threads=2,
            max_parallel_shots=2,enable_truncation=False)
        for tid in range(8):
            if time.perf_counter()-started > 1800:
                raise TimeoutError('Local process budget reached; preserve partial archive')
            block = out/'blocks'/f'{group}_{tid}'
            if (block/'sha256.json').exists():
                analysis.verify_files(block,'sha256.json')
                record = c.a.read(block/'record.json')
                assert record['seed'] == seed_for(group,tid) and record['group'] == GROUPS[group]
                continue
            if block.exists():
                raise ValueError('Partial block preserved; no silent retry')
            begin = time.perf_counter()
            result = sim.run(circuits[group,tid],shots=N,seed_simulator=seed_for(group,tid)).result()
            elapsed = time.perf_counter()-begin
            values = c.extract_expectations(result,18,N)
            if not result.success or result.results[0].metadata['num_qubits'] != 18:
                raise AssertionError('Invalid trajectory result')
            mask = plan['records'][tid]['readout_mask_little_endian']
            decoded = c.unmask_paulis(values,mask)
            block.mkdir()
            c.a.write(block/'record.json',{'group':GROUPS[group],'group_index':group,'twirl':tid,
                'seed':seed_for(group,tid),'trajectories':N,'native_paulis':values.tolist(),
                'decoded_paulis':decoded.tolist(),
                'with_readout_paulis':c.apply_readout(decoded,mask,matrices).tolist(),
                'run_wall_seconds':elapsed})
            c.a.write(block/'aer_result.json',result.to_dict())
            c.a.write(block/'sha256.json',{p.name:c.a.digest(p) for p in block.iterdir() if p.is_file()})
            print(json.dumps({'group':GROUPS[group],'completed_twirls':tid+1,
                              'trajectories':16*(tid+1),'seconds':elapsed}),flush=True)
    verify_inputs(plan)
    c.a.write(out/'run_summary.json',{'status':'COMPLETE_CZ_FOLDING_AND_CZOFF_DIAGNOSTIC',
        'new_qpu_seconds':0,'new_trajectories':384,'reused_trajectories':128,
        'group_run_seconds':{GROUPS[g]:sum(c.a.read(out/'blocks'/f'{g}_{t}'/'record.json')
            ['run_wall_seconds'] for t in range(8)) for g in (1,2,3)},
        'runner_elapsed_seconds':time.perf_counter()-started})
    c.a.write(out/'run_archive_sha256.json',{str(p.relative_to(out)):c.a.digest(p)
        for p in out.rglob('*') if p.is_file()})
    print(json.dumps(c.a.read(out/'run_summary.json')),flush=True)

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--resume',action='store_true')
    args=parser.parse_args()
    run(args.output.resolve(),args.resume)
