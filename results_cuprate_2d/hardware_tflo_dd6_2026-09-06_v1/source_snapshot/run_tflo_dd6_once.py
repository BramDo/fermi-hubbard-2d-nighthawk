"""One separately authorized 15-second 6x6 TFLO/DD job; no automatic retry."""
import argparse,ast,hashlib,io,json,logging,math,platform,shutil,time,unittest,uuid
from dataclasses import asdict
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import qiskit,qiskit_ibm_runtime
from qiskit import QuantumCircuit,qpy
from qiskit.primitives.containers import SamplerPub
from qiskit_ibm_runtime import QiskitRuntimeService,SamplerV2,RuntimeDecoder
from qiskit_ibm_runtime.options import SamplerOptions
from qiskit_ibm_runtime.utils.validations import validate_isa_circuits
from cuprate_2d_hubbard_pipeline import Cuprate2DConfig
from cuprate_2d_tflo import parameterized_network,compile_template,bind,explicit_twirl,embed_measurement,skeleton,flo_reference,physical_observables,initial_occupations,decode_bitstrings
import cuprate_2d_tflo_dd6 as m
import run_cuprate_2d_tflo_once as safe
from preflight_cuprate_2d_tflo_budget import WEIGHTS

ROOT=Path(__file__).resolve().parent
RUN=ROOT/'results_cuprate_2d/hardware_tflo_dd6_2026-09-06_v1'
LOCK=ROOT/'results_cuprate_2d/hardware_tflo_dd6_2026-09-06_attempt.json'
OLD=ROOT/'results_cuprate_2d/hardware_readout_cz_folding_6x6_2026-09-06'
ACCOUNT='qiskit-runtime-q9'; BACKEND='ibm_phoenix'
save=safe.exclusive_json; digest=safe.digest


def require(ok,label):
    if not ok: raise ValueError(label)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'),cls=RuntimeDecoder)


def log(stage,**details):
    row={'UTC':datetime.now(timezone.utc).isoformat(),'stage':stage,**details}
    with (RUN/'LOG.md').open('a',encoding='utf-8') as f: f.write('\n'+json.dumps(row)+'\n')
    print(json.dumps(row),flush=True)


def verify(folder,manifest):
    for name,h in read(folder/manifest).items():
        p=(folder/name).resolve()
        require(p.is_relative_to(folder.resolve()) and digest(p)==h,'Archive hash mismatch')


def circuit_file(path,circuit):
    with path.open('xb') as f: qpy.dump(circuit,f)
    with path.open('rb') as f: restored=qpy.load(f)[0]
    require(restored==circuit and restored.metadata==circuit.metadata,'QPY roundtrip mismatch')


def sources():
    pending=[Path(__file__).name,'analyze_tflo_dd6.py','test_tflo_dd6.py']; found=set()
    while pending:
        name=pending.pop()
        if name in found: continue
        found.add(name)
        for node in ast.walk(ast.parse((ROOT/name).read_text(encoding='utf-8-sig'))):
            modules=[a.name for a in node.names] if isinstance(node,ast.Import) else ([node.module] if isinstance(node,ast.ImportFrom) and node.module else [])
            for mod in modules:
                candidate=mod.split('.')[0]+'.py'
                if (ROOT/candidate).is_file() and candidate not in found: pending.append(candidate)
    return sorted(found)+['TFLO_DD_6X6_PROTOCOL.md']


def compile_local():
    require(not LOCK.exists(),'Authorization already attempted')
    require(not (RUN/'plan.json').exists(),'Plan already frozen')
    RUN.mkdir(exist_ok=True); folder=RUN/'local_only'; folder.mkdir(exist_ok=True)
    path=folder/'parameterized72.qpy'
    require(not path.exists(),'Compiled input exists; prepare instead')
    import resource,signal,faulthandler
    faulthandler.enable()
    soft,hard=resource.getrlimit(resource.RLIMIT_STACK)
    wanted=64*1024*1024 if hard<0 else min(hard,64*1024*1024)
    if soft>=0 and soft<wanted: resource.setrlimit(resource.RLIMIT_STACK,(wanted,hard))
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Offline compile 900-second bound')))
    signal.alarm(900)
    cfg=Cuprate2DConfig(**read(OLD/'plan.json')['config'])
    begin=time.perf_counter(); logical=parameterized_network(cfg)
    log('compile_start',logical_ops=len(logical.data),qpu_seconds=0)
    circuit=compile_template(logical)
    require(circuit.num_qubits==72 and circuit.num_parameters==2,'Unexpected template')
    circuit_file(path,circuit)
    save(folder/'compile.json',{'source_sha256':digest(ROOT/'cuprate_2d_tflo.py'),
        'qpy_sha256':digest(path),'seconds':time.perf_counter()-begin,'counts':dict(circuit.count_ops()),
        'depth':circuit.depth(),'skeleton':skeleton(circuit),'config':asdict(cfg)})
    signal.alarm(0)
    log('compile_done',seconds=time.perf_counter()-begin,CZ=circuit.count_ops().get('cz',0),qpu_seconds=0)


