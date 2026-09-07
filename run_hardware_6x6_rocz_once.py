"""Exactly one newly authorized readout + CZ-folding hardware pilot, cap15s, 72 modes."""
import argparse
import ast
from dataclasses import asdict
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
import benchmark_fermionic_6x6_mps as benchmark
import aer_cuprate_cz_zne as folding
from cuprate_2d_fermionic_mapping import build_network
from preflight_cuprate_2d_tflo_budget import wire_time, WEIGHTS
from cuprate_2d_tflo import archive_sampler_results, compile_template, explicit_twirl, embed_measurement

ROOT=Path(__file__).resolve().parent
RUN=ROOT/'results_cuprate_2d/hardware_readout_cz_folding_6x6_2026-09-06'
ACCOUNT='qiskit-runtime-q9'; BACKEND='ibm_phoenix'; CAP=15
PROTOCOL=ROOT/'HARDWARE_6X6_READOUT_CZ_PROTOCOL.md'
MAPPING=ROOT/'results_cuprate_2d/fermionic_mapping_2026-09-05/steps2/plan.json'
CLASSICAL=ROOT/'results_cuprate_2d/classical_full_6x6_mps_T04_v1'
WIDTH=72; SHOTS=512; TOTAL=13312; BASE_CZ=15400

def require(value,message):
    if not value: raise ValueError(message)

def verify_files(root,manifest):
    for name,h in safe.read(root/manifest).items():
        p=(root/name).resolve()
        require(p.is_relative_to(root.resolve()) and safe.digest(p)==h,'Frozen file changed')

def dependencies():
    pending=['run_hardware_6x6_rocz_once.py','analyze_hardware_6x6_rocz.py','test_hardware_6x6_rocz.py']
    found=set()
    while pending:
        name=pending.pop()
        if name in found: continue
        found.add(name)
        for node in ast.walk(ast.parse((ROOT/name).read_text())):
            modules=[a.name for a in node.names] if isinstance(node,ast.Import) else (
                [node.module] if isinstance(node,ast.ImportFrom) and node.module else [])
            for module in modules:
                candidate=module.split('.')[0]+'.py'
                if (ROOT/candidate).is_file() and candidate not in found: pending.append(candidate)
    return sorted(found)+[PROTOCOL.name]

def records(masks):
    require(np.asarray(masks).shape==(8,WIDTH),'Wrong mask dimensions')
    out=[{'setting_id':f'readout_all{s}','twirl_id':0,'role':'calibration','state':s,
        'shots':SHOTS,'readout_mask_little_endian':[0]*WIDTH} for s in range(2)]
    main=[{'setting_id':f'U8_T04_factor{f}','twirl_id':t,'role':'target','factor':f,
        'shots':SHOTS,'twirl_seed':202609040+t,'fold_seed':2026300000+t,
        'readout_mask_little_endian':list(masks[t])} for f in (1,2,3) for t in range(8)]
    rng=np.random.default_rng(2026090615)
    out.extend(main[int(i)] for i in rng.permutation(24))
    validate_records(out)
    return out

def validate_records(rows):
    require(len(rows)==26 and sum(x['shots'] for x in rows)==TOTAL,'Wrong exposure')
    require(len({(x['setting_id'],x['twirl_id']) for x in rows})==26,'Duplicate record')
    require([(x['state'],x['shots']) for x in rows if x['role']=='calibration']==[(0,512),(1,512)],'Wrong calibration')
    for f in (1,2,3):
        chosen=[x for x in rows if x.get('factor')==f]
        require(sorted(x['twirl_id'] for x in chosen)==list(range(8)),'Missing twirl')
        require(all(x['shots']==512 and x['role']=='target' for x in chosen),'Allocation changed')
    for rec in rows:
        mask=np.asarray(rec['readout_mask_little_endian'])
        require(mask.shape==(WIDTH,) and np.all((mask==0)|(mask==1)),'Invalid mask')
    for t in range(8):
        masks=[x['readout_mask_little_endian'] for x in rows if x['role']=='target' and x['twirl_id']==t]
        require(all(m==masks[0] for m in masks),'Factor masks differ')

