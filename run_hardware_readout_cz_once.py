"""Exactly one newly authorized readout + CZ-folding hardware pilot, cap5s."""
import argparse
import hashlib
import io
import json
import logging
from pathlib import Path
import shutil
import time
import unittest
import uuid
import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, qpy
from qiskit.primitives.containers import SamplerPub
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
from qiskit_ibm_runtime.options import SamplerOptions
from qiskit_ibm_runtime.utils.validations import validate_isa_circuits
import run_cuprate_2d_tflo_once as safe
import aer_readout_tflo_zne as r
from preflight_cuprate_2d_tflo_budget import wire_time
from cuprate_2d_tflo import archive_sampler_results

ROOT=Path(__file__).resolve().parent
RUN=ROOT/'results_cuprate_2d/hardware_readout_cz_folding_3x3_2026-09-06'
ACCOUNT='qiskit-runtime-q9'; BACKEND='ibm_phoenix'; CAP=5
PROTOCOL=ROOT/'HARDWARE_READOUT_CZ_PROTOCOL.md'
SOURCES=['run_hardware_readout_cz_once.py','analyze_hardware_readout_cz.py',
    'test_hardware_readout_cz.py','HARDWARE_READOUT_CZ_PROTOCOL.md',
    'run_cuprate_2d_tflo_once.py','preflight_cuprate_2d_tflo_budget.py',
    'aer_readout_tflo_zne.py']+r.b.SOURCES

def require(value,message):
    if not value: raise ValueError(message)

def embed(circuit,layout,width=120):
    require(circuit.num_qubits==circuit.num_clbits==len(layout)==18,'Wrong local widths')
    require(len(set(layout))==18 and min(layout)>=0 and max(layout)<width,'Invalid layout')
    out=QuantumCircuit(QuantumRegister(width,'q'),ClassicalRegister(18,'meas'))
    out.global_phase=circuit.global_phase
    for item in circuit.data:
        require(item.operation.name in r.a.NATIVE|{'measure'},'Unsupported local operation')
        out.append(item.operation.copy(),[layout[circuit.find_bit(q).index] for q in item.qubits],
            [circuit.find_bit(c).index for c in item.clbits])
    restored=r.a.remap_measured(out,layout)
    require(r.b.z.instruction_rows(restored)==r.b.z.instruction_rows(circuit),'Embedding changed circuit')
    require(abs(complex(np.exp(1j*float(out.global_phase-circuit.global_phase)))-1)<1e-13,'Phase changed')
    return out

def records(parent):
    out=[{'setting_id':f'readout_all{state}','twirl_id':0,'role':'calibration','state':state,
        'shots':64,'readout_mask_little_endian':[0]*18} for state in range(2)]
    main=[]
    for g,n in enumerate((64,7,14)):
        for t in range(8):
            main.append({'setting_id':f'U8_T04_factor{g+1}','twirl_id':t,'role':'target',
                'factor':g+1,'shots':n,'readout_mask_little_endian':parent['records'][t]['readout_mask_little_endian'],
                'source_qpy':str((r.PARENT/'circuits'/f'{g}_{t}.qpy').relative_to(ROOT))})
    rng=np.random.default_rng(2026090607)
    out.extend(main[i] for i in rng.permutation(24))
    validate_records(out)
    return out

def validate_records(rows):
    require(len(rows)==26 and sum(x['shots'] for x in rows)==808,'Wrong total exposure')
    require(len({(x['setting_id'],x['twirl_id']) for x in rows})==26,'Duplicate record')
    require([(x['state'],x['shots']) for x in rows if x['role']=='calibration']==[(0,64),(1,64)],'Wrong calibration')
    for f,n in enumerate((64,7,14),1):
        chosen=[x for x in rows if x.get('factor')==f]
        require(sorted(x['twirl_id'] for x in chosen)==list(range(8)),'Missing twirl')
        require(all(x['shots']==n for x in chosen),'Changed allocation')