def check_input(c,rec,index,plan_hash):
    require(c.num_qubits==120 and c.num_clbits==72 and c.num_parameters==0,'PUB shape changed')
    meta=c.metadata or {}
    require(meta.get('pilot_index')==index and meta.get('pilot_plan_sha256')==plan_hash,'Provenance changed')
    require(all(meta.get(k)==v for k,v in rec.items()),'Metadata changed')
    mapping={}
    for inst in c.data:
        op=inst.operation
        require(op.name in {'x','sx','rz','cz','delay','measure','barrier'},'Unsupported operation')
        require(all(np.isfinite(float(p)) for p in op.params),'Nonfinite angle')
        if op.name=='delay': require(op.unit=='dt' and op.duration>=0 and op.duration==int(op.duration),'Bad delay')
        if op.label==m.DD_LABEL: require(rec['dd'] and op.name=='x','Unexpected DD pulse')
        if op.name=='measure':
            ci=c.find_bit(inst.clbits[0]).index
            require(ci not in mapping,'Duplicate measurement')
            mapping[ci]=c.find_bit(inst.qubits[0]).index
    require(mapping==dict(enumerate(rec['physical_layout'])),'Measurement map changed')
    if rec['role']=='calibration': require(set(c.count_ops())<={'x','measure'},'Calibration contains dynamics')


