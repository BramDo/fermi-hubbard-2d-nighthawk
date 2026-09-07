"""Exactly one user-authorized TFLO Sampler job; prepare/submit/retrieve/recover.

The canonical plan-level lock survives all failures and output-directory changes.
Never remove it to retry. Recovery searches only the persisted unique job tag.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import logging
import os
import time
import uuid
import warnings
from pathlib import Path

import numpy as np
from qiskit import qpy
from qiskit.primitives.containers import SamplerPub
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
from qiskit_ibm_runtime.json import RuntimeEncoder
from qiskit_ibm_runtime.utils.validations import validate_isa_circuits
from urllib3.util.retry import Retry

from cuprate_2d_tflo import skeleton, archive_sampler_results, analyze
from analyze_cuprate_2d_tflo import load_archive
from preflight_cuprate_2d_tflo_budget import wire_time

BASE = Path(__file__).resolve().parent
PLAN = BASE/'results_cuprate_2d/tflo_pilot_3x3_2026-09-05_ready'
BUDGET = BASE/'results_cuprate_2d/tflo_budget_2026-09-05'
RUN = BASE/'results_cuprate_2d/tflo_run_3x3_2026-09-05'
PLAN_HASH = '453a3d3f237f1912577ef5528f950c96220f0916e231191a929df38d3cbe071e'
BUDGET_HASH = '97ac48119fd95928c5559368728ea3acd3984ee69afd7c678b9c019ca3f49996'
ACCOUNT, BACKEND, CAP = 'qiskit-runtime-q9', 'ibm_phoenix', 5


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def encode(value):
    text = json.dumps(value, cls=RuntimeEncoder, indent=2, allow_nan=False)+'\n'
    if 'crn:' in text.lower() or '"token":' in text.lower():
        raise ValueError('Secret-bearing data refused')
    return text


def exclusive_json(path, value):
    text = encode(value)
    with Path(path).open('x',encoding='utf-8') as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())


def save_if_absent(path, value):
    if not Path(path).exists():
        exclusive_json(path,value)


def safe_provider(label, function, *args, **kwargs):
    try:
        with warnings.catch_warnings(record=True), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return function(*args,**kwargs)
    except Exception as exc:
        raise RuntimeError(f'{label}: {type(exc).__name__}') from None


def verified_plan():
    assert digest(PLAN/'manifest.json')==PLAN_HASH, 'Approved plan changed'
    assert digest(BUDGET/'budget_preflight.json')==BUDGET_HASH, 'Approved preflight changed'
    for root in (PLAN,BUDGET):
        for name,expected in read(root/'sha256.json').items():
            target=(root/name).resolve()
            assert target.is_relative_to(root.resolve()) and digest(target)==expected
    audit=read(BASE/'results_cuprate_2d/tflo_pilot_3x3_2026-09-05_ready_audit/verification.json')
    for name,expected in audit['source_sha256'].items():
        assert digest(BASE/name)==expected, 'Audited source changed'
    plan=read(PLAN/'manifest.json')
    assert len(plan['records'])==80 and len(plan['settings'])==10
    assert sum(r['shots'] for r in plan['records'])==5120
    assert plan['backend_candidate']==BACKEND
    return plan


def bind_inputs(plan):
    with (PLAN/'twirled_sampler_templates.qpy').open('rb') as handle:
        templates=qpy.load(handle)
    pubs=[]
    for i,r in enumerate(plan['records']):
        template=templates[r['template_index']]
        assert template.metadata['twirl_seed']==r['seed']
        assert template.metadata['readout_mask_little_endian']==r['readout_mask_little_endian']
        circuit=template.assign_parameters({p:r['parameter_values'][p.name] for p in template.parameters})
        assert skeleton(circuit)==skeleton(template) and circuit.num_parameters==0
        assert circuit.count_ops()['cz']==1008 and r['shots']==64
        circuit.metadata={**circuit.metadata,'setting_id':r['setting_id'],'twirl_id':r['twirl_id'],
                          'tflo_record_index':i,'tflo_plan_sha256':PLAN_HASH}
        pub=SamplerPub.coerce((circuit,None,64))
        assert pub.shape==() and pub.shots==64
        pubs.append(pub)
    return pubs


def prepare():
    plan=verified_plan()
    if (PLAN/'submission_attempt.json').exists():
        raise FileExistsError('Plan already attempted; use retrieve or recover')
    RUN.mkdir(parents=True,exist_ok=False)
    (RUN/'bound_inputs').mkdir()
    pubs=bind_inputs(plan)
    for i,pub in enumerate(pubs):
        path=RUN/f'bound_inputs/circuit_{i:03d}.qpy'
        with path.open('wb') as handle:
            qpy.dump(pub.circuit,handle)
        with path.open('rb') as handle:
            assert qpy.load(handle)[0]==pub.circuit
    tag='tflo3x3-'+uuid.uuid4().hex[:16]
    options=read(BUDGET/'proposed_sampler_options.json')
    options['environment']={'job_tags':['2d-cuprate','tflo-3x3',tag]}
    assert options['max_execution_time']==CAP and options['default_shots']==64
    exclusive_json(RUN/'approved_intent.json',{
        'authorization':'User replied Ja to one TFLO job, max 5 QPU seconds, no automatic repeat.',
        'backend':BACKEND,'account_name':ACCOUNT,'plan_sha256':PLAN_HASH,
        'budget_preflight_sha256':BUDGET_HASH,'tag':tag,'options':options,
        'circuits':80,'shots':5120,'shots_per_setting':512,'records':plan['records'],
        'source_sha256':digest(__file__),'created_unix':time.time()})
    exclusive_json(RUN/'frozen_inputs_sha256.json',{
        str(p.relative_to(RUN)):digest(p) for p in RUN.rglob('*') if p.is_file()})
    print(json.dumps({'stage':'PREPARED_NOT_SUBMITTED','tag':tag,'circuits':80,'shots':5120,
                      'max_execution_time':CAP,'qpy_roundtrip_checks':80}),flush=True)


def verify_dispatch_files():
    plan=verified_plan()
    for name,expected in read(RUN/'frozen_inputs_sha256.json').items():
        path=(RUN/name).resolve()
        assert path.is_relative_to(RUN.resolve()) and digest(path)==expected
    intent=read(RUN/'approved_intent.json')
    assert intent['source_sha256']==digest(__file__), 'Runner changed after freezing'
    assert intent['plan_sha256']==PLAN_HASH and intent['options']['max_execution_time']==CAP
    pubs=bind_inputs(plan)
    for i,pub in enumerate(pubs):
        with (RUN/f'bound_inputs/circuit_{i:03d}.qpy').open('rb') as handle:
            assert qpy.load(handle)[0]==pub.circuit
    return plan,intent,pubs


def disable_retries(service, backend, sampler):
    clients=[backend._api_client]
    for selected_service in (service,sampler._service):
        clients.append(selected_service._active_api_client)
        clients.extend(selected_service._api_clients.values())
    seen=set()
    for client in clients:
        session=client._session
        if id(session) in seen:
            continue
        seen.add(id(session))
        for adapter in session.adapters.values():
            adapter.max_retries=Retry(total=0,connect=0,read=0,status=0,redirect=0,other=0)
            assert adapter.max_retries.total==0
    assert seen
    return {'runtime_sessions_with_retries_disabled':len(seen),'automatic_job_retry':False}


def dispatch_once(lock, receipt, intent, send):
    """Testable exactly-once boundary. Ambiguity never clears the lock."""
    if Path(receipt).exists():
        raise FileExistsError('Receipt already present')
    exclusive_json(lock,{'started_unix':time.time(),'tag':intent['tag'],'plan_sha256':PLAN_HASH,
                         'max_execution_time':CAP,'run_dir':str(Path(receipt).parent),
                         'warning':'Never delete this lock to retry; recover the job by tag.'})
    try:
        job=send()
    except Exception as exc:
        save_if_absent(Path(receipt).parent/'dispatch_uncertain.json',{
            'error_type':type(exc).__name__,'tag':intent['tag'],'resubmit_allowed':False})
        raise
    result={'job_id':str(job.job_id()),'backend':BACKEND,'account_name':ACCOUNT,
            'tag':intent['tag'],'submitted_unix':time.time(),'max_execution_time':CAP,
            'circuits':80,'shots':5120,'automatic_retry':False,'plan_sha256':PLAN_HASH}
    # Output the ID first so it remains recoverable even if disk receipt fails.
    print(json.dumps(result),flush=True)
    exclusive_json(receipt,result)
    return job


def submit(confirmed=False):
    if not confirmed:
        raise PermissionError('Explicit --confirm-one-job-max-5s is required')
    if (PLAN/'submission_attempt.json').exists() or (RUN/'job_receipt.json').exists():
        raise FileExistsError('Submission already attempted; retrieval only')
    plan,intent,pubs=verify_dispatch_files()
    service=safe_provider('authenticate',QiskitRuntimeService,name=ACCOUNT)
    backend=safe_provider('backend',service.backend,BACKEND)
    assert safe_provider('backend status',backend.status).operational
    fingerprint=hashlib.sha256(str(service.active_account().get('instance','')).encode()).hexdigest()
    assert fingerprint==read(BUDGET/'budget_preflight.json')['instance_sha256']
    validate_isa_circuits([p.circuit for p in pubs],backend.target)
    for pub in pubs:
        backend.check_faulty(pub.circuit)
    options=intent['options']
    assert options['execution']['rep_delay']==backend.default_rep_delay
    reset=max(backend.target['reset'][(q,)].duration for q in plan['initial_layout'])
    execution=sum(64*(wire_time(p.circuit,backend.target,aligned=True)+reset+backend.default_rep_delay) for p in pubs)
    assert 4+execution<CAP, 'Live two-subjob estimate no longer fits the approved cap'
    sampler=SamplerV2(mode=backend,options=options)
    assert sampler.mode is None and sampler.options.max_execution_time==CAP
    retry_info=disable_retries(service,backend,sampler)
    save_if_absent(RUN/'live_dispatch_check.json',{
        'checked_unix':time.time(),'backend':BACKEND,'instance_sha256':fingerprint,
        'all_80_circuits_ISA_valid':True,'execution_seconds':execution,
        'two_subjobs_estimate_seconds':4+execution,**retry_info})
    dispatch_once(PLAN/'submission_attempt.json',RUN/'job_receipt.json',intent,
                  lambda:safe_provider('single Sampler submission',sampler.run,pubs))


def recover():
    if (RUN/'job_receipt.json').exists():
        print(json.dumps(read(RUN/'job_receipt.json')),flush=True)
        return
    lock=read(PLAN/'submission_attempt.json')
    service=safe_provider('authenticate',QiskitRuntimeService,name=ACCOUNT)
    jobs=safe_provider('lookup existing tag',service.jobs,limit=10,backend_name=BACKEND,job_tags=[lock['tag']])
    if len(jobs)!=1:
        print(json.dumps({'matches':len(jobs),'tag':lock['tag'],'resubmit_allowed':False}),flush=True)
        return
    receipt={'job_id':jobs[0].job_id(),'backend':BACKEND,'account_name':ACCOUNT,'tag':lock['tag'],
             'max_execution_time':CAP,'circuits':80,'shots':5120,'recovered_by_tag':True,'plan_sha256':PLAN_HASH}
    exclusive_json(RUN/'job_receipt.json',receipt)
    print(json.dumps(receipt),flush=True)


def retrieve():
    receipt=read(RUN/'job_receipt.json')
    service=safe_provider('authenticate',QiskitRuntimeService,name=ACCOUNT)
    job=safe_provider('job lookup',service.job,receipt['job_id'])
    status=safe_provider('job status',job.status)
    status=str(getattr(status,'name',status))
    row={'job_id':receipt['job_id'],'status':status,'checked_unix':time.time()}
    with (RUN/'status_history.jsonl').open('a',encoding='utf-8') as handle:
        handle.write(json.dumps(row)+'\n')
    print(json.dumps(row),flush=True)
    metadata=safe_provider('job budget metadata',job._api_client.job_get,receipt['job_id'])
    budget={'job_id':receipt['job_id'],'provider_cost_field':metadata.get('cost'),
            'expected_max_execution_time':CAP,'verified':metadata.get('cost')==CAP}
    save_if_absent(RUN/'provider_budget_verification.json',budget)
    assert budget['verified'], 'Provider cap differs from approved cap; investigate, never resubmit'
    if status not in ('DONE','ERROR','CANCELLED','CANCELED'):
        return
    metrics=safe_provider('job metrics',job.metrics)
    save_if_absent(RUN/'provider_metrics.json',metrics)
    if status!='DONE':
        save_if_absent(RUN/'job_failed.json',{'job_id':receipt['job_id'],'status':status,
                                            'no_automatic_retry':True,'usage':metrics.get('usage')})
        return
    plan=verified_plan()
    expected=bind_inputs(plan)
    inputs=safe_provider('actual job inputs',lambda:job.inputs)
    actual=[SamplerPub.coerce(p) for p in inputs['pubs']]
    assert len(actual)==len(expected)==80
    folder=RUN/'provider_inputs'
    folder.mkdir(exist_ok=True)
    for i,(a,b) in enumerate(zip(actual,expected)):
        assert a.shots==b.shots==64 and a.shape==b.shape==()
        assert a.circuit==b.circuit, 'Provider circuit differs from frozen intent'
        path=folder/f'circuit_{i:03d}.qpy'
        if not path.exists():
            with path.open('wb') as handle:
                qpy.dump(a.circuit,handle)
    save_if_absent(folder/'options_and_metadata.json',{k:v for k,v in inputs.items() if k!='pubs'})
    result=safe_provider('job result',job.result)
    save_if_absent(RUN/'provider_result_complete.json',result)
    assert len(result)==80
    for i,(pub,r) in enumerate(zip(result,plan['records'])):
        md=pub.metadata.get('circuit_metadata',{})
        assert md.get('setting_id')==r['setting_id'] and md.get('twirl_id')==r['twirl_id']
        assert md.get('tflo_record_index')==i and md.get('tflo_plan_sha256')==PLAN_HASH
    raw_file=RUN/'raw_bitstrings.json'
    if not raw_file.exists():
        archive_sampler_results(raw_file,result,plan['records'],job_id=receipt['job_id'],width=18)
    save_if_absent(RUN/'provider_input_verification.json',{
        'job_id':receipt['job_id'],'all_circuits_match':True,'all_result_metadata_match':True,
        'scalar_pubs':80,'shots_per_pub':64,'total_shots':5120,'max_execution_time_verified':True})
    plan,raw,decoded,nup,ndown=load_archive(PLAN,raw_file)
    try:
        report=analyze(plan['settings'],decoded,nup,ndown,tolerance=0,bootstrap=200)
    except ValueError:
        save_if_absent(RUN/'analysis_not_valid.json',{
            'reason':'Frozen PS/TFLO analysis rejected data; inspect retained samples without changing the frozen rule.',
            'raw_bitstrings_preserved':True,'no_resubmission':True})
        return
    report.update(job_id=receipt['job_id'],usage=metrics.get('usage'),plan_sha256=PLAN_HASH)
    save_if_absent(RUN/'tflo_analysis.json',report)
    held=[r for r in report['settings'] if r['role']=='interacting_holdout']
    summary={'job_id':receipt['job_id'],'status':'DONE','usage':metrics.get('usage'),
        'bootstrap_failures':report['bootstrap_failures'],
        'heldout':[{'time':r['time'],'retained_shots':r['retained_shots'],
                   **{method:r[method]['rmse_charge_spin_double'] for method in ('raw','postselected','tflo')}} for r in held],
        'claim_boundary':'Small full-fermion validation pilot; no quantum advantage claim.'}
    save_if_absent(RUN/'comparison_summary.json',summary)
    print(json.dumps(summary),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','submit','retrieve','recover'])
    parser.add_argument('--confirm-one-job-max-5s',action='store_true')
    args=parser.parse_args()
    logging.disable(logging.CRITICAL)
    try:
        if args.action=='submit':
            submit(args.confirm_one_job_max_5s)
        else:
            globals()[args.action]()
    except Exception as exc:
        print(json.dumps({'action':args.action,'error_type':type(exc).__name__,
                          'automatic_resubmission':False}),flush=True)
        raise SystemExit(1) from None
