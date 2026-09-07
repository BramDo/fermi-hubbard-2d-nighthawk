"""Independent comparison to actual old provider inputs and SDK timing."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key]='1'
import hashlib,io,json,time
from pathlib import Path
from qiskit import qpy
from qiskit.circuit import Parameter,Measure,Reset
from qiskit.circuit.library import RZGate,SXGate,XGate,CZGate
from qiskit.transpiler import Target,InstructionProperties
from cuprate_2d_hubbard_pipeline import Cuprate2DConfig
from cuprate_2d_tflo import bind
from cuprate_2d_shallow_network import verify_cleanup

ROOT=Path(__file__).resolve().parent
RUN=ROOT/'results_cuprate_2d/quantum_compact_tflo_2026-09-07_v1'
OLD=ROOT/'results_cuprate_2d/hardware_tflo_dd6_2026-09-06_v1'
def read(p): return json.loads(p.read_text())
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p): return qpy.load(io.BytesIO(p.read_bytes()))[0]

def main():
    if (RUN/'independent_verification.json').exists(): raise FileExistsError('Preserve verification')
    started=time.perf_counter(); plan=read(RUN/'plan.json'); summary=read(RUN/'summary.json')
    for name,h in read(RUN/'analysis_sha256.json').items(): assert digest(RUN/name)==h,name
    for name,h in plan['input_sha256'].items(): assert digest(ROOT/name)==h,name
    cfg=Cuprate2DConfig(**plan['config']); oldplan=read(OLD/'plan.json')
    oldmanifest=read(OLD/'hardware_archive_sha256.json')
    timings=plan['timing']; target=Target(num_qubits=120,dt=timings['dt'],
        granularity=timings['granularity'],min_length=timings['min_length'],
        pulse_alignment=timings['pulse_alignment'],acquire_alignment=timings['acquire_alignment'])
    gates={'rz':RZGate(Parameter('theta')),'sx':SXGate(),'x':XGate(),'cz':CZGate(),'measure':Measure(),'reset':Reset()}
    for name,gate in gates.items():
        props={tuple(wires):InstructionProperties(duration=duration) for op,wires,duration in timings['durations'] if op==name}
        if props: target.add_instruction(gate,props)
    checks=[]; timing_checks=[]; readout_maps=[]
    for twirl,setting_id in [(i,'target') for i in range(4)]+[(0,'holdout1')]:
        record_index=next(i for i,r in enumerate(oldplan['records']) if r['role']!='calibration'
            and not r['dd'] and r['twirl_id']==twirl and r['setting_id']==setting_id)
        record=oldplan['records'][record_index]
        oldpath=OLD/'provider_inputs'/f'circuit_{record_index:03d}.qpy'
        assert digest(oldpath)==oldmanifest[str(oldpath.relative_to(OLD))]
        executed=load(oldpath)
        unscheduled=executed.copy_empty_like()
        for item in executed.data:
            if item.operation.label=='tflo_dd_echo_x': raise ValueError('Expected DD-off old circuit')
            if item.operation.name in ('delay','barrier'): continue
            unscheduled.append(item.operation,[executed.find_bit(q).index for q in item.qubits],
                [executed.find_bit(q).index for q in item.clbits])
        unscheduled.global_phase=executed.global_phase
        template=load(RUN/'circuits'/f'physical120_compact_parameterized_twirl{twirl}.qpy')
        candidate=bind(template,cfg,record['T'],record['U'])
        assert candidate.metadata['readout_mask_little_endian']==record['readout_mask_little_endian']
        check=verify_cleanup(unscheduled,candidate)
        checks.append(dict(twirl=twirl,setting=setting_id,old_provider_index=record_index,
            old_provider_sha256=digest(oldpath),**check))
        if setting_id=='target':
            duration=float(candidate.estimate_duration(target,unit='s'))
            before=float(unscheduled.estimate_duration(target,unit='s'))
            expected=summary['twirls'][twirl]
            assert abs(duration-expected['after']['saved_snapshot_ASAP_seconds'])<1e-12
            assert abs(before-expected['before']['saved_snapshot_ASAP_seconds'])<1e-12
            timing_checks.append(dict(twirl=twirl,sdk_before_seconds=before,sdk_after_seconds=duration,
                integer_clock_agrees=True))
        print(json.dumps({'verified_old_provider_input':record_index,'twirl':twirl,'setting':setting_id}),flush=True)
    result=dict(status='PASS',actual_old_provider_circuits_compared=checks,SDK_timing_checks=timing_checks,
        no_full72_statevector_used=True,all_old_readout_masks_preserved=True,
        delay_removal_for_ideal_comparison_only=True,
        unitary_error_claim_scope='Per-wire2x2 segment equality and global phase with unchanged CZ trace; not an interval-arithmetic certificate.',
        no_live_backend_or_hardware_error_check=True,seconds=time.perf_counter()-started,
        source_sha256=digest(Path(__file__)),independent_reused_verifier_sha256=digest(ROOT/'cuprate_2d_shallow_network.py'))
    with (RUN/'independent_verification.json').open('x',encoding='utf-8') as f:
        json.dump(result,f,indent=2,allow_nan=False); f.write('\n')
    print(json.dumps({'status':'PASS','provider_circuits':len(checks),'SDK_clock_checks':len(timing_checks),
        'max_segment_error':max(c['max_segment_error'] for c in checks),
        'max_global_phase_error':max(c['global_phase_error'] for c in checks),'seconds':result['seconds']}),flush=True)

if __name__=='__main__': main()
