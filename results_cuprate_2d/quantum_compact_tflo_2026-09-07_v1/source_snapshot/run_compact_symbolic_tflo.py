"""Bounded offline preparation of a compact, parameter-matched TFLO family."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMBA_NUM_THREADS'):
    os.environ[key]='1'
import argparse,gzip,hashlib,io,json,shutil,signal,subprocess,sys,time,unittest
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import psutil
from qiskit import qpy
from cuprate_2d_hubbard_pipeline import Cuprate2DConfig
from cuprate_2d_tflo import explicit_twirl,embed_measurement,bind,skeleton
import compact_symbolic_tflo as optimize

ROOT=Path(__file__).resolve().parent
OLD=ROOT/'results_cuprate_2d/hardware_tflo_dd6_2026-09-06_v1'
RUN=ROOT/'results_cuprate_2d/quantum_compact_tflo_2026-09-07_v1'
SOURCES=('QUANTUM_COMPACT_TFLO_PROTOCOL.md','compact_symbolic_tflo.py','run_compact_symbolic_tflo.py',
    'test_compact_symbolic_tflo.py','cuprate_2d_tflo.py','compile_tflo_dd6_blocks.py',
    'cuprate_2d_hubbard_pipeline.py','cuprate_2d_fermionic_mapping.py','cuprate_2d_fermionic_dynamics.py')

def read(path): return json.loads(path.read_text())
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):
    with path.open('x',encoding='utf-8') as file:
        json.dump(value,file,indent=2,allow_nan=False); file.write('\n')
def log(stage,**values):
    row=dict(UTC=datetime.now(timezone.utc).isoformat(),stage=stage,**values)
    with (RUN/'progress.jsonl').open('a',encoding='utf-8') as file: file.write(json.dumps(row)+'\n')
    print(json.dumps(row),flush=True)
def qpy_bytes(circuit):
    output=io.BytesIO(); qpy.dump(circuit,output); return output.getvalue()
def store_qpy(name,circuit):
    path=RUN/'circuits'/name
    data=qpy_bytes(circuit)
    with path.open('xb') as file: file.write(data)
    recovered=qpy.load(io.BytesIO(data))[0]
    if qpy_bytes(recovered)!=data: raise ValueError('QPY byte roundtrip mismatch')
    packed=RUN/'git_qpy_mirrors'/(name+'.gz')
    with packed.open('xb') as file:
        with gzip.GzipFile(filename='',mode='wb',fileobj=file,mtime=0) as target: target.write(data)
    with gzip.open(packed,'rb') as file:
        if hashlib.file_digest(file,'sha256').hexdigest()!=hashlib.sha256(data).hexdigest(): raise ValueError('Lossless QPY mirror mismatch')
    return dict(file=str(path.relative_to(RUN)),sha256=digest(path),bytes=len(data),
        gzip=str(packed.relative_to(RUN)),gzip_sha256=digest(packed),gzip_bytes=packed.stat().st_size)

def metrics(circuit,timing):
    durations={(name,tuple(wires)):duration for name,wires,duration in timing['durations']}
    dt=timing['dt']; clocks=np.zeros(circuit.num_qubits,dtype=np.int64)
    depths=np.zeros(circuit.num_qubits,dtype=np.int64); czdepth=np.zeros(circuit.num_qubits,dtype=np.int64)
    index={q:i for i,q in enumerate(circuit.qubits)}
    for inst in circuit.data:
        name=inst.operation.name; wires=tuple(index[q] for q in inst.qubits)
        if name=='barrier':
            clocks[list(wires)]=max(clocks[list(wires)]); depths[list(wires)]=max(depths[list(wires)]); continue
        if (name,wires) not in durations: raise ValueError('No saved native timing for '+str((name,wires)))
        duration=durations[name,wires]/dt
        if abs(duration-round(duration))>1e-6 or duration<0: raise ValueError('Invalid saved timing')
        clocks[list(wires)]=max(clocks[list(wires)])+round(duration)
        depths[list(wires)]=max(depths[list(wires)])+1
        if name=='cz': czdepth[list(wires)]=max(czdepth[list(wires)])+1
    counts=dict(circuit.count_ops())
    return dict(CZ=counts.get('cz',0),physical_X_SX=counts.get('x',0)+counts.get('sx',0),
        depth=int(max(depths)),CZ_depth=int(max(czdepth)),counts=counts,
        saved_snapshot_ASAP_seconds=float(max(clocks)*dt),saved_snapshot_duration_dt=int(max(clocks)),
        live_backend_verified=False,hardware_tested=False)

def check_inputs():
    plan=read(RUN/'plan.json')
    for name,h in plan['input_sha256'].items():
        if digest(ROOT/name)!=h: raise ValueError('Frozen input changed: '+name)
    return plan

def worker():
    plan=check_inputs(); cfg=Cuprate2DConfig(**plan['config'])
    started=time.perf_counter(); deadline=started+600
    def guard():
        if time.perf_counter()>deadline: raise TimeoutError('600-second worker limit')
        if psutil.Process().memory_info().rss>2*1024**3: raise MemoryError('2 GiB RSS limit')
    def alarm(signum,frame): raise TimeoutError('600-second alarm')
    signal.signal(signal.SIGALRM,alarm); signal.setitimer(signal.ITIMER_REAL,600)
    try:
        raw=(OLD/'local_only/parameterized72_blocks.qpy').read_bytes()
        original=qpy.load(io.BytesIO(raw))[0]
        if qpy_bytes(original)!=raw: raise ValueError('Original QPY byte roundtrip failed')
        if original.num_qubits!=72 or original.num_clbits or original.count_ops().get('cz')!=20736:
            raise ValueError('Unexpected original native template')
        def progress(i,check):
            guard(); log('native_round',round=i,CZ=check['counts'].get('cz',0),
                CZ_removed=check['cancellation']['CZ_removed'],counts=check['counts'])
        reduced,proof=optimize.optimize(original,rounds=3,progress=progress)
        save(RUN/'native_rewrite_proof.json',proof)
        saved=[store_qpy('native72_compact_parameterized.qpy',reduced)]
        reports=[]; binding_checks=[]
        for twirl in range(4):
            guard(); seed=202609061600+twirl
            before,mask=explicit_twirl(original,seed)
            candidate,newmask=explicit_twirl(reduced,seed)
            if len(mask)!=len(newmask): raise ValueError('Mask width mismatch')
            # A changed CZ count changes RNG consumption. Each circuit keeps its
            # own explicit mask; physics comparisons unmask using that own mask.
            compact,check=optimize.compact_constants(candidate)
            physical_old=embed_measurement(before,plan['layout72'],120)
            physical_new=embed_measurement(compact,plan['layout72'],120)
            old_metrics=metrics(physical_old,plan['timing']); new_metrics=metrics(physical_new,plan['timing'])
            expected=skeleton(physical_new)
            expected_map=[(physical_new.find_bit(i.qubits[0]).index,physical_new.find_bit(i.clbits[0]).index)
                for i in physical_new.data if i.operation.name=='measure']
            if expected_map!=list(zip(plan['layout72'],range(72))): raise ValueError('Readout order changed')
            for setting in plan['settings']:
                bound=bind(physical_new,cfg,setting['T'],setting['U'])
                if bound.num_parameters or skeleton(bound)!=expected or dict(bound.count_ops())!=new_metrics['counts']:
                    raise ValueError('Binding changed pulse/gate structure')
                if bound.metadata['readout_mask_little_endian']!=newmask.tolist(): raise ValueError('Mask changed on binding')
                binding_checks.append(dict(twirl=twirl,setting=setting['id'],T=setting['T'],U=setting['U'],
                    skeleton_sha256=expected,bound_qpy_sha256=hashlib.sha256(qpy_bytes(bound)).hexdigest()))
            saved.append(store_qpy(f'physical120_compact_parameterized_twirl{twirl}.qpy',physical_new))
            save(RUN/f'twirl{twirl}_constant_rewrite_proof.json',check)
            reports.append(dict(twirl=twirl,seed=seed,before=old_metrics,after=new_metrics,
                old_readout_mask=mask.tolist(),new_readout_mask=newmask.tolist(),
                masks_equal=bool(np.array_equal(mask,newmask)),CZ_twirl_draws_change_if_gate_count_changes=True,
                skeleton_sha256=expected,measurement_map=expected_map))
            log('twirl_complete',twirl=twirl,before_us=old_metrics['saved_snapshot_ASAP_seconds']*1e6,
                after_us=new_metrics['saved_snapshot_ASAP_seconds']*1e6,CZ_before=old_metrics['CZ'],CZ_after=new_metrics['CZ'],
                pulses_before=old_metrics['physical_X_SX'],pulses_after=new_metrics['physical_X_SX'])
        guard(); check_inputs()
        save(RUN/'binding_checks.json',binding_checks)
        save(RUN/'qpy_mirrors.json',saved)
        summary=dict(status='COMPLETE_OFFLINE_COMPACT_PARAMETERIZED_FAMILY',config=plan['config'],
            twirls=reports,native_before_counts=dict(original.count_ops()),native_after_counts=dict(reduced.count_ops()),
            all_36_bindings_preserve_structure=len(binding_checks)==36,
            symbolic_cleanup_before_binding=True,DD_inserted=False,
            all_four_snapshot_durations_shorter=all(r['after']['saved_snapshot_ASAP_seconds']<r['before']['saved_snapshot_ASAP_seconds'] for r in reports),
            physics_terms_removed=False,Trotter_steps_reduced=False,physical_layout_changed=False,
            exactness='Full72 per-wire constant2x2/symbolic-anchor proof; explicit diagonal CZ cancellation witnesses; small-system full operator and random-state checks.',
            hardware_error_reduction_measured=False,TFLO_holdouts_validated_on_new_hardware=False,
            ready_for_submission=False,new_hardware_authorization=False,hardware_seconds_used=0,
            previous_authorization_consumed=True,old_data_modified=False,
            estimated_durations_use_old_calibration_only=True,runtime_seconds=time.perf_counter()-started)
        save(RUN/'summary.json',summary)
        log('worker_complete',seconds=summary['runtime_seconds'],CZ_before=summary['native_before_counts'].get('cz'),
            CZ_after=summary['native_after_counts'].get('cz'),shorter_all_twirls=summary['all_four_snapshot_durations_shorter'])
    except Exception as error:
        save(RUN/'FAILED.json',dict(type=type(error).__name__,message=str(error),elapsed_seconds=time.perf_counter()-started,
            automatic_retry=False,hardware_seconds=0))
        raise
    finally: signal.setitimer(signal.ITIMER_REAL,0)

def driver():
    if RUN.exists(): raise FileExistsError('Do not overwrite or silently retry this offline preparation')
    old=read(OLD/'plan.json'); frozen=read(OLD/'frozen_inputs_sha256.json')
    names=('local_only/parameterized72_blocks.qpy','scheduling_target.json')
    for name in names:
        if digest(OLD/name)!=frozen[name]: raise ValueError('Frozen original input mismatch')
    for name in ('cuprate_2d_tflo.py','cuprate_2d_fermionic_mapping.py','cuprate_2d_fermionic_dynamics.py','cuprate_2d_hubbard_pipeline.py'):
        if digest(ROOT/name)!=old['source_sha256'][name]: raise ValueError('Original physics source changed')
    RUN.mkdir()
    for folder in ('source_snapshot','circuits','git_qpy_mirrors'): (RUN/folder).mkdir()
    for name in SOURCES: shutil.copyfile(ROOT/name,RUN/'source_snapshot'/name)
    inputs=[ROOT/name for name in SOURCES]+[OLD/name for name in names]+[OLD/'plan.json',OLD/'delivery_sha256.json']
    save(RUN/'plan.json',dict(config=old['config'],layout72=old['layout72'],settings=old['settings'],
        timing=read(OLD/'scheduling_target.json'),input_sha256={str(p.relative_to(ROOT)):digest(p) for p in inputs},
        hardware_authorized=False,read_only_old_archives=True,worker_limit_seconds=600,process_limit_seconds=630,
        source_old_job=read(OLD/'job_receipt.json')['job_id'],created_UTC=datetime.now(timezone.utc).isoformat()))
    log('frozen',inputs=len(inputs))
    stream=io.StringIO()
    tests=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('test_compact_symbolic_tflo'))
    (RUN/'unit_tests.txt').write_text(stream.getvalue(),encoding='utf-8')
    if not tests.wasSuccessful(): print(stream.getvalue(),flush=True); raise RuntimeError('Tests failed before full72 optimization')
    log('tests_passed',count=tests.testsRun)
    begun=time.perf_counter()
    try:
        result=subprocess.run([sys.executable,'-B','-u',str(Path(__file__)),'worker'],capture_output=True,text=True,timeout=630)
        (RUN/'worker_stdout_stderr.txt').write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
        save(RUN/'process_timing.json',dict(returncode=result.returncode,seconds=time.perf_counter()-begun,includes_Windows_WSL_launcher=False))
        print(result.stdout,flush=True)
        if result.returncode: print(result.stderr,flush=True); raise RuntimeError('Preserved worker failure; do not silently retry')
    except subprocess.TimeoutExpired:
        save(RUN/'PROCESS_TIMEOUT.json',dict(seconds=time.perf_counter()-begun,only_owned_worker_terminated=True,automatic_retry=False))
        raise
    check_inputs()
    save(RUN/'analysis_sha256.json',{str(p.relative_to(RUN)):digest(p) for p in RUN.rglob('*') if p.is_file()})
    print(json.dumps(read(RUN/'summary.json')),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('action',choices=('driver','worker'))
    globals()[parser.parse_args().action]()
