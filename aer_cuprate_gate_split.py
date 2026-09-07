"""Run, analyze and finalize a strictly offline CZ-versus-X/SX noise screen."""
from __future__ import annotations

import argparse
import io
import json
import shutil
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from qiskit import qpy
from qiskit.quantum_info import SuperOp
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, QuantumError

import aer_cuprate_noise_components as c
import analyze_aer_noise_components as analysis
from cuprate_2d_tflo import physical_observables
from verify_aer_noise_components import physical_by_enumeration

PARENT = c.a.RESULTS/'aer_nighthawk_components_T04_v1'
MODELS = ['cz_residual_only', 'x_sx_residual_only']
SEEDS = [2026091000, 2026091100]
SOURCES = ['aer_cuprate_gate_split.py', 'test_aer_cuprate_gate_split.py',
           'AER_CZ_VS_1Q_PROTOCOL.md', 'aer_cuprate_noise_components.py',
           'aer_cuprate_nighthawk_smoke.py', 'analyze_aer_noise_components.py',
           'cuprate_2d_tflo.py', 'verify_aer_noise_components.py',
           'test_aer_cuprate_noise_components.py', 'test_analyze_aer_noise_components.py']


def channel_map(encoded):
    result = {}
    for entry in encoded['errors']:
        if entry['type'] != 'qerror' or not entry.get('gate_qubits'):
            raise ValueError('Only local quantum gate errors are allowed')
        error = QuantumError.from_dict(entry)
        for name in entry['operations']:
            for qs in entry['gate_qubits']:
                if name not in {'cz', 'x', 'sx'}:
                    raise ValueError(f'Unexpected residual gate {name}')
                if len(qs) != (2 if name == 'cz' else 1):
                    raise ValueError('Gate width mismatch')
                key = (name, tuple(qs))
                if key in result:
                    raise ValueError('Duplicate error support')
                result[key] = error
    return result


def partition_channels(encoded):
    original = channel_map(encoded)
    models = {name: NoiseModel(basis_gates=sorted(c.a.NATIVE)) for name in MODELS}
    for (gate, qs), error in original.items():
        target = MODELS[0] if gate == 'cz' else MODELS[1]
        models[target].add_quantum_error(error, gate, qs)
    maps = [channel_map(models[name].to_dict()) for name in MODELS]
    if set(maps[0]) & set(maps[1]) or (set(maps[0]) | set(maps[1])) != set(original):
        raise AssertionError('Noise partition is not a disjoint complete union')
    distances = []
    for part in maps:
        for key, error in part.items():
            distance = float(np.max(np.abs(SuperOp(error).data-SuperOp(original[key]).data)))
            if distance > 1e-12:
                raise AssertionError('Gate noise parameter/channel changed')
            distances.append(distance)
    return models, {'status': 'PASS', 'original_channel_count': len(original),
        'channels_per_model': [len(m) for m in maps], 'disjoint_and_complete': True,
        'max_channel_difference': max(distances, default=0.),
        'supports': {name: [{'gate': g, 'qubits': q} for g, q in sorted(m)]
                     for name, m in zip(MODELS, maps)}}