def prepare():
    require(not LOCK.exists() and not (RUN/'plan.json').exists(),'Attempt or plan already exists')
    compile_info=read(RUN/'local_only/compile.json')
    require(digest(ROOT/'cuprate_2d_tflo.py')==compile_info['source_sha256'],'Compiler source changed')
    template_path=RUN/'local_only'/compile_info.get('template_file','parameterized72.qpy')
    require(template_path.resolve().is_relative_to((RUN/'local_only').resolve()),'Invalid template path')
    require(digest(template_path)==compile_info['qpy_sha256'],'Compiled template changed')
    if 'block_compiler_sha256' in compile_info:
        require(digest(ROOT/'compile_tflo_dd6_blocks.py')==compile_info['block_compiler_sha256'],'Block compiler changed')
    tests_log=io.StringIO()
    test=unittest.TextTestRunner(stream=tests_log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('test_tflo_dd6'))
    require(test.wasSuccessful(),'Local tests failed')
    with (RUN/'unit_tests.txt').open('x',encoding='utf-8') as f: f.write(tests_log.getvalue())
    old=read(OLD/'plan.json'); cfg=Cuprate2DConfig(**old['config']); layout=old['layout']
    require(asdict(cfg)==compile_info['config'],'Physics config changed')
    verify(OLD,'hardware_archive_sha256.json')
    service=safe.safe_provider('IBM authentication',QiskitRuntimeService,name=ACCOUNT)
    backend=safe.safe_provider('IBM backend',service.backend,BACKEND)
    status=safe.safe_provider('IBM status',backend.status)
    require(status.operational and backend.num_qubits==120,'Backend unavailable')
    fingerprint,timing=m.fingerprint(backend.target,layout)
    with template_path.open('rb') as f: native=qpy.load(f)[0]
    templates={}; masks=[]; schedules=[]
    begin=time.perf_counter()
    for t in range(m.TWIRLS):
        twin,mask=explicit_twirl(native,202609061600+t)
        masks.append(mask)
        physical=embed_measurement(twin,layout,120)
        off,on,info=m.schedule_pair(physical,backend.target,layout)
        for dd,c in [(False,off),(True,on)]:
            templates[dd,t]=c
            circuit_file(RUN/'local_only'/f'scheduled_dd{int(dd)}_twirl{t}.qpy',c)
        schedules.append({'twirl_id':t,**info})
        log('DD_pair_validated',twirl=t,echo_pairs=info['echo_pairs'],duration_seconds=info['duration_seconds'])
    rows=m.records(layout,masks); m.validate_records(rows)
    refs={}
    for s in m.settings():
        if s['U']==0:
            p,cov=flo_reference(cfg,s['T'])
            require(abs(np.trace(cov).real-32)<1e-10 and np.max(np.abs(cov@cov-cov))<1e-10,'FLO conservation')
            refs[s['id']]={'paulis':p.tolist(),'physical':physical_observables(p).tolist(),
                'exact_for':'finite_two_step_U0_circuit','N':32,'projector_residual':float(np.max(np.abs(cov@cov-cov)))}
    source_names=sources(); snap=RUN/'source_snapshot'; snap.mkdir()
    for name in source_names: shutil.copyfile(ROOT/name,snap/name)
    intent={'schema':'tflo-dd6-v1','backend':BACKEND,'account_name':ACCOUNT,'cap_seconds':m.CAP,
        'authorized_one_new_job':True,'automatic_retry':False,
        'authorization':'User Ja to one new 6x6 TFLO/DD/readout/twirling pilot, max15 QPU seconds, conditional on passing fresh budget check.',
        'tag':'tflo-dd6-'+uuid.uuid4().hex[:16],'config':asdict(cfg),'layout72':layout,
        'settings':m.settings(),'records':rows,'total_shots':m.TOTAL,'total_PUBs':m.PUBS,
        'source_sha256':{name:digest(ROOT/name) for name in source_names},
        'timing_fingerprint':fingerprint,'old_plan_sha256':digest(OLD/'plan.json'),
        'bootstrap_replicates':m.BOOTSTRAP,'bootstrap_seed':202609061615,'ridge':m.RIDGE,
        'TFLO_time_feature':False,'postselection':False,'DD_explicit':'native labeled XX pairs',
        'runtime':{'python':platform.python_version(),'qiskit':qiskit.__version__,'qiskit_ibm_runtime':qiskit_ibm_runtime.__version__},
        'created_unix':time.time(),'canonical_attempt_marker':str(LOCK.relative_to(ROOT))}
    save(RUN/'plan.json',intent); ph=digest(RUN/'plan.json')
    save(RUN/'references.json',refs); save(RUN/'scheduling_target.json',timing)
    save(RUN/'scheduling_validation.json',{'pairs':schedules,'seconds':time.perf_counter()-begin})
    bound=RUN/'bound_inputs'; bound.mkdir()
    expected_skeletons={}
    for i,rec in enumerate(rows):
        if rec['role']=='calibration':
            c=QuantumCircuit(72)
            if rec['state']: c.x(range(72))
            c=embed_measurement(c,layout,120)
        else:
            c=bind(templates[rec['dd'],rec['twirl_id']],cfg,rec['T'],rec['U'])
            key=(rec['dd'],rec['twirl_id']); sk=skeleton(c)
            expected_skeletons.setdefault(key,sk)
            require(expected_skeletons[key]==sk,'Bound skeleton changed')
        c.metadata={**rec,'pilot_index':i,'pilot_plan_sha256':ph,'pilot_tag':intent['tag']}
        check_input(c,rec,i,ph)
        circuit_file(bound/f'circuit_{i:03d}.qpy',c)
        if i%10==0: log('bound_archived',index=i,circuits=m.PUBS)
    save(RUN/'frozen_inputs_sha256.json',{str(p.relative_to(RUN)):digest(p) for p in RUN.rglob('*') if p.is_file() and p.name!='LOG.md'})
    verify(RUN,'frozen_inputs_sha256.json')
    log('prepared_not_submitted',circuits=m.PUBS,shots=m.TOTAL,cap=m.CAP,qpu_seconds=0)