def embed(local,layout):
    require(local.num_qubits==WIDTH and local.num_clbits==0,'Wrong local width')
    require(all(i.operation.name in {'rz','sx','x','cz'} for i in local.data),'Wrong basis')
    out=embed_measurement(local,layout,120)
    inverse={q:i for i,q in enumerate(layout)}
    rows=[(i.operation.name,tuple(inverse[out.find_bit(q).index] for q in i.qubits),
        (),repr(i.operation.params)) for i in out.data[:-WIDTH]]
    require(rows==folding.instruction_rows(local),'Embedding changed instruction order')
    measurements=[(out.find_bit(i.qubits[0]).index,out.find_bit(i.clbits[0]).index)
        for i in out.data[-WIDTH:] if i.operation.name=='measure']
    require(measurements==list(zip(layout,range(WIDTH))),'Measurement mapping changed')
    require(abs(np.exp(1j*float(out.global_phase-local.global_phase))-1)<1e-12,'Phase changed')
    return out

def prepare(confirmed=False):
    if not confirmed: raise PermissionError('Literal confirmation required')
    if RUN.exists(): raise FileExistsError('Prepared already; inspect only')
    log=io.StringIO()
    tests=unittest.TextTestRunner(stream=log,verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromName('test_hardware_6x6_rocz'))
    require(tests.wasSuccessful(),log.getvalue())
    cfg=benchmark.cfg_for(6)
    require((cfg.qubits,cfg.steps,cfg.dt,cfg.u_over_t,cfg.t_prime_over_t)==(72,2,.2,8,-.25),'Physics changed')
    tick=time.perf_counter()
    native=compile_template(build_network(cfg))
    require(native.num_parameters==0 and native.count_ops().get('cz')==BASE_CZ,'Native circuit changed')
    print(json.dumps({'stage':'COMPILED_72_MODES','cz':BASE_CZ,'depth':native.depth()}),flush=True)
    twirled=[explicit_twirl(native,202609040+t) for t in range(8)]
    rows=records([m.tolist() for _,m in twirled])
    sources=dependencies()
    inputs=[ROOT/n for n in sources]+[MAPPING,CLASSICAL/'plan.json',CLASSICAL/'summary.json']
    require(all(p.is_file() for p in inputs),'Missing provenance')
    layout=safe.read(MAPPING)['initial_layout']
    require(len(layout)==len(set(layout))==72,'Invalid layout')
    tag='ro-cz-6x6-'+uuid.uuid4().hex[:16]
    plan={'schema':'hardware-6x6-rocz-v1','backend':BACKEND,'account_name':ACCOUNT,
        'cap_seconds':CAP,'authorized_one_new_job':True,'automatic_retry':False,
        'authorization':'User explicitly approved one 15 QPU-second job; no automatic retry.',
        'tag':tag,'layout':layout,'config':asdict(cfg),'total_time':.4,
        'records':rows,'total_new_shots':TOTAL,'shots_per_factor':4096,'calibration_shots':1024,
        'linear_zne_weights':[4/3,1/3,-2/3],'bootstrap_replicates':2000,'bootstrap_seed':2026090616,
        'classical_reference_certified':False,'new_exact_72q_statevector':False,
        'input_sha256':{str(p.relative_to(ROOT)):safe.digest(p) for p in inputs},'created_unix':time.time()}
    RUN.mkdir(parents=True); (RUN/'bound_inputs').mkdir(); (RUN/'source_snapshot').mkdir()
    safe.exclusive_json(RUN/'plan.json',plan); ph=safe.digest(RUN/'plan.json')
    with (RUN/'native_template.qpy').open('xb') as f: qpy.dump(native,f)
    checks=[]
    for index,rec in enumerate(rows):
        if rec['role']=='calibration':
            local=QuantumCircuit(WIDTH)
            if rec['state']: local.x(range(WIDTH))
            audit={'calibration_state':rec['state']}
        else:
            local,audit=folding.fold_cz(twirled[rec['twirl_id']][0],rec['factor'],rec['fold_seed'])
            require(local.count_ops().get('cz')==BASE_CZ*rec['factor'],'Fold count changed')
        circuit=embed(local,layout)
        circuit.metadata={'setting_id':rec['setting_id'],'twirl_id':rec['twirl_id'],
            'readout_mask_little_endian':rec['readout_mask_little_endian'],
            'hardware_rocz_index':index,'hardware_rocz_plan_sha256':ph,'hardware_rocz_tag':tag}
        path=RUN/'bound_inputs'/f'circuit_{index:03d}.qpy'
        with path.open('xb') as f: qpy.dump(circuit,f)
        with path.open('rb') as f: require(qpy.load(f)[0]==circuit,'QPY roundtrip failed')
        checks.append({'index':index,'audit':audit,'ops':dict(circuit.count_ops()),'depth':circuit.depth()})
        print(json.dumps({'prepared':index+1,'total':26}),flush=True)
    for name in sources: shutil.copyfile(ROOT/name,RUN/'source_snapshot'/name)
    (RUN/'unit_tests.txt').write_text(log.getvalue(),encoding='utf-8')
    safe.exclusive_json(RUN/'local_verification.json',{'tests':tests.testsRun,
        'small_system_unitary_checks_pass':True,'full72_exact_simulation_performed':False,
        'structural_fold_and_embedding_checks':checks,'qpy_roundtrips':26,
        'local_prepare_seconds':time.perf_counter()-tick})
    safe.exclusive_json(RUN/'frozen_inputs_sha256.json',{str(p.relative_to(RUN)):safe.digest(p)
        for p in RUN.rglob('*') if p.is_file()})
    print(json.dumps({'stage':'PREPARED_NOT_SUBMITTED','shots':TOTAL,'circuits':26,'cap':CAP,'tag':tag}),flush=True)

