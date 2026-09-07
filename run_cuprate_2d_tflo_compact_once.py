"""One newly authorized compact TFLO job. Never reuse the legacy job lock.

prepare/submit require a literal confirmation flag; recover/retrieve only read
the existing provider job. Ambiguous submission consumes the local attempt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import shutil
import time
import uuid
from pathlib import Path

from qiskit import qpy
from qiskit.primitives.containers import SamplerPub
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
from qiskit_ibm_runtime.utils.validations import validate_isa_circuits

import run_cuprate_2d_tflo_once as legacy
from cuprate_2d_tflo import skeleton, archive_sampler_results
from analyze_cuprate_2d_tflo import load_archive
from prepare_cuprate_2d_tflo_compact_pilot import verify_tree, validate_records
from preflight_cuprate_2d_tflo_budget import wire_time

BASE = Path(__file__).resolve().parent
PLAN = BASE / 'results_cuprate_2d/tflo_compact_pilot_3x3_2026-09-05'
BUDGET = BASE / 'results_cuprate_2d/tflo_compact_budget_2026-09-05'
REVIEW = BASE / 'results_cuprate_2d/tflo_compact_review_2026-09-05'
RUN = BASE / 'results_cuprate_2d/tflo_compact_run_3x3_2026-09-05'
PLAN_HASH = '823015bd20de02232c582388294bbf8146de9781292843a17fab1b5c170aab6d'
BUDGET_HASH = '76faac9e89131d05b328c278dde26394f771e5964697460671d957544df5cc3a'
REVIEW_HASH = '79ba96f0edb15dd96af039114738b48787472e9ec01fe83527eb47ed0c2e62c1'
LEGACY_HASH = '8e4b28002cd884c4ca35cb6fe95aecd7d9f24951a3ca66c274ac12d5c9982184'
PROTOCOL_HASH = 'cfe212f3935c7c5952b56bd1217aea900ddffab29706c2630be6b8785f69ec5b'
ACCOUNT, BACKEND, CAP = 'qiskit-runtime-q9', 'ibm_phoenix', 5
digest, read = legacy.digest, legacy.read
exclusive_json, save_if_absent = legacy.exclusive_json, legacy.save_if_absent
safe_provider, disable_retries = legacy.safe_provider, legacy.disable_retries
DEPENDENCIES = ('run_cuprate_2d_tflo_compact_once.py', 'test_run_cuprate_2d_tflo_compact_once.py',
    'run_cuprate_2d_tflo_once.py', 'cuprate_2d_tflo.py', 'analyze_cuprate_2d_tflo.py',
    'prepare_cuprate_2d_tflo_compact_pilot.py', 'preflight_cuprate_2d_tflo_budget.py')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verified_plan():
    for path, expected in ((PLAN / 'manifest.json', PLAN_HASH),
            (PLAN / 'analysis_protocol.json', PROTOCOL_HASH),
            (BUDGET / 'budget_preflight.json', BUDGET_HASH),
            (REVIEW / 'verification.json', REVIEW_HASH),
            (Path(legacy.__file__), LEGACY_HASH)):
        require(digest(path) == expected, 'Approved source or artifact changed')
    for root in (PLAN, BUDGET, REVIEW):
        verify_tree(root)
    plan = read(PLAN / 'manifest.json')
    require(read(REVIEW / 'verification.json')['passed'], 'Review failed')
    validate_records(plan)
    require(plan['backend_candidate'] == BACKEND, 'Backend changed')
    require(digest(legacy.PLAN / 'submission_attempt.json') == plan['provenance']['old_submission_lock_sha256'],
            'Legacy job lock changed')
    require(plan['analysis_policy']['sector_tolerance'] == 1, 'Frozen filter changed')
    return plan


def bind_inputs(plan):
    with (PLAN / 'twirled_sampler_templates.qpy').open('rb') as handle:
        templates = qpy.load(handle)
    require(len(templates) == 8, 'Template count changed')
    pubs = []
    for index, record in enumerate(plan['records']):
        template = templates[record['template_index']]
        require(template.metadata['twirl_seed'] == record['seed'], 'Seed changed')
        require(template.metadata['readout_mask_little_endian'] == record['readout_mask_little_endian'], 'Readout mask changed')
        circuit = template.assign_parameters({p: record['parameter_values'][p.name] for p in template.parameters})
        require(skeleton(circuit) == skeleton(template) and circuit.num_parameters == 0, 'Binding changed structure')
        require(circuit.count_ops()['cz'] == 1008 and record['shots'] == 64, 'Exposure changed')
        circuit.metadata = {**circuit.metadata, 'setting_id': record['setting_id'],
            'twirl_id': record['twirl_id'], 'tflo_record_index': index,
            'tflo_plan_sha256': PLAN_HASH, 'tflo_protocol_sha256': PROTOCOL_HASH,
            'pilot_revision': 'compact-one-qubit-v1'}
        pub = SamplerPub.coerce((circuit, None, 64))
        require(pub.shape == () and pub.shots == 64, 'Non-scalar or wrong-shot PUB')
        pubs.append(pub)
    require(len(pubs) == 80 and sum(p.shots for p in pubs) == 5120, 'Wrong total exposure')
    return pubs


def prepare(confirmed=False):
    if not confirmed:
        raise PermissionError('Explicit --confirm-one-job-max-5s is required')
    if (PLAN / 'submission_attempt.json').exists():
        raise FileExistsError('This new pilot was already attempted; retrieval only')
    plan = verified_plan()
    pubs = bind_inputs(plan)
    RUN.mkdir(parents=True, exist_ok=False)
    (RUN / 'bound_inputs').mkdir()
    for index, pub in enumerate(pubs):
        path = RUN / f'bound_inputs/circuit_{index:03d}.qpy'
        with path.open('xb') as handle:
            qpy.dump(pub.circuit, handle)
        with path.open('rb') as handle:
            require(qpy.load(handle)[0] == pub.circuit, 'Prepared QPY differs')
    tag = 'tflo-compact-' + uuid.uuid4().hex[:16]
    options = read(BUDGET / 'proposed_sampler_options.json')
    options['environment'] = {'job_tags': ['2d-cuprate', 'tflo-compact-3x3', tag]}
    require(options['max_execution_time'] == CAP and options['default_shots'] == 64, 'Cap or shots changed')
    source = RUN / 'source_snapshot'
    source.mkdir()
    for name in DEPENDENCIES:
        shutil.copyfile(BASE / name, source / name)
    exclusive_json(RUN / 'approved_intent.json', {
        'authorization': 'User replied Ja to exactly one extra compact pilot on ibm_phoenix, max 5 QPU seconds, no automatic repetition.',
        'new_submission_authorized': True, 'checkpoint_id': 'compact-tflo-single-job-max5s',
        'checkpoint_resolved_by': 'explicit new user confirmation',
        'backend': BACKEND, 'account_name': ACCOUNT, 'plan_sha256': PLAN_HASH,
        'protocol_sha256': PROTOCOL_HASH, 'budget_preflight_sha256': BUDGET_HASH,
        'tag': tag, 'options': options, 'circuits': 80, 'shots': 5120,
        'shots_per_setting': 512, 'records': plan['records'],
        'source_sha256': {name: digest(BASE / name) for name in DEPENDENCIES},
        'created_unix': time.time(), 'automatic_retry': False,
        'legacy_authorization_reused': False})
    exclusive_json(RUN / 'frozen_inputs_sha256.json', {
        str(p.relative_to(RUN)): digest(p) for p in sorted(RUN.rglob('*')) if p.is_file()})
    print(json.dumps({'stage': 'COMPACT_AUTHORIZED_PREPARED_NOT_SUBMITTED',
        'tag': tag, 'circuits': 80, 'total_shots': 5120, 'max_execution_time': CAP,
        'bound_QPY_roundtrip_checks': 80}), flush=True)


def verify_dispatch_files():
    plan = verified_plan()
    for name, expected in read(RUN / 'frozen_inputs_sha256.json').items():
        path = (RUN / name).resolve()
        require(path.is_relative_to(RUN.resolve()) and digest(path) == expected, 'Prepared input changed')
    intent = read(RUN / 'approved_intent.json')
    require(intent['new_submission_authorized'] is True, 'No recorded approval')
    for name, expected in intent['source_sha256'].items():
        require(name in DEPENDENCIES and digest(BASE / name) == expected, 'Frozen runner dependency changed')
    options = read(BUDGET / 'proposed_sampler_options.json')
    options['environment'] = {'job_tags': ['2d-cuprate', 'tflo-compact-3x3', intent['tag']]}
    require(intent['options'] == options and intent['plan_sha256'] == PLAN_HASH, 'Approved options changed')
    pubs = bind_inputs(plan)
    for index, pub in enumerate(pubs):
        with (RUN / f'bound_inputs/circuit_{index:03d}.qpy').open('rb') as handle:
            require(qpy.load(handle)[0] == pub.circuit, 'Frozen dispatch circuit changed')
    return plan, intent, pubs


def dispatch_once(lock, receipt, intent, send):
    """Atomic durable local attempt before POST. A lost response never retries."""
    if Path(receipt).exists():
        raise FileExistsError('Receipt already exists')
    require(intent['plan_sha256'] == PLAN_HASH and intent['options']['max_execution_time'] == CAP,
            'Wrong plan or cap at dispatch boundary')
    exclusive_json(lock, {'started_unix': time.time(), 'tag': intent['tag'],
        'plan_sha256': PLAN_HASH, 'max_execution_time': CAP,
        'run_dir': str(Path(receipt).parent), 'authorization_consumed_on_attempt': True,
        'warning': 'Never delete this lock or repeat the POST. Recover the existing job by this unique tag.'})
    try:
        job = send()
    except Exception as exc:
        save_if_absent(Path(receipt).parent / 'dispatch_uncertain.json', {
            'error_type': type(exc).__name__, 'tag': intent['tag'], 'resubmit_allowed': False})
        raise
    row = {'job_id': str(job.job_id()), 'backend': BACKEND, 'account_name': ACCOUNT,
        'tag': intent['tag'], 'submitted_unix': time.time(), 'max_execution_time': CAP,
        'circuits': 80, 'shots': 5120, 'automatic_retry': False, 'plan_sha256': PLAN_HASH}
    print(json.dumps(row), flush=True)  # Recoverable even if receipt persistence fails.
    exclusive_json(receipt, row)
    return job


def verify_cap(job):
    metadata = safe_provider('provider cap lookup', job._api_client.job_get, job.job_id())
    row = {'job_id': job.job_id(), 'provider_cost_field': metadata.get('cost'),
        'expected_max_execution_time': CAP, 'verified': metadata.get('cost') == CAP}
    save_if_absent(RUN / 'provider_budget_verification.json', row)
    require(row['verified'], 'Provider cap mismatch; investigate the existing job, never resubmit')
    return row


def submit(confirmed=False):
    if not confirmed:
        raise PermissionError('Explicit --confirm-one-job-max-5s is required')
    if (PLAN / 'submission_attempt.json').exists() or (RUN / 'job_receipt.json').exists():
        raise FileExistsError('Already attempted; retrieve or recover only')
    plan, intent, pubs = verify_dispatch_files()
    print(json.dumps({'event': 'compact_frozen_dispatch_inputs_verified', 'circuits': 80}), flush=True)
    service = safe_provider('authenticate', QiskitRuntimeService, name=ACCOUNT)
    backend = safe_provider('backend', service.backend, BACKEND)
    status = safe_provider('backend status', backend.status)
    require(status.operational, 'Backend not operational')
    fingerprint = hashlib.sha256(str(service.active_account().get('instance', '')).encode()).hexdigest()
    require(fingerprint == read(BUDGET / 'budget_preflight.json')['instance_sha256'], 'Instance changed')
    safe_provider('live ISA validation', validate_isa_circuits, [p.circuit for p in pubs], backend.target)
    for pub in pubs:
        safe_provider('live faulty-instruction check', backend.check_faulty, pub.circuit)
    options = intent['options']
    require(options['max_execution_time'] == CAP and options['execution']['rep_delay'] == backend.default_rep_delay,
            'Live cap or rep_delay mismatch')
    reset = max(backend.target['reset'][(q,)].duration for q in plan['initial_layout'])
    execution = sum(p.shots * (wire_time(p.circuit, backend.target, aligned=True) + reset + backend.default_rep_delay) for p in pubs)
    require(0 < execution and 4 + execution < CAP, 'Live two-subjob estimate exceeds approved cap')
    sampler = safe_provider('Sampler setup', SamplerV2, mode=backend, options=options)
    require(sampler.mode is None and sampler.options.max_execution_time == CAP, 'Unexpected session/batch mode or cap')
    retry_info = disable_retries(service, backend, sampler)
    live = {'checked_unix': time.time(), 'backend': BACKEND, 'instance_sha256': fingerprint,
        'operational': status.operational, 'pending_jobs_at_check': status.pending_jobs,
        'all_80_circuits_ISA_valid': True, 'execution_seconds': execution,
        'two_subjobs_estimate_seconds': 4 + execution, 'subjob_count_known': False,
        'max_execution_time': CAP, **retry_info}
    save_if_absent(RUN / 'live_dispatch_check.json', live)
    print(json.dumps({'event': 'live_gate_passed', 'two_subjobs_estimate_seconds': 4 + execution,
        'max_execution_time': CAP, 'automatic_retry': False}), flush=True)
    job = dispatch_once(PLAN / 'submission_attempt.json', RUN / 'job_receipt.json', intent,
        lambda: safe_provider('single compact Sampler submission', sampler.run, pubs))
    print(json.dumps({'event': 'provider_cap_verified', **verify_cap(job)}), flush=True)


def recover():
    if (RUN / 'job_receipt.json').exists():
        print(json.dumps(read(RUN / 'job_receipt.json')), flush=True)
        return
    lock = read(PLAN / 'submission_attempt.json')
    require(lock['plan_sha256'] == PLAN_HASH, 'Recovery lock belongs to another plan')
    service = safe_provider('authenticate', QiskitRuntimeService, name=ACCOUNT)
    jobs = safe_provider('recover unique compact tag', service.jobs,
        limit=10, backend_name=BACKEND, job_tags=[lock['tag']])
    if len(jobs) != 1:
        print(json.dumps({'matches': len(jobs), 'tag': lock['tag'], 'resubmit_allowed': False}), flush=True)
        return
    receipt = {'job_id': jobs[0].job_id(), 'backend': BACKEND, 'account_name': ACCOUNT,
        'tag': lock['tag'], 'max_execution_time': CAP, 'circuits': 80, 'shots': 5120,
        'automatic_retry': False, 'recovered_by_tag': True, 'plan_sha256': PLAN_HASH}
    print(json.dumps(receipt), flush=True)
    exclusive_json(RUN / 'job_receipt.json', receipt)
    verify_cap(jobs[0])


def retrieve():
    receipt = read(RUN / 'job_receipt.json')
    require(receipt['plan_sha256'] == PLAN_HASH, 'Receipt belongs to another plan')
    service = safe_provider('authenticate', QiskitRuntimeService, name=ACCOUNT)
    job = safe_provider('job lookup', service.job, receipt['job_id'])
    status = safe_provider('job status', job.status)
    status = str(getattr(status, 'name', status))
    row = {'job_id': receipt['job_id'], 'status': status, 'checked_unix': time.time()}
    with (RUN / 'status_history.jsonl').open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(row) + '\n')
    print(json.dumps(row), flush=True)
    verify_cap(job)
    if status not in ('DONE', 'ERROR', 'CANCELLED', 'CANCELED'):
        return
    metrics = safe_provider('job metrics', job.metrics)
    save_if_absent(RUN / 'provider_metrics.json', metrics)
    if status != 'DONE':
        save_if_absent(RUN / 'job_failed.json', {**row, 'usage': metrics.get('usage'), 'no_automatic_retry': True})
        return
    plan, _, expected = verify_dispatch_files()
    inputs = safe_provider('actual provider inputs', lambda: job.inputs)
    actual = [SamplerPub.coerce(p) for p in inputs['pubs']]
    require(len(actual) == len(expected) == 80, 'Provider input count mismatch')
    folder = RUN / 'provider_inputs'
    folder.mkdir(exist_ok=True)
    for index, (a, b) in enumerate(zip(actual, expected)):
        require(a.shots == b.shots == 64 and a.shape == b.shape == (), 'Provider shots or shape differ')
        require(a.circuit == b.circuit, 'Provider input differs from approved circuit')
        path = folder / f'circuit_{index:03d}.qpy'
        if not path.exists():
            with path.open('xb') as handle:
                qpy.dump(a.circuit, handle)
        with path.open('rb') as handle:
            require(qpy.load(handle)[0] == a.circuit, 'Archived provider QPY differs')
    save_if_absent(folder / 'options_and_metadata.json', {k: v for k, v in inputs.items() if k != 'pubs'})
    result = safe_provider('completed job result', job.result)
    save_if_absent(RUN / 'provider_result_complete.json', result)
    require(len(result) == 80, 'Incomplete result')
    for index, (pub, record) in enumerate(zip(result, plan['records'])):
        md = pub.metadata.get('circuit_metadata', {})
        require(md.get('setting_id') == record['setting_id'] and md.get('twirl_id') == record['twirl_id'], 'Result order differs')
        require(md.get('tflo_record_index') == index and md.get('tflo_plan_sha256') == PLAN_HASH, 'Wrong result provenance')
        require(md.get('tflo_protocol_sha256') == PROTOCOL_HASH, 'Wrong analysis provenance')
    raw_file = RUN / 'raw_bitstrings.json'
    if not raw_file.exists():
        archive_sampler_results(raw_file, result, plan['records'], job_id=receipt['job_id'], width=18)
    _, _, decoded, nup, ndown = load_archive(PLAN, raw_file)
    total = sum(len(bits) for blocks in decoded.values() for bits in blocks.values())
    require(total == 5120 and nup == ndown == 4, 'Incomplete samples or wrong sector')
    verification = {'job_id': receipt['job_id'], 'all_circuits_match': True,
        'all_result_metadata_match': True, 'scalar_pubs': 80, 'shots_per_pub': 64,
        'total_shots': total, 'max_execution_time_verified': True,
        'plan_sha256': PLAN_HASH, 'protocol_sha256': PROTOCOL_HASH,
        'usage': metrics.get('usage'), 'analysis_status': 'pending frozen compact protocol; no automatic legacy analysis'}
    save_if_absent(RUN / 'provider_input_verification.json', verification)
    save_if_absent(RUN / 'completed_archive_sha256.json', {
        str(p.relative_to(RUN)): digest(p) for p in sorted(RUN.rglob('*'))
        if p.is_file() and p.name not in ('status_history.jsonl', 'completed_archive_sha256.json')})
    print(json.dumps({'status': 'DONE_ARCHIVED_AND_VERIFIED', **verification}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'submit', 'recover', 'retrieve'])
    parser.add_argument('--confirm-one-job-max-5s', action='store_true')
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    try:
        if args.action in ('prepare', 'submit'):
            globals()[args.action](args.confirm_one_job_max_5s)
        else:
            globals()[args.action]()
    except Exception as exc:
        print(json.dumps({'action': args.action, 'error_type': type(exc).__name__,
            'automatic_resubmission': False}), flush=True)
        raise SystemExit(1) from None
