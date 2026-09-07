"""One authorized5-second diagnostic job. No resubmission after an attempt."""
import argparse
import ast
from collections import Counter
from dataclasses import asdict
from datetime import datetime,timezone
import hashlib
import io
import json
import logging
from pathlib import Path
import platform
import shutil
import time
import unittest
import uuid
import numpy as np
import qiskit
from qiskit import QuantumCircuit,qpy
from qiskit.primitives.containers import SamplerPub
from qiskit_ibm_runtime import QiskitRuntimeService,SamplerV2,RuntimeDecoder
from qiskit_ibm_runtime.options import SamplerOptions
from qiskit_ibm_runtime.utils.validations import validate_isa_circuits
import qiskit_ibm_runtime
import run_cuprate_2d_tflo_once as safe
from preflight_cuprate_2d_tflo_budget import wire_time,WEIGHTS
from cuprate_2d_tflo import (parameterized_network,compile_template,bind,skeleton,
    explicit_twirl,embed_measurement,decode_bitstrings,pauli_samples,physical_observables)
from cuprate_2d_hardware_controls import (CAP,SHOTS,TOTAL,T,BOOTSTRAP,SCREEN,
    configurations,preparation,records,validate_records,references,corrected_paulis,
    quota_summary,budget_summary)

ROOT=Path(__file__).resolve().parent
RUN=ROOT/'results_cuprate_2d/hardware_controls_5x5_2026-09-06_v1'
LOCK=ROOT/'results_cuprate_2d/hardware_controls_5x5_2026-09-06_attempt.json'
OLD=ROOT/'results_cuprate_2d/hardware_readout_cz_folding_6x6_2026-09-06'
ACCOUNT='qiskit-runtime-q9'
BACKEND='ibm_phoenix'
PROTOCOL='HARDWARE_CONTROL_5X5_PROTOCOL.md'
digest=safe.digest
save=safe.exclusive_json


def require(value,label):
    if not value: raise ValueError(label)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'),cls=RuntimeDecoder)


def log(stage,details):
    row={'stage':stage,'UTC':datetime.now(timezone.utc).isoformat(),**details}
    with (RUN/'LOG.md').open('a',encoding='utf-8') as f:
        f.write('\n## '+row['UTC']+' '+stage+'\n\n'+safe.encode(details)+'\n')
    print(json.dumps(row),flush=True)


def verify(root,manifest):
    for name,value in read(root/manifest).items():
        path=(root/name).resolve()
        require(path.is_relative_to(root.resolve()) and digest(path)==value,'Frozen artifact mismatch')


def sources():
    pending=[Path(__file__).name,'test_hardware_control_5x5.py']; found=set()
    while pending:
        name=pending.pop()
        if name in found: continue
        found.add(name)
        for node in ast.walk(ast.parse((ROOT/name).read_text(encoding='utf-8-sig'))):
            modules=[a.name for a in node.names] if isinstance(node,ast.Import) else (
                [node.module] if isinstance(node,ast.ImportFrom) and node.module else [])
            for module in modules:
                candidate=module.split('.')[0]+'.py'
                if (ROOT/candidate).is_file() and candidate not in found: pending.append(candidate)
    return sorted(found)+[PROTOCOL,'HARDWARE_CONTROL_5X5_LOG.md']


def circuit_file(path,circuit):
    with path.open('xb') as f: qpy.dump(circuit,f)
    with path.open('rb') as f:
        restored=qpy.load(f)[0]
        require(restored==circuit and restored.metadata==circuit.metadata,'QPY roundtrip failed')


def check_input(circuit,record,index,ph):
    require(circuit.num_qubits==120 and circuit.num_clbits==record['width'],'Circuit/register width changed')
    require(circuit.num_parameters==0,'Unbound parameter')
    meta=circuit.metadata or {}
    require(meta.get('control_index')==index and meta.get('control_plan_sha256')==ph,'Circuit provenance mismatch')
    require(meta.get('readout_mask_little_endian')==record['readout_mask_little_endian'],'Mask changed')
    require(meta.get('role')==record['role'] and meta.get('setting_id')==record['setting_id'],'Role mismatch')
    if record['role']=='dynamics': require(meta.get('U')==0 and meta.get('T')==T,'Unapproved dynamics')
    mapping={}
    allowed={'rz','sx','x','cz','measure','barrier'}
    for inst in circuit.data:
        require(inst.operation.name in allowed,'Unexpected native operation')
        require(all(np.isfinite(float(p)) for p in inst.operation.params),'Nonfinite gate parameter')
        if inst.operation.name=='measure':
            c=circuit.find_bit(inst.clbits[0]).index
            require(c not in mapping,'Duplicate measurement')
            mapping[c]=circuit.find_bit(inst.qubits[0]).index
    require(mapping==dict(enumerate(record['physical_layout'])),'Measurement order changed')
    if record['role']!='dynamics':
        require(set(circuit.count_ops())<={'x','measure'},'Preparation/calibration contains evolution')


