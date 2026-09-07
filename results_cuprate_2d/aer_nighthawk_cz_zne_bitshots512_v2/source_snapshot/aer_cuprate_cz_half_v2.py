"""Controlled, offline CZ-residual reduction in the complete calibrated Aer model."""
from __future__ import annotations

import argparse
import copy
import io
import json
import shutil
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from qiskit import qpy
from qiskit.quantum_info import SuperOp, average_gate_fidelity
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error
from qiskit_aer.noise.device import basic_device_gate_errors, basic_device_readout_errors
from qiskit_ibm_runtime.models import BackendProperties

import aer_cuprate_noise_components as c
import analyze_aer_noise_components as analysis
from aer_cuprate_gate_split import channel_map
from cuprate_2d_tflo import physical_observables
from verify_aer_noise_components import physical_by_enumeration

PARENT = c.a.RESULTS/'aer_nighthawk_components_T04_v1'
MODELS = ['full_calibrated', 'full_cz_residual_half']
SEEDS = [2026100000, 2026200000]
SEED_STRIDE = 1000


def seed_for(model, twirl):
    if model not in (0, 1) or twirl not in range(8):
        raise ValueError('Invalid model or twirl')
    return SEEDS[model]+SEED_STRIDE*twirl

PRIMARY = 1  # Analytic readout ON; index 0 is only a secondary diagnostic.
SOURCES = ['aer_cuprate_cz_half_v2.py', 'aer_cuprate_cz_half.py', 'test_aer_cuprate_seed_policy.py', 'aer_seed_overlap_diagnostic.py', 'test_aer_cuprate_cz_half.py', 'AER_FULL_CZ_HALF_V2_PROTOCOL.md',
           'aer_cuprate_noise_components.py', 'aer_cuprate_nighthawk_smoke.py',
           'aer_cuprate_gate_split.py', 'analyze_aer_noise_components.py',
           'verify_aer_noise_components.py', 'cuprate_2d_tflo.py',
           'test_aer_cuprate_noise_components.py', 'test_analyze_aer_noise_components.py']


def scaled_full_model(properties, decomposition, scale):
    if not 0 <= scale <= 1:
        raise ValueError('CZ residual reduction scale must be in [0,1]')
    rows = {(r['gate'], tuple(r['local_qubits'])): r for r in decomposition}
    original = {(n, tuple(q)): e for n, q, e in basic_device_gate_errors(properties)}
    relaxation = {(n, tuple(q)): e for n, q, e in basic_device_gate_errors(properties,
                                  gate_error=False, thermal_relaxation=True, temperature=0)}
    model = NoiseModel(basis_gates=sorted(c.a.NATIVE))
    audit = []
    for key, error in sorted(original.items()):
        name, qs = key
        p = rows[key]['residual_p']
        r = relaxation.get(key, depolarizing_error(0, len(qs)))
        reconstruction = depolarizing_error(p, len(qs)).compose(r)
        reconstruction_error = float(np.max(np.abs(SuperOp(reconstruction).data-SuperOp(error).data)))
        if reconstruction_error > 1e-12:
            raise AssertionError('Decomposition does not reconstruct the original full channel')
        scaled = depolarizing_error(scale*p, len(qs)).compose(r) if name == 'cz' else error
        model.add_quantum_error(scaled, name, qs)
        change = float(np.max(np.abs(SuperOp(scaled).data-SuperOp(error).data)))
        if name != 'cz' and change != 0:
            raise AssertionError('Non-CZ channel changed')
        audit.append({'gate': name, 'local_qubits': qs, 'original_residual_p': p,
            'new_residual_p': p*scale if name == 'cz' else p,
            'scale': scale if name == 'cz' else 1.,
            'original_average_fidelity': float(average_gate_fidelity(error)),
            'new_average_fidelity': float(average_gate_fidelity(scaled)),
            'relaxation_average_fidelity': float(average_gate_fidelity(r)),
            'reconstruction_error': reconstruction_error, 'full_channel_change': change})
    for qs, error in basic_device_readout_errors(properties):
        model.add_readout_error(error, qs)
    return model, audit


def readout_entries(model):
    return {tuple(q): np.asarray(e['probabilities']) for e in model.to_dict()['errors']
            if e['type'] == 'roerror' for q in e['gate_qubits']}


