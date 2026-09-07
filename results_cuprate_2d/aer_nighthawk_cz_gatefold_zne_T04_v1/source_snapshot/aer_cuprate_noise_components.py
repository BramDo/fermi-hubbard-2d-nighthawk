"""Offline ablations preserving the calibrated full-model decomposition."""
from __future__ import annotations

import argparse
import json
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from qiskit import qpy
from qiskit.quantum_info import Pauli, SuperOp, average_gate_fidelity
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error
from qiskit_aer.noise.device import basic_device_gate_errors, basic_device_readout_errors
from qiskit_ibm_runtime.models import BackendProperties

import aer_cuprate_nighthawk_smoke as a

BASELINE = a.RESULTS/'aer_nighthawk_512_T04_2026-09-05'
COMPONENTS = ['residual_depolarization_only', 'gate_time_relaxation_only']


def split_model(properties):
    full = {(n, tuple(q)): e for n, q, e in basic_device_gate_errors(properties)}
    relax = {(n, tuple(q)): e for n, q, e in basic_device_gate_errors(
        properties, gate_error=False, thermal_relaxation=True, temperature=0)}
    models = {name: NoiseModel(basis_gates=sorted(a.NATIVE)) for name in COMPONENTS}
    verification = []
    for key, original in sorted(full.items()):
        name, qs = key
        nq, dim = len(qs), 2**len(qs)
        r = relax.get(key, depolarizing_error(0, nq))
        fr, ff = average_gate_fidelity(r), average_gate_fidelity(original)
        p = float(dim*(fr-ff)/(dim*fr-1))
        if p < -1e-12 or p > dim**2/(dim**2-1)+1e-12:
            raise ValueError('Invalid inferred residual depolarization')
        p = min(max(p, 0.), dim**2/(dim**2-1))
        d = depolarizing_error(p, nq)
        reconstructed = d.compose(r)
        distance = float(np.max(np.abs(SuperOp(reconstructed).data-SuperOp(original).data)))
        if distance > 1e-12:
            raise AssertionError(f'Full channel reconstruction failed: {key}, {distance}')
        if not d.ideal():
            models[COMPONENTS[0]].add_quantum_error(d, name, qs)
        if not r.ideal():
            models[COMPONENTS[1]].add_quantum_error(r, name, qs)
        verification.append({'gate': name, 'local_qubits': qs, 'residual_p': p,
            'full_average_fidelity': float(ff), 'relax_average_fidelity': float(fr),
            'reconstructed_max_superop_difference': distance})
    return models, verification


def readout_matrices(properties):
    matrices = np.tile(np.eye(2), (len(properties.qubits), 1, 1))
    for qs, error in basic_device_readout_errors(properties):
        if len(qs) != 1:
            raise ValueError('Expected independent one-qubit readout channels')
        matrices[qs[0]] = error.probabilities
    return matrices


def unmask_paulis(native, mask):
    sign = 1-2*np.asarray(mask, dtype=float)
    all_signs = np.concatenate([sign, sign[::2]*sign[1::2]])
    return np.asarray(native)*all_signs


def apply_readout(decoded, mask, matrices):
    """Exact moment transform for independent asymmetric readout and X masks."""
    decoded = np.asarray(decoded)
    width = len(mask)
    if width % 2 or decoded.shape[-1] != 3*width//2 or np.shape(matrices) != (width, 2, 2):
        raise ValueError('Incompatible moment/mask/readout dimensions')
    p01, p10 = matrices[:, 0, 1], matrices[:, 1, 0]
    alpha = 1-p01-p10
    beta = (p10-p01)*(1-2*np.asarray(mask, dtype=float))
    z = decoded[..., :width]
    zz = decoded[..., width:]
    z_out = z*alpha+beta
    zz_out = (zz*alpha[::2]*alpha[1::2]
              +z[..., ::2]*alpha[::2]*beta[1::2]
              +z[..., 1::2]*alpha[1::2]*beta[::2]
              +beta[::2]*beta[1::2])
    return np.concatenate([z_out, zz_out], axis=-1)