def prepare():
    require(not LOCK.exists(),'Authorization already attempted')
    if RUN.exists():
        # Resume only a compiler interruption BEFORE any inputs/plan were frozen.
        # Keep every earlier test log; never overwrite a circuit or authorization.
        require(not (RUN/'plan.json').exists() and not (RUN/'frozen_inputs_sha256.json').exists(),'Inputs already frozen')
        for path in RUN.rglob('*'):
            if path.is_file():
                require(path.parent==RUN and (path.name=='LOG.md' or path.name.startswith('unit_tests')),
                        'Unexpected partial output; refuse resume')
    tests_log=io.StringIO()
    tests=unittest.TextTestRunner(stream=tests_log,verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromName('test_hardware_control_5x5'))
    require(tests.wasSuccessful(),'Local control tests failed')
    cfg5,cfg6=configurations()
    previous=read(OLD/'plan.json')
    require(asdict(cfg6)==previous['config'],'Original6x6 preparation changed')
    layout=previous['layout']
    verify(OLD,'delivery_sha256.json')
    RUN.mkdir(exist_ok=True)
    for name in ('bound_inputs','local_only','source_snapshot'): (RUN/name).mkdir(exist_ok=True)
    previous_logs=list(RUN.glob('unit_tests*.txt'))
    tests_name='unit_tests.txt' if not previous_logs else f'unit_tests_resume{len(previous_logs)}.txt'
    with (RUN/tests_name).open('x',encoding='utf-8') as f: f.write(tests_log.getvalue())
    log('local_tests_pass',{'tests':tests.testsRun,'submission_attempted':False})
    before=time.perf_counter()
    # Process-local stack allowance for large symbolic native compilation.
    # No package, global environment, circuit or algorithm is changed.
    import resource,signal,faulthandler
    faulthandler.enable()
    soft,hard=resource.getrlimit(resource.RLIMIT_STACK)
    desired=64*1024*1024 if hard<0 else min(hard,64*1024*1024)
    if soft>=0 and soft<desired: resource.setrlimit(resource.RLIMIT_STACK,(desired,hard))
    def timeout(*_): raise TimeoutError('600-second offline compile limit')
    signal.signal(signal.SIGALRM,timeout); signal.alarm(600)
    logical=parameterized_network(cfg5)
    log('compile_start',{'logical_operations':len(logical.data),'stack_bytes':resource.getrlimit(resource.RLIMIT_STACK)[0]})
    template=compile_template(logical)
    log('compile_finished',{'native_operations':len(template.data),'native_CZ':template.count_ops().get('cz',0)})
    native0=bind(template,cfg5,T,0.)
    native8=bind(template,cfg5,T,8.)
    require(skeleton(template)==skeleton(native0)==skeleton(native8),'U0/U8 native skeleton differs')
    require(native0.count_ops()==native8.count_ops(),'Gate counts differ')
    circuit_file(RUN/'local_only/parameterized50.qpy',template)
    circuit_file(RUN/'local_only/U8_companion_DO_NOT_SUBMIT.qpy',native8)
    twins=[explicit_twirl(native0,202609060700+v) for v in range(4)]
    rows=records(layout,[mask.tolist() for _,mask in twins])
    refs=references(cfg5,cfg6)
    source_names=sources()
    for name in source_names: shutil.copyfile(ROOT/name,RUN/'source_snapshot'/name)
    intent={'schema':'hardware-controls5-v1','backend':BACKEND,'account_name':ACCOUNT,
        'cap_seconds':CAP,'authorized_one_new_job':True,'automatic_retry':False,
        'authorization':'User replied Ja to one preparation plus5x5 U0 control job, max5 QPU seconds, conditional on fresh preflight.',
        'tag':'controls5-'+uuid.uuid4().hex[:16],'config5':asdict(cfg5),'config6':asdict(cfg6),
        'layout72':layout,'records':rows,'total_shots':TOTAL,'total_PUBs':12,
        'source_sha256':{name:digest(ROOT/name) for name in source_names},
        'old_plan_sha256':digest(OLD/'plan.json'),'old_delivery_sha256':digest(OLD/'delivery_sha256.json'),
        'U0_U8_skeleton_sha256':skeleton(native0),'U8_hardware_authorized':False,
        'bootstrap_replicates':BOOTSTRAP,'bootstrap_seed':202609060799,
        'screen_RMS_charge_spin_doublon':SCREEN.tolist(),'screen_abs_N_error':.5,
        'screen_is_not_accuracy_certificate':True,'native50_operations':dict(native0.count_ops()),
        'runtime':{'python':platform.python_version(),'qiskit':qiskit.__version__,
                   'qiskit_ibm_runtime':qiskit_ibm_runtime.__version__},
        'readout_model':'independent asymmetric confusion channels; no clipping',
        'created_unix':time.time(),'canonical_attempt_marker':str(LOCK.relative_to(ROOT))}
    save(RUN/'plan.json',intent); ph=digest(RUN/'plan.json'); save(RUN/'references.json',refs)
    for index,rec in enumerate(rows):
        if rec['role']=='dynamics': local=twins[rec['twirl_id']][0]
        elif rec['role']=='preparation':
            local=preparation(cfg5 if rec['width']==50 else cfg6,rec['readout_mask_little_endian'])
        else:
            local=QuantumCircuit(72)
            if rec['state']: local.x(range(72))
        circuit=embed_measurement(local,rec['physical_layout'],120)
        circuit.metadata={**rec,'control_index':index,'control_plan_sha256':ph,'control_tag':intent['tag']}
        check_input(circuit,rec,index,ph)
        circuit_file(RUN/'bound_inputs'/f'circuit_{index:03d}.qpy',circuit)
    log('prepared_not_submitted',{'circuits':12,'shots':TOTAL,'cap_seconds':CAP,
        'native50_CZ':native0.count_ops().get('cz',0),'native50_depth':native0.depth(),
        'local_seconds':time.perf_counter()-before,'U0_U8_same_gate_skeleton':True})
    save(RUN/'frozen_inputs_sha256.json',{str(p.relative_to(RUN)):digest(p)
        for p in RUN.rglob('*') if p.is_file() and p.name!='LOG.md'})
    verify(RUN,'frozen_inputs_sha256.json')
    signal.alarm(0)


