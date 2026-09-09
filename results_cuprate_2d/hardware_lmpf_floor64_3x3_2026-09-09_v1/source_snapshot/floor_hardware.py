"""One newly authorized3x3 floor64 job. Frozen20 PUBs,3072 shots, hard cap5s."""
from pathlib import Path
import argparse,hashlib,io,json,logging,math,shutil,sys,time,unittest,uuid
import numpy as np
from qiskit import qpy
from qiskit.primitives.containers import SamplerPub
from qiskit_ibm_runtime import QiskitRuntimeService,SamplerV2
from qiskit_ibm_runtime.options import SamplerOptions
from qiskit_ibm_runtime.utils.validations import validate_isa_circuits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import run_cuprate_2d_tflo_once as safe
from preflight_cuprate_2d_tflo_budget import wire_time
from cuprate_2d_tflo import archive_sampler_results
CANDIDATE=ROOT/'results_cuprate_2d/lmpf_3x3_penalty_floor_2026-09-09_v1'
ARCHIVE=ROOT/'results_cuprate_2d/hardware_readout_cz_folding_3x3_2026-09-06'
RUN=ROOT/'results_cuprate_2d/hardware_lmpf_floor64_3x3_2026-09-09_v1'
LOCK=ROOT/'results_cuprate_2d/hardware_lmpf_floor64_3x3_2026-09-09_attempt.json'
ACCOUNT='qiskit-runtime-q9';BACKEND='ibm_phoenix';CAP=5;TOTAL=3072;REP=1e-6

def require(value,message):
    if not value:raise ValueError(message)

def expected_records():
    rows=[dict(id=f'cal_pre_{s}',role='calibration',state=s,provider_index=s,shots=128) for s in (0,1)]
    for block in range(4):
        for role,f,index,shots in (('shared_factor1',1,25,128),('factor2',2,19,128),
                                  ('baseline_only_factor1',1,25,256),('factor3',3,2,128)):
            rows.append(dict(id=f'block{block}_{role}',role=role,factor=f,provider_index=index,shots=shots))
    return rows+[dict(id=f'cal_post_{s}',role='calibration',state=s,provider_index=s,shots=128) for s in (0,1)]

def validate_draft(draft):
    require(draft['backend']==BACKEND and draft['proposed_max_execution_time_seconds']==5,'Changed backend/cap')
    require(draft['actual_shots_per_folded_factor']==512 and draft['penalty_denominator']==64 and draft['eta']==1,'Changed estimator')
    require(draft['total_union_shots']==TOTAL and draft['calibration_shots']==512 and draft['primary_target_shots']==1536,'Changed budget')
    require(draft['records']==expected_records(),'Changed frozen20 PUB order/roles/shots')
    require(draft['bootstrap_replicates']==10000 and draft['bootstrap_seed']==2026090922,'Changed analysis')
    require(not draft['automatic_retry'],'Retry not authorized')

def circuit_signature(circuit):
    require(circuit.num_parameters==0,'Unbound circuit')
    rows=[]
    for item in circuit.data:
        name=item.operation.name;require(name in ('rz','sx','x','cz','measure'),'Non-native or unexpected operation')
        pars=[float(x) for x in item.operation.params]
        require(np.isfinite(pars).all(),'Nonfinite circuit parameter')
        rows.append([name,[circuit.find_bit(q).index for q in item.qubits],
                     [circuit.find_bit(c).index for c in item.clbits],pars])
    return hashlib.sha256(json.dumps([circuit.num_qubits,circuit.num_clbits,float(circuit.global_phase),rows],
                                  sort_keys=True,allow_nan=False).encode()).hexdigest()

def verify_files(folder,manifest):
    for name,h in safe.read(folder/manifest).items():
        p=(folder/name).resolve();require(p.is_relative_to(folder.resolve()),'Unsafe manifest path')
        require(safe.digest(p)==h,'Changed frozen artifact')

def options(tag):
    obj={'max_execution_time':5,'default_shots':128,
        'execution':{'init_qubits':True,'rep_delay':REP,'meas_type':'classified'},
        'twirling':{'enable_gates':False,'enable_measure':False},
        'dynamical_decoupling':{'enable':False},
        'environment':{'job_tags':['2d-cuprate','lmpf-floor64',tag]}}
    SamplerOptions(**obj)
    return obj