def qerrors(model):
    return channel_map({'errors': [e for e in model.to_dict()['errors'] if e['type'] == 'qerror']})


def decode_serialized_noise(encoded):
    """Restore AerJSONEncoder [real,imag] pairs in matrix parameters on a COPY.

    QuantumError.from_dict accepts complex 2-D matrices, not the extra
    real/imag axis produced by NoiseModel.to_dict(serializable=True).
    Do not alter probabilities, supports, Pauli strings, or saved artifacts.
    """
    restored = copy.deepcopy(encoded)
    for entry in restored['errors']:
        if entry['type'] != 'qerror':
            continue
        for sequence in entry['instructions']:
            for instruction in sequence:
                if instruction['name'] not in {'kraus', 'unitary'}:
                    continue
                matrices = []
                for matrix in instruction['params']:
                    array = np.asarray(matrix)
                    if array.ndim == 3 and array.shape[-1] == 2:
                        array = array[..., 0]+1j*array[..., 1]
                    elif array.ndim == 2:
                        array = np.asarray(array, dtype=complex)
                    else:
                        raise ValueError(f'Unexpected serialized matrix shape {array.shape}')
                    matrices.append(array)
                instruction['params'] = matrices
    return restored


def validate_saved_control(model, encoded):
    encoded = decode_serialized_noise(encoded)
    saved = channel_map({'errors': [e for e in encoded['errors'] if e['type'] == 'qerror']})
    new = qerrors(model)
    if set(saved) != set(new):
        raise AssertionError('Full control has different gate-noise supports')
    error = max(float(np.max(np.abs(SuperOp(saved[k]).data-SuperOp(new[k]).data))) for k in saved)
    if error > 1e-12:
        raise AssertionError('Full control differs from previous saved model')
    old_ro = {tuple(q): np.asarray(e['probabilities']) for e in encoded['errors']
              if e['type'] == 'roerror' for q in e['gate_qubits']}
    ro = readout_entries(model)
    if set(old_ro) != set(ro):
        raise AssertionError('Different readout support')
    for q in ro:
        np.testing.assert_array_equal(ro[q], old_ro[q])
    return {'saved_full_quantum_channel_max_error': error, 'identical_readout_qubits': len(ro)}


