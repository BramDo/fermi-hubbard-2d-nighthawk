"""A new, strictly bounded original/compact 6x6 job; old archives are read-only."""
import argparse,ast,gzip,hashlib,io,json,logging,math,platform,shutil,time,uuid
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
from qiskit import qpy,QuantumCircuit
from qiskit.transpiler import PassManager
from qiskit.transpiler.passes import ALAPScheduleAnalysis,ConstrainedReschedule,PadDelay
from qiskit.primitives.containers import SamplerPub
from qiskit_ibm_runtime import QiskitRuntimeService,SamplerV2
from qiskit_ibm_runtime.utils.validations import validate_isa_circuits
import run_tflo_dd6_once as base
import cuprate_2d_tflo_dd6 as m
from tflo_dd6_fast_io import save_checked,qpy_bytes,native_equal
from cuprate_2d_tflo import bind,explicit_twirl,embed_measurement,skeleton,decode_bitstrings
from cuprate_2d_hubbard_pipeline import Cuprate2DConfig
from preflight_cuprate_2d_tflo_budget import WEIGHTS

ROOT=Path(__file__).resolve().parent
OLD=ROOT/'results_cuprate_2d/hardware_tflo_dd6_2026-09-06_v1'
COMPACT=ROOT/'results_cuprate_2d/quantum_compact_tflo_2026-09-07_v1'
RUN=ROOT/'results_cuprate_2d/hardware_compact_tflo_2026-09-07_v1'
LOCK=ROOT/'results_cuprate_2d/hardware_compact_tflo_2026-09-07_attempt.json'
ACCOUNT='qiskit-runtime-q9'; BACKEND='ibm_phoenix'; ARMS=('original','compact')
read=base.read; save=base.save; digest=base.digest; require=base.require; safe=base.safe

