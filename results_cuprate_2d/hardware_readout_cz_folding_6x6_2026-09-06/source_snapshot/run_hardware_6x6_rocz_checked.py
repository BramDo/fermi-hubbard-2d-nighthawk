"""Checked live boundary v2: missing quota is unknown, never zero or unlimited.
Preserves v1, all frozen circuits, cap15 and the SAME canonical attempt lock.
"""
import argparse
import hashlib
import io
import json
import logging
from pathlib import Path
import shutil
import time
import unittest
import numpy as np
import run_hardware_6x6_rocz_once as h
safe=h.safe; RUN=h.RUN; ROOT=h.ROOT; CAP=h.CAP

def usage_summary(raw):
    keys=('usage_limit_seconds','usage_allocation_seconds','usage_consumed_seconds','usage_remaining_seconds')
    usage={k:float(raw[k]) for k in keys if isinstance(raw.get(k),(int,float)) and not isinstance(raw.get(k),bool)}
    h.require(all(np.isfinite(v) and v>=0 for v in usage.values()),'Invalid usage values')
    if 'usage_remaining_seconds' not in usage:
        limit=usage.get('usage_limit_seconds',usage.get('usage_allocation_seconds'))
        consumed=usage.get('usage_consumed_seconds')
        if limit is not None and consumed is not None:
            usage['usage_remaining_seconds']=max(0,limit-consumed)
    remaining=usage.get('usage_remaining_seconds')
    if remaining is not None: h.require(remaining>=15,'Reported remaining quota below15s')
    return {**usage,'remaining_quota_reported':remaining is not None,
        'unknown_is_not_zero_or_unlimited':True,'authorized_job_cap_seconds':15}

def freeze_revision():
    h.require(not (RUN/'submission_attempt.json').exists(),'Already attempted')
    h.require(not (RUN/'live_preflight.json').exists(),'Preflight already frozen')
    h.verify_files(RUN,'frozen_inputs_sha256.json')
    # V1 data/protocol remain archived. This narrowly amends optional quota handling.
    report={'revision':2,'reason':'IBM returned usage_consumed_seconds but no limit/allocation/remaining fields.',
        'interpretation':'Missing remaining quota is unknown. Do not assert sufficient/unlimited quota.',
        'authority':'Same user authorization: one job with max_execution_time15, no retry.',
        'quota_gate':'Reject reported remaining quota below15; if unreported rely solely on explicit per-job cap.',
        'physics_circuits_shots_layout_cap_retry_unchanged':True,
        'plan_sha256':safe.digest(RUN/'plan.json'),'created_unix':time.time()}
    log=io.StringIO()
    tests=unittest.TextTestRunner(stream=log,verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromName('test_hardware_6x6_quota'))
    h.require(tests.wasSuccessful(),'Quota boundary tests failed')
    for name in ('run_hardware_6x6_rocz_checked.py','test_hardware_6x6_quota.py'):
        destination=RUN/'source_snapshot'/name
        if destination.exists(): raise FileExistsError('Revision source exists')
        shutil.copyfile(ROOT/name,destination)
    safe.exclusive_json(RUN/'implementation_revision2.json',report)
    (RUN/'revision2_tests.txt').write_text(log.getvalue(),encoding='utf-8')
    names=['implementation_revision2.json','revision2_tests.txt',
        'source_snapshot/run_hardware_6x6_rocz_checked.py','source_snapshot/test_hardware_6x6_quota.py']
    safe.exclusive_json(RUN/'implementation_revision2_sha256.json',{n:safe.digest(RUN/n) for n in names})
    print(json.dumps({'revision_frozen':2,'tests':tests.testsRun,'submission_attempted':False}),flush=True)

def checked_frozen():
    h.verify_files(RUN,'implementation_revision2_sha256.json')
    report=safe.read(RUN/'implementation_revision2.json')
    h.require(report['plan_sha256']==safe.digest(RUN/'plan.json'),'Revision plan mismatch')
    for name in ('run_hardware_6x6_rocz_checked.py','test_hardware_6x6_quota.py'):
        h.require(safe.digest(ROOT/name)==safe.digest(RUN/'source_snapshot'/name),'Revision source changed')
    return h.frozen()