def run(out, resume=False):
    analysis.verify_files(PARENT, 'final_archive_sha256.json')
    analysis.verify_files(c.BASELINE, 'final_archive_sha256.json')
    parent_plan = c.a.read(PARENT/'plan.json')
    records = parent_plan['records']
    models, partition = partition_channels(c.a.read(PARENT/'residual_depolarization_only_noise.json'))
    matrices = np.asarray(c.a.read(PARENT/'readout_matrices.json'))
    exact = np.asarray(parent_plan['setting']['reference'])
    inputs = [c.a.ROOT/n for n in SOURCES]+[PARENT/'plan.json', PARENT/'final_archive_sha256.json',
        PARENT/'residual_depolarization_only_noise.json', PARENT/'readout_matrices.json']
    inputs += [c.BASELINE/'circuits'/f'twirl_{t}.qpy' for t in range(8)]
    hashes = {str(p.relative_to(c.a.ROOT)): c.a.digest(p) for p in inputs}
    if out.exists():
        if not resume or (out/'run_summary.json').exists():
            raise ValueError('Refuse overwrite or resample of an existing/completed run')
        if c.a.read(out/'plan.json')['input_sha256'] != hashes:
            raise ValueError('Resume input/source mismatch')
    else:
        if resume:
            raise ValueError('Cannot resume missing output')
        out.mkdir(parents=True)
        for name in ['blocks', 'circuits', 'source_snapshot']:
            (out/name).mkdir()
        for name in SOURCES:
            shutil.copyfile(c.a.ROOT/name, out/'source_snapshot'/name)
        c.a.write(out/'plan.json', {'schema': 'aer-gate-class-screen-v1',
            'setting': parent_plan['setting'], 'layout': parent_plan['layout'], 'records': records,
            'models': MODELS, 'seed_bases': SEEDS, 'trajectories_per_twirl': 16,
            'trajectories_per_model': 128, 'bootstrap_repetitions': 2000, 'bootstrap_seed': 2026091201,
            'max_parallel_threads': 2, 'method': 'statevector', 'precision': 'double',
            'qiskit': c.a.qiskit.__version__, 'aer': c.a.qiskit_aer.__version__,
            'created_utc': datetime.now(timezone.utc).isoformat(), 'new_qpu_seconds': 0,
            'primary_noise': 'Residual depolarization on only the selected native gate class.',
            'all_ideal_gates_preserved': True, 'thermal_relaxation_in_primary': False,
            'readout_in_primary': False, 'mitigation_applied': False, 'input_sha256': hashes})
        c.a.write(out/'partition.json', partition)
        c.a.write(out/'readout_matrices.json', matrices.tolist())
        for name, model in models.items():
            c.a.write(out/f'{name}_noise.json', model.to_dict(serializable=True))
    checks, circuits = [], []
    ideal = AerSimulator(method='statevector', precision='double', max_parallel_threads=1,
                         enable_truncation=False)
    for tid in range(8):
        with (c.BASELINE/'circuits'/f'twirl_{tid}.qpy').open('rb') as handle:
            measured = qpy.load(handle)[0]
        circuit = c.expectation_circuit(measured)
        if any(circuit.count_ops().get(g, 0) != measured.count_ops().get(g, 0) for g in c.a.NATIVE):
            raise AssertionError('A native gate was removed or added')
        result = ideal.run(circuit, shots=1).result()
        decoded = c.unmask_paulis(c.extract_expectations(result, 18, 1), records[tid]['readout_mask_little_endian'])
        delta = float(np.max(np.abs(decoded[0]-exact)))
        if not result.success or delta > 1e-9 or circuit.count_ops()['cz'] != 1008:
            raise AssertionError('Full noise-free circuit validation failed')
        checks.append({'twirl_id': tid, 'max_exact_error': delta,
                       'native_counts': {g: circuit.count_ops().get(g, 0) for g in sorted(c.a.NATIVE)}})
        circuits.append(circuit)
        target = out/'circuits'/f'twirl_{tid}.qpy'
        if not target.exists():
            with target.open('wb') as handle:
                qpy.dump(circuit, handle)
    if not (out/'preflight.json').exists():
        c.a.write(out/'preflight.json', {'status': 'PASS', 'checks': checks})
    print(json.dumps({'stage': 'preflight_passed', 'max_exact_error': max(x['max_exact_error'] for x in checks),
                      'partition': partition['channels_per_model']}), flush=True)
    for index, name in enumerate(MODELS):
        simulator = AerSimulator(method='statevector', precision='double', noise_model=models[name],
            enable_truncation=False, max_parallel_threads=2, max_parallel_shots=2)
        for tid in range(8):
            block = out/'blocks'/f'{index}_{tid}'
            if (block/'sha256.json').exists():
                analysis.verify_files(block, 'sha256.json')
                old = c.a.read(block/'record.json')
                if old['model'] != name or old['seed'] != SEEDS[index]+tid:
                    raise ValueError('Completed block metadata mismatch')
                continue
            if block.exists():
                raise ValueError('Partial block preserved; inspect before retry')
            start = time.perf_counter()
            result = simulator.run(circuits[tid], shots=16, seed_simulator=SEEDS[index]+tid).result()
            elapsed = time.perf_counter()-start
            native = c.extract_expectations(result, 18, 16)
            if not result.success or result.results[0].metadata['num_qubits'] != 18:
                raise AssertionError('Wrong noisy run result')
            mask = records[tid]['readout_mask_little_endian']
            decoded = c.unmask_paulis(native, mask)
            block.mkdir()
            c.a.write(block/'record.json', {'model': name, 'twirl_id': tid, 'seed': SEEDS[index]+tid,
                'native_paulis': native.tolist(), 'decoded_paulis': decoded.tolist(),
                'with_readout_paulis': c.apply_readout(decoded, mask, matrices).tolist(),
                'run_wall_seconds': elapsed, 'trajectories': 16})
            c.a.write(block/'aer_result.json', result.to_dict())
            c.a.write(block/'sha256.json', {p.name: c.a.digest(p) for p in block.iterdir() if p.is_file()})
            print(json.dumps({'model': name, 'completed_twirls': tid+1,
                              'trajectories': 16*(tid+1), 'seconds': elapsed}), flush=True)
    c.a.write(out/'run_summary.json', {'status': 'COMPLETE_128_TRAJECTORIES_PER_GATE_CLASS',
        'new_qpu_seconds': 0, 'model_run_seconds': {name: sum(c.a.read(out/'blocks'/f'{i}_{t}'/'record.json')
            ['run_wall_seconds'] for t in range(8)) for i, name in enumerate(MODELS)}})
    c.a.write(out/'run_archive_sha256.json', {str(p.relative_to(out)): c.a.digest(p)
        for p in out.rglob('*') if p.is_file()})
    print(json.dumps(c.a.read(out/'run_summary.json')), flush=True)