def prepare(confirmed=False):
    if not confirmed: raise PermissionError('Literal confirmation required')
    if RUN.exists(): raise FileExistsError('Prepared or attempted already; inspect/retrieve only')
    parent_count=r.stats.verify_files(r.PARENT,'final_archive_sha256.json')
    parent=r.a.read(r.PARENT/'plan.json')
    rows=records(parent)
    dependencies=list(dict.fromkeys(SOURCES))
    inputs=[ROOT/n for n in dependencies]+[r.PARENT/'plan.json',r.PARENT/'final_archive_sha256.json',
        safe.PLAN/'submission_attempt.json',r.a.PLAN/'submission_attempt.json']
    inputs += [ROOT/x['source_qpy'] for x in rows if x['role']=='target']
    tag='ro-cz-3x3-'+uuid.uuid4().hex[:16]
    plan={'schema':'hardware-readout-cz-v1','backend':BACKEND,'account_name':ACCOUNT,'cap_seconds':CAP,
        'authorization':'User requested hardware runs with readout + ZNE CZ folding; begin with one max5s job, no retries.',
        'authorized_one_new_job':True,'automatic_retry':False,'tag':tag,'layout':parent['layout'],
        'target':parent['setting'],'records':rows,'total_new_shots':808,'main_arm_shots':512,
        'protocol_sha256':safe.digest(PROTOCOL),'created_unix':time.time(),
        'parent_files_verified':parent_count,'source_sha256':{n:safe.digest(ROOT/n) for n in dependencies},
        'input_sha256':{str(p.relative_to(ROOT)):safe.digest(p) for p in inputs}}
    log=io.StringIO()
    tests=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('test_hardware_readout_cz'))
    require(tests.wasSuccessful(),log.getvalue())
    # All fail-fast tests occur before the directory/authorization intent is frozen.
    RUN.mkdir(parents=True)
    (RUN/'bound_inputs').mkdir(); (RUN/'source_snapshot').mkdir()
    safe.exclusive_json(RUN/'plan.json',plan)
    plan_hash=safe.digest(RUN/'plan.json')
    checks=[]
    for index,rec in enumerate(rows):
        if rec['role']=='calibration':
            local=QuantumCircuit(QuantumRegister(18,'q'),ClassicalRegister(18,'meas'))
            if rec['state']: local.x(range(18))
            local.measure(range(18),range(18))
            require(local.count_ops().get('cz',0)==0,'Calibration has entanglers')
        else:
            with (ROOT/rec['source_qpy']).open('rb') as f: local=qpy.load(f)[0]
            require(local.count_ops().get('cz')==1008*rec['factor'],'CZ fold changed')
            p,norm,sector=r.a.exact_paulis(local,rec['readout_mask_little_endian'])
            err=float(np.max(np.abs(p-parent['setting']['reference'])))
            require(err<1e-9 and abs(norm-1)<1e-9 and sector<1e-9,'Noise-off verification failed')
            checks.append({'record_index':index,'factor':rec['factor'],'twirl':rec['twirl_id'],
                'max_error':err,'norm':norm,'outside_sector':sector,'cz':local.count_ops()['cz']})
        circuit=embed(local,plan['layout'])
        circuit.metadata={'setting_id':rec['setting_id'],'twirl_id':rec['twirl_id'],
            'readout_mask_little_endian':rec['readout_mask_little_endian'],
            'hardware_rocz_index':index,'hardware_rocz_plan_sha256':plan_hash,'hardware_rocz_tag':tag}
        path=RUN/'bound_inputs'/f'circuit_{index:03d}.qpy'
        with path.open('xb') as f: qpy.dump(circuit,f)
        with path.open('rb') as f: require(qpy.load(f)[0]==circuit,'QPY round trip failed')
        if index%6==0: print(json.dumps({'prepared_circuits':index+1,'total':26}),flush=True)
    for name in dependencies: shutil.copyfile(ROOT/name,RUN/'source_snapshot'/name)
    (RUN/'unit_tests.txt').write_text(log.getvalue(),encoding='utf-8')
    safe.exclusive_json(RUN/'local_verification.json',{'tests':tests.testsRun,'noise_off_checks':checks,'qpy_roundtrips':26})
    safe.exclusive_json(RUN/'frozen_inputs_sha256.json',{str(p.relative_to(RUN)):safe.digest(p)
        for p in RUN.rglob('*') if p.is_file()})
    print(json.dumps({'stage':'PREPARED_NOT_SUBMITTED','shots':808,'circuits':26,'cap':5,
        'max_noise_off_error':max(x['max_error'] for x in checks),'tag':tag}),flush=True)