def expectation_circuit(measured):
    circuit = measured.remove_final_measurements(inplace=False)
    if circuit.num_qubits % 2:
        raise ValueError('Expected spinful even width')
    for q in range(circuit.num_qubits):
        circuit.save_expectation_value(Pauli('Z'), [q], label=f'z_{q}', pershot=True)
    for s in range(circuit.num_qubits//2):
        circuit.save_expectation_value(Pauli('ZZ'), [2*s, 2*s+1], label=f'zz_{s}', pershot=True)
    return circuit


def extract_expectations(result, width, shots):
    values = result.data(0)
    labels = [f'z_{q}' for q in range(width)]+[f'zz_{s}' for s in range(width//2)]
    data = np.array([values[key] for key in labels], dtype=float).T
    if data.shape != (shots, 3*width//2) or not np.isfinite(data).all():
        raise AssertionError(f'Expected every trajectory, got {data.shape}')
    if np.max(np.abs(data)) > 1+1e-10:
        raise AssertionError('Pauli expectation outside physical range')
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    out = args.output.resolve()
    for name, expected in a.read(BASELINE/'final_archive_sha256.json').items():
        if a.digest(BASELINE/name) != expected:
            raise ValueError(f'Baseline archive changed: {name}')
    baseline = a.read(BASELINE/'plan.json')
    properties = BackendProperties.from_dict(a.read(BASELINE/'restricted_backend_properties.json'))
    models, decomposition = split_model(properties)
    matrices = readout_matrices(properties)
    records = sorted(baseline['records'], key=lambda r: r['twirl_id'])
    if [r['twirl_id'] for r in records] != list(range(8)):
        raise ValueError('Expected all eight original twirls')
    source_names = [Path(__file__).name, 'test_aer_cuprate_noise_components.py',
                    'AER_NOISE_COMPONENTS_PROTOCOL.md', 'aer_cuprate_nighthawk_smoke.py',
                    'cuprate_2d_tflo.py']
    inputs = [a.ROOT/name for name in source_names]+[BASELINE/'plan.json',
        BASELINE/'restricted_backend_properties.json', BASELINE/'final_archive_sha256.json']
    inputs += [BASELINE/'circuits'/f'twirl_{t}.qpy' for t in range(8)]
    hashes = {str(p.relative_to(a.ROOT)): a.digest(p) for p in inputs}
    if out.exists():
        if not args.resume:
            parser.error('Output exists; refuse overwrite')
        if (out/'run_summary.json').exists():
            parser.error('Already complete')
        if a.read(out/'plan.json')['input_sha256'] != hashes:
            raise ValueError('Resume source/input mismatch')
    else:
        if args.resume:
            parser.error('Cannot resume nonexistent run')
        out.mkdir(parents=True)
        for name in ['source_snapshot', 'circuits', 'blocks']:
            (out/name).mkdir()
        for name in source_names:
            shutil.copyfile(a.ROOT/name, out/'source_snapshot'/name)
        a.write(out/'plan.json', {
            'schema': 'aer-component-screen-v1', 'setting': baseline['setting'],
            'records': records, 'layout': baseline['layout'], 'models': COMPONENTS,
            'trajectories_per_twirl_per_model': 16, 'trajectories_per_model': 128,
            'seed_bases': [2026090700, 2026090800], 'bootstrap_repetitions': 2000,
            'bootstrap_seed': 2026090901, 'native_gates_changed': False,
            'terminal_measurement_replaced_by_pershot_expectations': True,
            'readout_only_exact_not_sampled': True, 'postselection_applied': False,
            'max_parallel_threads': 2, 'method': 'statevector', 'precision': 'double',
            'new_qpu_seconds': 0, 'qiskit': a.qiskit.__version__, 'aer': a.qiskit_aer.__version__,
            'created_utc': datetime.now(timezone.utc).isoformat(),
            'input_sha256': hashes, 'limitations': baseline['limitations'],
            'baseline_estimator': '512 sampled bitstrings; differs from 128 conditional expectation trajectories.'})
        a.write(out/'decomposition.json', decomposition)
        a.write(out/'readout_matrices.json', matrices.tolist())
        for name, model in models.items():
            a.write(out/f'{name}_noise.json', model.to_dict(serializable=True))
    exact = np.asarray(baseline['setting']['reference'])
    readout_exact, checks, circuits = [], [], []
    ideal_simulator = AerSimulator(method='statevector', precision='double',
                                   max_parallel_threads=1, enable_truncation=False)
    for tid, record in enumerate(records):
        with (BASELINE/'circuits'/f'twirl_{tid}.qpy').open('rb') as handle:
            measured = qpy.load(handle)[0]
        circuit = expectation_circuit(measured)
        result = ideal_simulator.run(circuit, shots=1).result()
        if not result.success:
            raise RuntimeError(result.status)
        extracted = extract_expectations(result, 18, 1)
        decoded = unmask_paulis(extracted, record['readout_mask_little_endian'])
        error = float(np.max(np.abs(decoded[0]-exact)))
        if error > 1e-9 or circuit.count_ops()['cz'] != 1008:
            raise AssertionError('Expectation estimator/noise-off native circuit mismatch')
        checks.append({'twirl': tid, 'max_exact_difference': error})
        readout_exact.append(apply_readout(exact, record['readout_mask_little_endian'], matrices))
        circuits.append(circuit)
        target = out/'circuits'/f'twirl_{tid}.qpy'
        if not target.exists():
            with target.open('wb') as handle:
                qpy.dump(circuit, handle)
    if not (out/'preflight.json').exists():
        a.write(out/'preflight.json', {'status': 'PASS', 'checks': checks,
            'readout_only_exact_per_twirl': np.asarray(readout_exact).tolist(),
            'max_channel_reconstruction_error': max(d['reconstructed_max_superop_difference'] for d in decomposition)})
    print(json.dumps({'stage': 'preflight_passed', 'ideal_max_error': max(c['max_exact_difference'] for c in checks)}), flush=True)
    for index, model_name in enumerate(COMPONENTS):
        simulator = AerSimulator(method='statevector', precision='double',
            noise_model=models[model_name], max_parallel_threads=2, max_parallel_shots=2,
            enable_truncation=False)
        for tid, record in enumerate(records):
            block = out/'blocks'/f'{index}_{tid}'
            if (block/'sha256.json').exists():
                for name, expected in a.read(block/'sha256.json').items():
                    if a.digest(block/name) != expected:
                        raise ValueError('Completed component block changed')
                continue
            if block.exists():
                raise ValueError('Partial block retained for inspection')
            seed = 2026090700+100*index+tid
            start = time.perf_counter()
            result = simulator.run(circuits[tid], shots=16, seed_simulator=seed).result()
            elapsed = time.perf_counter()-start
            if not result.success:
                raise RuntimeError(result.status)
            native = extract_expectations(result, 18, 16)
            decoded = unmask_paulis(native, record['readout_mask_little_endian'])
            with_readout = apply_readout(decoded, record['readout_mask_little_endian'], matrices)
            block.mkdir()
            a.write(block/'result.json', {'model': model_name, 'twirl_id': tid, 'seed': seed,
                'trajectories': 16, 'native_paulis': native.tolist(), 'decoded_paulis': decoded.tolist(),
                'decoded_with_readout_paulis': with_readout.tolist(), 'run_wall_seconds': elapsed})
            a.write(block/'aer_result.json', result.to_dict())
            a.write(block/'sha256.json', {p.name: a.digest(p) for p in block.iterdir() if p.is_file()})
            print(json.dumps({'model': model_name, 'completed_twirls': tid+1,
                              'trajectories': 16*(tid+1), 'block_seconds': elapsed}), flush=True)
    summary = {'status': 'COMPLETE_128_TRAJECTORIES_PER_COMPONENT', 'new_qpu_seconds': 0,
        'model_run_seconds': {COMPONENTS[i]: sum(a.read(out/'blocks'/f'{i}_{t}'/'result.json')['run_wall_seconds']
                                      for t in range(8)) for i in range(2)}}
    a.write(out/'run_summary.json', summary)
    a.write(out/'run_archive_sha256.json', {str(p.relative_to(out)): a.digest(p) for p in out.rglob('*') if p.is_file()})
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    main()
