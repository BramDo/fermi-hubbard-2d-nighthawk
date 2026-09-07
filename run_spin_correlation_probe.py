"""One bounded, CPU-only saved-state correlation probe; no hardware APIs."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMBA_NUM_THREADS'):
    os.environ[key]='1'
import argparse,hashlib,io,json,shutil,signal,subprocess,sys,time,unittest
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import psutil
from cuprate_2d_hubbard_pipeline import Cuprate2DConfig
from cuprate_2d_tflo import parameterized_network,bind
import cuprate_spin_correlation_probe as c

ROOT=Path(__file__).resolve().parent
RUN=ROOT/'results_cuprate_2d/spin_correlations_T04_2026-09-06_v1'
BASE=ROOT/'results_cuprate_2d/classical_full_6x6_mps_T04_v1'
LARGE=ROOT/'results_cuprate_2d/classical_full_6x6_mps_T04_chi64_v1'
PROFILES=[(3,chi,BASE/f'3x3_chi{chi}_threads3') for chi in (16,32,64)]+[
    (6,32,BASE/'6x6_chi32_threads1'),(6,64,LARGE/'6x6_chi64_threads1')]
TIMES=(.04,.08,.12,.24,.32,.48)
SOURCES=('ONDERZOEKSVOORSTEL_SPINCORRELATIES_2D.md','cuprate_spin_correlation_probe.py',
    'run_spin_correlation_probe.py','test_spin_correlation_probe.py','verify_classical_chi64_continuation.py',
    'cuprate_2d_tflo.py','cuprate_2d_hubbard_pipeline.py','cuprate_2d_fermionic_mapping.py','cuprate_2d_fermionic_dynamics.py')

def read(path): return json.loads(path.read_text())
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):
    with path.open('x',encoding='utf-8') as file:
        json.dump(value,file,indent=2,allow_nan=False); file.write('\n')
def log(stage,**values):
    row=dict(UTC=datetime.now(timezone.utc).isoformat(),stage=stage,**values)
    with (RUN/'progress.jsonl').open('a',encoding='utf-8') as file: file.write(json.dumps(row)+'\n')
    print(json.dumps(row),flush=True)

def check_inputs():
    plan=read(RUN/'plan.json')
    for name,expected in plan['inputs_sha256'].items():
        if digest(ROOT/name)!=expected: raise ValueError('Frozen input changed: '+name)
    return plan

def worker():
    check_inputs(); started=time.perf_counter(); deadline=started+180
    def guard():
        if time.perf_counter()>deadline: raise TimeoutError('180-second worker deadline')
        if psutil.Process().memory_info().rss>2*1024**3: raise MemoryError('2 GiB RSS limit')
    def alarm(signum,frame): raise TimeoutError('180-second alarm')
    signal.signal(signal.SIGALRM,alarm); signal.setitimer(signal.ITIMER_REAL,180)
    try:
        configs={}; rows={}; comparisons={}; local_checks={}; timings={}
        for size,chi,folder in PROFILES:
            guard(); key=f'{size}x{size}_chi{chi}'
            record=read(folder/'result.json'); cfg=Cuprate2DConfig(**record['config'])
            assert cfg.lx==cfg.ly==size and cfg.steps==2 and cfg.dt==.2 and cfg.u_over_t==8 and cfg.t_prime_over_t==-.25
            configs[size]=cfg; begun=time.perf_counter()
            arrays=c.load_arrays(folder)
            def progress(i,n):
                guard(); log('contracting',profile=key,mode=i,total=n)
            norm,z,zz=c.mps_moments(arrays,deadline=deadline,progress=progress)
            row=c.spin_from_z(z,zz); rows[key]=row
            difference=float(np.max(abs(row[3]-np.array(record['physical_means']))))
            assert abs(norm-1)<1e-9 and difference<1e-9
            local_checks[key]=dict(norm=norm,local_profile_max_abs=difference)
            timings[key]=time.perf_counter()-begun
            save(RUN/f'{key}.json',dict(**c.serialize(row),Z=z.tolist(),ZZ=zz.tolist(),
                source_folder=str(folder.relative_to(ROOT)),local_profile_check=local_checks[key],
                extraction_seconds=timings[key],not_full_simulation_time=True))
            log('profile_complete',profile=key,extraction_seconds=timings[key],local_profile_max_abs=difference)
        guard(); begun=time.perf_counter()
        from qiskit.quantum_info import Statevector
        cfg=configs[3]
        log('exact_anchor_started',qubits=18)
        state=Statevector.from_instruction(bind(parameterized_network(cfg),cfg,.4,8.)).data
        norm,z,zz=c.dense_z_moments(state,little_endian=True)
        assert abs(norm-1)<1e-10
        exact=c.spin_from_z(z,zz); rows['3x3_exact']=exact
        np.savez_compressed(RUN/'exact_3x3_state.npz',state=state)
        save(RUN/'3x3_exact.json',dict(**c.serialize(exact),Z=z.tolist(),ZZ=zz.tolist(),
            norm=norm,exact_for='finite two-step full t-t-prime-U circuit, not continuous exp(-iHT)',
            statevector_seconds=time.perf_counter()-begun))
        timings['3x3_exact']=time.perf_counter()-begun
        log('exact_anchor_complete',seconds=timings['3x3_exact'])
        for size,cfg in configs.items():
            guard(); begun=time.perf_counter()
            trained=[c.flo_spin_moments(cfg,T) for T in TIMES]
            average=c.mixture(trained)
            instant=c.flo_spin_moments(cfg,.4)
            rows[f'{size}x{size}_FLO_mean']=average; rows[f'{size}x{size}_FLO_T04']=instant
            save(RUN/f'{size}x{size}_FLO.json',dict(training_times=TIMES,
                mean=c.serialize(average),instant_T04=c.serialize(instant),
                training=[c.serialize(row) for row in trained],
                mixture_includes_between_time_classical_covariance=True,
                seconds=time.perf_counter()-begun))
            for method,row in [('FLO_mean',average),('FLO_T04',instant)]:
                reference=exact if size==3 else rows['6x6_chi64']
                comparisons[f'{size}x{size}_{method}_vs_'+('exact' if size==3 else 'chi64')]=c.compare(row[2],reference[2],size,size)
        for chi in (16,32,64):
            comparisons[f'3x3_chi{chi}_vs_exact']=c.compare(rows[f'3x3_chi{chi}'][2],exact[2],3,3)
        comparisons['3x3_chi32_vs_chi16']=c.compare(rows['3x3_chi32'][2],rows['3x3_chi16'][2],3,3)
        comparisons['3x3_chi64_vs_chi32']=c.compare(rows['3x3_chi64'][2],rows['3x3_chi32'][2],3,3)
        comparisons['6x6_chi64_vs_chi32']=c.compare(rows['6x6_chi64'][2],rows['6x6_chi32'][2],6,6)
        primary=[f'distance_{d}' for d in (1,2,3)]
        spread=comparisons['6x6_chi64_vs_chi32']
        gap=comparisons['6x6_FLO_mean_vs_chi64']
        convergence_screen=all(spread[k]['rms']<=.003 and spread[k]['max_abs']<=.01 for k in primary)
        flo_screen=all(gap[k]['rms']<=.01 and gap[k]['max_abs']<=.03 for k in primary)
        guard(); check_inputs()
        summary=dict(status='COMPLETE_EXPLORATORY_CORRELATION_PROBE',T=.4,steps=2,dt=.2,
            spin_convention='m=n_up-n_down=2S_z; C_m=4 C_Sz',comparisons=comparisons,
            saved_state_extraction_timings=timings,local_profile_checks=local_checks,
            six_by_six_chi32_to_64_screen_pass=convergence_screen,
            FLO_mean_within_proposed_tolerance_of_chi64=flo_screen,
            screening_only_not_certified_accuracy=True,chi64_exact=False,
            quantum_data_analyzed=False,hardware_seconds_added=0,
            U0_mixture_method='Average raw first and second moments, then subtract product of mixed means',
            runtime_seconds=time.perf_counter()-started,
            state='First T04 anchor only. No longer-time evolution, chi128/256, or new hardware performed.',
            peak_current_rss_bytes=psutil.Process().memory_info().rss)
        save(RUN/'summary.json',summary)
        log('worker_complete',seconds=summary['runtime_seconds'],chi_screen=convergence_screen,FLO_screen=flo_screen)
    except Exception as error:
        save(RUN/'FAILED.json',dict(type=type(error).__name__,message=str(error),seconds=time.perf_counter()-started,automatic_retry=False))
        raise
    finally: signal.setitimer(signal.ITIMER_REAL,0)

def driver():
    if RUN.exists(): raise FileExistsError('Preserve existing probe, do not overwrite or silently repeat')
    inputs=[ROOT/name for name in SOURCES]
    for _,_,folder in PROFILES:
        for name in ('result.json','mps_metadata.json','mps_arrays.npz'): inputs.append(folder/name)
    for archive in (BASE,LARGE):
        manifest=read(archive/'sha256.json')
        for name,expected in manifest.items(): assert digest(archive/name)==expected,name
        inputs.extend((archive/'sha256.json',archive/'plan.json'))
    RUN.mkdir(); (RUN/'source_snapshot').mkdir()
    for name in SOURCES: shutil.copyfile(ROOT/name,RUN/'source_snapshot'/name)
    save(RUN/'plan.json',dict(inputs_sha256={str(p.relative_to(ROOT)):digest(p) for p in inputs},
        budget=dict(worker_wall_seconds=180,process_wall_seconds=190,rss_bytes=2*1024**3,threads=1,hardware_seconds=0),
        screening=dict(primary_Manhattan_distances=[1,2,3],proposed_RMS=.01,proposed_max_abs=.03,
            MPS_spread_RMS=.003,MPS_spread_max_abs=.01,certification=False),
        scope='Saved-state T04 spin correlations with 3x3 exact anchor; all other proposal phases deferred',
        timestamp=datetime.now(timezone.utc).isoformat()))
    log('frozen',source_files=len(SOURCES),input_files=len(inputs))
    stream=io.StringIO()
    tests=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('test_spin_correlation_probe'))
    (RUN/'unit_tests.txt').write_text(stream.getvalue(),encoding='utf-8')
    if not tests.wasSuccessful(): raise RuntimeError('Independent tests failed before probe')
    log('tests_passed',tests=tests.testsRun)
    begun=time.perf_counter()
    try:
        process=subprocess.run([sys.executable,'-B','-u',str(Path(__file__)),'worker'],
            capture_output=True,text=True,timeout=190)
        (RUN/'worker_stdout_stderr.txt').write_text(process.stdout+'\n'+process.stderr,encoding='utf-8')
        save(RUN/'process_timing.json',dict(returncode=process.returncode,wall_seconds=time.perf_counter()-begun,
            includes_imports=True,includes_Windows_WSL_launcher=False,full_physics_simulation_time=False))
        print(process.stdout,flush=True)
        if process.returncode: raise RuntimeError('Worker failed; inspect preserved diagnostics')
    except subprocess.TimeoutExpired as error:
        save(RUN/'PROCESS_TIMEOUT.json',dict(wall_seconds=time.perf_counter()-begun,only_owned_worker_terminated=True,automatic_retry=False))
        raise
    check_inputs()
    save(RUN/'analysis_sha256.json',{str(p.relative_to(RUN)):digest(p) for p in RUN.rglob('*') if p.is_file()})
    print(json.dumps(read(RUN/'summary.json')),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('action',choices=('driver','worker'))
    globals()[parser.parse_args().action]()