def log(stage,**details):
    row=dict(UTC=datetime.now(timezone.utc).isoformat(),stage=stage,**details)
    if RUN.exists():
        with (RUN/'progress.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(row)+'\n')
    print(json.dumps(row),flush=True)

def verify(folder,manifest):
    base.verify(folder,manifest)

def records(layout,masks):
    cals=[]
    for block in ('start','end'):
        for state in (0,1):
            cals.append(dict(setting_id=f'cal{state}_{block}',role='calibration',block=block,
                state=state,arm='shared',dd=False,twirl_id=0,shots=512,width=72,
                physical_layout=layout,readout_mask_little_endian=[0]*72))
    pairs=[(s,t) for s in m.settings() for t in range(4)]
    rng=np.random.default_rng(202609071501); rng.shuffle(pairs); out=[]
    for pair_id,(s,t) in enumerate(pairs):
        arms=list(ARMS); rng.shuffle(arms)
        for arm in arms:
            out.append(dict(setting_id=s['id'],role=s['role'],T=s['T'],U=s['U'],arm=arm,
                pair_id=pair_id,dd=False,twirl_id=t,shots=512,width=72,physical_layout=layout,
                readout_mask_little_endian=list(map(int,masks[t]))))
    return cals[:2]+out+cals[2:]

def validate_records(rows):
    require(len(rows)==76 and sum(r['shots'] for r in rows)==38912,'Exposure changed')
    expected={(s['id'],a,t) for s in m.settings() for a in ARMS for t in range(4)}; seen=set()
    layout=rows[0]['physical_layout']
    require(len(layout)==len(set(layout))==72 and min(layout)>=0 and max(layout)<120,'Layout invalid')
    for r in rows:
        require(r['shots']==512 and r['width']==72 and not r['dd'],'Shot/width/DD scope changed')
        require(r['physical_layout']==layout,'Layout mismatch')
        mask=r['readout_mask_little_endian']; require(len(mask)==72 and set(mask)<={0,1},'Bad readout mask')
        if r['role']=='calibration':
            require(r['arm']=='shared' and r['state'] in (0,1) and not any(mask),'Calibration changed')
        else:
            key=(r['setting_id'],r['arm'],r['twirl_id']); require(key not in seen,'Duplicate setting'); seen.add(key)
            s=next(s for s in m.settings() if s['id']==r['setting_id'])
            require(all(r[k]==s[k] for k in ('role','U','T')),'Changed physics')
    require(seen==expected,'Missing settings')
    require([r['setting_id'] for r in rows[:2]+rows[-2:]]==['cal0_start','cal1_start','cal0_end','cal1_end'],'Calibration order')
    for i in range(2,74,2):
        a,b=rows[i:i+2]
        require({a['arm'],b['arm']}==set(ARMS),'Unpaired arms')
        require(all(a[k]==b[k] for k in ('setting_id','twirl_id','pair_id','readout_mask_little_endian')),'Pair mismatch')

def options(backend,tag):
    opts=base.options(backend,tag)
    opts['environment']['job_tags']=['2d-cuprate','compact-tflo6',tag]
    return opts

def provider():
    s=safe.safe_provider('IBM authentication',QiskitRuntimeService,name=ACCOUNT)
    b=safe.safe_provider('IBM backend',s.backend,BACKEND)
    status=safe.safe_provider('IBM status',b.status); props=safe.safe_provider('IBM properties',b.properties)
    require(b.name==BACKEND and status.operational and b.num_qubits==120,'Backend unavailable')
    require(not props.faulty_qubits() and not props.faulty_gates(),'Fault flags present')
    usage=m.quota(safe.safe_provider('IBM usage',s.usage))
    active=s.active_account().get('instance'); instances=safe.safe_provider('IBM instance type',s.instances)
    plans=[x.get('plan') for x in instances if x.get('crn')==active]
    require(len(plans)==1,'Selected instance ambiguous')
    require(usage['remaining_reported'] or plans[0]=='pay-as-you-go','Allocation unavailable')
    usage.update(selected_plan=plans[0],no_quota_limit_claimed=not usage['remaining_reported'])
    return s,b,props,dict(checked_unix=time.time(),backend=BACKEND,pending_jobs=status.pending_jobs,
        properties_updated=str(props.last_update_date),quota=usage,
        instance_sha256=hashlib.sha256(str(active).encode()).hexdigest())

def source_names():
    pending=[Path(__file__).name,'test_hardware_compact_tflo.py']; found=set()
    while pending:
        name=pending.pop()
        if name in found: continue
        found.add(name)
        for node in ast.walk(ast.parse((ROOT/name).read_text(encoding='utf-8-sig'))):
            mods=[a.name for a in node.names] if isinstance(node,ast.Import) else ([node.module] if isinstance(node,ast.ImportFrom) and node.module else [])
            for mod in mods:
                candidate=mod.split('.')[0]+'.py'
                if (ROOT/candidate).is_file() and candidate not in found: pending.append(candidate)
    return sorted(found)+['HARDWARE_COMPACT_TFLO_PROTOCOL.md']

def check_input(c,rec,index,ph):
    base.check_input(c,rec,index,ph)
    require(not any(i.operation.label==m.DD_LABEL for i in c.data),'Unexpected DD')
    if rec['role']!='calibration': require(c.count_ops().get('cz')==20736,'CZ count changed')

def prepare():
    require(not RUN.exists() and not LOCK.exists(),'Existing preparation/attempt; inspect before resume')
    verify(COMPACT,'delivery_sha256.json')
    require(read(COMPACT/'independent_verification.json')['status']=='PASS','Offline proof not passed')
    prior=read(OLD/'plan.json'); frozen=read(OLD/'frozen_inputs_sha256.json')
    src=OLD/'local_only/parameterized72_blocks.qpy'
    require(digest(src)==frozen[str(src.relative_to(OLD))],'Original template changed')
    cfg=Cuprate2DConfig(**prior['config']); layout=prior['layout72']
    for name,h in read(COMPACT/'plan.json')['input_sha256'].items(): require(digest(ROOT/name)==h,'Offline source changed')
    s,b,props,live=provider(); fp,timing=m.fingerprint(b.target,layout)
    RUN.mkdir()
    for name in ('source_snapshot','templates','bound_inputs'): (RUN/name).mkdir()
    save(RUN/'initial_live_check.json',live); save(RUN/'scheduling_target.json',timing)
    save(RUN/'backend_properties.json',props.to_dict())
    templates={}; masks=[]; schedules=[]
    original=qpy.load(io.BytesIO(src.read_bytes()))[0]
    for t in range(4):
        twirled,mask=explicit_twirl(original,202609061600+t); masks.append(mask.tolist())
        orig=embed_measurement(twirled,layout,120)
        cp=COMPACT/'circuits'/f'physical120_compact_parameterized_twirl{t}.qpy'
        compact=qpy.load(io.BytesIO(cp.read_bytes()))[0]
        require(compact.metadata['readout_mask_little_endian']==mask.tolist(),'Paired mask changed')
        for arm,c in zip(ARMS,(orig,compact)):
            scheduled=PassManager([ALAPScheduleAnalysis(target=b.target),ConstrainedReschedule(target=b.target),PadDelay(target=b.target)]).run(c)
            require(m.wire_sequences(c)[0]==m.wire_sequences(scheduled)[0],'Scheduling changed ideal gates')
            require(c.global_phase==scheduled.global_phase,'Scheduling changed global phase')
            dt,_=m.clocks(scheduled,b.target)
            sdk=float(bind(scheduled,cfg,.4,8.).estimate_duration(b.target,unit='s'))
            require(abs(sdk-dt*b.target.dt)<1e-10,'SDK versus independent clock mismatch')
            templates[arm,t]=scheduled
            # Parameterized QPY roundtrip uses byte equality, not float global phase.
            data=qpy_bytes(scheduled); restored=qpy.load(io.BytesIO(data))[0]
            require(qpy_bytes(restored)==data,'Template QPY roundtrip')
            with (RUN/'templates'/f'{arm}_twirl{t}.qpy').open('xb') as f: f.write(data)
            schedules.append(dict(arm=arm,twirl=t,duration_seconds=sdk,CZ=scheduled.count_ops().get('cz'),
                unscheduled_depth=c.depth(),skeleton_sha256=skeleton(scheduled),DD=False,
                counts=dict(scheduled.count_ops()),gate_order_preserved=True))
            log('template_scheduled',arm=arm,twirl=t,duration_us=sdk*1e6,CZ=20736)
    rows=records(layout,masks); validate_records(rows)
    names=source_names()
    for name in names: shutil.copyfile(ROOT/name,RUN/'source_snapshot'/name)
    plan=dict(schema='original-compact-tflo6-v1',backend=BACKEND,account_name=ACCOUNT,
        cap_seconds=15,authorized_one_new_job=True,automatic_retry=False,
        authorization='2026-09-07 user: Laten we maar een hardware test 6 x6 doen; accepts proposed one original/compact job max15 QPU seconds.',
        tag='compact-tflo6-'+uuid.uuid4().hex[:16],config=prior['config'],layout72=layout,
        settings=m.settings(),arms=list(ARMS),records=rows,total_PUBs=76,total_shots=38912,
        source_sha256={name:digest(ROOT/name) for name in names},timing_fingerprint=fp,
        old_plan_sha256=digest(OLD/'plan.json'),compact_delivery_sha256=digest(COMPACT/'delivery_sha256.json'),
        bootstrap_seed=202609071515,bootstrap_replicates=400,ridge=.001,
        TFLO_time_feature=False,postselection=False,DD=False,
        runtime=dict(python=platform.python_version(),qiskit=base.qiskit.__version__,qiskit_ibm_runtime=base.qiskit_ibm_runtime.__version__),
        created_unix=time.time(),canonical_attempt_marker=str(LOCK.relative_to(ROOT)))
    save(RUN/'plan.json',plan); ph=digest(RUN/'plan.json')
    require(digest(OLD/'references.json')==frozen['references.json'],'Exact U0 references changed')
    shutil.copyfile(OLD/'references.json',RUN/'references.json')
    save(RUN/'scheduling_validation.json',schedules)
    for i,rec in enumerate(rows):
        if rec['role']=='calibration':
            c=QuantumCircuit(72)
            if rec['state']: c.x(range(72))
            c=embed_measurement(c,layout,120)
        else:
            template=templates[rec['arm'],rec['twirl_id']]
            c=bind(template,cfg,rec['T'],rec['U'])
            require(skeleton(c)==skeleton(template),'Binding changed structure')
        c.metadata={**rec,'pilot_index':i,'pilot_plan_sha256':ph,'pilot_tag':plan['tag']}
        check_input(c,rec,i,ph); save_checked(RUN/'bound_inputs'/f'circuit_{i:03d}.qpy',c)
        if i%8==0: log('bound_archived',index=i,total=76)
    save(RUN/'frozen_inputs_sha256.json',{str(p.relative_to(RUN)):digest(p) for p in RUN.rglob('*') if p.is_file() and p.name!='progress.jsonl'})
    log('prepared_not_submitted',PUBs=76,shots=38912,cap=15)

def frozen():
    verify(RUN,'frozen_inputs_sha256.json'); plan=read(RUN/'plan.json'); ph=digest(RUN/'plan.json')
    require(plan['schema']=='original-compact-tflo6-v1' and plan['backend']==BACKEND and plan['account_name']==ACCOUNT,'Wrong plan')
    require(plan['cap_seconds']==15 and plan['authorized_one_new_job'] and not plan['automatic_retry'],'Wrong authority')
    validate_records(plan['records'])
    for name,h in plan['source_sha256'].items(): require(digest(ROOT/name)==h,'Source changed')
    pubs=[]
    for i,rec in enumerate(plan['records']):
        c=qpy.load(io.BytesIO((RUN/'bound_inputs'/f'circuit_{i:03d}.qpy').read_bytes()))[0]
        check_input(c,rec,i,ph); pubs.append(SamplerPub.coerce((c,None,512)))
    return plan,pubs

def budget_now(b,timing):
    rep=float(b.default_rep_delay); require(b.rep_delay_range[0]<=rep<=b.rep_delay_range[1],'Rep delay invalid')
    reset=max(float(b.target['reset'][(q,)].duration) for q in range(120))
    require(math.isfinite(reset) and reset>=0,'Reset invalid')
    require(len(timing)==76 and [r['index'] for r in timing]==list(range(76)),'Timing record mismatch')
    require(all(r['shots']==512 and math.isfinite(r['duration_seconds']) and r['duration_seconds']>0 for r in timing),'Invalid timing')
    budget=m.budget(sum(512*(r['duration_seconds']+rep+reset) for r in timing))
    require(budget['pass'],'Fresh 15s budget rejected')
    return dict(budget=budget,reset_all120_seconds=reset,rep_delay_seconds=rep)

def preflight():
    require(not LOCK.exists() and not (RUN/'live_preflight.json').exists(),'Preflight already exists/attempt consumed')
    plan,pubs=frozen(); s,b,props,report=provider()
    fp,_=m.fingerprint(b.target,plan['layout72']); require(fp==plan['timing_fingerprint'],'Scheduled target changed')
    timing=[]; memory=np.zeros(120,dtype=np.int64)
    for i,pub in enumerate(pubs):
        c=pub.circuit
        safe.safe_provider('ISA validation',validate_isa_circuits,[c],b.target)
        safe.safe_provider('Faulty gate check',b.check_faulty,c)
        dt,_=m.clocks(c,b.target); seconds=float(c.estimate_duration(b.target,unit='s'))
        require(abs(seconds-dt*b.target.dt)<1e-10,'Independent timing mismatch')
        for inst in c.data:
            if inst.operation.name!='barrier': memory[[c.find_bit(q).index for q in inst.qubits]]+=WEIGHTS[inst.operation.name]
        timing.append(dict(index=i,shots=512,duration_seconds=seconds))
        if i%8==0: log('ISA_timing_verified',index=i,total=76)
    memory+=50*76; require(int(max(memory))<26800000,'Instruction memory budget rejected')
    report.update(status='PASS_NOT_SUBMITTED',options=options(b,plan['tag']),timing_fingerprint=fp,
        timing_by_pub=timing,plan_sha256=digest(RUN/'plan.json'),instruction_memory_max_per_wire=int(max(memory)),**budget_now(b,timing))
    report['checked_unix']=time.time()
    save(RUN/'live_preflight.json',report)
    save(RUN/'preflight_sha256.json',{'live_preflight.json':digest(RUN/'live_preflight.json')})
    log('preflight_passed',budget=report['budget'],quota=report['quota'])

def dispatch_once(lock,receipt,intent,send,confirmed=False):
    if not confirmed: raise PermissionError('Literal one-job confirmation required')
    require(intent['cap_seconds']==15 and intent['authorized_one_new_job'] and not intent['automatic_retry'],'Wrong authority')
    require(not Path(receipt).exists(),'Existing receipt')
    save(lock,dict(tag=intent['tag'],plan_sha256=intent['plan_sha256'],cap_seconds=15,
        started_unix=time.time(),authorization_consumed_on_attempt=True,resubmit_allowed=False))
    try: job=send()
    except Exception as error:
        safe.save_if_absent(Path(receipt).parent/'dispatch_uncertain.json',dict(error_type=type(error).__name__,tag=intent['tag'],resubmit_allowed=False))
        raise
    result=dict(job_id=str(job.job_id()),backend=BACKEND,account_name=ACCOUNT,tag=intent['tag'],
        plan_sha256=intent['plan_sha256'],cap_seconds=15,circuits=76,shots=38912,submitted_unix=time.time(),automatic_retry=False)
    print(json.dumps(result),flush=True); save(receipt,result); return job

def verify_cap(job):
    meta=safe.safe_provider('Provider cap lookup',job._api_client.job_get,job.job_id())
    result=dict(job_id=job.job_id(),expected_cap_seconds=15,provider_cost_field=meta.get('cost'),verified=meta.get('cost')==15)
    safe.save_if_absent(RUN/'provider_cap_verification.json',result)
    if not result['verified']:
        try: cancelled=safe.safe_provider('Protective cancellation',job.cancel)
        except Exception as error: cancelled=type(error).__name__
        safe.save_if_absent(RUN/'cap_mismatch_stop.json',dict(cancellation_result=cancelled,resubmit_allowed=False))
        raise RuntimeError('Provider cap mismatch; cancellation attempted')
    return result

def submit(confirmed=False):
    if not confirmed: raise PermissionError('Literal --confirm-one-job-max-15s required')
    require(not LOCK.exists() and not (RUN/'job_receipt.json').exists(),'Attempt already consumed')
    require(not (RUN/'dispatch_live_check.json').exists(),'Existing dispatch check; inspect before continuing')
    plan,pubs=frozen(); verify(RUN,'preflight_sha256.json'); previous=read(RUN/'live_preflight.json')
    require(previous['status']=='PASS_NOT_SUBMITTED' and previous['budget']['pass'],'Preflight failed')
    require(previous['plan_sha256']==digest(RUN/'plan.json'),'Preflight plan changed')
    require(0<=time.time()-previous['checked_unix']<=1800,'Preflight older than30min')
    require(plan['runtime']['qiskit']==base.qiskit.__version__ and plan['runtime']['qiskit_ibm_runtime']==base.qiskit_ibm_runtime.__version__,'SDK changed')
    s,b,props,live=provider(); fp,_=m.fingerprint(b.target,plan['layout72'])
    require(fp==plan['timing_fingerprint']==previous['timing_fingerprint'],'Native target changed')
    opts=options(b,plan['tag']); require(opts==previous['options'],'Options changed')
    require(live['instance_sha256']==previous['instance_sha256'],'Account instance changed')
    live.update(timing_fingerprint=fp,options=opts,plan_sha256=digest(RUN/'plan.json'),
        full_preflight_sha256=digest(RUN/'live_preflight.json'),
        full_ISA_reused_only_for_identical_bytes_target_SDK=True,**budget_now(b,previous['timing_by_pub']))
    sampler=safe.safe_provider('Sampler setup',SamplerV2,mode=b,options=opts)
    require(sampler.mode is None and sampler.options.max_execution_time==15,'Wrong mode/cap')
    live.update(safe.disable_retries(s,b,sampler)); save(RUN/'dispatch_live_check.json',live)
    log('ready_single_POST',circuits=76,shots=38912,cap=15,budget=live['budget'])
    job=dispatch_once(LOCK,RUN/'job_receipt.json',{**plan,'plan_sha256':digest(RUN/'plan.json')},
        lambda:safe.safe_provider('Single authorized POST',sampler.run,pubs),confirmed=True)
    log('submitted',**verify_cap(job))

def retrieve():
    receipt=read(RUN/'job_receipt.json'); require(receipt['plan_sha256']==digest(RUN/'plan.json'),'Receipt mismatch')
    s=safe.safe_provider('Retrieval authentication',QiskitRuntimeService,name=ACCOUNT)
    job=safe.safe_provider('Existing job lookup',s.job,receipt['job_id'])
    status=safe.safe_provider('Job status',job.status); status=str(getattr(status,'name',status))
    log('job_status',job_id=receipt['job_id'],status=status); verify_cap(job)
    if status not in ('DONE','ERROR','CANCELED','CANCELLED'): return
    metrics=safe.safe_provider('Metrics',job.metrics); safe.save_if_absent(RUN/'provider_metrics.json',metrics)
    if status!='DONE':
        safe.save_if_absent(RUN/'FAILED.json',dict(status=status,usage=metrics.get('usage'),resubmit_allowed=False)); return
    if (RUN/'retrieval_verification.json').exists(): verify(RUN,'hardware_archive_sha256.json'); return
    plan,expected=frozen(); inputs=safe.safe_provider('Actual provider inputs',lambda:job.inputs)
    actual=[SamplerPub.coerce(p) for p in inputs['pubs']]; require(len(actual)==len(expected)==76,'PUB count mismatch')
    folder=RUN/'provider_inputs'; folder.mkdir(exist_ok=True)
    for i,(got,want) in enumerate(zip(actual,expected)):
        require(got.shape==want.shape==() and got.shots==want.shots==512,'Actual exposure mismatch')
        require(qpy_bytes(got.circuit)==qpy_bytes(want.circuit) or native_equal(got.circuit,want.circuit),'Actual circuit mismatch')
        save_checked(folder/f'circuit_{i:03d}.qpy',got.circuit)
        if i%8==0: log('provider_input_verified',index=i)
    safe.save_if_absent(folder/'options.json',{k:v for k,v in inputs.items() if k!='pubs'})
    result=safe.safe_provider('Completed result',job.result); require(len(result)==76,'Missing results')
    safe.save_if_absent(RUN/'provider_result_complete.json',result); rows=[]
    for i,(pub,rec) in enumerate(zip(result,plan['records'])):
        meta=pub.metadata.get('circuit_metadata',{})
        require(meta.get('pilot_index')==i and meta.get('pilot_plan_sha256')==receipt['plan_sha256'],'Result provenance')
        require(all(meta.get(k)==v for k,v in rec.items()),'Result metadata changed')
        bits=pub.data.meas; require(bits.shape==() and bits.num_bits==72 and bits.num_shots==512,'BitArray shape')
        strings=bits.get_bitstrings(); decode_bitstrings(strings,72,rec['readout_mask_little_endian'])
        rows.append({**rec,'bitstrings':strings})
    safe.save_if_absent(RUN/'raw_bitstrings.json',dict(job_id=receipt['job_id'],width=72,records=rows))
    safe.save_if_absent(RUN/'retrieval_verification.json',dict(status='DONE_ARCHIVED_VERIFIED',job_id=receipt['job_id'],
        actual_shots=sum(len(r['bitstrings']) for r in rows),provider_circuits_match=76,usage=metrics.get('usage')))
    safe.save_if_absent(RUN/'hardware_archive_sha256.json',{str(p.relative_to(RUN)):digest(p) for p in RUN.rglob('*') if p.is_file() and p.name!='progress.jsonl'})
    log('retrieved',shots=38912,usage=metrics.get('usage'))

def recover():
    if (RUN/'job_receipt.json').exists(): log('receipt_exists',**read(RUN/'job_receipt.json')); return
    attempt=read(LOCK); require(attempt['plan_sha256']==digest(RUN/'plan.json'),'Wrong attempt')
    s=safe.safe_provider('Recovery authentication',QiskitRuntimeService,name=ACCOUNT)
    jobs=safe.safe_provider('Unique tag recovery',s.jobs,limit=10,backend_name=BACKEND,job_tags=[attempt['tag']])
    require(len(jobs)==1,'Recovery not unique; never resubmit')
    rec={**attempt,'job_id':jobs[0].job_id(),'backend':BACKEND,'account_name':ACCOUNT,'recovered':True,'circuits':76,'shots':38912}
    save(RUN/'job_receipt.json',rec); verify_cap(jobs[0]); log('recovered',**rec)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','preflight','submit','retrieve','recover'))
    parser.add_argument('--confirm-one-job-max-15s',action='store_true')
    args=parser.parse_args(); logging.disable(logging.CRITICAL)
    try:
        if args.action=='submit': submit(args.confirm_one_job_max_15s)
        else: globals()[args.action]()
    except Exception as error:
        # Provider wrappers remove messages/inputs; report class only as final safety net.
        log('stopped',action=args.action,error_type=type(error).__name__,automatic_resubmission=False)
        raise SystemExit(1) from None