def frozen():
    verify(RUN,'frozen_inputs_sha256.json')
    plan=read(RUN/'plan.json'); ph=digest(RUN/'plan.json')
    require(plan['cap_seconds']==CAP and plan['backend']==BACKEND and plan['authorized_one_new_job'],'Wrong authorization')
    require(not plan['automatic_retry'] and not plan['U8_hardware_authorized'],'Scope changed')
    validate_records(plan['records'])
    for name,value in plan['source_sha256'].items(): require(digest(ROOT/name)==value,'Source changed since freezing')
    pubs=[]
    for i,record in enumerate(plan['records']):
        with (RUN/'bound_inputs'/f'circuit_{i:03d}.qpy').open('rb') as f: circuit=qpy.load(f)[0]
        check_input(circuit,record,i,ph)
        pubs.append(SamplerPub.coerce((circuit,None,SHOTS)))
    require(sum(p.shots for p in pubs)==TOTAL,'Exposure changed')
    return plan,pubs


def options_for(backend,tag):
    result={'max_execution_time':CAP,'default_shots':SHOTS,
        'execution':{'init_qubits':True,'rep_delay':float(backend.default_rep_delay),'meas_type':'classified'},
        'twirling':{'enable_gates':False,'enable_measure':False},'dynamical_decoupling':{'enable':False},
        'environment':{'job_tags':['2d-cuprate','preparation-flo-control',tag]}}
    SamplerOptions(**result)
    return result


