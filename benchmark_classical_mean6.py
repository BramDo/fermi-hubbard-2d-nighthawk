"""Measure an existing post-hoc classical baseline; never submit hardware."""
import time
START=time.perf_counter()
CPU_START=time.process_time()
import argparse,hashlib,json,os,platform,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
RUN=ROOT/'results_cuprate_2d/classical_mean6_timing_2026-09-06_v1'
HARDWARE=ROOT/'results_cuprate_2d/hardware_tflo_dd6_2026-09-06_v1'
CONFIG=dict(lx=6,ly=6,holes=4,hopping_t=1.0,t_prime_over_t=-.25,u_over_t=8,
    chemical_potential=0.,steps=2,dt=.2,boundary_x='open',boundary_y='open',
    initial_state='stripe_neel',shots=512)
TIMES=(.04,.08,.12,.24,.32,.48)

def deny_inputs_and_network(event,args):
    if event=='open' and args and isinstance(args[0],(str,bytes,os.PathLike)):
        name=os.fsdecode(args[0]).lower().replace('\\','/')
        if 'results_cuprate_2d' in name or '/.qiskit/' in name or name.endswith('.env'):
            raise PermissionError('Worker cannot read result archives or credentials')
    if event in ('socket.connect','socket.connect_ex','socket.getaddrinfo'):
        raise PermissionError('Network forbidden in this local benchmark')
    if event=='import' and args[0].startswith(('qiskit_ibm_runtime','fireopal')):
        raise PermissionError('Hardware provider imports forbidden')

def worker():
    sys.addaudithook(deny_inputs_and_network)
    import numpy as np
    import qiskit
    from cuprate_2d_hubbard_pipeline import Cuprate2DConfig,validate_config
    from cuprate_2d_tflo import flo_reference,physical_observables
    imported=time.perf_counter()
    compute_start=time.perf_counter(); compute_cpu=time.process_time()
    cfg=Cuprate2DConfig(**CONFIG); validate_config(cfg)
    paulis=[]; covariances=[]; per_reference=[]
    for value in TIMES:
        begun=time.perf_counter()
        p,c=flo_reference(cfg,value)
        paulis.append(p); covariances.append(c)
        per_reference.append(time.perf_counter()-begun)
    physical=physical_observables(np.array(paulis))
    prediction=physical.mean(axis=0)
    compute_seconds=time.perf_counter()-compute_start
    compute_cpu_seconds=time.process_time()-compute_cpu
    ready_seconds=time.perf_counter()-START
    residuals=dict(projector=0.,hermitian=0.,particle=0.,spin_sector=0.,
        cross_spin=0.,direct_covariance_observables=0.)
    for i,c in enumerate(covariances):
        density=c.diagonal().real; up=density[::2]; down=density[1::2]
        direct=np.stack((up+down,up-down,up*down-abs(c[np.arange(0,72,2),np.arange(1,72,2)])**2),axis=-1)
        checks=dict(projector=np.max(abs(c@c-c)),hermitian=np.max(abs(c-c.conj().T)),
            particle=abs(density.sum()-32),spin_sector=max(abs(up.sum()-16),abs(down.sum()-16)),
            cross_spin=np.max(abs(c[::2,1::2])),direct_covariance_observables=np.max(abs(direct-physical[i])))
        for name,value in checks.items(): residuals[name]=max(residuals[name],float(value))
    assert max(residuals.values())<1e-11,residuals
    from threadpoolctl import threadpool_info
    pools=threadpool_info()
    assert all(p['num_threads']==1 for p in pools if p['user_api']=='blas'),pools
    result=dict(schema='classical-mean6-worker-v1',config=CONFIG,times=TIMES,
        import_and_script_start_seconds=imported-START,kernel_seconds=compute_seconds,
        kernel_cpu_seconds=compute_cpu_seconds,python_to_result_ready_seconds=ready_seconds,
        per_reference_seconds=per_reference,training_paulis=np.array(paulis).tolist(),
        training_physical=physical.tolist(),prediction=prediction.tolist(),N=float(prediction[:,0].sum()),
        verification_residuals=residuals,python_including_checks_seconds=time.perf_counter()-START,
        process_cpu_through_checks_seconds=time.process_time()-CPU_START,
        runtime=dict(python=platform.python_version(),numpy=np.__version__,qiskit=qiskit.__version__,
            executable=sys.executable,platform=platform.platform(),pid=os.getpid(),threadpools=pools),
        archive_reads_allowed=False,network_allowed=False,hardware_used=False,
        stored_training_references_used=False,U8_target_data_used=False)
    print(json.dumps(result,allow_nan=False),flush=True)

def read(path): return json.loads(path.read_text())
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):
    with path.open('x',encoding='utf-8') as file:
        json.dump(value,file,indent=2,allow_nan=False); file.write('\n')