def frozen():
    verify(RUN,'frozen_inputs_sha256.json')
    plan=read(RUN/'plan.json'); ph=digest(RUN/'plan.json')
    require(plan['cap_seconds']==15 and plan['authorized_one_new_job'] and not plan['automatic_retry'],'Wrong authorization')
    require(plan['backend']==BACKEND and plan['total_shots']==m.TOTAL,'Scope changed')
    m.validate_records(plan['records'])
    for name,h in plan['source_sha256'].items(): require(digest(ROOT/name)==h,'Source changed since freeze')
    pubs=[]
    for i,rec in enumerate(plan['records']):
        with (RUN/'bound_inputs'/f'circuit_{i:03d}.qpy').open('rb') as f: c=qpy.load(f)[0]
        check_input(c,rec,i,ph); pubs.append(SamplerPub.coerce((c,None,m.SHOTS)))
    return plan,pubs


def options(backend,tag):
    opts={'max_execution_time':m.CAP,'default_shots':m.SHOTS,
        'execution':{'init_qubits':True,'rep_delay':float(backend.default_rep_delay),'meas_type':'classified'},
        'twirling':{'enable_gates':False,'enable_measure':False},'dynamical_decoupling':{'enable':False},
        'environment':{'job_tags':['2d-cuprate','tflo-dd6',tag]}}
    SamplerOptions(**opts); return opts


def live_gate(plan,pubs):
    service=safe.safe_provider('IBM authentication',QiskitRuntimeService,name=ACCOUNT)
    b=safe.safe_provider('IBM backend',service.backend,BACKEND)
    status=safe.safe_provider('IBM status',b.status)
    require(status.operational and b.num_qubits==120,'Backend unavailable')
    props=safe.safe_provider('IBM properties',b.properties)
    require(not set(plan['layout72']).intersection(props.faulty_qubits()),'Faulty qubit')
    fp,_=m.fingerprint(b.target,plan['layout72'])
    require(fp==plan['timing_fingerprint'],'Timing changed after explicit DD scheduling; do not submit')
    safe.safe_provider('ISA validation',validate_isa_circuits,[p.circuit for p in pubs],b.target)
    usage=m.quota(safe.safe_provider('IBM quota',service.usage))
    rep=float(b.default_rep_delay)
    require(b.rep_delay_range[0]<=rep<=b.rep_delay_range[1],'Invalid rep delay')
    reset=max(float(b.target['reset'][(q,)].duration) for q in plan['layout72'])
    timing=[]; memory=np.zeros(120,dtype=np.int64)
    for i,p in enumerate(pubs):
        safe.safe_provider('Faulty gate validation',b.check_faulty,p.circuit)
        manual,_=m.clocks(p.circuit,b.target); manual*=b.target.dt
        sdk=float(p.circuit.estimate_duration(b.target))
        require(abs(sdk-manual)<1e-10,'Independent duration mismatch')
        for inst in p.circuit.data:
            if inst.operation.name!='barrier':
                memory[[p.circuit.find_bit(q).index for q in inst.qubits]]+=WEIGHTS[inst.operation.name]
        timing.append({'index':i,'shots':p.shots,'duration_seconds':sdk,'all_shots_seconds':p.shots*(sdk+reset+rep)})
    memory+=50*len(pubs); require(max(memory)<26800000,'Instruction memory budget')
    budget=m.budget(sum(v['all_shots_seconds'] for v in timing))
    report={'status':'PASS_NOT_SUBMITTED' if budget['pass'] else 'BUDGET_REJECTED',
        'checked_unix':time.time(),'backend':BACKEND,'pending_jobs':status.pending_jobs,
        'instance_sha256':hashlib.sha256(str(service.active_account().get('instance','')).encode()).hexdigest(),
        'properties_updated':str(props.last_update_date),'options':options(b,plan['tag']),
        'quota':usage,'budget':budget,'timing_by_pub':timing,'reset_seconds':reset,'rep_delay_seconds':rep,
        'timing_fingerprint':fp,'plan_sha256':digest(RUN/'plan.json'),'instruction_memory_max_per_wire':int(max(memory))}
    return service,b,props,report


def preflight():
    require(not LOCK.exists(),'Attempt consumed')
    plan,pubs=frozen(); _,_,props,report=live_gate(plan,pubs)
    save(RUN/'live_preflight.json',report); save(RUN/'live_backend_properties.json',props.to_dict())
    save(RUN/'preflight_sha256.json',{n:digest(RUN/n) for n in ('live_preflight.json','live_backend_properties.json')})
    log('preflight',budget=report['budget'],quota=report['quota'])
    require(report['budget']['pass'],'Budget rejected')