def frozen():
    r.stats.verify_files(RUN,'frozen_inputs_sha256.json')
    plan=safe.read(RUN/'plan.json')
    require(plan['backend']==BACKEND and plan['cap_seconds']==CAP and plan['authorized_one_new_job'],'Wrong authority')
    require(plan['automatic_retry'] is False,'Retry not authorized')
    validate_records(plan['records'])
    for name,h in plan['input_sha256'].items(): require(safe.digest(ROOT/name)==h,'Frozen dependency changed')
    pubs=[]
    for i,rec in enumerate(plan['records']):
        with (RUN/'bound_inputs'/f'circuit_{i:03d}.qpy').open('rb') as f: circuit=qpy.load(f)[0]
        pubs.append(SamplerPub.coerce((circuit,None,rec['shots'])))
    return plan,pubs

def options_for(backend,tag):
    options={'max_execution_time':CAP,'default_shots':64,
        'execution':{'init_qubits':True,'rep_delay':float(backend.default_rep_delay),'meas_type':'classified'},
        'twirling':{'enable_gates':False,'enable_measure':False},'dynamical_decoupling':{'enable':False},
        'environment':{'job_tags':['2d-cuprate','readout-cz-folding',tag]}}
    SamplerOptions(**options)
    return options

def live_gate(plan,pubs):
    service=safe.safe_provider('IBM authentication',QiskitRuntimeService,name=ACCOUNT)
    backend=safe.safe_provider('IBM backend',service.backend,BACKEND)
    status=safe.safe_provider('IBM status',backend.status)
    require(status.operational and backend.num_qubits==120,'Backend unavailable or changed')
    properties=safe.safe_provider('IBM properties',backend.properties)
    require(not set(plan['layout']).intersection(properties.faulty_qubits()),'Faulty selected qubit')
    safe.safe_provider('ISA validation',validate_isa_circuits,[p.circuit for p in pubs],backend.target)
    timing=[]
    target=backend.target
    reset=max(float(target['reset'][(q,)].duration) for q in plan['layout'])
    for p in pubs:
        safe.safe_provider('Faulty gate validation',backend.check_faulty,p.circuit)
        sdk=float(p.circuit.estimate_duration(target)); manual=wire_time(p.circuit,target)
        require(abs(sdk-manual)<1e-10,'Timing methods disagree')
        aligned=wire_time(p.circuit,target,aligned=True)
        require(aligned>=manual-1e-12,'Alignment shortened circuit')
        timing.append({'shots':p.shots,'duration':sdk,'aligned_duration':aligned,
            'shot_execution_seconds':p.shots*(aligned+reset+backend.default_rep_delay)})
    execution=sum(x['shot_execution_seconds'] for x in timing)
    require(0<execution and 4+execution<CAP,'Two-subjob estimate exceeds cap')
    fingerprint=hashlib.sha256(str(service.active_account().get('instance','')).encode()).hexdigest()
    options=options_for(backend,plan['tag'])
    report={'status':'LIVE_PREFLIGHT_PASS_NOT_SUBMITTED','checked_unix':time.time(),'backend':BACKEND,
        'instance_sha256':fingerprint,'pending_jobs':status.pending_jobs,'options':options,
        'execution_seconds':execution,'one_subjob_estimate':2+execution,'two_subjob_estimate':4+execution,
        'three_subjob_estimate':6+execution,'subjob_count_known':False,'cost_is_estimate_not_guarantee':True,
        'all26_ISA_and_fault_checks_pass':True,'reset_seconds':reset,'timing_by_pub':timing,
        'plan_sha256':safe.digest(RUN/'plan.json'),'properties_updated':str(properties.last_update_date)}
    return service,backend,properties,report

def preflight():
    if (RUN/'submission_attempt.json').exists(): raise FileExistsError('Already attempted')
    plan,pubs=frozen()
    service,backend,properties,report=live_gate(plan,pubs)
    safe.exclusive_json(RUN/'live_preflight.json',report)
    safe.exclusive_json(RUN/'live_backend_properties.json',properties.to_dict())
    safe.exclusive_json(RUN/'preflight_sha256.json',{n:safe.digest(RUN/n) for n in ['live_preflight.json','live_backend_properties.json']})
    print(json.dumps({k:report[k] for k in ['status','pending_jobs','execution_seconds','one_subjob_estimate','two_subjob_estimate','three_subjob_estimate']}),flush=True)