def prepare(confirmed=False):
    if not confirmed:raise PermissionError('Explicit one-job confirmation required')
    require(not RUN.exists() and not LOCK.exists(),'Existing run/attempt: inspect only')
    draft=safe.read(CANDIDATE/'hardware_candidate.json');validate_draft(draft)
    verify_files(CANDIDATE,'sha256.json')
    require(safe.read(CANDIDATE/'verification/verification.json')['status']=='PENALTY_FLOOR_ACTUAL_SHOT_KKT_AUDIT_PASSED','Missing forecast audit')
    archive_plan=safe.read(ARCHIVE/'plan.json');layout=archive_plan['layout']
    require(len(layout)==18 and len(set(layout))==18,'Changed layout')
    rows=[];loaded={};inputs=[CANDIDATE/'hardware_candidate.json',CANDIDATE/'HARDWARE_CANDIDATE.md',
                             CANDIDATE/'verification/verification.json',ARCHIVE/'plan.json',ARCHIVE/'frozen_inputs_sha256.json']
    for index in (0,1,25,19,2):
        path=ARCHIVE/'provider_inputs'/f'circuit_{index:03d}.qpy';bound=ARCHIVE/'bound_inputs'/path.name
        expected=safe.read(ARCHIVE/'frozen_inputs_sha256.json')[f'bound_inputs/{path.name}']
        require(safe.digest(path)==safe.digest(bound)==expected,'Changed source QPY')
        with path.open('rb') as f:group=qpy.load(f)
        require(len(group)==1,'Wrong source QPY count');c=group[0]
        require(c.num_qubits==120 and c.num_clbits==18 and c.cregs[0].name=='meas','Changed registers')
        measurements=[(c.find_bit(x.qubits[0]).index,c.find_bit(x.clbits[0]).index) for x in c.data if x.operation.name=='measure']
        require(sorted(measurements,key=lambda t:t[1])==list(zip(layout,range(18))),'Changed measurement mapping')
        loaded[index]=c;inputs += [path,bound]
    for record in draft['records']:
        source=archive_plan['records'][record['provider_index']];c=loaded[record['provider_index']]
        if record['role']=='calibration':require(source['state']==record['state'] and c.count_ops().get('cz',0)==0,'Wrong calibration')
        else:require(source['twirl_id']==1 and source['factor']==record['factor'] and c.count_ops().get('cz',0)==1008*record['factor'],'Wrong folded circuit')
        rows.append({**record,'setting_id':record['id'],'twirl_id':source['twirl_id'],
            'readout_mask_little_endian':source['readout_mask_little_endian'],
            'original_provider_qpy_sha256':safe.digest(ARCHIVE/'provider_inputs'/f"circuit_{record['provider_index']:03d}.qpy"),
            'physics_signature':circuit_signature(c)})
    sources=[ROOT/'lmpf_2d/floor_hardware.py',ROOT/'test_lmpf_floor_hardware.py',
        ROOT/'run_cuprate_2d_tflo_once.py',ROOT/'preflight_cuprate_2d_tflo_budget.py',ROOT/'cuprate_2d_tflo.py',
        ROOT/'lmpf_2d/single_twirl.py',ROOT/'lmpf_2d/shot_aware.py',ROOT/'lmpf_2d/fit.py',
        ROOT/'lmpf_2d/PLAN_PENALTY_FLOOR.md']
    log=io.StringIO();tests=unittest.TextTestRunner(stream=log,verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromName('test_lmpf_floor_hardware'))
    require(tests.wasSuccessful(),'Offline boundary tests failed')
    tag='lmpf3x3-floor64-'+uuid.uuid4().hex[:16]
    plan={'schema':'authorized-floor64-hardware-v1','backend':BACKEND,'account_name':ACCOUNT,
        'cap_seconds':5,'total_shots':TOTAL,'pubs':20,'penalty_denominator':64,'actual_factor_shots':512,
        'authorization':'User replied Ja to3x3 ibm_phoenix,512 shots per factor,3072 total,maximum5 QPU seconds,after a passing live preflight.',
        'authorized_one_new_job':True,'automatic_retry':False,'tag':tag,'layout':layout,'records':rows,
        'analysis_protocol_sha256':safe.digest(CANDIDATE/'HARDWARE_CANDIDATE.md'),'created_unix':time.time(),
        'source_sha256':{str(p.relative_to(ROOT)):safe.digest(p) for p in sources},
        'input_sha256':{str(p.relative_to(ROOT)):safe.digest(p) for p in inputs},
        'target':archive_plan['target'],'proposed_options':options(tag),'draft':draft}
    RUN.mkdir();(RUN/'bound_inputs').mkdir();(RUN/'source_snapshot').mkdir()
    safe.exclusive_json(RUN/'plan.json',plan);ph=safe.digest(RUN/'plan.json')
    for i,r in enumerate(rows):
        c=loaded[r['provider_index']].copy()
        c.metadata={**(c.metadata or {}),'setting_id':r['setting_id'],'twirl_id':r['twirl_id'],
            'readout_mask_little_endian':r['readout_mask_little_endian'],
            'floor_record_index':i,'floor_record_id':r['id'],'floor_plan_sha256':ph,'floor_job_tag':tag}
        require(circuit_signature(c)==r['physics_signature'],'Physics changed by labeling')
        path=RUN/'bound_inputs'/f'circuit_{i:03d}.qpy'
        with path.open('xb') as f:qpy.dump(c,f)
        with path.open('rb') as f:roundtrip=qpy.load(f)[0]
        require(roundtrip==c and roundtrip.metadata==c.metadata,'QPY roundtrip failed')
        pub=SamplerPub.coerce((c,None,r['shots']));require(pub.shape==() and pub.shots==r['shots'],'Changed PUB exposure')
    for p in sources:shutil.copyfile(p,RUN/'source_snapshot'/p.name)
    shutil.copyfile(CANDIDATE/'HARDWARE_CANDIDATE.md',RUN/'analysis_protocol.md')
    (RUN/'tests.txt').write_text(log.getvalue())
    safe.exclusive_json(RUN/'local_verification.json',{'tests_passed':tests.testsRun,'qpy_roundtrips':20,
        'physics_and_measurement_signatures_verified':True,'shots':TOTAL,'new_qpu_seconds':0})
    safe.exclusive_json(RUN/'frozen_inputs_sha256.json',{str(p.relative_to(RUN)):safe.digest(p) for p in RUN.rglob('*') if p.is_file()})
    print(json.dumps({'status':'PREPARED_NOT_SUBMITTED','tag':tag,'pubs':20,'shots':TOTAL,'cap':5,'tests':tests.testsRun}),flush=True)