def dispatch_once(lock,receipt,intent,send,confirmed=False):
    if not confirmed: raise PermissionError('Explicit one-job15s confirmation required')
    require(intent['cap_seconds']==15 and intent['authorized_one_new_job'] and not intent['automatic_retry'],'Wrong authority')
    require(not Path(receipt).exists(),'Existing receipt')
    save(lock,{'tag':intent['tag'],'plan_sha256':intent['plan_sha256'],'cap_seconds':15,
        'started_unix':time.time(),'authorization_consumed_on_attempt':True,'resubmit_allowed':False})
    try: job=send()
    except Exception as exc:
        safe.save_if_absent(Path(receipt).parent/'dispatch_uncertain.json',{'error_type':type(exc).__name__,'tag':intent['tag'],'resubmit_allowed':False})
        raise
    rec={'job_id':str(job.job_id()),'backend':BACKEND,'account_name':ACCOUNT,
        'tag':intent['tag'],'plan_sha256':intent['plan_sha256'],'cap_seconds':15,
        'circuits':m.PUBS,'shots':m.TOTAL,'submitted_unix':time.time(),'automatic_retry':False}
    print(json.dumps(rec),flush=True); save(receipt,rec); return job


def verify_cap(job):
    meta=safe.safe_provider('Provider cap lookup',job._api_client.job_get,job.job_id())
    result={'job_id':job.job_id(),'expected_cap_seconds':15,'provider_cost_field':meta.get('cost'),'verified':meta.get('cost')==15}
    safe.save_if_absent(RUN/'provider_cap_verification.json',result)
    if not result['verified']:
        try: canceled=safe.safe_provider('Protective cap cancellation',job.cancel)
        except Exception as exc: canceled=type(exc).__name__
        safe.save_if_absent(RUN/'cap_mismatch_stop.json',{'cancellation_result':canceled,'resubmit_allowed':False})
        raise RuntimeError('Cap unverified; stop')
    return result


def submit(confirmed=False):
    if not confirmed: raise PermissionError('Explicit --confirm-one-job-max-15s required')
    require(not LOCK.exists() and not (RUN/'job_receipt.json').exists(),'Attempt consumed')
    plan,pubs=frozen(); verify(RUN,'preflight_sha256.json'); previous=read(RUN/'live_preflight.json')
    require(previous['budget']['pass'],'Preflight rejected')
    service,b,_,current=live_gate(plan,pubs)
    require(current['budget']['pass'],'Fresh budget rejected')
    require(current['instance_sha256']==previous['instance_sha256'] and current['options']==previous['options'],'Instance/options changed')
    sampler=safe.safe_provider('Sampler setup',SamplerV2,mode=b,options=current['options'])
    require(sampler.mode is None and sampler.options.max_execution_time==15,'Wrong mode/cap')
    retries=safe.disable_retries(service,b,sampler)
    save(RUN/'dispatch_live_check.json',{**current,**retries})
    log('ready_for_single_POST',cap=15,circuits=m.PUBS,shots=m.TOTAL,budget=current['budget'])
    job=dispatch_once(LOCK,RUN/'job_receipt.json',{**plan,'plan_sha256':digest(RUN/'plan.json')},
        lambda:safe.safe_provider('Single authorized Sampler POST',sampler.run,pubs),confirmed=True)
    log('submitted',**verify_cap(job))


def recover():
    if (RUN/'job_receipt.json').exists(): print(json.dumps(read(RUN/'job_receipt.json'))); return
    attempt=read(LOCK); require(attempt['plan_sha256']==digest(RUN/'plan.json'),'Wrong attempt')
    service=safe.safe_provider('Recovery authentication',QiskitRuntimeService,name=ACCOUNT)
    jobs=safe.safe_provider('Unique tag lookup',service.jobs,limit=10,backend_name=BACKEND,job_tags=[attempt['tag']])
    require(len(jobs)==1,'Recovery not unique; never resubmit')
    rec={**attempt,'job_id':jobs[0].job_id(),'backend':BACKEND,'account_name':ACCOUNT,'recovered':True,'circuits':m.PUBS,'shots':m.TOTAL}
    save(RUN/'job_receipt.json',rec); verify_cap(jobs[0]); print(json.dumps(rec))