def analyze(out):
    destination = out/'analysis'
    if destination.exists():
        raise ValueError('Analysis already exists; refuse overwrite')
    verified = analysis.verify_files(out, 'run_archive_sha256.json')
    plan = c.a.read(out/'plan.json')
    for name, digest in plan['input_sha256'].items():
        if c.a.digest(c.a.ROOT/name) != digest:
            raise ValueError('Original input/source changed')
    data = np.empty((2, 8, 16, 2, 27))
    enumerated = np.empty((2, 8, 16, 2, 9, 3))
    matrices = np.asarray(c.a.read(out/'readout_matrices.json'))
    identity = np.tile(np.eye(2), (18, 1, 1))
    for model, name in enumerate(MODELS):
        for tid in range(8):
            block = c.a.read(out/'blocks'/f'{model}_{tid}'/'record.json')
            raw = c.a.read(out/'blocks'/f'{model}_{tid}'/'aer_result.json')
            if block['model'] != name or block['twirl_id'] != tid or block['seed'] != SEEDS[model]+tid:
                raise ValueError('Wrong block provenance')
            labels = [f'z_{q}' for q in range(18)]+[f'zz_{s}' for s in range(9)]
            native = np.array([raw['results'][0]['data'][key] for key in labels]).T
            if not raw['success'] or native.shape != (16, 27):
                raise AssertionError('Missing noisy trajectory values')
            np.testing.assert_allclose(native, block['native_paulis'], atol=0, rtol=0)
            mask = plan['records'][tid]['readout_mask_little_endian']
            decoded = c.unmask_paulis(native, mask)
            readout = c.apply_readout(decoded, mask, matrices)
            np.testing.assert_allclose(decoded, block['decoded_paulis'], atol=1e-14, rtol=0)
            np.testing.assert_allclose(readout, block['with_readout_paulis'], atol=1e-14, rtol=0)
            data[model, tid] = np.stack([decoded, readout], axis=1)
            for variant, channel in enumerate([identity, matrices]):
                enumerated[model, tid, :, variant] = physical_by_enumeration(native, mask, channel)
    independent_error = float(np.max(np.abs(enumerated-physical_observables(data))))
    if independent_error > 1e-12 or not np.isfinite(data).all():
        raise AssertionError('Independent physical-observable validation failed')
    exact = np.asarray(plan['setting']['reference'])
    mean = data.mean(axis=(1, 2))
    draws = analysis.bootstrap(data, repetitions=2000, seed=2026091201)
    metric_draws = analysis.metrics(draws, exact)
    point = analysis.metrics(mean, exact)
    parent = c.a.read(PARENT/'analysis/results.json')
    parent_draws = np.load(PARENT/'analysis/bootstrap_draws.npz')['means'][:, 0, 0]
    parent_point = np.asarray(parent['means'])[0, 0]
    report = {'schema': 'aer-gate-class-analysis-v1', 'models': MODELS, 'setting': plan['setting'],
        'variants': ['no_readout', 'analytic_readout_added'], 'metric_order': analysis.METRICS,
        'means': mean.tolist(), 'physical_means': physical_observables(mean).tolist(),
        'metrics': point.tolist(), 'metric_ci95': analysis.ci(metric_draws),
        'cz_minus_xsx_metric_ci95': analysis.ci(metric_draws[:, 0, 0]-metric_draws[:, 1, 0]),
        'parent_all_residual_context': {'metrics': analysis.metrics(parent_point, exact).tolist(),
            'metric_ci95': analysis.ci(analysis.metrics(parent_draws, exact)),
            'same_estimator_and_128_trajectories_but_independent_historical_sample': True},
        'resolution': {str(n*8): analysis.metrics(data[:, :, :n].mean(axis=(1, 2)), exact).tolist()
                       for n in [8, 16]},
        'new_qpu_seconds': 0, 'run_seconds': c.a.read(out/'run_summary.json')['model_run_seconds'],
        'run_manifest_sha256': c.a.digest(out/'run_archive_sha256.json'),
        'independent_max_physical_error': independent_error,
        'boundary': 'Residual noise classes only; no thermal/readout in primary; no hardware root-cause or additive attribution.'}
    log = io.StringIO()
    suite = unittest.defaultTestLoader.loadTestsFromNames(['test_aer_cuprate_gate_split',
        'test_aer_cuprate_noise_components', 'test_analyze_aer_noise_components'])
    tests = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    if not tests.wasSuccessful():
        raise AssertionError(log.getvalue())
    destination.mkdir()
    c.a.write(destination/'results.json', report)
    np.savez_compressed(destination/'bootstrap_draws.npz', means=draws)
    (destination/'unit_tests.txt').write_text(log.getvalue(), encoding='utf-8')
    c.a.write(destination/'verification.json', {'status': 'PASS', 'tests': tests.testsRun,
        'run_hashes_verified': verified, 'input_hashes_verified': len(plan['input_sha256']),
        'independent_max_physical_error': independent_error})
    lines = ['# CZ versus X/SX: resterende gateruis', '',
        'Zelfde U/t=8, T=0.4, 18-qubitcircuit; acht twirls x 16 ruistrajecten per model.',
        'Alle gates behouden; geen T1/T2, uitleesruis of mitigation in de primaire vergelijking.', '',
        '| Ruis op | RMSE lading | RMSE spin | RMSE doublon | Spincontrast | 95%-interval spin-RMSE |',
        '|---|---:|---:|---:|---:|---|']
    for i, name in enumerate(MODELS):
        v = point[i, 0]
        lo, hi = report['metric_ci95']['low'][i][0][1], report['metric_ci95']['high'][i][0][1]
        lines.append(f'| {name} | {v[0]:.5f} | {v[1]:.5f} | {v[2]:.5f} | {v[3]:.5f} | [{lo:.5f}, {hi:.5f}] |')
    diff = report['cz_minus_xsx_metric_ci95']
    lines += ['', f'CZ minus X/SX spin-RMSE: {point[0,0,1]-point[1,0,1]:.5f}; '
        f'puntgewijs 95%-interval [{diff["low"][1]:.5f}, {diff["high"][1]:.5f}].',
        '2000 fixed-twirl bootstrapherhalingen; geen onbekende model- of driftfouten inbegrepen.',
        'Spincontrast is projectie op het ideale spinpatroon, geen fideliteit.',
        '128 trajecten zijn een screeningbudget, geen convergentiecertificaat; geneste 64/128-resultaten zijn bewaard.',
        'Dit vergelijkt totale circuitbijdragen, niet fout per gate. Componentfouten zijn niet optelbaar.',
        'De extra hardwareafwijking wordt hiermee niet automatisch geidentificeerd.', '',
        f'Verificatie: {tests.testsRun} tests; onafhankelijke observabelenfout {independent_error:.3g}.',
        'Nieuwe QPU-seconden: 0. Aer-runtijden: '+json.dumps(report['run_seconds']), '']
    (destination/'REPORT.md').write_text('\n'.join(lines), encoding='utf-8')
    c.a.write(destination/'sha256.json', {str(p.relative_to(destination)): c.a.digest(p)
        for p in destination.rglob('*') if p.is_file()})
    print(json.dumps({'metrics': point.tolist(), 'ci95': report['metric_ci95'],
        'difference_ci95': diff, 'tests': tests.testsRun, 'seconds': report['run_seconds']}), flush=True)


def finalize(out):
    if (out/'COMPLETION.json').exists():
        raise ValueError('Already finalized')
    counts = [analysis.verify_files(out, 'run_archive_sha256.json'),
              analysis.verify_files(out/'analysis', 'sha256.json')]
    plan = c.a.read(out/'plan.json')
    for name, digest in plan['input_sha256'].items():
        if c.a.digest(c.a.ROOT/name) != digest:
            raise ValueError('Source/input changed before finalization')
    c.a.write(out/'COMPLETION.json', {'status': 'COMPLETE_CZ_VS_XSX_SCREEN', 'new_qpu_seconds': 0,
        'scope': '128 trajectories per residual gate class; same eight twirls and finite circuit.',
        'hash_counts': counts, 'verification': c.a.read(out/'analysis/verification.json')})
    c.a.write(out/'final_archive_sha256.json', {str(p.relative_to(out)): c.a.digest(p)
        for p in out.rglob('*') if p.is_file()})
    print(json.dumps(c.a.read(out/'COMPLETION.json')))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['run', 'analyze', 'finalize'])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    path = args.output.resolve()
    if args.stage == 'run':
        run(path, resume=args.resume)
    elif args.stage == 'analyze':
        analyze(path)
    else:
        finalize(path)