def dispatch_once(lock,receipt,intent,send):
    require(intent['authorized_one_new_job'] and intent['cap_seconds']==5,'Wrong authorization/cap')
    if Path(receipt).exists(): raise FileExistsError('Already has receipt')
    safe.exclusive_json(lock,{'tag':intent['tag'],'plan_sha256':intent['plan_sha256'],
        'cap_seconds':5,'started_unix':time.time(),'authorization_consumed_on_attempt':True,
        'resubmit_allowed':False})
    try: job=send()
    except Exception as exc:
        safe.save_if_absent(Path(receipt).parent/'dispatch_uncertain.json',{'tag':intent['tag'],
            'error_type':type(exc).__name__,'resubmit_allowed':False})
        raise
    row={'job_id':str(job.job_id()),'backend':BACKEND,'account_name':ACCOUNT,'tag':intent['tag'],
        'plan_sha256':intent['plan_sha256'],'submitted_unix':time.time(),'cap_seconds':5,
        'circuits':26,'shots':808,'automatic_retry':False}
    print(json.dumps(row),flush=True)
    safe.exclusive_json(receipt,row)
    return job

def verify_provider_cap(job):
    meta=safe.safe_provider('Provider cap lookup',job._api_client.job_get,job.job_id())
    report={'job_id':job.job_id(),'expected_cap_seconds':CAP,'provider_cost_field':meta.get('cost'),
        'verified':meta.get('cost')==CAP}
    safe.save_if_absent(RUN/'provider_cap_verification.json',report)
    require(report['verified'],'Provider cap not confirmed; inspect existing job, never resubmit')
    return report

def submit(confirmed=False):
    if not confirmed: raise PermissionError('Literal confirmation required')
    if (RUN/'submission_attempt.json').exists() or (RUN/'job_receipt.json').exists():
        raise FileExistsError('Attempt consumed; recover/retrieve only')
    plan,pubs=frozen(); r.stats.verify_files(RUN,'preflight_sha256.json')
    old=safe.read(RUN/'live_preflight.json')
    service,backend,properties,check=live_gate(plan,pubs)
    require(check['instance_sha256']==old['instance_sha256'],'Instance changed')
    require(check['options']==old['options'],'Approved options changed')
    sampler=safe.safe_provider('Sampler setup',SamplerV2,mode=backend,options=check['options'])
    require(sampler.mode is None and sampler.options.max_execution_time==CAP,'Unexpected session/batch/cap')
    retry=safe.disable_retries(service,backend,sampler)
    safe.exclusive_json(RUN/'dispatch_live_check.json',{**check,**retry})
    intent={**plan,'plan_sha256':safe.digest(RUN/'plan.json')}
    print(json.dumps({'event':'LIVE_GATE_PASSED','two_subjobs_estimate':check['two_subjob_estimate'],
        'cap':CAP,'retries_disabled':True,'shots':808}),flush=True)
    job=dispatch_once(RUN/'submission_attempt.json',RUN/'job_receipt.json',intent,
        lambda:safe.safe_provider('Single authorized Sampler POST',sampler.run,pubs))
    print(json.dumps(verify_provider_cap(job)),flush=True)

def recover():
    if (RUN/'job_receipt.json').exists():
        print(json.dumps(safe.read(RUN/'job_receipt.json')),flush=True); return
    lock=safe.read(RUN/'submission_attempt.json')
    require(lock['plan_sha256']==safe.digest(RUN/'plan.json'),'Lock differs')
    service=safe.safe_provider('Authenticate recovery',QiskitRuntimeService,name=ACCOUNT)
    jobs=safe.safe_provider('Unique-tag recovery',service.jobs,limit=10,backend_name=BACKEND,job_tags=[lock['tag']])
    if len(jobs)!=1:
        print(json.dumps({'tag':lock['tag'],'matches':len(jobs),'resubmit_allowed':False}),flush=True); return
    row={'job_id':jobs[0].job_id(),'backend':BACKEND,'account_name':ACCOUNT,'tag':lock['tag'],
        'plan_sha256':lock['plan_sha256'],'cap_seconds':5,'shots':808,'circuits':26,'recovered':True,'automatic_retry':False}
    safe.exclusive_json(RUN/'job_receipt.json',row)
    print(json.dumps(row),flush=True); verify_provider_cap(jobs[0])

