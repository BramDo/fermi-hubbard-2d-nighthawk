"""Read-only numerical/archive checks plus a separate durable audit bundle."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys

import numpy as np

import analyze_cuprate_2d_tflo_compact_run as analysis
from prepare_cuprate_2d_tflo_compact_pilot import read, save, digest, verify_tree

BASE, RUN, PLAN = analysis.BASE, analysis.RUN, analysis.PLAN
OUT = RUN / 'final_audit'


def check_hashes(root, manifest):
    root = root.resolve()
    values = read(root / manifest)
    for name, expected in values.items():
        path = (root / name).resolve()
        if not path.is_relative_to(root) or digest(path) != expected:
            raise ValueError('Changed or unsafe archived artifact')
    return len(values)


def run():
    if OUT.exists():
        raise FileExistsError('Do not overwrite final audit')
    checked_hashes = check_hashes(RUN, 'completed_archive_sha256.json') + verify_tree(analysis.OUT) + verify_tree(PLAN)
    result = read(analysis.OUT / 'results.json')
    receipt = read(RUN / 'job_receipt.json')
    provider = read(RUN / 'provider_input_verification.json')
    checks = []
    def check(name, condition):
        checks.append({'name': name, 'passed': bool(condition)})
        if not condition:
            raise ValueError('Audit failed: ' + name)
    check('job_identity', result['job_id'] == receipt['job_id'] == provider['job_id'] == 'dae5gat1ierc738lmg10')
    check('provider_cap', read(RUN / 'provider_budget_verification.json')['provider_cost_field'] == 5)
    check('actual_usage', provider['usage']['qpu_charge_time_seconds'] == 4 and provider['usage']['status'] == 'complete')
    check('shots_and_inputs', provider['total_shots'] == 5120 and provider['all_circuits_match'] and provider['all_result_metadata_match'])
    lock = read(PLAN / 'submission_attempt.json')
    check('single_attempt_identity', lock['tag'] == receipt['tag'] and lock['plan_sha256'] == analysis.PLAN_HASH)
    check('no_retry', receipt['automatic_retry'] is False and not (RUN / 'dispatch_uncertain.json').exists())
    plan, _, decoded, nup, ndown = analysis.load_archive(PLAN, RUN / 'raw_bitstrings.json')
    old_plan = BASE / 'results_cuprate_2d/tflo_pilot_3x3_2026-09-05_ready'
    check('legacy_lock_unchanged', digest(old_plan / 'submission_attempt.json') == plan['provenance']['old_submission_lock_sha256'])
    for root, mapping in ((BASE, read(RUN / 'approved_intent.json')['source_sha256']),
            (BASE, read(analysis.OUT / 'implementation_frozen.json')['source_sha256'])):
        for name, expected in mapping.items():
            check('source_' + name, digest(root / name) == expected)
    settings = plan['settings']
    decoded = {s['id']: decoded[s['id']] for s in settings}
    target = [i for i, s in enumerate(settings) if s['role'] == 'interacting_holdout']
    reference = np.asarray([settings[i]['reference'] for i in target])
    central, counts, model = analysis.evaluate_once(settings, decoded, nup, ndown)
    check('model_reproduced', model == read(analysis.OUT / 'U0_fit_frozen.json')['model'])
    check('retention_reproduced', counts == [result['retained_counts'][s['id']] for s in settings])
    independently_computed_mse = []
    for j, method in enumerate(analysis.METHODS):
        residuals = (central[j, target, :] - reference).ravel()
        value = float(np.dot(residuals, residuals) / residuals.size)
        independently_computed_mse.append(value)
        check('central_MSE_' + method, abs(value - result['global_U8_pauli_MSE'][method]) < 1e-12)
    with np.load(analysis.OUT / 'bootstrap_pauli_predictions.npz') as archive:
        samples = archive['samples']
    check('bootstrap_shape', samples.shape == (400, 3, 10, 27))
    check('bootstrap_finite', np.isfinite(samples).all())
    rng = np.random.default_rng(2026090517)
    for b in range(3):
        expected = analysis.evaluate_once(settings, analysis.resample_paired(decoded, rng), nup, ndown)[0]
        check('bootstrap_reproduce_' + str(b), np.allclose(expected, samples[b], rtol=0, atol=1e-12))
    raw_mse = ((samples[:, 0, target, :] - reference)**2).reshape(400, -1).mean(axis=1)
    tflo_mse = ((samples[:, 2, target, :] - reference)**2).reshape(400, -1).mean(axis=1)
    classical_mse = result['global_U8_pauli_MSE']['classical_FLO_only']
    for name, gain in (('raw_minus_tflo', raw_mse-tflo_mse), ('classical_minus_tflo', classical_mse-tflo_mse)):
        expected = np.percentile(gain, [2.5, 97.5])
        actual = result['paired_gain_ci95'][name]
        check('paired_CI_' + name, np.allclose(expected, [actual['low'], actual['high']], rtol=0, atol=1e-12))
    check('inference_no_classical_gain', result['inference']['TFLO_better_than_classical_FLO_only'] is False)
    check('inference_raw_gain', result['inference']['TFLO_better_than_raw'] is True)
    previous_root = BASE / 'results_cuprate_2d/tflo_followup_2026-09-05/reanalysis'
    checked_hashes += verify_tree(previous_root)
    previous = read(previous_root / 'results.json')
    check('same_historical_physics', plan['config'] == read(old_plan / 'manifest.json')['config'] and
          settings == read(old_plan / 'manifest.json')['settings'])
    comparison = {'old_job_id': previous['job_id'], 'new_job_id': result['job_id'],
        'old_raw_MSE': previous['global_U8_pauli_MSE']['raw'], 'new_raw_MSE': independently_computed_mse[0],
        'old_TFLO_MSE': previous['global_U8_pauli_MSE']['corrected'], 'new_TFLO_MSE': independently_computed_mse[2],
        'raw_MSE_fractional_reduction': 1-independently_computed_mse[0]/previous['global_U8_pauli_MSE']['raw'],
        'boundary': 'Descriptive different-job comparison, not causal: hardware drift and prior exploratory filter selection differ. Final TFLO accuracy did not improve.'}
    tests = subprocess.run([sys.executable, '-m', 'unittest', '-v',
        'test_run_cuprate_2d_tflo_compact_once',
        'test_run_cuprate_2d_tflo_once.OnceTests.test_http_retries_disabled_for_all_known_runtime_clients',
        'test_run_cuprate_2d_tflo_once.OnceTests.test_secret_bearing_output_rejected',
        'test_analyze_cuprate_2d_tflo_compact_run', 'test_cuprate_2d_tflo_compact_pilot',
        'test_cuprate_2d_tflo_refinement'], cwd=BASE, capture_output=True, text=True, timeout=120)
    check('regression_suite', tests.returncode == 0)
    OUT.mkdir()
    save(OUT / 'verification.json', {'passed': True, 'checks_passed': len(checks), 'checks': checks,
        'artifact_hashes_verified': checked_hashes, 'job_id': result['job_id'], 'extra_QPU_seconds': 0,
        'audit_source_sha256': digest(__file__)})
    save(OUT / 'historical_comparison.json', comparison)
    with (OUT / 'unit_tests.txt').open('x', encoding='utf-8') as handle:
        handle.write(tests.stdout + tests.stderr)
    shutil.copyfile(__file__, OUT / 'audit_cuprate_2d_tflo_compact_run.py')
    save(OUT / 'sha256.json', {p.name: digest(p) for p in OUT.iterdir() if p.is_file()})
    print(json.dumps({'checks_passed': len(checks), 'artifact_hashes_verified': checked_hashes,
        'unit_test_exit_code': tests.returncode, 'historical_comparison': comparison}), flush=True)


if __name__ == '__main__':
    run()
