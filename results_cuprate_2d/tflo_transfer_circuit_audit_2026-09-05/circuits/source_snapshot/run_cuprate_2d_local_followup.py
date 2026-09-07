"""Local, artifact-first exploratory audit. No IBM/Fire Opal submission path."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from qiskit import qpy
from scipy.sparse.linalg import expm_multiply
from threadpoolctl import threadpool_limits

from cuprate_2d_hubbard_pipeline import Cuprate2DConfig
from cuprate_2d_tflo import (parameterized_network, compile_template, bind, skeleton,
    explicit_twirl, embed_measurement, physical_observables, pauli_samples, flo_reference)
from cuprate_2d_tflo_refinement import cleanup_one_qubit, active_circuit, resample_paired
from analyze_cuprate_2d_tflo import load_archive
from cuprate_2d_exact_sector_baseline import sector_basis, initial_state_vector, build_hamiltonian, MODEL_FULL
from validate_cuprate_2d_fermionic_dynamics import independent_hamiltonian
from prepare_cuprate_2d_tflo_compact_pilot import read, save, digest, verify_tree
from preflight_cuprate_2d_tflo_budget import wire_time
from cuprate_2d_local_followup import (METHODS, means, fit_models, predict,
    sparse_template, local_state, phase_distance, two_qubit_depth, interval)

BASE = Path(__file__).resolve().parent
RESULTS = BASE / 'results_cuprate_2d'
ROOT = RESULTS / 'tflo_transfer_circuit_audit_2026-09-05'
PLAN = RESULTS / 'tflo_compact_pilot_3x3_2026-09-05'
RUN = RESULTS / 'tflo_compact_run_3x3_2026-09-05'
OLD = RESULTS / 'tflo_pilot_3x3_2026-09-05_ready'
SOURCE_NAMES = ('cuprate_2d_local_followup.py', 'run_cuprate_2d_local_followup.py',
    'test_cuprate_2d_local_followup.py', 'cuprate_2d_tflo.py', 'cuprate_2d_tflo_refinement.py',
    'cuprate_2d_fermionic_mapping.py', 'cuprate_2d_fermionic_dynamics.py',
    'cuprate_2d_hubbard_pipeline.py', 'cuprate_2d_exact_sector_baseline.py',
    'validate_cuprate_2d_fermionic_dynamics.py', 'analyze_cuprate_2d_tflo.py',
    'preflight_cuprate_2d_tflo_budget.py')


def setup(stage):
    verify_tree(PLAN)
    verify_tree(RUN / 'primary_analysis')
    plan = read(PLAN / 'manifest.json')
    if digest(PLAN / 'manifest.json') != '823015bd20de02232c582388294bbf8146de9781292843a17fab1b5c170aab6d':
        raise ValueError('Frozen plan changed')
    if digest(RUN / 'raw_bitstrings.json') != read(RUN / 'primary_analysis/results.json')['raw_sha256']:
        raise ValueError('Hardware samples changed')
    if digest(OLD / 'submission_attempt.json') != plan['provenance']['old_submission_lock_sha256']:
        raise ValueError('Original submission lock changed')
    folder = ROOT / stage
    folder.mkdir(exist_ok=False)
    source = folder / 'source_snapshot'
    source.mkdir()
    for name in SOURCE_NAMES:
        shutil.copyfile(BASE / name, source / name)
    save(folder / 'inputs.json', {'protocol_sha256': digest(ROOT / 'PROTOCOL.md'),
        'plan_sha256': digest(PLAN / 'manifest.json'), 'raw_sha256': digest(RUN / 'raw_bitstrings.json'),
        'old_lock_sha256': digest(OLD / 'submission_attempt.json'),
        'compact_lock_sha256': digest(PLAN / 'submission_attempt.json'),
        'source_sha256': {name: digest(BASE / name) for name in SOURCE_NAMES},
        'new_QPU_seconds': 0, 'created_unix': time.time(), 'exploratory': True})
    return folder, plan, Cuprate2DConfig(**plan['config'])


def seal(folder):
    save(folder / 'sha256.json', {str(p.relative_to(folder)): digest(p)
         for p in sorted(folder.rglob('*')) if p.is_file()})
    verify_tree(folder)


def audit():
    folder, plan, _ = setup('transfer')
    _, _, decoded, _, _ = load_archive(PLAN, RUN / 'raw_bitstrings.json')
    settings = plan['settings']
    decoded = {s['id']: decoded[s['id']] for s in settings}
    cal = [s for s in settings if s['u_over_t'] == 0]
    valid = [i for i, s in enumerate(settings) if s['role'] == 'flo_holdout']
    target = [i for i, s in enumerate(settings) if s['role'] == 'interacting_holdout']
    partner = [next(i for i, s in enumerate(settings) if s['u_over_t'] == 0 and s['time'] == settings[j]['time']) for j in target]
    models = fit_models(cal, {s['id']: decoded[s['id']] for s in cal})
    selected, counts = means(settings, decoded)
    unfiltered, _ = means(settings, decoded, 18, 1)
    times = [s['time'] for s in settings]
    predictions = {name: predict(model, selected, times) for name, model in models.items()}
    old_model = read(RUN / 'primary_analysis/U0_fit_frozen.json')['model']
    if not np.allclose(old_model['coefficients'], models['linear_linear']['coefficients'], atol=1e-12, rtol=0):
        raise ValueError('Current TFLO model not reproduced')
    save(folder / 'models_U0_only.json', {'models': models,
        'training_ids': [s['id'] for s in cal if s['role'] == 'train'], 'model_selected': None,
        'no_U8_training': True, 'old_primary_unchanged': True})
    refs = np.asarray([s['reference'] for s in settings])
    classical = np.asarray([r['pauli_prediction'] for r in read(PLAN / 'classical_control_predictions.json')])
    actual_ids = [settings[i]['id'] for i in target]
    if actual_ids != [r['setting_id'] for r in read(PLAN / 'classical_control_predictions.json')]:
        raise ValueError('Classical control order mismatch')
    B, rng = 400, np.random.default_rng(2026090551)
    draws = {name: np.full((B, 10, 27), np.nan) for name in METHODS}
    raw_draws = np.full((B, 10, 27), np.nan)
    failures = 0
    for b in range(B):
        sampled = resample_paired(decoded, rng)
        try:
            x, _ = means(settings, sampled)
            fitted = fit_models(cal, {s['id']: sampled[s['id']] for s in cal})
            raw_draws[b] = means(settings, sampled, 18, 1)[0]
            for name in METHODS:
                draws[name][b] = predict(fitted[name], x, times)
        except ValueError:
            failures += 1
        if (b+1) % 100 == 0:
            print(json.dumps({'stage': 'transfer_bootstrap', 'completed': b+1}), flush=True)
    np.savez_compressed(folder / 'bootstrap_predictions.npz', raw=raw_draws, **draws)
    classical_mse = float(np.mean((classical-refs[target])**2))
    true_delta = refs[target]-refs[partner]
    zero_delta_mse = float(np.mean(true_delta**2))
    zero_norm = float(np.sum(true_delta**2))
    rows = []
    for name in METHODS:
        p, samples = predictions[name], draws[name]
        mse_samples = np.mean((samples[:, target]-refs[target])**2, axis=(1, 2))
        delta = p[target]-p[partner]
        delta_samples = samples[:, target]-samples[:, partner]
        row = {'method': name, 'U0_holdout_MSE': float(np.mean((p[valid]-refs[valid])**2)),
            'U8_target_MSE': float(np.mean((p[target]-refs[target])**2)),
            'classical_minus_method_MSE_gain_ci95': interval(classical_mse-mse_samples),
            'contrast_MSE': float(np.mean((delta-true_delta)**2)),
            'zero_minus_contrast_MSE_gain_ci95': interval(zero_delta_mse-np.mean((delta_samples-true_delta)**2, axis=(1, 2))),
            'contrast_projection_fraction': float(np.sum(delta*true_delta)/zero_norm),
            'contrast_projection_ci95': interval(np.sum(delta_samples*true_delta, axis=(1, 2))/zero_norm),
            'per_time': []}
        for i in target:
            phys = physical_observables(p[i])
            phys_samples = physical_observables(samples[:, i])
            mask = np.isfinite(phys_samples).all(axis=(1, 2))
            phys_samples = phys_samples[mask]
            row['per_time'].append({'time': settings[i]['time'],
                'rmse_charge_spin_double': np.sqrt(np.mean((phys-physical_observables(refs[i]))**2, axis=0)).tolist(),
                'rms_bootstrap_SE_charge_spin_double': np.sqrt(np.mean(np.var(phys_samples, axis=0, ddof=1), axis=0)).tolist(),
                'out_of_bounds_count': int(np.sum((phys<[0., -1., 0.]) | (phys>[2., 1., 1.])))})
        rows.append(row)
    full, full_samples = predictions['linear_linear'], draws['linear_linear']
    mse_real = np.mean((full_samples[:, target]-refs[target])**2, axis=(1, 2))
    mse_ablated = np.mean((full_samples[:, partner]-refs[target])**2, axis=(1, 2))
    ablation = {'description': 'Replace U8 measured input with same-time U0 measured input; fitted model held fixed per replicate.',
        'actual_U8_MSE': float(np.mean((full[target]-refs[target])**2)),
        'ablated_U8_MSE': float(np.mean((full[partner]-refs[target])**2)),
        'ablated_minus_real_MSE_gain_ci95': interval(mse_ablated-mse_real)}
    result = {'stage': 'EXPLORATORY_TRANSFER_AUDIT', 'new_QPU_seconds': 0,
        'source_job': 'dae5gat1ierc738lmg10', 'fixed_tolerance': 1, 'fixed_ridge': .001,
        'counts': counts, 'models': rows, 'classical_FLO_only_MSE': classical_mse,
        'raw_U8_MSE': float(np.mean((unfiltered[target]-refs[target])**2)),
        'zero_contrast_MSE': zero_delta_mse, 'current_TFLO_ablation': ablation,
        'bootstrap_replicates': B, 'bootstrap_failures': failures,
        'no_model_selected_or_promoted': True,
        'limits': 'Post-hoc diagnostic; same-time U0 contrast points trained the models. No new independent validation or bias-free CI claim.'}
    save(folder / 'results.json', result)
    seal(folder)
    print(json.dumps({'stage': result['stage'], 'models': [{k: r[k] for k in ('method', 'U0_holdout_MSE', 'U8_target_MSE', 'contrast_MSE', 'contrast_projection_fraction')} for r in rows], 'ablation': ablation}), flush=True)


class CachedTarget(dict):
    pass


def timing_target():
    snapshot = read(RESULTS / 'tflo_compact_budget_2026-09-05/backend_timing_snapshot.json')
    target = CachedTarget()
    for instruction in snapshot['used_instructions']:
        name, pair = instruction['name'], tuple(instruction['qubits'])
        prop = SimpleNamespace(duration=instruction['duration_seconds'], error=instruction['error'])
        target.setdefault(name, {})[pair] = prop
        if name == 'cz':
            target[name].setdefault(tuple(reversed(pair)), prop)
    target.dt = snapshot['dt_seconds']
    target.pulse_alignment = snapshot['pulse_alignment_dt']
    target.acquire_alignment = snapshot['acquire_alignment_dt']
    return target, snapshot


def qpy_checked(path, circuit):
    with path.open('xb') as handle:
        qpy.dump(circuit, handle)
    with path.open('rb') as handle:
        restored = qpy.load(handle)
    expected = circuit if isinstance(circuit, list) else [circuit]
    if restored != expected:
        raise ValueError('QPY roundtrip failed')


def circuits():
    folder, plan, cfg = setup('circuits')
    target, snapshot = timing_target()
    reference = parameterized_network(cfg)
    refs = {(u, t): local_state(bind(reference, cfg, t, u)) for u, t in ((0., .2), (8., .2), (8., .4))}
    candidates = {'network': reference, **{name: sparse_template(cfg, name) for name in ('left', 'right', 'look4', 'look12')}}
    rows, natives = [], {}
    for name, circuit in candidates.items():
        native = compile_template(circuit)
        natives[name] = native
        row = {'name': name, 'operations': dict(native.count_ops()), 'depth': native.depth(),
            'CZ': native.count_ops().get('cz', 0), 'two_qubit_depth': two_qubit_depth(native),
            'source_routing_fswaps': circuit.metadata.get('routing_fswaps'), 'state_checks': []}
        physical = embed_measurement(native, plan['initial_layout'], 120)
        row['cached_measured_circuit_seconds'] = wire_time(physical, target, aligned=True)
        for (u, t), exact in refs.items():
            logical_state = local_state(bind(circuit, cfg, t, u))
            native_state = local_state(bind(native, cfg, t, u))
            error = max(phase_distance(logical_state, exact), phase_distance(native_state, exact))
            row['state_checks'].append({'U': u, 'time': t, 'max_phase_aligned_state_distance': error})
            if error > 1e-9:
                save(folder / ('FAILED_' + name + '.json'), row)
                raise ValueError('Candidate changed the ideal circuit')
        signatures = [skeleton(bind(native, cfg, s['time'], s['u_over_t'])) for s in plan['settings']]
        if any(value != skeleton(native) for value in signatures):
            raise ValueError('Binding changed native skeleton')
        qpy_checked(folder / (name + '_unbound_native.qpy'), native)
        rows.append(row)
        print(json.dumps({'stage': 'circuit_candidate', **{k: row[k] for k in ('name', 'CZ', 'depth', 'two_qubit_depth', 'cached_measured_circuit_seconds')}}), flush=True)
    baseline = next(r for r in rows if r['name'] == 'network')
    if baseline['CZ'] != 1008:
        raise ValueError('Original native CZ count not reproduced')
    best = min(rows, key=lambda r: (r['CZ'], r['two_qubit_depth'], r['name']))
    native = natives[best['name']]
    twirled, twirl_rows = [], []
    for twirl in range(8):
        logical, mask = explicit_twirl(native, 202609050+twirl)
        compact = cleanup_one_qubit(embed_measurement(logical, plan['initial_layout'], 120))
        twirled.append(compact)
        row = {'twirl': twirl, 'readout_mask_little_endian': mask.tolist(),
            'CZ': compact.count_ops().get('cz', 0), 'operations': dict(compact.count_ops()),
            'depth': compact.depth(), 'cached_measured_circuit_seconds': wire_time(compact, target, aligned=True)}
        for setting in plan['settings']:
            if skeleton(bind(compact, cfg, setting['time'], setting['u_over_t'])) != skeleton(compact):
                raise ValueError('Twirled binding changed skeleton')
        check = active_circuit(bind(compact, cfg, .2, 8.), plan['initial_layout'])
        for q in np.flatnonzero(mask):
            check.x(int(q))
        row['decoded_target_state_distance'] = phase_distance(local_state(check), refs[(8., .2)])
        if row['decoded_target_state_distance'] > 1e-9:
            raise ValueError('Twirl/readout/cleanup changed decoded ideal state')
        twirl_rows.append(row)
    qpy_checked(folder / 'best_eight_unbound_templates.qpy', twirled)
    all_shots = sum(10*64*(r['cached_measured_circuit_seconds']+snapshot['selected_reset_duration_seconds']+snapshot['default_rep_delay_seconds']) for r in twirl_rows)
    result = {'stage': 'LOCAL_SAME_IDEAL_CIRCUIT_COMPARISON', 'new_QPU_seconds': 0,
        'candidates': rows, 'minimum_CZ_candidate': best['name'],
        'CZ_reduction_fraction': 1-best['CZ']/baseline['CZ'], 'twirled_best': twirl_rows,
        'cached_total_5120_shot_execution_seconds': all_shots,
        'calibration_captured_utc': snapshot['captured_utc'],
        'timing_limit': 'Saved calibration, symmetric CZ-duration lookup; not live ISA validation, billing or fidelity measurement.',
        'hardware_ready_or_authorized': False, 'new_noncommuting_order': False}
    save(folder / 'results.json', result)
    seal(folder)
    print(json.dumps({'stage': result['stage'], 'best': best['name'], 'CZ': best['CZ'],
        'CZ_reduction_fraction': result['CZ_reduction_fraction'], 'cached_shot_execution_seconds': all_shots}), flush=True)


def trotter():
    from scipy.linalg import expm
    from scipy.sparse import save_npz
    from cuprate_2d_tflo import initial_occupations
    from cuprate_2d_fermionic_dynamics import hopping_operations
    folder, plan, cfg = setup('trotter')
    basis, index, nup, ndown = sector_basis(cfg)
    if len(basis) != 15876 or nup != 4 or ndown != 4:
        raise ValueError('Wrong fixed sector')
    bits = ((np.asarray(basis, dtype=np.uint32)[:, None] >> np.arange(cfg.qubits)) & 1).astype(np.uint8)
    paulis = pauli_samples(bits)
    initial = initial_state_vector(cfg, index)
    checks, rows, vectors = [], [], {'basis': np.asarray(basis), 'initial_sector': initial}
    hardware = read(RUN / 'primary_analysis/results.json')
    def check(name, value, tolerance):
        checks.append({'name': name, 'value': float(value), 'tolerance': tolerance, 'passed': bool(value <= tolerance)})
        if value > tolerance or not np.isfinite(value):
            save(folder / 'FAILED_CHECKS.json', checks)
            raise ValueError('Trotter check failed: ' + name)
    for u in (0., 8.):
        selected = replace(cfg, u_over_t=u)
        started = time.perf_counter()
        h = independent_hamiltonian(selected, basis)
        h2, meta = build_hamiltonian(selected, MODEL_FULL)
        difference = h-h2
        check(f'independent_H_U{u}', np.max(np.abs(difference.data)) if difference.nnz else 0., 1e-12)
        difference = h-h.conj().T
        check(f'H_hermitian_U{u}', np.max(np.abs(difference.data)) if difference.nnz else 0., 1e-12)
        build_seconds = time.perf_counter()-started
        save_npz(folder / f'hamiltonian_U{u:g}.npz', h)
        for total_time in (.2, .4):
            start = time.perf_counter()
            exact = expm_multiply(-1j*total_time*h, initial)
            solve_seconds = time.perf_counter()-start
            check(f'exact_norm_{u}_{total_time}', abs(np.vdot(exact, exact).real-1), 1e-11)
            half = expm_multiply(-.5j*total_time*h, initial)
            check(f'exact_time_composition_{u}_{total_time}', np.linalg.norm(exact-expm_multiply(-.5j*total_time*h, half)), 1e-11)
            exact_pauli = np.abs(exact)**2 @ paulis
            exact_phys = physical_observables(exact_pauli)
            vectors[f'H_U{u:g}_T{total_time}'] = exact
            row = {'U': u, 'time': total_time, 'H_build_two_implementations_seconds': build_seconds,
                'exact_H_evolve_seconds': solve_seconds, 'exact_H_paulis': exact_pauli.tolist(),
                'basis_dimension': meta['basis_dimension'], 'refinements': []}
            if u == 0:
                single = np.zeros((cfg.qubits, cfg.qubits))
                for p, q, coefficient in hopping_operations(selected):
                    single[p, q] = single[q, p] = coefficient
                np.fill_diagonal(single, -cfg.chemical_potential)
                evolution = expm(-1j*total_time*single)
                covariance = evolution @ np.diag(initial_occupations(cfg)) @ evolution.conj().T
                z = 1-2*covariance.diagonal().real
                gaussian = np.r_[z, [z[2*s]*z[2*s+1]-4*abs(covariance[2*s, 2*s+1])**2 for s in range(cfg.sites)]]
                check(f'continuous_H_FLO_limit_{total_time}', np.max(np.abs(gaussian-exact_pauli)), 1e-11)
            for steps in (2, 4, 8):
                refined = replace(selected, steps=steps, dt=total_time/steps)
                if u == 0:
                    estimated, _ = flo_reference(refined, total_time)
                    state_error = None
                else:
                    circuit = bind(parameterized_network(refined), refined, total_time, u)
                    state = local_state(circuit)
                    check(f'full_norm_{total_time}_{steps}', abs(np.vdot(state, state).real-1), 1e-10)
                    sector = state[np.asarray(basis)]
                    check(f'sector_{total_time}_{steps}', abs(np.vdot(sector, sector).real-1), 1e-10)
                    estimated = np.abs(sector)**2 @ paulis
                    state_error = phase_distance(sector, exact)
                    vectors[f'circuit_U8_T{total_time}_steps{steps}'] = sector
                    qpy_checked(folder / f'logical_U8_T{total_time}_steps{steps}.qpy', circuit)
                if steps == 2:
                    matching = next(s for s in plan['settings'] if s['time'] == total_time and s['u_over_t'] == u)
                    check(f'original_finite_reference_{u}_{total_time}', np.max(np.abs(estimated-matching['reference'])), 1e-10)
                errors = physical_observables(estimated)-exact_phys
                row['refinements'].append({'steps': steps, 'dt': total_time/steps,
                    'state_distance_to_exact_H': state_error,
                    'rmse_charge_spin_double': np.sqrt(np.mean(errors**2, axis=0)).tolist(),
                    'max_abs_charge_spin_double': np.max(np.abs(errors), axis=0).tolist(),
                    'pauli_MSE': float(np.mean((estimated-exact_pauli)**2)), 'paulis': estimated.tolist()})
            if u == 8:
                state_errors = [r['state_distance_to_exact_H'] for r in row['refinements']]
                row['state_error_refinement_ratios'] = [state_errors[i]/state_errors[i+1] for i in range(2)]
                check(f'decreasing_state_error_{total_time}', int(not state_errors[0] > state_errors[1] > state_errors[2]), 0)
                point = next(r for r in hardware['targets'] if r['time'] == total_time)
                row['hardware_TFLO_rmse_to_exact_H'] = np.sqrt(np.mean((np.asarray(point['methods']['tflo']['observables'])-exact_phys)**2, axis=0)).tolist()
            rows.append(row)
            print(json.dumps({'stage': 'trotter', 'U': u, 'time': total_time,
                'rmse_by_steps': [r['rmse_charge_spin_double'] for r in row['refinements']]}), flush=True)
    np.savez_compressed(folder / 'reference_sector_states.npz', **vectors)
    result = {'stage': 'EXACT_H_TROTTER_AUDIT', 'new_QPU_seconds': 0, 'checks': checks,
        'checks_passed': len(checks), 'rows': rows,
        'timing_boundary': 'Local single runs including separately reported Hamiltonian construction; not a scaling or matched-accuracy speed claim.'}
    save(folder / 'results.json', result)
    seal(folder)


def summarize():
    for name in ('transfer', 'circuits', 'trotter'):
        verify_tree(ROOT / name)
    folder, _, _ = setup('summary')
    transfer, routing, physics = [read(ROOT / name / 'results.json') for name in ('transfer', 'circuits', 'trotter')]
    inputs = read(folder / 'inputs.json')
    for name in ('transfer', 'circuits', 'trotter'):
        previous = read(ROOT / name / 'inputs.json')
        for key in ('protocol_sha256', 'plan_sha256', 'raw_sha256', 'old_lock_sha256', 'compact_lock_sha256', 'source_sha256'):
            if previous[key] != inputs[key]:
                raise ValueError('Stage inputs changed')
    # Independently recompute intervals and verify the saved finite references.
    checks = []
    def check(name, condition):
        checks.append({'name': name, 'passed': bool(condition)})
        if not condition:
            raise ValueError('Audit check failed: ' + name)
    plan = read(PLAN / 'manifest.json')
    target = [i for i, s in enumerate(plan['settings']) if s['u_over_t'] == 8]
    partner = [next(i for i, s in enumerate(plan['settings']) if s['u_over_t'] == 0 and s['time'] == plan['settings'][j]['time']) for j in target]
    exact = np.asarray([s['reference'] for s in plan['settings']])
    with np.load(ROOT / 'transfer/bootstrap_predictions.npz') as archive:
        for row in transfer['models']:
            samples = archive[row['method']]
            check('bootstrap_shape_' + row['method'], samples.shape == (400, 10, 27))
            valid = samples[np.isfinite(samples).all(axis=(1, 2))]
            gain = transfer['classical_FLO_only_MSE']-np.mean((valid[:, target]-exact[target])**2, axis=(1, 2))
            ci = row['classical_minus_method_MSE_gain_ci95']
            check('bootstrap_CI_' + row['method'], np.allclose(np.percentile(gain, [2.5, 97.5]), [ci['low'], ci['high']], atol=1e-12, rtol=0))
            if row['method'] == 'time_only':
                check('classical_control_zero_contrast', np.max(np.abs(valid[:, target]-valid[:, partner])) < 1e-12)
    for row in routing['candidates']:
        check('candidate_state_equivalence_' + row['name'], all(r['max_phase_aligned_state_distance'] < 1e-9 for r in row['state_checks']))
    check('trotter_numerics', all(r['passed'] for r in physics['checks']))
    tests = subprocess.run([sys.executable, '-B', '-m', 'unittest', '-v',
        'test_cuprate_2d_local_followup', 'test_cuprate_2d_tflo_refinement',
        'test_cuprate_2d_tflo_compact_pilot'], cwd=BASE, capture_output=True, text=True, timeout=180)
    check('regression_tests', tests.returncode == 0)
    with (folder / 'unit_tests.txt').open('x', encoding='utf-8') as handle:
        handle.write(tests.stdout + tests.stderr)
    save(folder / 'verification.json', {'checks': checks, 'checks_passed': len(checks), 'new_QPU_seconds': 0})
    lines = ['# Lokale TFLO-overdrachtaudit, circuitroutes en Trotterfout', '',
        '**0 nieuwe QPU-seconden. Alle oorspronkelijke resultaten en indieningslocks zijn behouden.**', '',
        '## 1. TFLO-overdracht op bestaande data', '',
        'Alle modellen zijn uitsluitend met zes U=0-punten getraind. De twee U=0-validatiepunten en alle U=8-punten bleven buiten de fit. '
        'De audit is post-hoc/verkennend: geen methode wordt tot nieuwe primaire uitkomst gepromoveerd.', '',
        '| Model | U=0 validatie-MSE | U=8 MSE | Interactiecontrast-MSE | Projectie op exact interactiecontrast |',
        '|---|---:|---:|---:|---:|']
    for row in transfer['models']:
        lines.append(f"| {row['method']} | {row['U0_holdout_MSE']:.6f} | {row['U8_target_MSE']:.6f} | {row['contrast_MSE']:.6f} | {row['contrast_projection_fraction']:.4f} |")
    lines += ['', f"Exacte klassieke U=0-FLO-voorspelling op U=8-doelen: MSE {transfer['classical_FLO_only_MSE']:.6f}.",
        'De projectie is een beschrijvende schaalfactor van het voorspelde verschil U=8 minus U=0 langs het exacte verschil. '
        'Een factor 1 alleen bewijst geen juiste observabelen; orthogonale fouten tellen in de contrast-MSE mee. '
        'De U=0-contrastpartners zijn trainingspunten, niet nieuwe holdouts.', '']
    for row in transfer['models']:
        lines.append(f"- {row['method']}: 95%-interval winst boven klassieke FLO {row['classical_minus_method_MSE_gain_ci95']}; contrastprojectie {row['contrast_projection_ci95']}.")
    ablation = transfer['current_TFLO_ablation']
    lines += ['', f"Ablatie huidige TFLO: echte U=8-input MSE {ablation['actual_U8_MSE']:.6f}; vervangen door U=0-input {ablation['ablated_U8_MSE']:.6f}.",
        f"95%-interval voor de winst van de echte U=8-input: {ablation['ablated_minus_real_MSE_gain_ci95']}.",
        f"Bootstrap: 400 aangevraagd, {transfer['bootstrap_failures']} mislukte resamples. Intervallen sluiten transferbias en drift uit.", '',
        '## 2. Exact dezelfde ideale circuitwerking, andere routing', '',
        '| Route | CZ | Twee-qubitdiepte | Totale diepte | Circuitduur uit opgeslagen kalibratie |',
        '|---|---:|---:|---:|---:|']
    for row in routing['candidates']:
        lines.append(f"| {row['name']} | {row['CZ']} | {row['two_qubit_depth']} | {row['depth']} | {row['cached_measured_circuit_seconds']*1e6:.3f} us |")
    lines += ['', f"Minimum-CZ-kandidaat: {routing['minimum_CZ_candidate']}; CZ-reductie {routing['CZ_reduction_fraction']*100:.2f}%.",
        'De volgorde van niet-commuterende Hamiltoniantermen is behouden. Fermiontekens en modevolgorde zijn gecontroleerd. '
        'Zeven basistests bevatten volledige 2x2-operatorvergelijkingen; alle kandidaten zijn daarnaast op drie volledige 18-qubitdoeltoestanden getest.',
        'Acht getwirlde fysieke templates van de minimum-CZ-kandidaat zijn opnieuw gevalideerd, met hun eigen readoutmaskers. '
        'De 80 parameterbindings en QPY-herlaadtests zijn gecontroleerd. Dit is geen nieuwe hardwaremeting of submissietoestemming.',
        f"Kalibratiebron: {routing['calibration_captured_utc']}; alle 5120 shots met reset/rep_delay samen lokaal geraamd op {routing['cached_total_5120_shot_execution_seconds']:.6f} s, exclusief provideroverhead.",
        'Minder CZ kan samengaan met grotere diepte. Een lokale gatebesparing bewijst geen hardwarefidelitywinst.', '',
        '## 3. Exacte continue Hubbard-dynamica versus eindige Trotterstappen', '',
        '| U/t | Tijd | Stappen | Lading RMSE | Spin RMSE | Doublon RMSE |',
        '|---|---:|---:|---:|---:|---:|']
    for row in physics['rows']:
        for refinement in row['refinements']:
            e = refinement['rmse_charge_spin_double']
            lines.append(f"| {row['U']:g} | {row['time']} | {refinement['steps']} | {e[0]:.6f} | {e[1]:.6f} | {e[2]:.6f} |")
    for row in physics['rows']:
        if row['U'] == 8:
            lines += ['', f"U=8,T={row['time']}: toestandsfout-ratio's 2/4 en 4/8 stappen: {row['state_error_refinement_ratios']}.",
                f"De bestaande hardware-TFLO-observabelen rechtstreeks tegenover exacte H-dynamica: RMSE lading/spin/doublon {row['hardware_TFLO_rmse_to_exact_H']}."]
    lines += ['', 'Trotterbias en meet-/mitigatiefout zijn aparte foutbronnen. De directe vergelijking met exacte H hierboven telt ze niet ten onrechte als onafhankelijke statistische fouten op.',
        f"{physics['checks_passed']} numerieke Hamiltonian-, norm-, sector-, FLO- en referentiecontroles geslaagd.", '',
        '## Grenzen en vervolg', '',
        'Geen nieuwe fit op U=8, geen gunstige sites geselecteerd, geen extra PEC/ZNE, geen negatieve waarden geclipt. '
        'Een eventueel kansrijk alternatief moet op nieuwe, vooraf vastgelegde meetdata worden bevestigd. '
        'Deze audit is geen quantum-advantagebewijs en wijzigt geen eerder resultaat.',
        '[2D-paper: TFLO-overdracht, controles en circuitkosten](https://arxiv.org/html/2510.26845v2).', '',
        f"Eindcontrole: {len(checks)} aanvullende controles; alle regressietests geslaagd (zie unit_tests.txt)."]
    with (folder / 'AUDIT_REPORT.md').open('x', encoding='utf-8') as handle:
        handle.write('\n'.join(lines) + '\n')
    seal(folder)
    print(json.dumps({'stage': 'LOCAL_AUDIT_COMPLETE', 'new_QPU_seconds': 0,
        'report': str(folder / 'AUDIT_REPORT.md'), 'checks': len(checks)}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['audit', 'circuits', 'trotter', 'summarize'])
    args = parser.parse_args()
    with threadpool_limits(limits=1):
        globals()[args.stage]()