def frozen():
    verify_files(RUN,'frozen_inputs_sha256.json');plan=safe.read(RUN/'plan.json')
    require(plan['backend']==BACKEND and plan['cap_seconds']==5 and plan['total_shots']==TOTAL and plan['authorized_one_new_job'],'Changed authority')
    require(not plan['automatic_retry'],'Changed retry policy');validate_draft(plan['draft'])
    for name,h in {**plan['source_sha256'],**plan['input_sha256']}.items():require(safe.digest(ROOT/name)==h,'Frozen dependency changed')
    pubs=[]
    for i,r in enumerate(plan['records']):
        with (RUN/'bound_inputs'/f'circuit_{i:03d}.qpy').open('rb') as f:c=qpy.load(f)[0]
        require(circuit_signature(c)==r['physics_signature'],'Changed bound circuit')
        require(c.metadata['floor_plan_sha256']==safe.digest(RUN/'plan.json') and c.metadata['floor_record_index']==i,'Wrong provenance')
        pubs.append(SamplerPub.coerce((c,None,r['shots'])))
    require(len(pubs)==20 and sum(p.shots for p in pubs)==TOTAL,'Changed exposure')
    return plan,pubs

def quota_summary(raw):
    keys=('usage_limit_seconds','usage_allocation_seconds','usage_consumed_seconds','usage_remaining_seconds')
    result={k:float(raw[k]) for k in keys if isinstance(raw.get(k),(int,float)) and not isinstance(raw[k],bool)}
    require(all(math.isfinite(v) and v>=0 for v in result.values()),'Invalid quota value')
    if 'usage_remaining_seconds' not in result:
        limit=result.get('usage_limit_seconds',result.get('usage_allocation_seconds'));used=result.get('usage_consumed_seconds')
        if limit is not None and used is not None:result['usage_remaining_seconds']=max(0.,limit-used)
    remaining=result.get('usage_remaining_seconds')
    if remaining is not None:require(remaining>=5,'Reported remaining quota below authorized cap')
    return {**result,'remaining_reported':remaining is not None,'unknown_is_not_unlimited':True,'per_job_cap_seconds':5}

