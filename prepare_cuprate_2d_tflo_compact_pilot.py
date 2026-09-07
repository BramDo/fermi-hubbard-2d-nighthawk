"""Freeze a distinct compact TFLO pilot locally. No provider or submit path.

Reuses the validated unbound templates, never an old submission authorization.
The legacy runner is hash-locked to its already-used plan and must not be reused.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import qiskit
from qiskit import qpy
from qiskit.primitives.containers import SamplerPub

from cuprate_2d_tflo import skeleton
from cuprate_2d_tflo_refinement import cz_trace, measurement_map

BASE = Path(__file__).resolve().parent
RESULTS = BASE / 'results_cuprate_2d'
ORIGINAL = RESULTS / 'tflo_pilot_3x3_2026-09-05_ready'
OPTIMIZED = RESULTS / 'tflo_followup_2026-09-05/optimization_v2'
DESTINATION = RESULTS / 'tflo_compact_pilot_3x3_2026-09-05'
ORIGINAL_HASH = '453a3d3f237f1912577ef5528f950c96220f0916e231191a929df38d3cbe071e'
OPTIMIZED_HASH = '80389af9551b3e24d4222e3cbd78bedb2c5c9a8bd1e01d7419f974c17c4edc06'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save(path, value):
    with Path(path).open('x', encoding='utf-8') as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write('\n')


def verify_tree(root):
    root = Path(root).resolve()
    hashes = read(root / 'sha256.json')
    for name, expected in hashes.items():
        target = (root / name).resolve()
        if not target.is_relative_to(root) or digest(target) != expected:
            raise ValueError('Unsafe or changed frozen artifact')
    return len(hashes)


def validate_records(plan):
    settings = {s['id']: s for s in plan['settings']}
    if len(settings) != 10 or len(plan['records']) != 80:
        raise ValueError('Expected ten settings and eighty records')
    seen, totals = set(), Counter()
    for record in plan['records']:
        key = record['setting_id'], record['twirl_id']
        if key in seen or key[0] not in settings or key[1] not in range(8):
            raise ValueError('Unexpected or duplicate setting/twirl')
        seen.add(key)
        if record['shots'] != 64 or record['template_index'] != key[1]:
            raise ValueError('Shot budget or template index changed')
        setting = settings[key[0]]
        values = record['parameter_values']
        expected = {'step_time': setting['time'] / plan['config']['steps'],
                    'interaction_phase': setting['u_over_t'] * plan['config']['hopping_t']
                    * setting['time'] / plan['config']['steps']}
        if set(values) != set(expected) or any(
                not np.isfinite(values[k]) or abs(values[k] - v) > 1e-14
                for k, v in expected.items()):
            raise ValueError('Physics parameter binding changed')
        totals[key[0]] += record['shots']
    if set(totals.values()) != {512} or sum(totals.values()) != 5120:
        raise ValueError('Incomplete or changed shot allocation')


def classical_predictions(settings):
    """Read U=0 reference values only; U=8 reference poisoning cannot change it."""
    u0 = {s['time']: s['reference'] for s in settings if s['u_over_t'] == 0}
    return [{'setting_id': s['id'], 'time': s['time'],
             'pauli_prediction': copy.deepcopy(u0[s['time']]),
             'source': 'exact U=0 FLO at the same finite-Trotter time'}
            for s in settings if s['role'] == 'interacting_holdout']


def analysis_protocol():
    return {
        'kind': 'prospective compact-circuit validation; no new data yet',
        'training': 'six U=0 training settings, newly measured on compact circuits only',
        'validation': 'two U=0 holdouts, excluded from fit',
        'targets': 'U/t=8 at dimensionless times t_hop*T/hbar=0.2 and 0.4',
        'fit': 'per Pauli exact=m*noisy+c*T+b; ridge toward identity',
        'ridge': 0.001, 'sector_tolerance': 1, 'minimum_retained_per_setting': 32,
        'filter_rule': 'abs(N_up-4)+abs(N_down-4)<=1',
        'filter_selection': 'locked now from the previous exploratory U=0 choice; no new selection',
        'old_model_reused': False, 'U8_in_fit_or_filter_selection': False,
        'primary_metric': 'MSE pooled equally over 27 Z/onsite-ZZ observables and both U=8 times',
        'comparators': ['same-job raw', 'same-job filter-only', 'frozen classical U=0 FLO-only'],
        'bootstrap_replicates': 400, 'bootstrap_seed': 2026090517,
        'bootstrap': 'paired twirl IDs across settings, then shots within each block; refit U=0 only',
        'confidence_interval': '95% percentile paired-gain intervals',
        'minimum_valid_bootstrap_fraction_for_inference': 0.95,
        'inference_gate': 'TFLO advantage over both raw and FLO-only requires both gain CI lower bounds >0; otherwise inconclusive',
        'failure_rule': 'below 32 in any setting: no primary fit; keep all raw data, no filter relaxation or new job',
        'diagnostics': 'report per-time charge/spin/doublon errors, retention, U=0 validation and physical bounds',
        'clip_unphysical_estimates': False, 'spin_convention': 'n_up-n_down, not S_z',
        'reference': 'same two-step finite Trotter circuit, not exact continuous-H evolution',
        'uncertainty_exclusions': ['TFLO transfer bias', 'Trotter error', 'between-job hardware drift'],
        'historical_comparison': 'descriptive only; not a randomized A/B test or causal gate-cleanup proof',
        'disclosure': 'Prior raw and corrected U=8 data informed the follow-up; this is not a wholly blind discovery',
        'claim_boundary': 'small classically simulable pilot; no quantum advantage certification',
    }


def prepare(destination=DESTINATION):
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError('Never overwrite a frozen compact pilot')
    verified_files = verify_tree(ORIGINAL) + verify_tree(OPTIMIZED)
    if digest(ORIGINAL / 'manifest.json') != ORIGINAL_HASH:
        raise ValueError('Original validated physics plan changed')
    if digest(OPTIMIZED / 'optimized_unbound_templates.qpy') != OPTIMIZED_HASH:
        raise ValueError('Validated optimized templates changed')
    lock_hash = digest(ORIGINAL / 'submission_attempt.json')
    old = read(ORIGINAL / 'manifest.json')
    validate_records(old)
    previous_checks = read(OPTIMIZED / 'checks.json')
    if len(previous_checks) != 138 or not all(c['passed'] for c in previous_checks):
        raise ValueError('Prior ideal-equivalence validation incomplete')
    with (ORIGINAL / 'twirled_sampler_templates.qpy').open('rb') as handle:
        originals = qpy.load(handle)
    with (OPTIMIZED / 'optimized_unbound_templates.qpy').open('rb') as handle:
        templates = qpy.load(handle)
    if len(originals) != len(templates) or len(templates) != 8:
        raise ValueError('Expected eight matched templates')
    checks = []

    def check(name, passed):
        checks.append({'name': name, 'passed': bool(passed)})
        if not passed:
            raise ValueError('Local verification failed: ' + name)

    for index, (before, after) in enumerate(zip(originals, templates)):
        check(f'CZ_partial_order_{index}', cz_trace(before) == cz_trace(after))
        check(f'measurement_map_{index}', measurement_map(before) == measurement_map(after))
        check(f'unbound_parameters_{index}', before.parameters == after.parameters and len(after.parameters) == 2)
        check(f'native_counts_{index}', after.count_ops()['cz'] == 1008 and after.count_ops()['measure'] == 18)
        check(f'unbound_cleanup_{index}', after.metadata['cleanup_before_binding'] is True)
    for index, record in enumerate(old['records']):
        template = templates[record['template_index']]
        check(f'seed_and_readout_{index}', template.metadata['twirl_seed'] == record['seed'] and
              template.metadata['readout_mask_little_endian'] == record['readout_mask_little_endian'])
        bound = template.assign_parameters({p: record['parameter_values'][p.name] for p in template.parameters})
        check(f'structure_{index}', skeleton(bound) == skeleton(template) and bound.num_parameters == 0)
        check(f'finite_angles_{index}', all(np.isfinite(float(p)) for item in bound.data for p in item.operation.params))
        stream = io.BytesIO()
        qpy.dump(bound, stream)
        stream.seek(0)
        check(f'bound_QPY_roundtrip_{index}', qpy.load(stream)[0] == bound)
        pub = SamplerPub.coerce((bound, None, record['shots']))
        check(f'scalar_PUB_{index}', pub.shape == () and pub.shots == 64)

    plan = copy.deepcopy(old)
    plan.update(status='COMPACT_PREPARED_NOT_AUTHORIZED_NOT_SUBMITTED',
                revision='compact-one-qubit-v1', live_backend_verified=False,
                backend_calibration_source='inherited layout; fresh separate preflight required',
                native_operations=[dict(t.count_ops()) for t in templates],
                native_depth=[t.depth() for t in templates],
                native_structure_sha256=[skeleton(t) for t in templates],
                created_utc=datetime.now(timezone.utc).isoformat())
    plan.pop('elapsed_local_seconds', None)
    plan['budget'].update(new_submission_authorized=False, max_new_jobs=1,
        proposed_max_execution_time_seconds=5, provider_runtime_estimate_seconds=None,
        warning='Proposed only: separate explicit authorization and fresh live budget check required; no automatic retry.')
    plan['analysis_policy'].update(sector_tolerance=1,
        prospective_protocol='analysis_protocol.json', new_filter_selection=False,
        classical_control_required=True)
    plan['provenance'] = {'original_plan_sha256': ORIGINAL_HASH,
        'optimized_QPY_sha256': OPTIMIZED_HASH, 'old_submission_lock_sha256': lock_hash,
        'original_job_id': 'dae3rou42tqs73au78d0', 'old_authorization_reusable': False,
        'preparer_sha256': digest(__file__), 'qiskit': qiskit.__version__}
    for key in ('config', 'settings', 'records', 'sampling', 'initial_layout'):
        check('unchanged_' + key, plan[key] == old[key])
    check('old_submission_lock_preserved', digest(ORIGINAL / 'submission_attempt.json') == lock_hash)
    check('original_plan_preserved', digest(ORIGINAL / 'manifest.json') == ORIGINAL_HASH)

    destination.mkdir(parents=True, exist_ok=False)
    save(destination / 'analysis_protocol.json', analysis_protocol())
    save(destination / 'manifest.json', plan)
    save(destination / 'classical_control_predictions.json', classical_predictions(plan['settings']))
    shutil.copyfile(OPTIMIZED / 'optimized_unbound_templates.qpy', destination / 'twirled_sampler_templates.qpy')
    check('copied_QPY_hash', digest(destination / 'twirled_sampler_templates.qpy') == OPTIMIZED_HASH)
    save(destination / 'verification.json', {'passed': True, 'checks_passed': len(checks),
        'checks': checks, 'source_artifact_hashes_verified': verified_files,
        'prior_ideal_equivalence_checks_verified': 138,
        'prior_max_state_distance': read(OPTIMIZED / 'summary.json')['max_state_distance'],
        'new_ideal_statevector_simulation_performed': False, 'new_QPU_seconds': 0})
    save(destination / 'authorization_checkpoint.json', {
        'checkpoint_id': 'compact-tflo-single-job-max5s', 'checkpoint_type': 'decision',
        'checkpoint_reason': 'explicit', 'awaiting': 'new user authorization for exactly one compact pilot on ibm_phoenix, max 5 QPU seconds',
        'verification_prework_done': ['frozen 80 scalar inputs', '80 bound QPY roundtrips', 'unchanged physics and old lock'],
        'resume_contract': ['explicit new authorization', 'successful fresh preflight', 'independent exactly-once lock', 'live ISA and cap recheck'],
        'success_path': 'after approval, prepare guarded one-shot dispatch; no batch, session, backend switch or automatic retry',
        'issue_path': 'preserve everything and report; no spend or implicit cap increase',
        'execution_segment': {'completed_tasks': ['compact input preparation', 'prospective analysis freeze'],
            'current_task': 'fresh preflight then approval', 'cursor': 'before hardware dispatch',
            'resume_preconditions': ['new authorization', 'preflight passed'], 'downstream_locked': True},
        'new_submission_authorized': False, 'execution_attempted': False, 'quantum_seconds_used': 0,
        'legacy_runner_warning': 'run_cuprate_2d_tflo_once.py is intentionally locked to the already-used old plan; do not change its constants or remove its lock',
    })
    with (destination / 'PREPARATION_REPORT.md').open('x', encoding='utf-8') as handle:
        handle.write('# Compacte TFLO-hardwarepilot: voorbereid, niet ingediend\n\n'
            '0 nieuwe QPU-seconden. Een nieuwe expliciete toestemming blijft vereist.\n\n'
            'Zelfde 3x3-model met volledige fermiontekens, t, t-prime/t=-0.25, U/t=8, '
            '18 logische qubits, twee Trotterstappen en dezelfde fysieke mapping op ibm_phoenix. '
            '10 instellingen x 8 twirls x 64 shots = 5120 shots; 512 per instelling, inclusief U=0-kalibratie.\n\n'
            'Alleen de al gevalideerde een-qubit-opschoning verandert de circuits: 42.4% minder X/SX, '
            'diepte 623-637, nog 1008 CZ per circuit. Geen hardwareverbetering gemeten.\n\n'
            'Analyse nu vooraf vastgelegd: filtertolerantie 1, minimum 32, vaste ridge 0.001. '
            'De keuze komt uit de eerdere verkenning; de oude strikte primaire analyse blijft mislukt bewaard. '
            'Fit opnieuw uitsluitend op zes nieuwe U=0-trainingspunten, twee U=0-validatiepunten buiten de fit. '
            'Geen hergebruik van oude fitcoefficienten en geen nieuwe filterkeuze op U=8.\n\n'
            'Verplicht vergelijken met raw, filter-only en een vooraf opgeslagen geheel klassieke U=0-FLO-voorspelling. '
            'Rapporteer paired-gain-intervallen met 400 twirl/shot-bootstrapreplicaties en U=0-refits. '
            'Geen claim van extra winst wanneer het interval nul bevat. Bij onvoldoende samples stopt de primaire fit; '
            'geen automatische filteraanpassing of herhaling.\n\n'
            f'{len(checks)} nieuwe lokale controles geslaagd, waaronder alle 80 bound-QPY-herlaadtests. '
            f'{verified_files} oorspronkelijke artifacthashes gecontroleerd. De 138 eerdere ideale-equivalentiechecks '
            'zijn via hun hashes geverifieerd, niet opnieuw gesimuleerd.\n\n'
            'Deze voorbereiding heeft geen submissionfunctie. De oude runner en indieningsblokkering zijn onaangeroerd. '
            'Voorstel na toestemming: precies een job, max_execution_time=5, geen sessie/batch/retry/backendwissel. '
            'Eerst een aparte actuele read-only tijdsraming; onbekende subjoboverhead kan de job laten afbreken.\n\n'
            'Vergelijkingen met de vorige job zijn beschrijvend door mogelijke hardwaredrift. '
            'Referentie: hetzelfde eindige Trottercircuit, niet exact continue dynamica. '
            'Deze kleine klassiek oplosbare pilot kan geen quantum advantage bewijzen.\n')
    sources = destination / 'source_snapshot'
    sources.mkdir()
    for name in ('prepare_cuprate_2d_tflo_compact_pilot.py', 'test_cuprate_2d_tflo_compact_pilot.py',
                 'preflight_cuprate_2d_tflo_budget.py', 'cuprate_2d_tflo_refinement.py'):
        shutil.copyfile(BASE / name, sources / name)
    save(destination / 'sha256.json', {str(p.relative_to(destination)): digest(p)
         for p in sorted(destination.rglob('*')) if p.is_file()})
    verify_tree(destination)
    print(json.dumps({'status': plan['status'], 'checks_passed': len(checks),
        'circuits': 80, 'shots_per_setting': 512, 'total_shots': 5120,
        'new_QPU_seconds': 0, 'output': str(destination)}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--outdir', type=Path, default=DESTINATION)
    args = parser.parse_args()
    prepare(args.outdir)