def frozen():
    verify_files(RUN,'frozen_inputs_sha256.json')
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
    options={'max_execution_time':CAP,'default_shots':512,
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
    raw_usage=safe.safe_provider('IBM usage',service.usage)
    usage={k:float(raw_usage[k]) for k in ('usage_limit_seconds','usage_consumed_seconds','usage_remaining_seconds')
        if isinstance(raw_usage.get(k),(int,float)) and not isinstance(raw_usage.get(k),bool)}
    require(usage.get('usage_remaining_seconds',0)>=CAP,'Insufficient or unknown remaining budget')
    low_level=np.zeros(120,dtype=np.int64)
    target=backend.target
    require(backend.rep_delay_range[0]<=backend.default_rep_delay<=backend.rep_delay_range[1],'Invalid rep delay')
    reset=max(float(target['reset'][(q,)].duration) for q in plan['layout'])
    for p in pubs:
        safe.safe_provider('Faulty gate validation',backend.check_faulty,p.circuit)
        sdk=float(p.circuit.estimate_duration(target)); manual=wire_time(p.circuit,target)
        require(abs(sdk-manual)<1e-10,'Timing methods disagree')
        aligned=wire_time(p.circuit,target,aligned=True)
        require(aligned>=manual-1e-12,'Alignment shortened circuit')
        for item in p.circuit.data:
            wires=[p.circuit.find_bit(q).index for q in item.qubits]
            low_level[wires]+=WEIGHTS[item.operation.name]
        timing.append({'shots':p.shots,'duration':sdk,'aligned_duration':aligned,
            'shot_execution_seconds':p.shots*(aligned+reset+backend.default_rep_delay)})
    low_level+=50*len(pubs)
    require(max(low_level)<26_800_000,'Instruction memory exceeded')
    execution=sum(x['shot_execution_seconds'] for x in timing)
    require(0<execution and 12+execution<CAP,'Six-subjob planning scenario exceeds cap')
    fingerprint=hashlib.sha256(str(service.active_account().get('instance','')).encode()).hexdigest()
    options=options_for(backend,plan['tag'])
    report={'status':'LIVE_PREFLIGHT_PASS_NOT_SUBMITTED','checked_unix':time.time(),'backend':BACKEND,
        'instance_sha256':fingerprint,'pending_jobs':status.pending_jobs,'options':options,
        'execution_seconds':execution,'one_subjob_estimate':2+execution,'two_subjob_estimate':4+execution,
        'three_subjob_estimate':6+execution,'six_subjob_estimate':12+execution,'subjob_count_known':False,'cost_is_estimate_not_guarantee':True,
        'all26_ISA_and_fault_checks_pass':True,'reset_seconds':reset,'timing_by_pub':timing,
        'plan_sha256':safe.digest(RUN/'plan.json'),'properties_updated':str(properties.last_update_date), 'usage':usage,
        'instruction_memory_max_per_wire':int(max(low_level))}
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
    require(intent['authorized_one_new_job'] and intent['cap_seconds']==15,'Wrong authorization/cap')
    if Path(receipt).exists(): raise FileExistsError('Already has receipt')
    safe.exclusive_json(lock,{'tag':intent['tag'],'plan_sha256':intent['plan_sha256'],
        'cap_seconds':CAP,'started_unix':time.time(),'authorization_consumed_on_attempt':True,
        'resubmit_allowed':False})
    try: job=send()
    except Exception as exc:
        safe.save_if_absent(Path(receipt).parent/'dispatch_uncertain.json',{'tag':intent['tag'],
            'error_type':type(exc).__name__,'resubmit_allowed':False})
        raise
    row={'job_id':str(job.job_id()),'backend':BACKEND,'account_name':ACCOUNT,'tag':intent['tag'],
        'plan_sha256':intent['plan_sha256'],'submitted_unix':time.time(),'cap_seconds':CAP,
        'circuits':26,'shots':TOTAL,'automatic_retry':False}
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
    plan,pubs=frozen(); verify_files(RUN,'preflight_sha256.json')
    old=safe.read(RUN/'live_preflight.json')
    service,backend,properties,check=live_gate(plan,pubs)
    require(check['instance_sha256']==old['instance_sha256'],'Instance changed')
    require(check['options']==old['options'],'Approved options changed')
    sampler=safe.safe_provider('Sampler setup',SamplerV2,mode=backend,options=check['options'])
    require(sampler.mode is None and sampler.options.max_execution_time==CAP,'Unexpected session/batch/cap')
    retry=safe.disable_retries(service,backend,sampler)
    safe.exclusive_json(RUN/'dispatch_live_check.json',{**check,**retry})
    intent={**plan,'plan_sha256':safe.digest(RUN/'plan.json')}
    print(json.dumps({'event':'LIVE_GATE_PASSED','six_subjobs_estimate':check['six_subjob_estimate'],
        'cap':CAP,'retries_disabled':True,'shots':TOTAL}),flush=True)
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
        'plan_sha256':lock['plan_sha256'],'cap_seconds':CAP,'shots':TOTAL,'circuits':26,'recovered':True,'automatic_retry':False}
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
    if not raw.exists(): archive_sampler_results(raw,result,plan['records'],job_id=receipt['job_id'],width=WIDTH)
    require(sum(len(x['bitstrings']) for x in safe.read(raw)['records'])==TOTAL,'Incomplete raw shots')
    verified={'status':'DONE_ARCHIVED_VERIFIED','job_id':receipt['job_id'],'shots':TOTAL,'all26_provider_circuits_match':True,
        'all26_result_metadata_match':True,'usage':metrics.get('usage'),'max_execution_time_verified':CAP}
    safe.save_if_absent(RUN/'retrieval_verification.json',verified)
    safe.save_if_absent(RUN/'hardware_archive_sha256.json',{str(p.relative_to(RUN)):safe.digest(p)
        for p in RUN.rglob('*') if p.is_file() and p.name!='status_history.jsonl'})
    print(json.dumps(verified),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','preflight','submit','recover','retrieve'])
    parser.add_argument('--confirm-one-job-max-15s',action='store_true')
    args=parser.parse_args(); logging.disable(logging.CRITICAL)
    try:
        if args.action in ('prepare','submit'): globals()[args.action](args.confirm_one_job_max_15s)
        else: globals()[args.action]()
    except Exception as exc:
        print(json.dumps({'action':args.action,'error_type':type(exc).__name__,'automatic_resubmission':False}),flush=True)
        raise SystemExit(1) from None