def live_gate(plan,pubs):
    service=safe.safe_provider('IBM authentication',QiskitRuntimeService,name=ACCOUNT)
    backend=safe.safe_provider('IBM backend',service.backend,BACKEND)
    status=safe.safe_provider('IBM status',backend.status)
    require(status.operational and backend.num_qubits==120,'Backend not available')
    properties=safe.safe_provider('IBM properties',backend.properties)
    require(not set(plan['layout72']).intersection(properties.faulty_qubits()),'Faulty selected qubit')
    safe.safe_provider('ISA validation',validate_isa_circuits,[p.circuit for p in pubs],backend.target)
    quota=quota_summary(safe.safe_provider('IBM quota',service.usage))
    target=backend.target; rep=float(backend.default_rep_delay)
    require(backend.rep_delay_range[0]<=rep<=backend.rep_delay_range[1],'Invalid repetition delay')
    reset=max(float(target['reset'][(q,)].duration) for q in plan['layout72'])
    require(np.isfinite(reset) and reset>=0,'Invalid reset duration')
    timing=[]; low=np.zeros(120,dtype=np.int64)
    for i,pub in enumerate(pubs):
        safe.safe_provider('Faulty gate validation',backend.check_faulty,pub.circuit)
        sdk=float(pub.circuit.estimate_duration(target))
        manual=wire_time(pub.circuit,target)
        require(abs(sdk-manual)<1e-10,'SDK and independent timing disagree')
        aligned=wire_time(pub.circuit,target,aligned=True)
        require(aligned>=manual-1e-12,'Alignment shortened circuit')
        for inst in pub.circuit.data:
            if inst.operation.name=='barrier': continue
            low[[pub.circuit.find_bit(q).index for q in inst.qubits]]+=WEIGHTS[inst.operation.name]
        timing.append({'index':i,'width':pub.circuit.num_clbits,'shots':pub.shots,
            'duration_seconds':sdk,'aligned_seconds':aligned,
            'all_shots_seconds':pub.shots*(aligned+reset+rep)})
    low+=50*len(pubs); require(int(max(low))<26_800_000,'Instruction memory limit exceeded')
    budget=budget_summary(sum(r['all_shots_seconds'] for r in timing))
    report={'status':'LIVE_PREFLIGHT_PASS_NOT_SUBMITTED' if budget['pass'] else 'BUDGET_REJECTED',
        'checked_unix':time.time(),'backend':BACKEND,'pending_jobs':status.pending_jobs,
        'instance_sha256':hashlib.sha256(str(service.active_account().get('instance','')).encode()).hexdigest(),
        'properties_updated':str(properties.last_update_date),'options':options_for(backend,plan['tag']),
        'quota':quota,'budget':budget,'timing_by_pub':timing,'reset_seconds':reset,
        'rep_delay_seconds':rep,'plan_sha256':digest(RUN/'plan.json'),
        'ISA_and_fault_checks_pass':True,'instruction_memory_max_per_wire':int(max(low))}
    return service,backend,properties,report


def preflight():
    require(not LOCK.exists(),'Attempt consumed')
    plan,pubs=frozen()
    _,_,properties,report=live_gate(plan,pubs)
    save(RUN/'live_preflight.json',report)
    save(RUN/'live_backend_properties.json',properties.to_dict())
    save(RUN/'preflight_sha256.json',{n:digest(RUN/n) for n in ('live_preflight.json','live_backend_properties.json')})
    log('preflight',{'budget':report['budget'],'quota':report['quota'],'pending_jobs':report['pending_jobs']})
    require(report['budget']['pass'],'Budget preflight rejected; do not submit')


def dispatch_once(lock,receipt,intent,send,confirmed=False):
    if not confirmed: raise PermissionError('Literal one-job max5s confirmation required')
    require(intent['cap_seconds']==5 and intent['authorized_one_new_job'] and not intent['automatic_retry'],'Wrong authority')
    if Path(receipt).exists(): raise FileExistsError('Receipt exists')
    save(lock,{'tag':intent['tag'],'plan_sha256':intent['plan_sha256'],'cap_seconds':CAP,
        'started_unix':time.time(),'authorization_consumed_on_attempt':True,'resubmit_allowed':False})
    try: job=send()
    except Exception as exc:
        safe.save_if_absent(Path(receipt).parent/'dispatch_uncertain.json',
            {'tag':intent['tag'],'error_type':type(exc).__name__,'resubmit_allowed':False})
        raise
    record={'job_id':str(job.job_id()),'backend':BACKEND,'account_name':ACCOUNT,
        'tag':intent['tag'],'plan_sha256':intent['plan_sha256'],'cap_seconds':CAP,
        'circuits':12,'shots':TOTAL,'submitted_unix':time.time(),'automatic_retry':False}
    print(json.dumps(record),flush=True)
    save(receipt,record)
    return job