def analyze():
    import numpy as np
    raw=read(RUN/'windows_timings.json'); runs=raw['runs']
    assert len(runs)==5 and all(r['returncode']==0 for r in runs)
    plan=read(HARDWARE/'plan.json'); refs=read(HARDWARE/'references.json')
    assert plan['config']==CONFIG
    classical_path=ROOT/'results_cuprate_2d/classical_full_6x6_mps_T04_chi64_v1/summary.json'
    classical=read(classical_path)
    summary=read(HARDWARE/'analysis/summary.json')
    audit=read(HARDWARE/'delivery_audit.json')
    reference=np.array(classical['result']['physical_means'])
    expected=np.array([refs[f'train{i}']['physical'] for i in range(6)])
    previous=np.array(audit['additional_posthoc_diagnostic_not_a_selected_method']['RMS_to_uncertified_U8_chi64'])
    max_reference_difference=0.; max_rms_difference=0.; max_repeat_difference=0.
    for run in runs:
        result=run['worker']; assert result['config']==CONFIG and result['times']==list(TIMES)
        assert not result['hardware_used'] and not result['stored_training_references_used'] and not result['U8_target_data_used']
        actual=np.array(result['training_physical']); pred=np.array(result['prediction'])
        assert actual.shape==(6,36,3) and pred.shape==(36,3)
        delta=float(np.max(abs(actual-expected)))
        rms=np.sqrt(np.mean((pred-reference)**2,axis=0))
        max_reference_difference=max(max_reference_difference,delta)
        max_rms_difference=max(max_rms_difference,float(np.max(abs(rms-previous))))
        max_repeat_difference=max(max_repeat_difference,float(np.max(abs(pred-np.array(runs[0]['worker']['prediction'])))))
    assert max(max_reference_difference,max_rms_difference,max_repeat_difference)<1e-12
    def statistics(values):
        return dict(all_seconds=values,median_seconds=float(np.median(values)),
            minimum_seconds=min(values),maximum_seconds=max(values),repetitions=len(values))
    timings={key:statistics([r['worker'][key] for r in runs]) for key in
        ('kernel_seconds','import_and_script_start_seconds','python_to_result_ready_seconds','python_including_checks_seconds')}
    timings['windows_wsl_python_complete']=statistics([r['windows_call_seconds'] for r in runs])
    hardware=next(r for r in summary['target_rows'] if r['dd'] and r['arm']=='readout_tflo')
    metrics=read(HARDWARE/'provider_metrics.json')
    from datetime import datetime
    begin=datetime.fromisoformat(metrics['timestamps']['running'].replace('Z','+00:00'))
    end=datetime.fromisoformat(metrics['timestamps']['finished'].replace('Z','+00:00'))
    verification=dict(training_profiles_match_archive_max_abs=max_reference_difference,
        historical_RMS_reproduced_max_abs=max_rms_difference,repeat_profile_max_abs=max_repeat_difference,
        config_matches_frozen_plan=True,all_references_recomputed=True,
        comparison_loaded_after_timed_workers=True,source_hashes_match_protocol_manifest=True)
    frozen=read(RUN/'source_sha256.json')
    for name,expected_hash in frozen.items(): assert digest(ROOT/name)==expected_hash,name
    report=dict(status='COMPLETE_TIMING_OF_POSTHOC_CLASSICAL_CONTROL',timings=timings,
        classical_control_RMS_charge_spin_doublon=rms.tolist(),N=runs[0]['worker']['N'],
        hardware_TFLO_DD_RMS_charge_spin_doublon=hardware['RMS_charge_spin_doublon'],
        control_RMS_smaller_in_all_three=bool(np.all(rms<np.array(hardware['RMS_charge_spin_doublon']))),
        old_MPS_kernel_seconds=classical['result']['kernel_seconds'],
        old_MPS_cold_worker_seconds=classical['process_timing']['cold_worker_seconds'],
        old_MPS_had_concurrent_local_work=classical['process_timing']['measured_with_concurrent_local_work'],
        QPU_charged_seconds=metrics['usage']['qpu_charge_time_seconds'],
        quantum_service_running_to_done_seconds=(end-begin).total_seconds(),
        quantum_analysis_archive_and_bootstrap_seconds=summary['seconds'],
        quantum_full_end_to_end_seconds_not_measured=True,
        verification=verification,benchmark_scope='Five fresh processes; OS caches and other machine load uncontrolled; six references recomputed each time. Existing code, no performance tuning.',
        scientific_scope='Post-hoc, fixed single-endpoint heuristic, not a U-dependent interacting dynamics solver. chi64 reference uncertified. No prospective tolerance or quantum advantage certification.',
        hardware_seconds_added=0,
        source_artifact_sha256={str(p.relative_to(ROOT)):digest(p) for p in
            (HARDWARE/'plan.json',HARDWARE/'references.json',HARDWARE/'analysis/summary.json',
             HARDWARE/'delivery_audit.json',HARDWARE/'provider_metrics.json',HARDWARE/'delivery_sha256.json',classical_path)})
    save(RUN/'summary.json',report); save(RUN/'verification.json',verification)
    print(json.dumps(report),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('action',choices=('worker','analyze'))
    args=parser.parse_args()
    globals()[args.action]()