def run(out, resume=False):
    analysis.verify_files(PARENT, 'final_archive_sha256.json')
    analysis.verify_files(c.BASELINE, 'final_archive_sha256.json')
    parent = c.a.read(PARENT/'plan.json')
    properties = BackendProperties.from_dict(c.a.read(c.BASELINE/'restricted_backend_properties.json'))
    decomposition = c.a.read(PARENT/'decomposition.json')
    matrices = c.readout_matrices(properties)
    pairs = [scaled_full_model(properties, decomposition, scale) for scale in [1., .5]]
    models = {name: pair[0] for name, pair in zip(MODELS, pairs)}
    controls = validate_saved_control(models[MODELS[0]], c.a.read(c.BASELINE/'noise_model.json'))
    for q, value in readout_entries(models[MODELS[0]]).items():
        np.testing.assert_array_equal(value, readout_entries(models[MODELS[1]])[q])
    inputs = [c.a.ROOT/name for name in SOURCES]+[PARENT/'plan.json', PARENT/'decomposition.json',
        PARENT/'final_archive_sha256.json', c.BASELINE/'restricted_backend_properties.json',
        c.BASELINE/'noise_model.json', c.BASELINE/'final_archive_sha256.json']
    inputs += [c.BASELINE/'circuits'/f'twirl_{t}.qpy' for t in range(8)]
    hashes = {str(p.relative_to(c.a.ROOT)): c.a.digest(p) for p in inputs}
    if out.exists():
        if not resume or (out/'run_summary.json').exists():
            raise ValueError('Refuse overwrite or resampling of a completed run')
        if c.a.read(out/'plan.json')['input_sha256'] != hashes:
            raise ValueError('Resume source/input mismatch')
    else:
        if resume:
            raise ValueError('Cannot resume missing output')
        out.mkdir(parents=True)
        for folder in ['blocks', 'circuits', 'source_snapshot']:
            (out/folder).mkdir()
        for name in SOURCES:
            shutil.copyfile(c.a.ROOT/name, out/'source_snapshot'/name)
        c.a.write(out/'plan.json', {'schema': 'full-model-cz-half-v2', 'models': MODELS,
            'setting': parent['setting'], 'layout': parent['layout'], 'records': parent['records'],
            'trajectories_per_twirl': 16, 'trajectories_per_model': 128, 'seed_bases': SEEDS, 'seed_stride_between_twirls': SEED_STRIDE,
            'per_shot_rng_seed_policy': 'Aer uses run seed plus shot index; all ranges disjoint',
            'primary_variant': PRIMARY, 'primary_readout_on': True,
            'primary_readout_application': 'exact analytic moment transform, once after premeasurement saves',
            'bootstrap_seed': 2026092201, 'bootstrap_repetitions': 2000,
            'cz_residual_scales': [1., .5], 'all_other_model_errors_unchanged': True,
            'method': 'statevector', 'precision': 'double', 'max_parallel_threads': 2,
            'qiskit': c.a.qiskit.__version__, 'aer': c.a.qiskit_aer.__version__,
            'created_utc': datetime.now(timezone.utc).isoformat(), 'new_qpu_seconds': 0,
            'input_sha256': hashes, 'mitigation_implemented': False})
        c.a.write(out/'model_change_audit.json', {'control': controls,
            'models': {name: pair[1] for name, pair in zip(MODELS, pairs)}})
        c.a.write(out/'readout_matrices.json', matrices.tolist())
        for name, model in models.items():
            c.a.write(out/f'{name}_noise.json', model.to_dict(serializable=True))
    records = parent['records']
    exact = np.asarray(parent['setting']['reference'])
    ideal = AerSimulator(method='statevector', precision='double', max_parallel_threads=1,
                         enable_truncation=False)
    circuits, checks = [], []
    for tid in range(8):
        with (c.BASELINE/'circuits'/f'twirl_{tid}.qpy').open('rb') as handle:
            measured = qpy.load(handle)[0]
        circuit = c.expectation_circuit(measured)
        if any(circuit.count_ops().get(g, 0) != measured.count_ops().get(g, 0) for g in c.a.NATIVE):
            raise AssertionError('Native gates changed')
        result = ideal.run(circuit, shots=1).result()
        decoded = c.unmask_paulis(c.extract_expectations(result, 18, 1), records[tid]['readout_mask_little_endian'])
        error = float(np.max(np.abs(decoded[0]-exact)))
        if not result.success or error > 1e-9 or circuit.count_ops()['cz'] != 1008:
            raise AssertionError('Noise-off circuit mismatch')
        checks.append({'twirl_id': tid, 'max_exact_error': error, 'cz': circuit.count_ops()['cz']})
        circuits.append(circuit)
        target = out/'circuits'/f'twirl_{tid}.qpy'
        if not target.exists():
            with target.open('wb') as handle:
                qpy.dump(circuit, handle)
    if not (out/'preflight.json').exists():
        c.a.write(out/'preflight.json', {'status': 'PASS', 'checks': checks})
    print(json.dumps({'stage': 'preflight_passed', 'control': controls,
                      'max_exact_error': max(r['max_exact_error'] for r in checks)}), flush=True)
    for index, name in enumerate(MODELS):
        simulator = AerSimulator(method='statevector', precision='double', noise_model=models[name],
            max_parallel_threads=2, max_parallel_shots=2, enable_truncation=False)
        for tid in range(8):
            block = out/'blocks'/f'{index}_{tid}'
            if (block/'sha256.json').exists():
                analysis.verify_files(block, 'sha256.json')
                record = c.a.read(block/'record.json')
                if record['model'] != name or record['seed'] != seed_for(index, tid):
                    raise ValueError('Completed block mismatch')
                continue
            if block.exists():
                raise ValueError('Partial block preserved; inspect before retry')
            start = time.perf_counter()
            result = simulator.run(circuits[tid], shots=16, seed_simulator=seed_for(index, tid)).result()
            elapsed = time.perf_counter()-start
            native = c.extract_expectations(result, 18, 16)
            if not result.success or result.results[0].metadata['num_qubits'] != 18:
                raise AssertionError('Invalid noise trajectories')
            mask = records[tid]['readout_mask_little_endian']
            decoded = c.unmask_paulis(native, mask)
            block.mkdir()
            c.a.write(block/'record.json', {'model': name, 'twirl_id': tid, 'seed': seed_for(index, tid),
                'trajectories': 16, 'native_paulis': native.tolist(), 'decoded_paulis': decoded.tolist(),
                'with_readout_paulis': c.apply_readout(decoded, mask, matrices).tolist(),
                'run_wall_seconds': elapsed})
            c.a.write(block/'aer_result.json', result.to_dict())
            c.a.write(block/'sha256.json', {p.name: c.a.digest(p) for p in block.iterdir() if p.is_file()})
            print(json.dumps({'model': name, 'completed_twirls': tid+1, 'trajectories': (tid+1)*16,
                              'seconds': elapsed}), flush=True)
    c.a.write(out/'run_summary.json', {'status': 'COMPLETE_FULL_VS_HALF_CZ_128_EACH',
        'new_qpu_seconds': 0, 'model_run_seconds': {name: sum(c.a.read(out/'blocks'/f'{i}_{t}'/'record.json')
            ['run_wall_seconds'] for t in range(8)) for i, name in enumerate(MODELS)}})
    c.a.write(out/'run_archive_sha256.json', {str(p.relative_to(out)): c.a.digest(p)
        for p in out.rglob('*') if p.is_file()})
    print(json.dumps(c.a.read(out/'run_summary.json')), flush=True)


