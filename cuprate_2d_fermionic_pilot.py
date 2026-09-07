"""Frozen 18-qubit full-fermion pilot: prepare, submit ONCE, or retrieve.

All physics includes t, t-prime, U and JW signs. The 3x3 circuit is a validation
pilot, not a quantum-advantage task. No submission occurs in prepare mode.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
import uuid
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, qpy, transpile
from qiskit.quantum_info import SparsePauliOp
from qiskit_aer import AerSimulator
from scipy.sparse.linalg import expm_multiply
from threadpoolctl import threadpool_limits

from cuprate_2d_hubbard_pipeline import Cuprate2DConfig
from cuprate_2d_fermionic_mapping import build_network
from cuprate_2d_exact_sector_baseline import sector_basis, initial_state_vector, diagonal_site_rows
from validate_cuprate_2d_fermionic_dynamics import independent_hamiltonian, phase_distance
from validate_cuprate_2d_fswap_baseline import differences
from prepare_cuprate_2d_fermionic_sweep import save_qpy, circuit_summary, pauli_records
from optimize_cuprate_2d_fermionic_mapping import find_paths

KEYS = ('charge', 'spin_z', 'double_occupancy')
BACKEND = 'ibm_phoenix'
ACCOUNT = 'qiskit-runtime-q9'
SHOTS = 512
MAX_SECONDS = 5
FACTORS = [1.0, 3.0, 5.0]


def save(path, value):
    from qiskit_ibm_runtime.json import RuntimeEncoder
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, cls=RuntimeEncoder, indent=2) + '\n', encoding='utf-8')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sources():
    names = [Path(__file__).name, 'cuprate_2d_hubbard_pipeline.py',
             'cuprate_2d_fermionic_mapping.py', 'cuprate_2d_fermionic_dynamics.py',
             'cuprate_2d_exact_sector_baseline.py', 'validate_cuprate_2d_fermionic_dynamics.py',
             'prepare_cuprate_2d_fermionic_sweep.py', 'optimize_cuprate_2d_fermionic_mapping.py',
             'validate_cuprate_2d_fswap_baseline.py', 'ibm_staged_fermi_hubbard_runner.py']
    return {name: digest(Path(__file__).with_name(name)) for name in names}


def simulator_state(circuit):
    simulator = AerSimulator(method='statevector', max_parallel_threads=1,
                             precision='double', enable_truncation=False)
    copy = circuit.copy()
    copy.save_statevector()
    prepared = transpile(copy, backend=simulator, optimization_level=0, seed_transpiler=9)
    result = simulator.run(prepared, shots=1).result()
    if not result.success:
        raise RuntimeError('Exact local simulation failed')
    return np.asarray(result.get_statevector(), dtype=complex)


def pilot_observables(cfg):
    records, ops = [], []
    for site in range(cfg.sites):
        def label(qubits):
            text = ['I'] * cfg.qubits
            for q in qubits:
                text[cfg.qubits-1-q] = 'Z'
            return ''.join(text)
        ident, up, dn, both = label([]), label([2*site]), label([2*site+1]), label([2*site, 2*site+1])
        definitions = [('charge', [(ident, 1.0), (up, -0.5), (dn, -0.5)]),
                       ('spin_z', [(up, -0.5), (dn, 0.5)]),
                       ('double_occupancy', [(ident, 0.25), (up, -0.25), (dn, -0.25), (both, 0.25)])]
        for name, terms in definitions:
            ops.append(SparsePauliOp.from_list(terms))
            records.append({'site': site, 'x': site % cfg.lx, 'y': site // cfg.lx,
                            'observable': name, 'logical_paulis': terms})
    return records, ops


def options(tag):
    # 8 randomizations x 64 shots = 512 per factor, one common Z basis.
    return {'default_shots': SHOTS, 'max_execution_time': MAX_SECONDS,
            'resilience_level': 0, 'dynamical_decoupling': {'enable': False},
            'twirling': {'enable_gates': True, 'enable_measure': True,
                         'num_randomizations': 8, 'shots_per_randomization': 64},
            'environment': {'job_tags': ['2d-cuprate', 'full-fermion-pilot', tag]},
            'resilience': {'measure_mitigation': False, 'pec_mitigation': False,
                           'zne_mitigation': True, 'zne': {'amplifier': 'gate_folding',
                           'noise_factors': FACTORS, 'extrapolator': ['linear', 'fallback'],
                           'extrapolated_noise_factors': [0.0]}}}


def prepare(root):
    if (root/'plan.json').exists() or (root/'submission_attempt.json').exists():
        raise FileExistsError('Refusing to overwrite an existing pilot plan or submission')
    root.mkdir(parents=True, exist_ok=True)
    cfg = Cuprate2DConfig(lx=3, ly=3, holes=1, steps=2, dt=0.1, shots=SHOTS)
    save(root/'config.json', asdict(cfg))
    checks = []
    def check(name, value, tolerance):
        record = {'check': name, 'value': float(value), 'threshold': tolerance,
                  'passed': bool(value <= tolerance)}
        checks.append(record)
        print(json.dumps(record), flush=True)
        if not record['passed']:
            save(root/'failed_checks.json', checks)
            raise AssertionError(name)
    started = time.perf_counter()
    basis, index, n_up, n_down = sector_basis(cfg)
    h = independent_hamiltonian(cfg, basis)
    difference = h-h.conj().T
    check('independent_H_hermitian', np.max(np.abs(difference.data)) if difference.nnz else 0, 1e-12)
    init = initial_state_vector(cfg, index)
    exact = expm_multiply(-1j*cfg.total_time*h, init)
    check('exact_H_norm', abs(np.vdot(exact, exact).real-1), 1e-10)
    exact_rows = diagonal_site_rows(cfg, basis, exact, cfg.steps, cfg.total_time, 'exact_H')
    save(root/'exact_hamiltonian_observables.json', exact_rows)
    refinement = []
    logical = build_network(cfg)
    state = simulator_state(logical)
    np.savez_compressed(root/'exact_reference_states.npz', basis=np.asarray(basis, dtype=np.int64),
                        logical_statevector=state, exact_hamiltonian_sector_state=exact)
    logical_hash = save_qpy(root/'logical_circuit.qpy', logical)
    logical_rows = diagonal_site_rows(cfg, basis, state[basis], cfg.steps, cfg.total_time, 'exact_circuit')
    save(root/'exact_circuit_observables.json', logical_rows)
    check('logical_state_norm', abs(np.vdot(state, state).real-1), 1e-10)
    check('logical_correct_spin_sector', abs(np.vdot(state[basis], state[basis]).real-1), 1e-10)
    for steps in (2, 4, 8):
        selected = replace(cfg, steps=steps, dt=cfg.total_time/steps)
        vector = state if steps == 2 else simulator_state(build_network(selected))
        rows = diagonal_site_rows(selected, basis, vector[basis], steps, cfg.total_time, f'dt_{selected.dt}')
        check(f'refined_sector_steps{steps}', abs(np.vdot(vector[basis], vector[basis]).real-1), 1e-10)
        refinement.append({'steps': steps, 'dt': selected.dt,
                           'state_distance_to_exact_H': phase_distance(vector[basis], exact),
                           'observable_errors_to_exact_H': differences(rows, exact_rows), 'sites': rows})
    for i in (0, 1):
        ratio = refinement[i]['state_distance_to_exact_H']/refinement[i+1]['state_distance_to_exact_H']
        check(f'second_order_refinement_ratio_{i}', abs(ratio-4.0), 0.7)
    # This pilot isolates hardware error against its exact circuit; its finite
    # timestep bias is reported separately, never counted as QPU noise.
    save(root/'timestep_refinement.json', refinement)
    records, ops = pilot_observables(cfg)
    for record, op in zip(records, ops):
        expected = logical_rows[record['site']][record['observable']]
        check(f"observable_{record['site']}_{record['observable']}",
              abs(float(np.real(np.vdot(state, op.to_matrix(sparse=True) @ state)))-expected), 1e-10)
    classical_seconds = time.perf_counter()-started
    print(json.dumps({'event': 'exact_reference_ready', 'sector_dimension': len(basis),
                      'classical_validation_seconds': classical_seconds}), flush=True)

    from ibm_staged_fermi_hubbard_runner import build_runtime_service
    backend = build_runtime_service(ACCOUNT).backend(BACKEND)
    status = backend.status()
    if not status.operational:
        raise RuntimeError('Phoenix is not operational; no submission')
    paths, calibration = find_paths(backend, cfg.qubits)
    layout = paths[0]['path']
    save(root/'layout_candidates.json', paths)
    save(root/'backend_snapshot.json', {'name': backend.name, 'num_qubits': backend.num_qubits,
         'captured_unix': time.time(), 'status': status.to_dict(), **calibration})
    save(root/'backend_properties.json', backend.properties().to_dict())
    isa = transpile(logical, backend=backend, initial_layout=layout, routing_method='none',
                    optimization_level=3, seed_transpiler=9, approximation_degree=1.0)
    if isa.layout.final_index_layout(filter_ancillas=True) != layout:
        raise ValueError('Unexpected routing permutation')
    edges = {tuple(e) for e in calibration['coupling_edges']}
    inverse = {physical: logical_q for logical_q, physical in enumerate(layout)}
    trimmed = QuantumCircuit(cfg.qubits)
    trimmed.global_phase = isa.global_phase
    for instruction in isa.data:
        physical = [isa.find_bit(q).index for q in instruction.qubits]
        if any(q not in inverse for q in physical):
            raise ValueError('Transpiler used wires outside the frozen path')
        if len(physical) == 2 and tuple(sorted(physical)) not in edges:
            raise ValueError('Non-native coupling in ISA')
        if instruction.operation.name not in ('rz', 'sx', 'x', 'cz'):
            raise ValueError('Non-native gate or measurement in ISA')
        trimmed.append(instruction.operation, [inverse[q] for q in physical])
    native_state = simulator_state(trimmed)
    check('native_ISA_state_equivalence_18_qubits', phase_distance(native_state, state), 2e-9)
    save_qpy(root/'isa_active18_circuit.qpy', trimmed)
    isa_hash = save_qpy(root/'isa_circuit.qpy', isa)
    mapped = []
    for record, op in zip(records, ops):
        physical_op = op.apply_layout(isa.layout)
        recovered = []
        for label, coefficient in physical_op.to_list():
            assert all(letter == 'I' or q in inverse for q, letter in enumerate(reversed(label)))
            recovered.append((''.join(label[isa.num_qubits-1-layout[q]] for q in reversed(range(cfg.qubits))), coefficient))
        assert SparsePauliOp.from_list(recovered).equiv(op)
        mapped.append({**record, 'physical_paulis': pauli_records(physical_op)})
    save(root/'observables.json', mapped)
    tag = 'fh3x3-' + uuid.uuid4().hex[:16]
    opts = options(tag)
    from qiskit_ibm_runtime.options import EstimatorOptions
    EstimatorOptions(**opts)
    try:
        gate_duration = float(isa.estimate_duration(backend.target, unit='s'))
    except Exception:
        gate_duration = None
    plan = {'submitted': False, 'backend': BACKEND, 'account_name': ACCOUNT,
            'tag': tag, 'config': asdict(cfg), 'circuit_family': 'fermionic_fswap_network',
            'initial_layout': layout, 'final_index_layout': isa.layout.final_index_layout(filter_ancillas=True),
            'logical': circuit_summary(logical), 'isa': circuit_summary(isa),
            'qpy_sha256': {'logical': logical_hash, 'isa': isa_hash}, 'options': opts,
            'observable_count': len(mapped), 'measurement_bases': ['Z'],
            'target_shots_all_factors': SHOTS*len(FACTORS),
            'gate_only_duration_estimate_s': gate_duration,
            'folded_gate_only_seconds_all_shots': None if gate_duration is None else gate_duration*SHOTS*sum(FACTORS),
            'budget_boundary': 'max_execution_time=5 is a provider cap, not a promise of success or a gate-only billing estimate.',
            'sector': {'n_up': n_up, 'n_down': n_down, 'dimension': len(basis)},
            'classical_reference_and_validation_seconds': classical_seconds,
            'validation': {'passed': True, 'checks': checks, 'source_sha256': sources()},
            'reference_kind': 'Exact circuit statevector and independent fixed-sector Hamiltonian evolution',
            'pilot_point_estimate_targets': {'rmse_each_observable': 0.05, 'max_site_error_each_observable': 0.10},
            'target_boundary': 'Exploratory point-estimate screen, not a statistical certification or a quantum-advantage claim.'}
    save(root/'plan.json', plan)
    save(root/'frozen_inputs_sha256.json', {p.name: digest(p) for p in root.iterdir() if p.is_file() and p.name != 'frozen_inputs_sha256.json'})
    print(json.dumps({'event': 'pilot_prepared', 'checks_passed': len(checks),
                      'isa': plan['isa'], 'options': opts,
                      'folded_gate_only_seconds_all_shots': plan['folded_gate_only_seconds_all_shots']}), flush=True)


def verify_frozen(root):
    for name, expected in read(root/'frozen_inputs_sha256.json').items():
        if digest(root/name) != expected:
            raise ValueError(f'Frozen input changed: {name}')
    plan = read(root/'plan.json')
    for name, expected in plan['validation']['source_sha256'].items():
        if digest(Path(__file__).with_name(name)) != expected:
            raise ValueError(f'Validated source changed: {name}')
    if not plan['validation']['passed'] or not all(c['passed'] for c in plan['validation']['checks']):
        raise ValueError('Physics validation not passed')
    if plan['options'] != options(plan['tag']) or plan['backend'] != BACKEND:
        raise ValueError('Frozen budget/options/backend mismatch')
    return plan


def submit(root):
    plan = verify_frozen(root)
    receipt = root/'submission_receipt.json'
    attempt = root/'submission_attempt.json'
    if receipt.exists() or attempt.exists():
        raise FileExistsError('Submission already attempted: retrieve or investigate, never retry blindly')
    from ibm_staged_fermi_hubbard_runner import build_runtime_service
    from qiskit_ibm_runtime import EstimatorV2
    service = build_runtime_service(ACCOUNT)
    backend = service.backend(BACKEND)
    if not backend.status().operational:
        raise RuntimeError('Backend unavailable; submission not attempted')
    with (root/'isa_circuit.qpy').open('rb') as handle:
        isa = qpy.load(handle)[0]
    ops = [SparsePauliOp.from_list(r['physical_paulis']) for r in read(root/'observables.json')]
    estimator = EstimatorV2(mode=backend, options=plan['options'])
    with attempt.open('x', encoding='utf-8') as handle:
        json.dump({'started_unix': time.time(), 'tag': plan['tag'],
                   'max_execution_time': MAX_SECONDS, 'shots_per_factor': SHOTS,
                   'warning': 'A missing receipt after dispatch requires lookup by tag, not resubmission.'}, handle)
    job = estimator.run([(isa, ops)])
    result = {'submitted': True, 'submitted_unix': time.time(), 'job_id': str(job.job_id()),
              'backend': BACKEND, 'account_name': ACCOUNT, 'tag': plan['tag'],
              'max_execution_time': MAX_SECONDS, 'shots_per_factor': SHOTS}
    save(receipt, result)
    print(json.dumps(result), flush=True)


def rows_from_values(values, records, profile, stds=None):
    rows = {}
    for i, (record, value) in enumerate(zip(records, values, strict=True)):
        site = record['site']
        row = rows.setdefault(site, {'site': site, 'x': record['x'], 'y': record['y'],
                                    'profile': profile, 'step': 2, 'time': 0.2})
        row[record['observable']] = float(value)
        if stds is not None:
            row[record['observable']+'_standard_error'] = float(stds[i])
    for row in rows.values():
        row['n_up'] = (row['charge']+row['spin_z'])/2
        row['n_down'] = (row['charge']-row['spin_z'])/2
    return [rows[s] for s in sorted(rows)]


def retrieve(root):
    from ibm_staged_fermi_hubbard_runner import build_runtime_service
    receipt = read(root/'submission_receipt.json')
    service = build_runtime_service(ACCOUNT)
    job = service.job(receipt['job_id'])
    status = job.status()
    status = str(getattr(status, 'name', status))
    live = {'job_id': receipt['job_id'], 'status': status, 'checked_unix': time.time()}
    save(root/'job_status.json', live)
    print(json.dumps(live), flush=True)
    if status != 'DONE':
        if status in ('ERROR', 'CANCELLED'):
            save(root/'job_failure.json', {'status': status, 'error': job.error_message()})
        return
    plan = verify_frozen(root)
    primitive = job.result()
    metrics = job.metrics()
    save(root/'provider_metrics.json', metrics)
    save(root/'provider_inputs.json', job.inputs)
    save(root/'provider_result_complete.json', primitive)
    data = primitive[0].data
    arrays = {key: np.asarray(getattr(data, key)).tolist() for key in
              ('evs', 'stds', 'evs_noise_factors', 'stds_noise_factors',
               'ensemble_stds_noise_factors', 'evs_extrapolated', 'stds_extrapolated') if hasattr(data, key)}
    save(root/'result_arrays.json', {'arrays': arrays, 'metadata': primitive[0].metadata})
    records = read(root/'observables.json')
    rows = rows_from_values(np.asarray(data.evs).reshape(-1), records, 'zne', np.asarray(data.stds).reshape(-1))
    profiles = [('zne', rows)]
    if hasattr(data, 'evs_noise_factors'):
        raw = np.asarray(data.evs_noise_factors)
        if raw.shape != (len(records), len(FACTORS)):
            raise ValueError(f'Unexpected factor array shape {raw.shape}')
        for i, factor in enumerate(FACTORS):
            profiles.append((f'factor_{factor:g}', rows_from_values(raw[:, i], records, f'factor_{factor:g}')))
    reference = read(root/'exact_circuit_observables.json')
    h_reference = read(root/'exact_hamiltonian_observables.json')
    comparison = []
    for name, measured in profiles:
        save(root/f'{name}_site_observables.json', measured)
        comparison.append({'profile': name, 'vs_exact_circuit': differences(measured, reference),
                           'vs_exact_hamiltonian': differences(measured, h_reference),
                           'total_charge': sum(r['charge'] for r in measured),
                           'total_spin_z': sum(r['spin_z'] for r in measured)})
    targets = plan['pilot_point_estimate_targets']
    point_screen = all(v['rmse'] <= targets['rmse_each_observable'] and
                       v['max_abs'] <= targets['max_site_error_each_observable']
                       for v in comparison[0]['vs_exact_circuit'].values())
    summary = {'job_id': receipt['job_id'], 'status': 'DONE', 'comparison': comparison,
               'zne_point_estimate_screen_passed': point_screen, 'targets': targets,
               'qpu_charge_time_seconds': metrics.get('usage', {}).get('qpu_charge_time_seconds'),
               'claim_boundary': 'Small exact-reference full-fermion hardware pilot. Pointwise statistical errors do not include all ZNE systematic bias; no advantage claim.'}
    save(root/'comparison.json', summary)
    lines = ['# 3x3 full-fermion hardware pilot', '', f"Job: {receipt['job_id']} on {BACKEND}; DONE.",
             '18 logical qubits, one hole, N-up=N-down=4, U/t=8, t-prime/t=-0.25; two dt=0.1 steps.',
             'ZNE factors 1/3/5, 512 shots per factor, eight twirls of 64 shots. No additional readout learning or PEC job.',
             f"Provider QPU charge time: {summary['qpu_charge_time_seconds']} seconds; requested maximum 5 seconds.", '',
             '| profile | charge RMSE | spin RMSE | doublon RMSE | total charge (target 8) |',
             '|---|---:|---:|---:|---:|']
    for r in comparison:
        d = r['vs_exact_circuit']
        lines.append(f"| {r['profile']} | {d['charge']['rmse']:.6f} | {d['spin_z']['rmse']:.6f} | {d['double_occupancy']['rmse']:.6f} | {r['total_charge']:.6f} |")
    lines += ['', f'ZNE point-estimate screen passed: {point_screen}. RMSE <= 0.05 and maximum site error <= 0.10 for each of the three observables.',
              'Factor 1 is the unextrapolated, twirled result from the SAME job; it is not an independent no-twirling raw control.',
              'Hardware errors above are against the exact finite-step circuit. Hamiltonian/Trotter bias is separately recorded in timestep_refinement.json and comparison.json.',
              'Spin-z uses n-up minus n-down (twice physical S-z). No clipping, particle-sector projection, or favorable-site selection is applied.',
              'This screen is exploratory, not statistical certification. ZNE standard errors omit possible model/systematic bias; covariance between different observables is not reconstructed.',
              'This classically tractable pilot validates a workflow; it cannot demonstrate quantum advantage or establish 6x6 performance.', '']
    (root/'pilot_report.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'submit', 'retrieve'])
    parser.add_argument('--outdir', type=Path, required=True)
    args = parser.parse_args()
    with threadpool_limits(limits=1):
        {'prepare': prepare, 'submit': submit, 'retrieve': retrieve}[args.action](args.outdir)