def live_gate(plan,pubs):
    service=safe.safe_provider('IBM authentication',QiskitRuntimeService,name=ACCOUNT)
    backend=safe.safe_provider('IBM backend lookup',service.backend,BACKEND)
    status=safe.safe_provider('IBM status',backend.status)
    require(status.operational and backend.num_qubits==120,'Backend unavailable or changed')
    props=safe.safe_provider('IBM properties',backend.properties)
    require(not set(plan['layout']).intersection(props.faulty_qubits()),'Faulty selected qubit')
    target=backend.target
    safe.safe_provider('ISA check',validate_isa_circuits,[p.circuit for p in pubs],target)
    low,high=backend.rep_delay_range;require(low<=REP<=high,'Approved rep_delay not supported')
    quota=quota_summary(safe.safe_provider('IBM usage check',service.usage))
    reset=max(float(target['reset'][(q,)].duration) for q in plan['layout'])
    require(math.isfinite(reset) and reset>=0,'Invalid reset duration')
    timing=[]
    for i,p in enumerate(pubs):
        safe.safe_provider('Faulty gate check',backend.check_faulty,p.circuit)
        sdk=float(p.circuit.estimate_duration(target));manual=wire_time(p.circuit,target)
        require(abs(sdk-manual)<1e-10,'Independent live timing disagrees')
        aligned=wire_time(p.circuit,target,aligned=True)
        require(aligned>=manual-1e-12,'Alignment shortened circuit')
        timing.append({'index':i,'shots':p.shots,'duration':sdk,'aligned_duration':aligned,
            'shot_execution_seconds':p.shots*(aligned+reset+REP)})
    total=sum(r['shot_execution_seconds'] for r in timing)
    require(0<total and 4+total<5,'Two-subjob live estimate exceeds cap')
    fingerprint=hashlib.sha256(str(service.active_account().get('instance','')).encode()).hexdigest()
    report={'status':'LIVE_PREFLIGHT_PASS_NOT_SUBMITTED','backend':BACKEND,'instance_sha256':fingerprint,
        'checked_unix':time.time(),'pending_jobs':status.pending_jobs,'options':options(plan['tag']),
        'usage':quota,'execution_seconds':total,'one_subjob_estimate':2+total,'two_subjob_estimate':4+total,
        'three_subjob_estimate':6+total,'subjob_count_known':False,'cost_is_estimate_not_guarantee':True,
        'all20_ISA_and_fault_checks_pass':True,'reset_seconds':reset,'rep_delay_seconds':REP,
        'timing_by_pub':timing,'properties_updated':str(props.last_update_date),'plan_sha256':safe.digest(RUN/'plan.json')}
    return service,backend,props,report

def preflight():
    require(not LOCK.exists(),'Attempt already consumed')
    plan,pubs=frozen();_,_,props,report=live_gate(plan,pubs)
    safe.exclusive_json(RUN/'live_preflight.json',report)
    safe.exclusive_json(RUN/'live_backend_properties.json',props.to_dict())
    safe.exclusive_json(RUN/'preflight_sha256.json',{n:safe.digest(RUN/n) for n in ('live_preflight.json','live_backend_properties.json')})
    print(json.dumps({k:report[k] for k in ('status','pending_jobs','execution_seconds','two_subjob_estimate','usage')}),flush=True)