def benefits(metric_values):
    """Positive = lower RMSE or larger spin projection; PRIMARY includes readout."""
    values = np.asarray(metric_values)
    if values.shape[-3:] != (2, 2, 4):
        raise ValueError('Expected model x readout-variant x four metrics')
    return np.concatenate([values[..., 0, PRIMARY, :3]-values[..., 1, PRIMARY, :3],
        (values[..., 1, PRIMARY, 3]-values[..., 0, PRIMARY, 3])[..., None]], axis=-1)


def analyze(out):
    destination = out/'analysis'
    if destination.exists():
        raise ValueError('Refuse analysis overwrite')
    verified = analysis.verify_files(out, 'run_archive_sha256.json')
    plan = c.a.read(out/'plan.json')
    for name, digest in plan['input_sha256'].items():
        if c.a.digest(c.a.ROOT/name) != digest:
            raise ValueError('Input/source changed')
    matrices = np.asarray(c.a.read(out/'readout_matrices.json'))
    identity = np.tile(np.eye(2), (18, 1, 1))
    data = np.empty((2, 8, 16, 2, 27))
    independent = np.empty((2, 8, 16, 2, 9, 3))
    for model, name in enumerate(MODELS):
        for tid in range(8):
            block = c.a.read(out/'blocks'/f'{model}_{tid}'/'record.json')
            raw = c.a.read(out/'blocks'/f'{model}_{tid}'/'aer_result.json')
            if block['model'] != name or block['twirl_id'] != tid or block['seed'] != seed_for(model, tid):
                raise ValueError('Wrong block provenance')
            labels = [f'z_{q}' for q in range(18)]+[f'zz_{s}' for s in range(9)]
            native = np.asarray([raw['results'][0]['data'][key] for key in labels]).T
            if not raw['success'] or native.shape != (16, 27):
                raise ValueError('Missing successful trajectories')
            np.testing.assert_allclose(native, block['native_paulis'], atol=0, rtol=0)
            mask = plan['records'][tid]['readout_mask_little_endian']
            decoded = c.unmask_paulis(native, mask)
            with_readout = c.apply_readout(decoded, mask, matrices)
            np.testing.assert_allclose(decoded, block['decoded_paulis'], atol=1e-14, rtol=0)
            np.testing.assert_allclose(with_readout, block['with_readout_paulis'], atol=1e-14, rtol=0)
            data[model, tid] = np.stack([decoded, with_readout], axis=1)
            for variant, channel in enumerate([identity, matrices]):
                independent[model, tid, :, variant] = physical_by_enumeration(native, mask, channel)
    maximum_error = float(np.max(np.abs(independent-physical_observables(data))))
    if maximum_error > 1e-12 or not np.isfinite(data).all():
        raise AssertionError('Independent physical-observable mismatch')
    exact = np.asarray(plan['setting']['reference'])
    means = data.mean(axis=(1, 2))
    draws = analysis.bootstrap(data, repetitions=2000, seed=2026092201)
    metrics = analysis.metrics(means, exact)
    metric_draws = analysis.metrics(draws, exact)
    gain = benefits(metrics)
    gain_draws = benefits(metric_draws)
    old = c.a.read(c.BASELINE/'comparison/results.json')
    old_mean = np.asarray(old['pauli_means'])[0, 0]
    old_draws = np.load(c.BASELINE/'comparison/bootstrap_draws.npz')['fixed'][:, 0, 0]
    old_metrics = analysis.metrics(old_mean, exact)
    old_metric_draws = analysis.metrics(old_draws, exact)
    # Independently reproduce the primary spin benefit directly from Z values.
    target_spin = (exact[1:18:2]-exact[:18:2])/2
    bootstrap_spin = (draws[..., 1:18:2]-draws[..., :18:2])/2
    spin_rmse = np.sqrt(np.mean((bootstrap_spin-target_spin)**2, axis=-1))
    direct_spin_benefit = spin_rmse[:, 0, PRIMARY]-spin_rmse[:, 1, PRIMARY]
    np.testing.assert_allclose(direct_spin_benefit, gain_draws[:, 1], atol=1e-14, rtol=0)
    output = {'schema': 'full-model-cz-half-analysis-v2', 'models': MODELS,
        'setting': plan['setting'], 'variants': ['pre_readout_secondary', 'with_readout_PRIMARY'],
        'primary_variant_index': PRIMARY, 'metric_order': analysis.METRICS,
        'means': means.tolist(), 'physical_means': physical_observables(means).tolist(),
        'metrics': metrics.tolist(), 'metric_ci95': analysis.ci(metric_draws),
        'benefit_order': ['charge_rmse_reduction', 'spin_rmse_reduction', 'doublon_rmse_reduction',
                          'spin_contrast_increase'],
        'primary_benefits': gain.tolist(), 'primary_benefit_ci95': analysis.ci(gain_draws),
        'relative_spin_rmse_reduction': float(gain[1]/metrics[0, PRIMARY, 1]),
        'relative_spin_rmse_reduction_ci95': analysis.ci(gain_draws[:, 1]/metric_draws[:, 0, PRIMARY, 1]),
        'resolution': {str(n*8): analysis.metrics(data[:, :, :n].mean(axis=(1, 2)), exact).tolist()
                       for n in [8, 16]},
        'benefit_ci_bootstrap_resolution': {str(n): analysis.ci(gain_draws[:n]) for n in [500, 1000, 2000]},
        'historical_512_full_context': {'metrics': old_metrics.tolist(),
            'ci95': analysis.ci(old_metric_draws), 'different_estimator_and_sample_size': True,
            'historical_ci_validity': 'PROVISIONAL: old adjacent twirl seeds overlap across shots; do not use old independent-bootstrap CI for significance'},
        'new_qpu_seconds': 0, 'run_seconds': c.a.read(out/'run_summary.json')['model_run_seconds'],
        'independent_max_physical_error': maximum_error, 'primary_spin_benefit_independently_reproduced': True,
        'run_manifest_sha256': c.a.digest(out/'run_archive_sha256.json'),
        'boundary': 'Hypothetical CZ residual reduction, not implemented mitigation; old approximate model limitations remain.'}
    log = io.StringIO()
    suite = unittest.defaultTestLoader.loadTestsFromNames(['test_aer_cuprate_seed_policy', 'test_aer_cuprate_cz_half',
        'test_aer_cuprate_noise_components', 'test_analyze_aer_noise_components'])
    tests = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    if not tests.wasSuccessful():
        raise AssertionError(log.getvalue())
    destination.mkdir()
    c.a.write(destination/'results.json', output)
    np.savez_compressed(destination/'bootstrap_draws.npz', means=draws)
    (destination/'unit_tests.txt').write_text(log.getvalue(), encoding='utf-8')
    c.a.write(destination/'verification.json', {'status': 'PASS', 'tests': tests.testsRun,
        'run_hashes_verified': verified, 'input_hashes_verified': len(plan['input_sha256']),
        'independent_max_physical_error': maximum_error,
        'primary_readout_applied_once': True, 'primary_spin_benefit_independently_reproduced': True})
    lines = ['# Volledig Aer-model: CZ-restdepolarisatie halveren', '',
        'Beide modellen: zelfde 128 ruistrajecten als budget, acht twirls, U/t=8, T=0.4.',
        'T1/T2, X/SX-fouten en uitleeskanalen blijven gelijk. Primaire resultaten INCLUSIEF uitleesruis.', '',
        '| Model | RMSE lading | RMSE spin | RMSE doublon | Spincontrast | 95%-interval spin-RMSE |',
        '|---|---:|---:|---:|---:|---|']
    for i, name in enumerate(MODELS):
        v = metrics[i, PRIMARY]
        lo = output['metric_ci95']['low'][i][PRIMARY][1]
        hi = output['metric_ci95']['high'][i][PRIMARY][1]
        lines.append(f'| {name} | {v[0]:.5f} | {v[1]:.5f} | {v[2]:.5f} | {v[3]:.5f} | [{lo:.5f}, {hi:.5f}] |')
    lo, hi = output['primary_benefit_ci95']['low'][1], output['primary_benefit_ci95']['high'][1]
    lines += ['', f'Spin-RMSE reductie: {gain[1]:.5f}; puntgewijs 95%-interval [{lo:.5f}, {hi:.5f}].',
        f'Relatieve puntinschatting: {100*output["relative_spin_rmse_reduction"]:.1f}%.',
        '2000 fixed-twirl bootstrap-herhalingen; alle seedbereiken zijn gescheiden; geen onbekende model- of hardwarefouten inbegrepen.',
        'CZ-restdepolarisatie halveert, niet de totale CZ-infideliteit: CZ-relaxatie blijft aanwezig.',
        'Dit is geen ZNE/PEC-experiment en geen gerealiseerde hardwareverbetering.',
        'Het oorspronkelijke model mist nog idle-gap-relaxatie, coherente fouten, crosstalk, leakage en drift.',
        'De oude 512-bitshotcontrole en v1 hadden overlappende seedbereiken; hun onafhankelijke bootstrapintervallen zijn voorlopig ongeldig.',
        'De 64/128-trajectreeksen zijn genest en bewijzen geen algemene convergentie.', '',
        f'Verificatie: {tests.testsRun} tests, onafhankelijke fysieke fout {maximum_error:.3g}.',
        'Nieuwe QPU-seconden: 0. Aer-runtijden: '+json.dumps(output['run_seconds']), '']
    (destination/'REPORT.md').write_text('\n'.join(lines), encoding='utf-8')
    c.a.write(destination/'sha256.json', {str(p.relative_to(destination)): c.a.digest(p)
        for p in destination.rglob('*') if p.is_file()})
    print(json.dumps({'primary_metrics': metrics[:, PRIMARY].tolist(),
        'primary_ci95': {'low': np.asarray(output['metric_ci95']['low'])[:, PRIMARY].tolist(),
                         'high': np.asarray(output['metric_ci95']['high'])[:, PRIMARY].tolist()},
        'benefits': output['primary_benefits'], 'benefit_ci95': output['primary_benefit_ci95'],
        'relative_spin_reduction': output['relative_spin_rmse_reduction'],
        'tests': tests.testsRun, 'seconds': output['run_seconds']}), flush=True)


def finalize(out):
    if (out/'COMPLETION.json').exists():
        raise ValueError('Already finalized')
    counts = [analysis.verify_files(out, 'run_archive_sha256.json'),
              analysis.verify_files(out/'analysis', 'sha256.json')]
    for name, digest in c.a.read(out/'plan.json')['input_sha256'].items():
        if c.a.digest(c.a.ROOT/name) != digest:
            raise ValueError('Source/input changed')
    c.a.write(out/'COMPLETION.json', {'status': 'COMPLETE_FULL_MODEL_CZ_HALF_SENSITIVITY',
        'new_qpu_seconds': 0, 'scope': '128 trajectories per variant; primary includes unchanged readout.',
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
    out = args.output.resolve()
    if args.stage == 'run':
        run(out, resume=args.resume)
    elif args.stage == 'analyze':
        analyze(out)
    else:
        finalize(out)
