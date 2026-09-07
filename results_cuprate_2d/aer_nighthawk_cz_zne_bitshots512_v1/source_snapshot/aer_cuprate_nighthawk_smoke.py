"""Offline, calibrated Aer feasibility test. Never contacts IBM or submits jobs.

Preserves submitted native gates and measurement mapping; restricts the saved
device properties to the SAME physical wires. This is not a hardware twin.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import time
import warnings

import numpy as np
from qiskit import QuantumCircuit, qpy
import qiskit
import qiskit_aer
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel
from qiskit_aer.noise.device import basic_device_gate_errors, basic_device_readout_errors
from qiskit_ibm_runtime import RuntimeDecoder, RuntimeEncoder
from qiskit_ibm_runtime.models import BackendProperties

from cuprate_2d_tflo import decode_bitstrings, pauli_samples, sector_mask

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / 'results_cuprate_2d'
PLAN = RESULTS / 'tflo_compact_pilot_3x3_2026-09-05'
RUN = RESULTS / 'tflo_compact_run_3x3_2026-09-05'
CAL = RESULTS / 'fermionic_pilot_3x3_2026-09-05'
NATIVE = {'rz', 'sx', 'x', 'cz'}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'), cls=RuntimeDecoder)


def write(path, value):
    Path(path).write_text(json.dumps(value, cls=RuntimeEncoder, indent=2) + '\n', encoding='utf-8')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def restrict_properties(original, layout):
    """SI conversion is delegated to BackendProperties/Aer, not hand-applied.

    CZ is symmetric: supply the reversed gate when the calibration only lists
    one orientation. Per-wire T1/T2 remain attached to their original wires.
    """
    if len(layout) != len(set(layout)) or not layout:
        raise ValueError('Layout must be nonempty and injective')
    if min(layout) < 0 or max(layout) >= len(original['qubits']):
        raise ValueError('Physical qubit outside calibration')
    inv = {p: q for q, p in enumerate(layout)}
    reduced = copy.deepcopy(original)
    reduced['qubits'] = [copy.deepcopy(original['qubits'][p]) for p in layout]
    reduced['gates'] = []
    reduced['general'] = []
    reduced['general_qlists'] = []
    for gate in original['gates']:
        if gate['gate'] in NATIVE and all(q in inv for q in gate['qubits']):
            mapped = copy.deepcopy(gate)
            mapped['qubits'] = [inv[q] for q in gate['qubits']]
            reduced['gates'].append(mapped)
    known = {(g['gate'], tuple(g['qubits'])) for g in reduced['gates']}
    mirrored = []
    for gate in list(reduced['gates']):
        reverse = tuple(reversed(gate['qubits']))
        if gate['gate'] == 'cz' and ('cz', reverse) not in known:
            other = copy.deepcopy(gate)
            other['qubits'] = list(reverse)
            other['name'] = f'cz_mirrored_{reverse[0]}_{reverse[1]}'
            reduced['gates'].append(other)
            known.add(('cz', reverse))
            mirrored.append([layout[q] for q in reverse])
    return reduced, mirrored


def remap_measured(circuit, layout):
    """Preserve instruction order, classical bits, all gates and readout Xs."""
    inv = {p: q for q, p in enumerate(layout)}
    if len(inv) != len(layout):
        raise ValueError('Non-injective layout')
    out = QuantumCircuit(len(layout), circuit.num_clbits)
    out.global_phase = circuit.global_phase
    measured = set()
    for inst in circuit.data:
        physical = [circuit.find_bit(q).index for q in inst.qubits]
        if any(q not in inv for q in physical):
            raise ValueError('Circuit uses a wire outside the frozen layout')
        if measured.intersection(physical):
            raise ValueError('Non-terminal or repeated measurement')
        if inst.operation.name not in NATIVE | {'measure'}:
            raise ValueError(f'Unexpected instruction: {inst.operation.name}')
        if inst.operation.name == 'measure':
            measured.update(physical)
        out.append(inst.operation, [inv[q] for q in physical],
                   [circuit.find_bit(c).index for c in inst.clbits])
    out.metadata = {**(circuit.metadata or {}), 'synthetic_aer': True,
                    'logical_to_physical': list(layout)}
    if out.count_ops() != circuit.count_ops():
        raise AssertionError('Gate counts changed')
    expected = sorted((q, q) for q in range(len(layout)))
    actual = sorted((out.find_bit(i.qubits[0]).index, out.find_bit(i.clbits[0]).index)
                    for i in out.data if i.operation.name == 'measure')
    if actual != expected:
        raise ValueError('Unexpected measurement map: refusing implicit bit permutation')
    return out


def build_noise(properties):
    """Aer backend-model channels without the unused automatic delay pass.

    The saved device lacks frequency. Aer 0.17.2's automatic delay-pass wrapper
    raises BackendPropertyError on this, even at zero temperature. Its public
    gate/readout helpers support missing frequency at T=0: excited population
    is zero, so no frequency is required or invented. No delays in this test.
    """
    for q in range(len(properties.qubits)):
        if not (np.isfinite(properties.t1(q)) and properties.t1(q) > 0
                and np.isfinite(properties.t2(q)) and properties.t2(q) > 0):
            raise ValueError(f'Missing or invalid T1/T2 for local wire {q}')
    model = NoiseModel(basis_gates=sorted(NATIVE))
    for qubits, error in basic_device_readout_errors(properties):
        model.add_readout_error(error, qubits)
    for name, qubits, error in basic_device_gate_errors(
            properties, gate_error=True, thermal_relaxation=True, temperature=0):
        model.add_quantum_error(error, name, qubits)
    return model


def exact_paulis(circuit, mask):
    """Noise-free finite-circuit verification, not Monte Carlo estimation."""
    unitary = circuit.remove_final_measurements(inplace=False)
    unitary.save_probabilities()
    simulator = AerSimulator(method='statevector', precision='double',
                             max_parallel_threads=1, enable_truncation=False)
    result = simulator.run(unitary, shots=1).result()
    if not result.success:
        raise RuntimeError(result.status)
    probabilities = np.asarray(result.data(0)['probabilities'])
    indices = np.arange(len(probabilities), dtype=np.uint32)
    bits = ((indices[:, None] >> np.arange(circuit.num_qubits)) & 1).astype(np.uint8)
    bits ^= np.asarray(mask, dtype=np.uint8)
    samples = pauli_samples(bits)
    return probabilities @ samples, float(probabilities.sum()), float(
        probabilities[~sector_mask(bits, 4, 4, tolerance=0)].sum())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--shots', type=int, default=8)
    parser.add_argument('--seed', type=int, default=2026090581)
    args = parser.parse_args()
    if not 1 <= args.shots <= 64:
        parser.error('Smoke test restricted to 1..64 shots, not a production sweep')
    if args.output.exists():
        parser.error('Output already exists; preserve earlier runs and select a new path')
    plan = read(PLAN / 'manifest.json')
    layout = plan['initial_layout']
    if len(layout) != 18:
        raise ValueError('This smoke test is explicitly scoped to the 18-qubit pilot')
    setting_id = 'interacting_holdout_U8_T0.4'
    index, record = next((i, r) for i, r in enumerate(plan['records'])
                         if r['setting_id'] == setting_id and r['twirl_id'] == 0)
    setting = next(s for s in plan['settings'] if s['id'] == setting_id)
    circuit_file = RUN / 'provider_inputs' / f'circuit_{index:03d}.qpy'
    with circuit_file.open('rb') as handle:
        physical = qpy.load(handle)[0]
    if physical.num_qubits != 120 or physical.parameters:
        raise ValueError('Expected bound, submitted 120-wire device circuit')
    measured = remap_measured(physical, layout)
    properties = read(CAL / 'backend_properties.json')
    snapshot = read(CAL / 'backend_snapshot.json')
    if properties['backend_name'] != 'ibm_phoenix' or snapshot['name'] != 'ibm_phoenix':
        raise ValueError('Wrong calibration device')
    edges = {tuple(e) for e in snapshot['coupling_edges']}
    for inst in physical.data:
        if inst.operation.name == 'cz':
            pair = tuple(physical.find_bit(q).index for q in inst.qubits)
            if pair not in edges and pair[::-1] not in edges:
                raise ValueError(f'CZ not in captured coupling map: {pair}')
    reduced, mirrored = restrict_properties(properties, layout)
    backend_properties = BackendProperties.from_dict(reduced)
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter('always')
        noise = build_noise(backend_properties)
    noise_dict = noise.to_dict(serializable=True)
    coverage = {(name, tuple(qs)) for e in noise_dict['errors'] if e['type'] == 'qerror'
                for name in e['operations'] for qs in e['gate_qubits']}
    required = {(i.operation.name, tuple(measured.find_bit(q).index for q in i.qubits))
                for i in measured.data if i.operation.name in {'x', 'sx', 'cz'}}
    if required - coverage:
        raise ValueError(f'Missing native noise channels: {required - coverage}')
    readouts = {q for e in noise_dict['errors'] if e['type'] == 'roerror'
                for qs in e['gate_qubits'] for q in qs}
    if readouts != set(range(18)):
        raise ValueError('Missing local readout errors')
    ideal, norm, outside_sector = exact_paulis(measured, record['readout_mask_little_endian'])
    max_error = float(np.max(np.abs(ideal - setting['reference'])))
    if max_error > 1e-9 or abs(norm - 1) > 1e-9 or outside_sector > 1e-9:
        raise AssertionError('Noise-off reference / normalization / particle sector failed')
    inputs = [Path(__file__), PLAN / 'manifest.json', circuit_file,
              CAL / 'backend_properties.json', CAL / 'backend_snapshot.json',
              ROOT / 'cuprate_2d_tflo.py']
    args.output.mkdir(parents=True)
    provenance = {
        'schema': 'aer-nighthawk-smoke-v1', 'synthetic_not_hardware': True,
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'backend_calibration': properties['backend_name'],
        'calibration_updated': properties['last_update_date'],
        'calibration_captured_unix': snapshot['captured_unix'],
        'original_job': 'dae5gat1ierc738lmg10', 'record_index': index, 'record': record,
        'physical_layout': layout, 'mirrored_symmetric_cz_physical_pairs': mirrored,
        'shots': args.shots, 'seed_simulator': args.seed,
        'method': 'statevector', 'precision': 'double', 'max_parallel_threads': 2,
        'qpu_seconds': 0, 'qiskit': qiskit.__version__, 'aer': qiskit_aer.__version__,
        'python': platform.python_version(),
        'native_counts': dict(measured.count_ops()), 'native_depth': measured.depth(),
        'noise_off_max_pauli_error': max_error, 'noise_off_norm': norm,
        'noise_off_probability_outside_4_4_sector': outside_sector,
        'covered_required_native_noise_keys': len(required), 'readout_qubits': sorted(readouts),
        'model': 'Aer calibrated depolarization + gate-time T1/T2 relaxation + readout',
        'temperature_mK': 0, 'warnings': [str(w.message) for w in captured],
        'noise_builder': 'Aer basic_device_gate_errors + basic_device_readout_errors',
        'missing_frequency_handling': 'No invented values; zero excited population at T=0.',
        'limitations': [
            'Earlier same-day full calibration, NOT last-job-time exact noise.',
            'No added idle-gap scheduling or relaxation, no pulse-level emulation.',
            'No correlated crosstalk, leakage, drift, non-Markovian or coherent-error model.',
            'Ideal initial reset; recorded init_error is not injected.',
            'Eight-shot default is feasibility only; no accuracy or mitigation conclusion.',
            'No TFLO, PEC or ZNE fitted/applied in this smoke test.',
            'Dense statevector trajectories only: not a quantum-advantage benchmark.'
        ],
        'input_sha256': {str(p.relative_to(ROOT)): digest(p) for p in inputs}
    }
    write(args.output / 'provenance.json', provenance)
    write(args.output / 'restricted_backend_properties.json', reduced)
    write(args.output / 'noise_model.json', noise_dict)
    with (args.output / 'measured_active18.qpy').open('wb') as handle:
        qpy.dump(measured, handle)
    print(json.dumps({'stage': 'verified_noise_off_and_mapping', 'max_error': max_error,
                      'shots': args.shots, 'cz': measured.count_ops()['cz']}), flush=True)
    simulator = AerSimulator(method='statevector', precision='double', noise_model=noise,
                             max_parallel_threads=2, max_parallel_shots=2,
                             enable_truncation=False)
    start = time.perf_counter()
    result = simulator.run(measured, shots=args.shots, memory=True,
                           seed_simulator=args.seed).result()
    elapsed = time.perf_counter() - start
    if not result.success:
        raise RuntimeError(result.status)
    memory = result.get_memory(0)
    bits = decode_bitstrings(memory, 18, record['readout_mask_little_endian'])
    if len(memory) != args.shots:
        raise AssertionError('Shot count mismatch')
    raw = {'schema': 'synthetic-aer-memory-v1', 'setting_id': setting_id,
           'twirl_id': record['twirl_id'], 'readout_mask_little_endian': record['readout_mask_little_endian'],
           'memory': memory, 'decoded_little_endian_bits': bits.tolist()}
    write(args.output / 'synthetic_memory.json', raw)
    write(args.output / 'aer_result.json', result.to_dict())
    summary = {'status': 'PASS_feasibility_only', 'noisy_shots': args.shots,
               'run_wall_seconds': elapsed, 'qpu_seconds': 0,
               'noise_off_max_pauli_error': max_error,
               'quality_not_established': True,
               'linear_512_shot_projection_seconds_not_benchmark': elapsed / args.shots * 512}
    write(args.output / 'summary.json', summary)
    write(args.output / 'sha256.json', {p.name: digest(p) for p in args.output.iterdir() if p.is_file()})
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    main()