def verify_cap(job):
    meta=safe.safe_provider('Provider cap lookup',job._api_client.job_get,job.job_id())
    result={'job_id':job.job_id(),'expected_cap_seconds':CAP,'provider_cost_field':meta.get('cost'),
            'verified':meta.get('cost')==CAP}
    safe.save_if_absent(RUN/'provider_cap_verification.json',result)
    if not result['verified']:
        # Protective cancellation of THIS job only, never another submission.
        try: canceled=safe.safe_provider('Protective cap cancellation',job.cancel)
        except Exception as exc: canceled=type(exc).__name__
        safe.save_if_absent(RUN/'cap_mismatch_stop.json',{'cancellation_result':canceled,'resubmit_allowed':False})
        raise RuntimeError('Provider cap unverified; stop')
    return result


def submit(confirmed=False):
    if not confirmed: raise PermissionError('Explicit --confirm-one-job-max-5s required')
    if LOCK.exists() or (RUN/'job_receipt.json').exists(): raise FileExistsError('Attempt consumed; recover/retrieve only')
    plan,pubs=frozen(); verify(RUN,'preflight_sha256.json')
    previous=read(RUN/'live_preflight.json')
    require(previous['budget']['pass'],'Previous budget rejected')
    service,backend,_,current=live_gate(plan,pubs)
    require(current['budget']['pass'],'Fresh dispatch budget rejected')
    require(current['instance_sha256']==previous['instance_sha256'],'IBM instance changed')
    require(current['options']==previous['options'],'Execution options changed')
    sampler=safe.safe_provider('Sampler setup',SamplerV2,mode=backend,options=current['options'])
    require(sampler.mode is None and sampler.options.max_execution_time==5,'Unexpected session/batch/cap')
    retry=safe.disable_retries(service,backend,sampler)
    save(RUN/'dispatch_live_check.json',{**current,**retry})
    log('ready_for_single_POST',{'budget':current['budget'],'circuits':12,'shots':TOTAL,'cap':5,'automatic_retry':False})
    intent={**plan,'plan_sha256':digest(RUN/'plan.json')}
    job=dispatch_once(LOCK,RUN/'job_receipt.json',intent,
        lambda:safe.safe_provider('Single authorized Sampler POST',sampler.run,pubs),confirmed=True)
    log('submitted',verify_cap(job))


def recover():
    if (RUN/'job_receipt.json').exists():
        print(json.dumps(read(RUN/'job_receipt.json')),flush=True); return
    attempt=read(LOCK)
    require(attempt['plan_sha256']==digest(RUN/'plan.json'),'Lock belongs to another plan')
    service=safe.safe_provider('IBM recovery authentication',QiskitRuntimeService,name=ACCOUNT)
    jobs=safe.safe_provider('Unique tag recovery',service.jobs,limit=10,backend_name=BACKEND,job_tags=[attempt['tag']])
    require(len(jobs)==1,'Recovery not unique; never resubmit')
    receipt={**attempt,'job_id':jobs[0].job_id(),'backend':BACKEND,'account_name':ACCOUNT,
             'circuits':12,'shots':TOTAL,'recovered':True,'automatic_retry':False}
    save(RUN/'job_receipt.json',receipt); verify_cap(jobs[0])
    print(json.dumps(receipt),flush=True)


