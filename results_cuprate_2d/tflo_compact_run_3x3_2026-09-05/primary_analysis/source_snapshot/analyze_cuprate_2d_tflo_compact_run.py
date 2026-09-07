"""Execute the pre-submission frozen compact TFLO protocol on one saved job.

No provider calls; no filter selection, retuning, clipping or old-model reuse.
Implementation is snapshotted before loading samples, after hardware execution.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

from cuprate_2d_tflo import (analyze, apply_tflo, fit_tflo, pauli_samples,
    physical_observables, sector_mask)
from cuprate_2d_tflo_refinement import resample_paired
from analyze_cuprate_2d_tflo import load_archive
from prepare_cuprate_2d_tflo_compact_pilot import digest, read, save

BASE = Path(__file__).resolve().parent
PLAN = BASE / 'results_cuprate_2d/tflo_compact_pilot_3x3_2026-09-05'
RUN = BASE / 'results_cuprate_2d/tflo_compact_run_3x3_2026-09-05'
OUT = RUN / 'primary_analysis'
PROTOCOL_HASH = 'cfe212f3935c7c5952b56bd1217aea900ddffab29706c2630be6b8785f69ec5b'
PLAN_HASH = '823015bd20de02232c582388294bbf8146de9781292843a17fab1b5c170aab6d'
METHODS = ('raw', 'postselected', 'tflo')


class RetentionFailure(ValueError):
    pass


def evaluate_once(settings, raw, nup=4, ndown=4):
    """Only training U=0 references can enter the fit; no other reference read."""
    ids = [s['id'] for s in settings]
    if len(ids) != 10 or len(set(ids)) != 10 or set(raw) != set(ids):
        raise ValueError('Expected the ten frozen settings')
    train = [i for i, s in enumerate(settings) if s['role'] == 'train']
    if len(train) != 6 or any(settings[i]['u_over_t'] != 0 for i in train):
        raise ValueError('Fit must use exactly six U=0 training settings')
    means, filtered, counts = [], [], []
    for setting in settings:
        blocks = raw[setting['id']]
        bits = np.concatenate([blocks[t] for t in sorted(blocks)])
        means.append(pauli_samples(bits).mean(axis=0))
        keep = sector_mask(bits, nup, ndown, 1)
        counts.append(int(keep.sum()))
        if counts[-1] < 32:
            raise RetentionFailure('Below the frozen 32-shot minimum')
        filtered.append(pauli_samples(bits[keep]).mean(axis=0))
    filtered = np.asarray(filtered)
    model = fit_tflo(filtered[train], [settings[i]['reference'] for i in train],
        [settings[i]['time'] for i in train], ridge=0.001)
    corrected = np.array([apply_tflo(model, value, setting['time'])
        for value, setting in zip(filtered, settings)])
    values = np.asarray([means, filtered, corrected])
    if not np.isfinite(values).all():
        raise ValueError('Nonfinite estimate')
    return values, counts, model


def ci(values):
    if len(values) == 0:
        return None
    return {'low': np.quantile(values, .025, axis=0).tolist(),
            'high': np.quantile(values, .975, axis=0).tolist()}


def inference_gate(gains, valid, requested):
    reliable = valid / requested >= 0.95
    return {'sampling_reliable': reliable,
        'TFLO_better_than_raw': reliable and gains['raw_minus_tflo'] is not None and gains['raw_minus_tflo']['low'] > 0,
        'TFLO_better_than_classical_FLO_only': reliable and gains['classical_minus_tflo'] is not None and gains['classical_minus_tflo']['low'] > 0}


def run():
    if OUT.exists():
        raise FileExistsError('Never overwrite this primary analysis')
    if digest(PLAN / 'analysis_protocol.json') != PROTOCOL_HASH or digest(PLAN / 'manifest.json') != PLAN_HASH:
        raise ValueError('Pre-submission protocol or physics plan changed')
    protocol = read(PLAN / 'analysis_protocol.json')
    if (protocol['sector_tolerance'], protocol['ridge'], protocol['bootstrap_replicates'],
            protocol['bootstrap_seed'], protocol['minimum_retained_per_setting']) != (1, .001, 400, 2026090517, 32):
        raise ValueError('Unsupported frozen analysis protocol')
    receipt = read(RUN / 'job_receipt.json')
    verified = read(RUN / 'provider_input_verification.json')
    if not verified['all_circuits_match'] or verified['total_shots'] != 5120 or verified['job_id'] != receipt['job_id']:
        raise ValueError('Hardware archive is not verified')
    tests = subprocess.run([sys.executable, '-m', 'unittest', '-v',
        'test_analyze_cuprate_2d_tflo_compact_run'], cwd=BASE, capture_output=True, text=True, timeout=120)
    if tests.returncode != 0:
        raise ValueError('Analysis unit tests failed')
    OUT.mkdir()
    source = OUT / 'source_snapshot'
    source.mkdir()
    names = ('analyze_cuprate_2d_tflo_compact_run.py', 'test_analyze_cuprate_2d_tflo_compact_run.py',
        'cuprate_2d_tflo.py', 'cuprate_2d_tflo_refinement.py', 'analyze_cuprate_2d_tflo.py')
    for name in names:
        shutil.copyfile(BASE / name, source / name)
    save(OUT / 'implementation_frozen.json', {'created_unix': time.time(),
        'source_sha256': {name: digest(BASE / name) for name in names},
        'pre_submission_protocol_sha256': PROTOCOL_HASH,
        'disclosure': 'Implementation written after hardware execution to execute the previously frozen protocol; no new sample-dependent choices.',
        'new_samples_loaded_by_this_analysis': False})
    with (OUT / 'unit_tests.txt').open('x', encoding='utf-8') as handle:
        handle.write(tests.stdout + tests.stderr)
    plan, raw, decoded, nup, ndown = load_archive(PLAN, RUN / 'raw_bitstrings.json')
    if raw['job_id'] != receipt['job_id']:
        raise ValueError('Wrong hardware job in sample archive')
    settings = plan['settings']
    decoded = {s['id']: decoded[s['id']] for s in settings}
    counts = {s['id']: int(sum(sector_mask(bits, nup, ndown, 1).sum()
        for bits in decoded[s['id']].values())) for s in settings}
    save(OUT / 'retention.json', {'filter_tolerance': 1, 'counts': counts, 'minimum_required': 32})
    try:
        central, _, model = evaluate_once(settings, decoded, nup, ndown)
    except RetentionFailure:
        save(OUT / 'primary_analysis_stopped.json', {'reason': 'frozen minimum retained shots not reached',
            'job_id': raw['job_id'], 'retained_counts': counts, 'filter_changed': False,
            'no_resubmission': True, 'raw_data_preserved': True})
        with (OUT / 'RESULT_REPORT.md').open('x', encoding='utf-8') as handle:
            handle.write('# Compacte pilot: primaire analyse gestopt\n\n'
                'De hardwarejob is voltooid en alle gegevens zijn bewaard, maar minstens een instelling '
                'houdt minder dan de vooraf vereiste 32 shots over. Geen filterwijziging, fit of nieuwe job.\n')
        seal()
        print(json.dumps({'status': 'PRIMARY_STOPPED_FROZEN_RETENTION_GATE', 'counts': counts}), flush=True)
        return
    save(OUT / 'U0_fit_frozen.json', {'model': model, 'protocol_sha256': PROTOCOL_HASH,
        'training_ids': [s['id'] for s in settings if s['role'] == 'train'],
        'U8_in_fit': False, 'filter_reselected': False})
    target = [i for i, s in enumerate(settings) if s['role'] == 'interacting_holdout']
    validation = [i for i, s in enumerate(settings) if s['role'] == 'flo_holdout']
    refs = np.array([s['reference'] for s in settings])
    classical_map = {r['setting_id']: r['pauli_prediction'] for r in read(PLAN / 'classical_control_predictions.json')}
    classical = np.array([classical_map[settings[i]['id']] for i in target])
    B = protocol['bootstrap_replicates']
    rng = np.random.default_rng(protocol['bootstrap_seed'])
    samples = np.full((B,) + central.shape, np.nan)
    failures = 0
    for b in range(B):
        sampled = resample_paired(decoded, rng)
        try:
            samples[b] = evaluate_once(settings, sampled, nup, ndown)[0]
        except RetentionFailure:
            failures += 1
        if (b + 1) % 100 == 0:
            print(json.dumps({'event': 'fixed_protocol_bootstrap', 'completed': b + 1, 'total': B}), flush=True)
    np.savez_compressed(OUT / 'bootstrap_pauli_predictions.npz', samples=samples)
    valid_mask = np.isfinite(samples).all(axis=(1, 2, 3))
    valid_samples = samples[valid_mask]
    mse = np.mean((central[:, target, :] - refs[target])**2, axis=(1, 2))
    classical_mse = float(np.mean((classical - refs[target])**2))
    mse_draws = np.mean((valid_samples[:, :, target, :] - refs[target])**2, axis=(2, 3))
    gains = {'raw_minus_tflo': ci(mse_draws[:, 0] - mse_draws[:, 2]),
             'classical_minus_tflo': ci(classical_mse - mse_draws[:, 2])}
    inference = inference_gate(gains, len(valid_samples), B)
    rows = []
    for i in target:
        row = {'id': settings[i]['id'], 'time': settings[i]['time'], 'retained_shots': counts[settings[i]['id']], 'methods': {}}
        for j, method in enumerate(METHODS):
            values = physical_observables(central[j, i])
            row['methods'][method] = {'observables': values.tolist(),
                'rmse_charge_spin_double': np.sqrt(np.mean((values - physical_observables(refs[i]))**2, axis=0)).tolist(),
                'ci95': ci(physical_observables(valid_samples[:, j, i])),
                'out_of_bounds_count': int(np.sum((values < [0., -1., 0.]) | (values > [2., 1., 1.])))}
        rows.append(row)
    # Independent existing evaluator: central fit, retention and physical RMSE
    # must match, irrespective of bootstrap RNG iteration order.
    legacy_check = analyze(settings, decoded, nup, ndown, tolerance=1, bootstrap=2, seed=2026090517)
    maximum_delta = 0.
    for i, row in enumerate(legacy_check['settings']):
        if row['retained_shots'] != counts[settings[i]['id']]:
            raise ValueError('Independent retention mismatch')
        for j, method in enumerate(METHODS):
            maximum_delta = max(maximum_delta, float(np.max(np.abs(
                np.asarray(row[method]['observables']) - physical_observables(central[j, i])))))
    if maximum_delta > 1e-12:
        raise ValueError('Independent central observable mismatch')
    result = {'status': 'COMPACT_PRIMARY_FIXED_PROTOCOL_COMPLETE', 'job_id': raw['job_id'],
        'plan_sha256': PLAN_HASH, 'protocol_sha256': PROTOCOL_HASH,
        'raw_sha256': digest(RUN / 'raw_bitstrings.json'), 'usage': verified['usage'],
        'new_analysis_QPU_seconds': 0, 'sector_tolerance': 1, 'retained_counts': counts,
        'global_U8_pauli_MSE': {**dict(zip(METHODS, mse.tolist())), 'classical_FLO_only': classical_mse},
        'paired_gain_ci95': gains, 'inference': inference,
        'U0_holdout_MSE': dict(zip(METHODS, np.mean((central[:, validation, :] - refs[validation])**2, axis=(1, 2)).tolist())),
        'bootstrap_replicates': B, 'valid_bootstrap_replicates': len(valid_samples),
        'bootstrap_retention_failures': failures, 'targets': rows,
        'independent_evaluator_max_observable_difference': maximum_delta,
        'claim_boundary': 'Small classically simulable hardware validation; no quantum advantage. Historical run comparisons are descriptive, not causal.',
        'uncertainty_exclusions': protocol['uncertainty_exclusions']}
    save(OUT / 'results.json', result)
    lines = ['# Compacte TFLO-pilot: hardware-uitkomst', '',
        f"Job `{raw['job_id']}` is DONE; werkelijk QPU-verbruik: {verified['usage']['qpu_charge_time_seconds']} seconden. De providerlimiet was 5 seconden.",
        'Alle 80 circuits en 5120 shots zijn ontvangen en geverifieerd. Geen herhaling.', '',
        'Filtertolerantie 1, minimum 32 en ridge 0.001 waren vooraf vastgelegd. De zes nieuwe U=0-punten trainen de fit; validatie en U=8 niet.', '',
        '| Tijd | Behouden / 512 | Methode | Lading RMSE | Spin RMSE | Doublon RMSE |',
        '|---|---:|---|---:|---:|---:|']
    for row in rows:
        for method, values in row['methods'].items():
            error = values['rmse_charge_spin_double']
            lines.append(f"| {row['time']} | {row['retained_shots']} | {method} | {error[0]:.4f} | {error[1]:.4f} | {error[2]:.4f} |")
    lines += ['', '## Verplichte klassieke controle', '',
        f'Gepoolde Pauli-MSE: raw {mse[0]:.6f}; TFLO {mse[2]:.6f}; klassieke U=0-FLO-voorspelling {classical_mse:.6f}.',
        f'95%-interval voor raw-minus-TFLO MSE: {gains["raw_minus_tflo"]}.',
        f'95%-interval voor klassiek-minus-TFLO MSE: {gains["classical_minus_tflo"]}.',
        f'Inferentie volgens de vooraf vastgelegde grens: {inference}.', '',
        f'{len(valid_samples)}/{B} bootstrapreplicaties bruikbaar; {failures} gestopt wegens te weinig behouden shots.',
        f'Onafhankelijke bestaande evaluator: maximaal verschil in centrale observabelen {maximum_delta:.3e}.',
        'Unit-tests en alle schattingen/replicaties zijn opgeslagen. Geen clipping, filterherselectie of oude fitcoefficienten.', '',
        'De code is na hardwareuitvoering geschreven om het vooraf bevroren protocol uit te voeren, en voor analyse vastgelegd. '
        'Intervallen dekken sampling/refitting, niet TFLO-transferbias, Trotterfout of hardwaredrift tussen jobs. '
        'Referenties horen bij hetzelfde eindige Trottercircuit. Geen quantum-advantageclaim.']
    with (OUT / 'RESULT_REPORT.md').open('x', encoding='utf-8') as handle:
        handle.write('\n'.join(lines) + '\n')
    seal()
    print(json.dumps({k: result[k] for k in ('status', 'job_id', 'usage', 'global_U8_pauli_MSE',
        'paired_gain_ci95', 'inference', 'valid_bootstrap_replicates', 'bootstrap_retention_failures')}), flush=True)


def seal():
    save(OUT / 'sha256.json', {str(p.relative_to(OUT)): digest(p)
        for p in sorted(OUT.rglob('*')) if p.is_file()})


if __name__ == '__main__':
    run()