def retrieve():
    receipt=read(RUN/'job_receipt.json'); require(receipt['plan_sha256']==digest(RUN/'plan.json'),'Receipt mismatch')
    service=safe.safe_provider('Retrieval authentication',QiskitRuntimeService,name=ACCOUNT)
    job=safe.safe_provider('Existing job',service.job,receipt['job_id'])
    status=safe.safe_provider('Job status',job.status); status=str(getattr(status,'name',status))
    log('job_status',job_id=receipt['job_id'],status=status); verify_cap(job)
    if status not in ('DONE','ERROR','CANCELED','CANCELLED'): return
    metrics=safe.safe_provider('Job metrics',job.metrics); safe.save_if_absent(RUN/'provider_metrics.json',metrics)
    if status!='DONE': safe.save_if_absent(RUN/'FAILED.json',{'status':status,'usage':metrics.get('usage'),'resubmit_allowed':False}); return
    plan,expected=frozen(); inputs=safe.safe_provider('Provider inputs',lambda:job.inputs)
    actual=[SamplerPub.coerce(p) for p in inputs['pubs']]; require(len(actual)==len(expected)==m.PUBS,'PUB count changed')
    folder=RUN/'provider_inputs'; folder.mkdir(exist_ok=True)
    for i,(got,wanted) in enumerate(zip(actual,expected)):
        require(got.shape==wanted.shape==() and got.shots==wanted.shots==m.SHOTS,'Exposure changed')
        require(got.circuit==wanted.circuit and got.circuit.metadata==wanted.circuit.metadata,'Provider circuit changed')
        path=folder/f'circuit_{i:03d}.qpy'
        if not path.exists(): circuit_file(path,got.circuit)
    safe.save_if_absent(folder/'options.json',{k:v for k,v in inputs.items() if k!='pubs'})
    result=safe.safe_provider('Completed result',job.result); require(len(result)==m.PUBS,'Missing result')
    safe.save_if_absent(RUN/'provider_result_complete.json',result)
    rows=[]
    for i,(pub,rec) in enumerate(zip(result,plan['records'])):
        meta=pub.metadata.get('circuit_metadata',{})
        require(meta.get('pilot_index')==i and meta.get('pilot_plan_sha256')==receipt['plan_sha256'],'Result provenance')
        require(all(meta.get(k)==v for k,v in rec.items()),'Result metadata changed')
        bits=pub.data.meas; require(bits.shape==() and bits.num_bits==72 and bits.num_shots==m.SHOTS,'Result BitArray changed')
        strings=bits.get_bitstrings(); decode_bitstrings(strings,72,rec['readout_mask_little_endian'])
        rows.append({**rec,'bitstrings':strings})
    safe.save_if_absent(RUN/'raw_bitstrings.json',{'job_id':receipt['job_id'],'width':72,'records':rows})
    safe.save_if_absent(RUN/'retrieval_verification.json',{'status':'DONE_ARCHIVED_VERIFIED','job_id':receipt['job_id'],
        'actual_shots':sum(len(r['bitstrings']) for r in rows),'provider_circuits_match':m.PUBS,'usage':metrics.get('usage')})
    safe.save_if_absent(RUN/'hardware_archive_sha256.json',{str(p.relative_to(RUN)):digest(p) for p in RUN.rglob('*') if p.is_file() and p.name!='LOG.md'})
    log('retrieved',shots=m.TOTAL,usage=metrics.get('usage'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['compile','prepare','preflight','submit','recover','retrieve'])
    parser.add_argument('--confirm-one-job-max-15s',action='store_true')
    args=parser.parse_args(); logging.disable(logging.CRITICAL)
    try:
        if args.action=='submit': submit(args.confirm_one_job_max_15s)
        elif args.action=='compile': compile_local()
        else: globals()[args.action]()
    except Exception as exc:
        print(json.dumps({'action':args.action,'error_type':type(exc).__name__,'automatic_resubmission':False}),flush=True)
        raise SystemExit(1) from None


if __name__=='__main__': main()