def retrieve():
    receipt=read(RUN/'job_receipt.json')
    require(receipt['plan_sha256']==digest(RUN/'plan.json'),'Receipt mismatch')
    service=safe.safe_provider('IBM retrieval authentication',QiskitRuntimeService,name=ACCOUNT)
    job=safe.safe_provider('Existing job',service.job,receipt['job_id'])
    value=safe.safe_provider('Job status',job.status); status=str(getattr(value,'name',value))
    log('job_status',{'job_id':receipt['job_id'],'status':status})
    verify_cap(job)
    if status not in ('DONE','ERROR','CANCELED','CANCELLED'): return
    metrics=safe.safe_provider('Job metrics',job.metrics)
    safe.save_if_absent(RUN/'provider_metrics.json',metrics)
    if status!='DONE':
        safe.save_if_absent(RUN/'FAILED.json',{'status':status,'usage':metrics.get('usage'),'resubmit_allowed':False})
        return
    plan,expected=frozen()
    inputs=safe.safe_provider('Provider inputs',lambda:job.inputs)
    actual=[SamplerPub.coerce(p) for p in inputs['pubs']]
    require(len(actual)==len(expected)==12,'Provider PUB count mismatch')
    folder=RUN/'provider_inputs'; folder.mkdir(exist_ok=True)
    for i,(got,wanted) in enumerate(zip(actual,expected)):
        require(got.shape==wanted.shape==() and got.shots==wanted.shots==SHOTS,'Provider exposure mismatch')
        require(got.circuit==wanted.circuit,'Provider circuit mismatch')
        path=folder/f'circuit_{i:03d}.qpy'
        if not path.exists(): circuit_file(path,got.circuit)
    safe.save_if_absent(folder/'options.json',{k:v for k,v in inputs.items() if k!='pubs'})
    result=safe.safe_provider('Completed result',job.result)
    require(len(result)==12,'Incomplete result')
    safe.save_if_absent(RUN/'provider_result_complete.json',result)
    rows=[]
    for i,(pub,rec) in enumerate(zip(result,plan['records'])):
        meta=pub.metadata.get('circuit_metadata',{})
        require(meta.get('control_index')==i and meta.get('control_plan_sha256')==receipt['plan_sha256'],'Result order mismatch')
        require(meta.get('readout_mask_little_endian')==rec['readout_mask_little_endian'],'Provider mask mismatch')
        bits=pub.data.meas
        require(bits.num_bits==rec['width'] and bits.num_shots==SHOTS and bits.shape==(),'BitArray mismatch')
        strings=bits.get_bitstrings()
        decode_bitstrings(strings,rec['width'],rec['readout_mask_little_endian'])
        rows.append({**rec,'bitstrings':strings})
    safe.save_if_absent(RUN/'raw_bitstrings.json',{'job_id':receipt['job_id'],'records':rows})
    safe.save_if_absent(RUN/'retrieval_verification.json',{'status':'DONE_ARCHIVED_VERIFIED',
        'job_id':receipt['job_id'],'actual_shots':sum(len(r['bitstrings']) for r in rows),
        'provider_circuits_match':12,'provider_result_metadata_match':12,'usage':metrics.get('usage')})
    log('retrieved',{'job_id':receipt['job_id'],'shots':TOTAL,'usage':metrics.get('usage')})


def analyze():
    # Implemented below; this path never invokes the provider.
    return analyze_local()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','preflight','submit','recover','retrieve','analyze'])
    parser.add_argument('--confirm-one-job-max-5s',action='store_true')
    args=parser.parse_args(); logging.disable(logging.CRITICAL)
    try:
        if args.action=='submit': submit(args.confirm_one_job_max_5s)
        else: globals()[args.action]()
    except Exception as exc:
        print(json.dumps({'action':args.action,'error_type':type(exc).__name__,'automatic_resubmission':False}),flush=True)
        raise SystemExit(1) from None