def dispatch_once(lock,receipt,intent,send):
    require(intent.get('authorized_one_new_job') is True and intent['cap_seconds']==5 and intent['total_shots']==TOTAL,'Wrong dispatch authority')
    if Path(receipt).exists():raise FileExistsError('Receipt already exists')
    safe.exclusive_json(lock,{'tag':intent['tag'],'plan_sha256':intent['plan_sha256'],'cap_seconds':5,
        'total_shots':TOTAL,'started_unix':time.time(),'authorization_consumed':True,'resubmit_allowed':False})
    try:
        job=send();job_id=str(job.job_id());require(bool(job_id),'Missing job id')
        row={'job_id':job_id,'backend':BACKEND,'account_name':ACCOUNT,'tag':intent['tag'],
            'plan_sha256':intent['plan_sha256'],'cap_seconds':5,'shots':TOTAL,'pubs':20,
            'submitted_unix':time.time(),'automatic_retry':False}
        safe.exclusive_json(receipt,row)
    except Exception as e:
        safe.save_if_absent(Path(receipt).parent/'dispatch_uncertain.json',{'error_type':type(e).__name__,
            'tag':intent['tag'],'resubmit_allowed':False})
        raise
    print(json.dumps(row),flush=True);return job

def provider_cap(job):
    meta=safe.safe_provider('Provider cap lookup',job._api_client.job_get,job.job_id())
    report={'job_id':job.job_id(),'expected_cap_seconds':5,'provider_cost_field':meta.get('cost'),'verified':meta.get('cost')==5}
    safe.save_if_absent(RUN/'provider_cap_verification.json',report)
    require(report['verified'],'Provider cap not confirmed: inspect existing job, never resubmit')
    return report

def submit(confirmed=False):
    if not confirmed:raise PermissionError('Explicit one-job confirmation required')
    require(not LOCK.exists() and not (RUN/'job_receipt.json').exists(),'Attempt consumed: recover/retrieve only')
    plan,pubs=frozen();verify_files(RUN,'preflight_sha256.json')
    old=safe.read(RUN/'live_preflight.json');service,backend,props,check=live_gate(plan,pubs)
    require(check['instance_sha256']==old['instance_sha256'] and check['options']==old['options'],'Instance/options changed')
    sampler=safe.safe_provider('Sampler setup',SamplerV2,mode=backend,options=check['options'])
    require(sampler.mode is None and sampler.options.max_execution_time==5,'Unexpected session/batch/cap')
    retry=safe.disable_retries(service,backend,sampler)
    safe.exclusive_json(RUN/'dispatch_live_check.json',{**check,**retry})
    safe.exclusive_json(RUN/'dispatch_backend_properties.json',props.to_dict())
    print(json.dumps({'event':'LIVE_GATE_PASSED','pubs':20,'shots':TOTAL,'cap_seconds':5,
        'two_subjob_estimate':check['two_subjob_estimate'],'retries_disabled':True}),flush=True)
    job=dispatch_once(LOCK,RUN/'job_receipt.json',{**plan,'plan_sha256':safe.digest(RUN/'plan.json')},
        lambda:safe.safe_provider('Single authorized Sampler POST',sampler.run,pubs))
    print(json.dumps(provider_cap(job)),flush=True)

def recover():
    if (RUN/'job_receipt.json').exists():print(json.dumps(safe.read(RUN/'job_receipt.json')));return
    lock=safe.read(LOCK);require(lock['plan_sha256']==safe.digest(RUN/'plan.json'),'Changed intent')
    service=safe.safe_provider('Recovery authentication',QiskitRuntimeService,name=ACCOUNT)
    jobs=safe.safe_provider('Existing unique-tag lookup',service.jobs,limit=10,backend_name=BACKEND,job_tags=[lock['tag']])
    if len(jobs)!=1:print(json.dumps({'matching_jobs':len(jobs),'tag':lock['tag'],'resubmit_allowed':False}));return
    row={'job_id':jobs[0].job_id(),'backend':BACKEND,'account_name':ACCOUNT,'tag':lock['tag'],
         'plan_sha256':lock['plan_sha256'],'cap_seconds':5,'shots':TOTAL,'pubs':20,'recovered':True,'automatic_retry':False}
    safe.exclusive_json(RUN/'job_receipt.json',row);print(json.dumps(row),flush=True)
    print(json.dumps(provider_cap(jobs[0])),flush=True)