def live_gate(plan,pubs):
    service=safe.safe_provider('IBM authentication',h.QiskitRuntimeService,name=h.ACCOUNT)
    backend=safe.safe_provider('IBM backend',service.backend,h.BACKEND)
    status=safe.safe_provider('IBM status',backend.status)
    h.require(status.operational and backend.num_qubits==120,'Backend unavailable or changed')
    properties=safe.safe_provider('IBM properties',backend.properties)
    h.require(not set(plan['layout']).intersection(properties.faulty_qubits()),'Faulty selected qubit')
    safe.safe_provider('ISA validation',h.validate_isa_circuits,[p.circuit for p in pubs],backend.target)
    usage=usage_summary(safe.safe_provider('IBM usage',service.usage))
    target=backend.target; timing=[]; low_level=np.zeros(120,dtype=np.int64)
    rep=float(backend.default_rep_delay)
    h.require(backend.rep_delay_range[0]<=rep<=backend.rep_delay_range[1],'Invalid rep delay')
    reset=max(float(target['reset'][(q,)].duration) for q in plan['layout'])
    h.require(np.isfinite(reset) and reset>=0,'Invalid reset')
    for index,p in enumerate(pubs):
        safe.safe_provider('Faulty gate validation',backend.check_faulty,p.circuit)
        sdk=float(p.circuit.estimate_duration(target)); manual=h.wire_time(p.circuit,target)
        h.require(abs(sdk-manual)<1e-10,'Timing methods disagree')
        aligned=h.wire_time(p.circuit,target,aligned=True)
        h.require(aligned>=manual-1e-12,'Alignment shortened circuit')
        for item in p.circuit.data:
            low_level[[p.circuit.find_bit(q).index for q in item.qubits]]+=h.WEIGHTS[item.operation.name]
        timing.append({'index':index,'shots':p.shots,'duration':sdk,'aligned_duration':aligned,
            'shot_execution_seconds':p.shots*(aligned+reset+rep)})
        if index%6==5: print(json.dumps({'live_checked_pubs':index+1,'total':26}),flush=True)
    low_level+=50*len(pubs)
    h.require(max(low_level)<26_800_000,'Instruction memory exceeded')
    execution=sum(x['shot_execution_seconds'] for x in timing)
    h.require(0<execution and 12+execution<CAP,'Six-subjob planning scenario exceeds cap')
    fingerprint=hashlib.sha256(str(service.active_account().get('instance','')).encode()).hexdigest()
    report={'status':'LIVE_PREFLIGHT_PASS_NOT_SUBMITTED','implementation_revision':2,
        'checked_unix':time.time(),'backend':h.BACKEND,'instance_sha256':fingerprint,
        'pending_jobs':status.pending_jobs,'options':h.options_for(backend,plan['tag']),
        'execution_seconds':execution,'one_subjob_estimate':2+execution,'two_subjob_estimate':4+execution,
        'three_subjob_estimate':6+execution,'six_subjob_estimate':12+execution,
        'subjob_count_known':False,'cost_is_estimate_not_guarantee':True,
        'all26_ISA_and_fault_checks_pass':True,'reset_seconds':reset,'timing_by_pub':timing,
        'plan_sha256':safe.digest(RUN/'plan.json'),'properties_updated':str(properties.last_update_date),
        'usage':usage,'instruction_memory_max_per_wire':int(max(low_level))}
    return service,backend,properties,report

def preflight():
    h.require(not (RUN/'submission_attempt.json').exists(),'Already attempted')
    plan,pubs=checked_frozen()
    _,_,properties,report=live_gate(plan,pubs)
    safe.exclusive_json(RUN/'live_preflight.json',report)
    safe.exclusive_json(RUN/'live_backend_properties.json',properties.to_dict())
    safe.exclusive_json(RUN/'preflight_sha256.json',{n:safe.digest(RUN/n)
        for n in ['live_preflight.json','live_backend_properties.json']})
    print(json.dumps({k:report[k] for k in ('status','pending_jobs','execution_seconds',
        'two_subjob_estimate','six_subjob_estimate','usage')}),flush=True)

def submit(confirmed=False):
    if not confirmed: raise PermissionError('Literal confirmation required')
    if (RUN/'submission_attempt.json').exists() or (RUN/'job_receipt.json').exists():
        raise FileExistsError('Attempt consumed; recover/retrieve only')
    plan,pubs=checked_frozen(); h.verify_files(RUN,'preflight_sha256.json')
    old=safe.read(RUN/'live_preflight.json')
    service,backend,properties,check=live_gate(plan,pubs)
    h.require(check['instance_sha256']==old['instance_sha256'],'Instance changed')
    h.require(check['options']==old['options'],'Approved options changed')
    sampler=safe.safe_provider('Sampler setup',h.SamplerV2,mode=backend,options=check['options'])
    h.require(sampler.mode is None and sampler.options.max_execution_time==15,'Session/batch/cap changed')
    retry=safe.disable_retries(service,backend,sampler)
    safe.exclusive_json(RUN/'dispatch_live_check.json',{**check,**retry})
    intent={**plan,'plan_sha256':safe.digest(RUN/'plan.json')}
    print(json.dumps({'event':'LIVE_GATE_PASSED','six_subjob_estimate':check['six_subjob_estimate'],
        'cap':15,'retries_disabled':True,'shots':h.TOTAL}),flush=True)
    job=h.dispatch_once(RUN/'submission_attempt.json',RUN/'job_receipt.json',intent,
        lambda:safe.safe_provider('Single authorized Sampler POST',sampler.run,pubs))
    print(json.dumps(h.verify_provider_cap(job)),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['freeze_revision','preflight','submit','recover','retrieve'])
    parser.add_argument('--confirm-one-job-max-15s',action='store_true')
    args=parser.parse_args(); logging.disable(logging.CRITICAL)
    try:
        if args.action=='submit': submit(args.confirm_one_job_max_15s)
        elif args.action in ('recover','retrieve'): getattr(h,args.action)()
        else: globals()[args.action]()
    except Exception as exc:
        print(json.dumps({'action':args.action,'error_type':type(exc).__name__,
            'automatic_resubmission':False}),flush=True)
        raise SystemExit(1) from None

