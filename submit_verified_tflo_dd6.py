"""Single authorized POST with fresh provider checks and immutable-preflight reuse."""
import argparse,hashlib,io,json,logging,math,shutil,time
from pathlib import Path
from qiskit import qpy
from qiskit.primitives.containers import SamplerPub
from qiskit_ibm_runtime import QiskitRuntimeService,SamplerV2
import run_tflo_dd6_once as r
import cuprate_2d_tflo_dd6 as m


def cached_pubs(plan,previous):
    """Identical bytes + identical SDK version preserve completed native validation."""
    r.require(previous['status']=='PASS_NOT_SUBMITTED' and previous['budget']['pass'],'No passing full preflight')
    r.require(previous['plan_sha256']==r.digest(r.RUN/'plan.json'),'Preflight plan mismatch')
    r.require(0<=time.time()-previous['checked_unix']<=1800,'Full preflight older than30min')
    r.require(plan['cap_seconds']==15 and plan['total_PUBs']==76 and plan['total_shots']==38912,'Scope changed')
    r.require(plan['authorized_one_new_job'] and not plan['automatic_retry'],'Wrong authority')
    r.require(plan['runtime']['qiskit']==r.qiskit.__version__ and plan['runtime']['qiskit_ibm_runtime']==r.qiskit_ibm_runtime.__version__,'SDK version changed')
    m.validate_records(plan['records'])
    for name,h in plan['source_sha256'].items(): r.require(r.digest(r.ROOT/name)==h,'Original source changed')
    manifest=r.read(r.RUN/'frozen_inputs_sha256.json'); pubs=[]
    for i,rec in enumerate(plan['records']):
        relative=f'bound_inputs/circuit_{i:03d}.qpy'
        data=(r.RUN/relative).read_bytes()
        r.require(hashlib.sha256(data).hexdigest()==manifest[relative],'Validated input bytes changed')
        c=qpy.load(io.BytesIO(data))[0]
        meta=c.metadata or {}
        r.require(meta.get('pilot_plan_sha256')==previous['plan_sha256'] and meta.get('pilot_index')==i,'PUB provenance')
        r.require(all(meta.get(k)==v for k,v in rec.items()),'PUB metadata changed')
        r.require(c.num_qubits==120 and c.num_clbits==72 and c.num_parameters==0,'PUB shape changed')
        pubs.append(SamplerPub.coerce((c,None,rec['shots'])))
    r.require(len(pubs)==76 and sum(p.shots for p in pubs)==38912,'Exposure changed')
    return pubs


def submit(confirmed=False):
    if not confirmed: raise PermissionError('Literal --confirm-one-job-max-15s is required')
    r.require(not r.LOCK.exists() and not (r.RUN/'job_receipt.json').exists(),'Attempt consumed; recover only')
    r.require(not (r.RUN/'dispatch_live_check.json').exists(),'Existing dispatch record; inspect, do not repeat automatically')
    r.verify(r.RUN,'frozen_inputs_sha256.json'); r.verify(r.RUN,'preflight_sha256.json')
    plan=r.read(r.RUN/'plan.json'); previous=r.read(r.RUN/'live_preflight.json')
    pubs=cached_pubs(plan,previous)
    service=r.safe.safe_provider('Fresh dispatch authentication',QiskitRuntimeService,name=r.ACCOUNT)
    b=r.safe.safe_provider('Fresh dispatch backend',service.backend,r.BACKEND)
    status=r.safe.safe_provider('Fresh dispatch status',b.status)
    r.require(status.operational and b.num_qubits==120,'Backend unavailable')
    props=r.safe.safe_provider('Fresh dispatch properties',b.properties)
    # Stronger than a selected-subgraph test. Any faulty qubit/gate blocks this cached route.
    r.require(not props.faulty_qubits() and not props.faulty_gates(),'Fault reported; cached dispatch prohibited')
    fp,_=m.fingerprint(b.target,plan['layout72'])
    r.require(fp==plan['timing_fingerprint']==previous['timing_fingerprint'],'Native timing/topology changed')
    r.require('delay' in b.target.operation_names,'Delay support changed')
    opts=r.options(b,plan['tag'])
    r.require(opts==previous['options'] and opts['max_execution_time']==15,'Execution options changed')
    instance=hashlib.sha256(str(service.active_account().get('instance','')).encode()).hexdigest()
    r.require(instance==previous['instance_sha256'],'Account instance changed')
    quota=m.quota(r.safe.safe_provider('Fresh dispatch quota',service.usage))
    rep=float(b.default_rep_delay)
    r.require(b.rep_delay_range[0]<=rep<=b.rep_delay_range[1],'Invalid repetition delay')
    # Padding may touch unused physical wires: conservatively account for all120 resets.
    reset=max(float(b.target['reset'][(q,)].duration) for q in range(120))
    r.require(math.isfinite(reset) and reset>=0,'Invalid reset duration')
    timing=previous['timing_by_pub']
    r.require([x['index'] for x in timing]==list(range(76)) and all(x['shots']==512 for x in timing),'Preflight exposure changed')
    r.require(all(math.isfinite(x['duration_seconds']) and x['duration_seconds']>0 for x in timing),'Invalid cached duration')
    budget=m.budget(sum(x['shots']*(x['duration_seconds']+reset+rep) for x in timing))
    r.require(budget['pass'],'Fresh budget rejected')
    sampler=r.safe.safe_provider('Sampler setup',SamplerV2,mode=b,options=opts)
    r.require(sampler.mode is None and sampler.options.max_execution_time==15,'Wrong mode or cap')
    retries=r.safe.disable_retries(service,b,sampler)
    extra=r.RUN/'additional_checks'; extra.mkdir(exist_ok=True)
    path=extra/Path(__file__).name
    if not path.exists(): shutil.copyfile(Path(__file__),path)
    r.require(r.digest(path)==r.digest(Path(__file__)),'Dispatch source snapshot changed')
    report={'checked_unix':time.time(),'backend':r.BACKEND,'pending_jobs':status.pending_jobs,
        'properties_updated':str(props.last_update_date),'instance_sha256':instance,
        'timing_fingerprint':fp,'options':opts,'quota':quota,'budget':budget,
        'reset_all120_seconds':reset,'rep_delay_seconds':rep,'plan_sha256':r.digest(r.RUN/'plan.json'),
        'full_preflight_sha256':r.digest(r.RUN/'live_preflight.json'),
        'full_ISA_and_duration_checks_reused_only_for_identical_bytes_and_target':True,
        'all120_fault_flags_freshly_clear':True,'script_sha256':r.digest(Path(__file__)),**retries}
    r.save(r.RUN/'dispatch_live_check.json',report)
    r.log('ready_for_single_POST',cap=15,circuits=76,shots=38912,budget=budget,
        fresh_status_quota_timing_and_fault_checks=True,unchanged_full_preflight_reused=True)
    job=r.dispatch_once(r.LOCK,r.RUN/'job_receipt.json',{**plan,'plan_sha256':report['plan_sha256']},
        lambda:r.safe.safe_provider('Single authorized Sampler POST',sampler.run,pubs),confirmed=True)
    r.log('submitted',**r.verify_cap(job))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--confirm-one-job-max-15s',action='store_true')
    args=parser.parse_args(); logging.disable(logging.CRITICAL)
    try: submit(args.confirm_one_job_max_15s)
    except Exception as exc:
        print(json.dumps({'error_type':type(exc).__name__,'automatic_resubmission':False}),flush=True)
        raise SystemExit(1) from None