def retrieve():
    receipt=safe.read(RUN/'job_receipt.json');require(receipt['plan_sha256']==safe.digest(RUN/'plan.json'),'Receipt mismatch')
    service=safe.safe_provider('Retrieve authentication',QiskitRuntimeService,name=ACCOUNT)
    job=safe.safe_provider('Existing job lookup',service.job,receipt['job_id'])
    value=safe.safe_provider('Job status',job.status);status=str(getattr(value,'name',value))
    row={'job_id':receipt['job_id'],'status':status,'checked_unix':time.time()}
    with (RUN/'status_history.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
    print(json.dumps(row),flush=True);provider_cap(job)
    if status not in ('DONE','ERROR','CANCELLED','CANCELED'):return
    metrics=safe.safe_provider('Provider metrics',job.metrics);safe.save_if_absent(RUN/'provider_metrics.json',metrics)
    if status!='DONE':
        safe.save_if_absent(RUN/'FAILED.json',{**row,'usage':metrics.get('usage'),'resubmit_allowed':False});return
    plan,expected=frozen();provided=safe.safe_provider('Actual provider inputs',lambda:job.inputs)
    actual=[SamplerPub.coerce(p) for p in provided['pubs']];require(len(actual)==20,'Wrong provider PUB count')
    folder=RUN/'provider_inputs';folder.mkdir(exist_ok=True)
    for i,(received,wanted) in enumerate(zip(actual,expected)):
        require(received.shape==wanted.shape==() and received.shots==wanted.shots,'Provider exposure changed')
        require(circuit_signature(received.circuit)==circuit_signature(wanted.circuit),'Provider circuit changed')
        require(received.circuit.metadata==wanted.circuit.metadata,'Provider metadata changed')
        p=folder/f'circuit_{i:03d}.qpy'
        if not p.exists():
            with p.open('xb') as f:qpy.dump(received.circuit,f)
    safe.save_if_absent(folder/'options.json',{k:v for k,v in provided.items() if k in ('options','version','support_qiskit')})
    result=safe.safe_provider('Completed sampler result',job.result)
    require(len(result)==20,'Incomplete provider result')
    safe.save_if_absent(RUN/'provider_result_complete.json',result)
    for i,(pub,r) in enumerate(zip(result,plan['records'])):
        meta=pub.metadata.get('circuit_metadata',{})
        require(meta.get('floor_record_index')==i and meta.get('floor_record_id')==r['id']
            and meta.get('floor_plan_sha256')==receipt['plan_sha256'],'Wrong result order/provenance')
    if not (RUN/'raw_bitstrings.json').exists():
        archive_sampler_results(RUN/'raw_bitstrings.json',result,plan['records'],job_id=receipt['job_id'],width=18)
    require(sum(len(r['bitstrings']) for r in safe.read(RUN/'raw_bitstrings.json')['records'])==TOTAL,'Missing shots')
    report={'status':'DONE_ARCHIVED_VERIFIED','job_id':receipt['job_id'],'shots':TOTAL,'pubs':20,
        'all_provider_circuits_shots_and_metadata_match':True,'usage':metrics.get('usage'),'verified_cap_seconds':5}
    safe.save_if_absent(RUN/'retrieval_verification.json',report)
    safe.save_if_absent(RUN/'hardware_archive_sha256.json',{str(p.relative_to(RUN)):safe.digest(p) for p in RUN.rglob('*')
        if p.is_file() and p.name not in ('status_history.jsonl','hardware_archive_sha256.json')})
    print(json.dumps(report),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','preflight','submit','recover','retrieve'])
    p.add_argument('--confirm-one-job-max-5s-3072-shots',action='store_true');args=p.parse_args()
    logging.disable(logging.CRITICAL)
    try:
        if args.action in ('prepare','submit'):globals()[args.action](args.confirm_one_job_max_5s_3072_shots)
        else:globals()[args.action]()
    except Exception as e:
        report={'action':args.action,'error_type':type(e).__name__,'safe_label':str(e) if isinstance(e,RuntimeError) else None,
                'automatic_resubmission':False}
        if RUN.exists():safe.save_if_absent(RUN/(args.action+'_failure.json'),report)
        print(json.dumps(report),flush=True);raise SystemExit(1) from None