def retrieve():
    receipt=safe.read(RUN/'job_receipt.json')
    require(receipt['plan_sha256']==safe.digest(RUN/'plan.json'),'Receipt mismatch')
    service=safe.safe_provider('Authenticate retrieve',QiskitRuntimeService,name=ACCOUNT)
    job=safe.safe_provider('Existing job lookup',service.job,receipt['job_id'])
    status=safe.safe_provider('Job status',job.status)
    status=str(getattr(status,'name',status))
    row={'job_id':receipt['job_id'],'status':status,'checked_unix':time.time()}
    with (RUN/'status_history.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(row)+'\n')
    print(json.dumps(row),flush=True); verify_provider_cap(job)
    if status not in ('DONE','ERROR','CANCELLED','CANCELED'): return
    metrics=safe.safe_provider('Job metrics',job.metrics)
    safe.save_if_absent(RUN/'provider_metrics.json',metrics)
    if status!='DONE':
        safe.save_if_absent(RUN/'FAILED.json',{**row,'usage':metrics.get('usage'),'resubmit_allowed':False}); return
    plan,expected=frozen()
    inputs=safe.safe_provider('Actual provider inputs',lambda:job.inputs)
    actual=[SamplerPub.coerce(p) for p in inputs['pubs']]
    require(len(actual)==len(expected)==26,'Wrong provider PUB count')
    folder=RUN/'provider_inputs'; folder.mkdir(exist_ok=True)
    for i,(received,wanted) in enumerate(zip(actual,expected)):
        require(received.shape==wanted.shape==() and received.shots==wanted.shots,'Changed provider shots')
        require(received.circuit==wanted.circuit,'Changed provider circuit')
        path=folder/f'circuit_{i:03d}.qpy'
        if not path.exists():
            with path.open('xb') as f: qpy.dump(received.circuit,f)
        with path.open('rb') as f: require(qpy.load(f)[0]==wanted.circuit,'Provider QPY mismatch')
    safe.save_if_absent(folder/'options.json',{k:v for k,v in inputs.items() if k!='pubs'})
    result=safe.safe_provider('Completed result',job.result)
    require(len(result)==26,'Incomplete provider result')
    safe.save_if_absent(RUN/'provider_result_complete.json',result)
    for i,(pub,rec) in enumerate(zip(result,plan['records'])):
        meta=pub.metadata.get('circuit_metadata',{})
        require(meta.get('hardware_rocz_index')==i and meta.get('hardware_rocz_plan_sha256')==receipt['plan_sha256'],'Wrong result order')
        require(meta.get('setting_id')==rec['setting_id'] and meta.get('twirl_id')==rec['twirl_id'],'Wrong result provenance')
    raw=RUN/'raw_bitstrings.json'
    if not raw.exists(): archive_sampler_results(raw,result,plan['records'],job_id=receipt['job_id'],width=18)
    require(sum(len(x['bitstrings']) for x in safe.read(raw)['records'])==808,'Incomplete raw shots')
    verified={'status':'DONE_ARCHIVED_VERIFIED','job_id':receipt['job_id'],'shots':808,'all26_provider_circuits_match':True,
        'all26_result_metadata_match':True,'usage':metrics.get('usage'),'max_execution_time_verified':5}
    safe.save_if_absent(RUN/'retrieval_verification.json',verified)
    safe.save_if_absent(RUN/'hardware_archive_sha256.json',{str(p.relative_to(RUN)):safe.digest(p)
        for p in RUN.rglob('*') if p.is_file() and p.name!='status_history.jsonl'})
    print(json.dumps(verified),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','preflight','submit','recover','retrieve'])
    parser.add_argument('--confirm-one-job-max-5s',action='store_true')
    args=parser.parse_args(); logging.disable(logging.CRITICAL)
    try:
        if args.action in ('prepare','submit'): globals()[args.action](args.confirm_one_job_max_5s)
        else: globals()[args.action]()
    except Exception as exc:
        print(json.dumps({'action':args.action,'error_type':type(exc).__name__,'automatic_resubmission':False}),flush=True)
        raise SystemExit(1) from None