def analyze_local():
    plan,_=frozen()
    retrieval=read(RUN/'retrieval_verification.json')
    require(retrieval['status']=='DONE_ARCHIVED_VERIFIED','No completed verified result')
    raw=read(RUN/'raw_bitstrings.json'); refs=read(RUN/'references.json')
    require(raw['job_id']==read(RUN/'job_receipt.json')['job_id'],'Wrong data source')
    require(len(raw['records'])==12,'Wrong raw record count')
    out=RUN/'analysis'
    if out.exists(): raise FileExistsError('Do not overwrite an analysis')
    blocks={}; calibrations={}; drift={}
    for rec,wanted in zip(raw['records'],plan['records']):
        require(all(rec[k]==v for k,v in wanted.items()),'Raw metadata changed')
        bits=decode_bitstrings(rec['bitstrings'],rec['width'],rec['readout_mask_little_endian'])
        require(len(bits)==SHOTS,'Missing shots')
        if rec['role']=='calibration': calibrations[rec['state'],rec['block']]=bits
        else: blocks[rec['setting_id'],rec['twirl_id']]=(rec,bits,pauli_samples(bits))
    fail=np.array([sum(calibrations[0,b].sum(axis=0) for b in ('start','end')),
                   sum((1-calibrations[1,b]).sum(axis=0) for b in ('start','end'))])
    errors=(fail+.5)/(2*SHOTS+1)
    require(np.all(1-errors.sum(axis=0)>.1),'Readout inverse unstable')
    for state in (0,1):
        drift[str(state)]={b:float(np.mean(calibrations[state,b] if state==0 else 1-calibrations[state,b])) for b in ('start','end')}
    rng=np.random.default_rng(plan['bootstrap_seed'])
    errors_boot=rng.beta(fail+.5,2*SHOTS-fail+.5,size=(BOOTSTRAP,2,72))
    summaries=[]; bootstrap_archive={}; independent_max=0.
    from threadpoolctl import threadpool_limits
    with threadpool_limits(limits=1):
        for setting in ('prep5','prep6','flo5_T04'):
            entries=[blocks[k] for k in sorted(blocks) if k[0]==setting]
            width=entries[0][0]['width']; n=width//2
            pts=[]; boot=[]; direct=[]
            for rec,bits,samples in entries:
                mask=np.array(rec['readout_mask_little_endian'])
                mean=samples.mean(axis=0)
                corrected=corrected_paulis(mean,mask,errors[:,:width])
                pts.append(np.stack([mean,corrected]))
                weights=rng.multinomial(SHOTS,np.full(SHOTS,1/SHOTS),size=BOOTSTRAP)
                means=weights@samples/SHOTS
                corrected_boot=corrected_paulis(means,mask,errors_boot[:,:,:width])
                boot.append(np.stack([means,corrected_boot],axis=1))
                native=bits^mask
                # Independent native pair-probability inversion, before unmasking.
                phys=[]
                for site in range(n):
                    a,b=2*site,2*site+1
                    probs=np.bincount(2*native[:,a]+native[:,b],minlength=4)/SHOTS
                    matrices=[]
                    for q in (a,b):
                        e0,e1=errors[:,q]
                        matrices.append(np.array([[1-e0,e1],[e0,1-e1]]))
                    probs=np.linalg.solve(np.kron(*matrices),probs)
                    probs=probs[np.arange(4)^(2*mask[a]+mask[b])]
                    phys.append([probs[1]+probs[2]+2*probs[3],probs[2]-probs[1],probs[3]])
                independent_max=max(independent_max,float(np.max(np.abs(np.array(phys)-physical_observables(corrected)))))
                # No decoder/Pauli helper in the independent total-number count.
                m=sum(int(v)<<q for q,v in enumerate(mask))
                direct.extend((int(s,2)^m).bit_count() for s in rec['bitstrings'])
            point=np.mean(pts,axis=0); bootp=np.mean(boot,axis=0)
            physical=physical_observables(point); bootphysical=physical_observables(bootp)
            reference=np.asarray(refs[setting]['physical'])
            require(abs(physical[0,:,0].sum()-np.mean(direct))<1e-11,'Independent popcount disagrees')
            bootstrap_archive[setting]=bootphysical
            allbits=np.concatenate([b for _,b,_ in entries])
            sector=np.mean((allbits[:,::2].sum(axis=1)==refs[setting]['N_up'])&
                           (allbits[:,1::2].sum(axis=1)==refs[setting]['N_down']))
            for arm_index,arm in enumerate(('raw','readout')):
                values=physical[arm_index]; samples=bootphysical[:,arm_index]
                delta=values-reference
                rmse=np.sqrt(np.mean(delta**2,axis=0))
                n_samples=samples[:,:,0].sum(axis=1)
                rms_samples=np.sqrt(np.mean((samples-reference)**2,axis=1))
                number=float(values[:,0].sum())
                z=point[arm_index,:width]
                row={'setting':setting,'arm':arm,'target_shots':len(direct),'calibration_shots_shared':2048,
                    'reference':refs[setting]['exact_for'],'expected_N':refs[setting]['N'],'N':number,
                    'N_95_interval':np.quantile(n_samples,[.025,.975]).tolist(),
                    'N_up':float(((1-z[::2])/2).sum()),'N_down':float(((1-z[1::2])/2).sum()),
                    'RMS_charge_spin_doublon':rmse.tolist(),
                    'RMS_95_intervals':np.quantile(rms_samples,[.025,.975],axis=0).tolist(),
                    'physical_profile':values.tolist(),'reference_profile':reference.tolist(),
                    'physical_95_intervals':np.quantile(samples,[.025,.975],axis=0).tolist(),
                    'raw_sector_fraction_not_postselected':float(sector),
                    'raw_number_histogram':dict(sorted(Counter(direct).items())),
                    'out_of_range_Paulis':int(np.sum(np.abs(point[arm_index])>1)),
                    'provisional_screen_pass':bool(np.all(rmse<=SCREEN) and abs(number-refs[setting]['N'])<=.5),
                    'screen_is_accuracy_certificate':False}
                summaries.append(row)
            log('analysis_setting',{'setting':setting,'readout_N':summaries[-1]['N'],
                'readout_RMS_charge_spin_doublon':summaries[-1]['RMS_charge_spin_doublon']})
    require(independent_max<2e-11,'Independent readout inverse disagrees')
    out.mkdir()
    metrics=read(RUN/'provider_metrics.json')
    result={'job_id':raw['job_id'],'status':'DIAGNOSTIC_COMPLETE','rows':summaries,
        'readout_errors_Jeffreys':errors.tolist(),'nominal_bookend_mean_bit_error':drift,
        'provider_shot_order_guaranteed':False,'independent_readout_max_error':independent_max,
        'bootstrap_replicates':BOOTSTRAP,'usage':metrics.get('usage'),'cap_seconds':5,
        'statistical_scope':'Conditional whole-shot bootstrap at fixed variants and shared independent calibration draws; excludes drift/correlated SPAM/readout model bias.',
        'no_clipping':True,'no_ZNE_PEC_TFLO_fit_postselection':True,'U8_hardware_authorized':False}
    save(out/'summary.json',result)
    np.savez_compressed(out/'bootstrap.npz',**bootstrap_archive)
    lines=['# Hardwarecontrole: voorbereiding en5x5 U=0','',
        f"Job: {raw['job_id']}. Maximaal5 QPU-seconden; providergebruik: {metrics.get('usage')}.",
        '12 circuits x512 shots:6144 totaal. Geen U8-hardware, ZNE, PEC, qDRIFT, TFLO-fit of postselectie.',
        '5x5 heeft22 deeltjes,6x6 heeft32. Spin=n_up-n_down. Alle ruwe bits zijn behouden.','',
        '| Controle | Analyse | N | N95%-interval | RMS lading | RMS spin | RMS doublon |',
        '|---|---|---:|---|---:|---:|---:|']
    for r in summaries:
        errors3=r['RMS_charge_spin_doublon']; interval=r['N_95_interval']
        lines.append(f"| {r['setting']} | {r['arm']} | {r['N']:.5f} | [{interval[0]:.5f}, {interval[1]:.5f}] | {errors3[0]:.5f} | {errors3[1]:.5f} | {errors3[2]:.5f} |")
    lines+=['','De U=0-vergelijking gebruikt de exacte IDEALE EINDIGE-CIRCUITreferentie; de afzonderlijke continue-tijdreferentie en Trotterconvergentie staan in references.json.',
        f'Onafhankelijke native uitleesmatrixinversie versus Pauli-methode: maximaal {independent_max:.3g} afwijking.',
        'De intervallen omvatten shot- en onafhankelijke kalibratieonzekerheid, niet drift, gecorreleerde SPAM of modelbias.',
        'De vooraf vastgelegde screen is diagnostisch en geen nauwkeurigheidscertificaat. Een correct totaal N alleen bewijst geen correcte lokale fysica.',
        'Als voorbereiding goed is maar U0-dynamica faalt, wijst dat op fouten tijdens de diepere uitvoering; het is geen bewijs welke afzonderlijke ruisbron verantwoordelijk is.',
        'Een geslaagde U0-controle bewijst nog geen nauwkeurige U8- of6x6-dynamica. Daarvoor is nieuwe toestemming en aparte validatie nodig.',
        'Physics- en veilige-API-skills stuurden onafhankelijke referenties, vaste analyse, budgetgrens en eenmalige indiening.','']
    (out/'RAPPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    save(out/'sha256.json',{str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file()})
    verify(out,'sha256.json')
    log('analysis_complete',{'independent_readout_max_error':independent_max,'usage':metrics.get('usage')})


if __name__=='__main__': main()
