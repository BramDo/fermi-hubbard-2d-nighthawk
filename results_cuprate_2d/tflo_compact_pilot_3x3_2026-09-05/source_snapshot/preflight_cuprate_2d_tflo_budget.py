"""Read-only live IBM compatibility and QPU-time estimate for the frozen TFLO plan.

No Sampler.run, submit, session, batch, cancellation or retry path exists.
Provider operations are read-only and exceptions are redacted. A local estimate
is not a provider quote or a guarantee of completion below the 5-second cap.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import logging
import math
import numbers
import sys
import time
import warnings
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import qiskit
from qiskit import qpy
import qiskit_ibm_runtime
from qiskit_ibm_runtime import QiskitRuntimeService
from qiskit_ibm_runtime.options import SamplerOptions
from qiskit_ibm_runtime.utils.validations import validate_isa_circuits

from cuprate_2d_tflo import skeleton, write_json

ACCOUNT = 'qiskit-runtime-q9'
BACKEND = 'ibm_phoenix'
CAP_SECONDS = 5
WEIGHTS = {'rz':1, 'delay':1, 'sx':2, 'x':2, 'cz':5, 'measure':10, 'reset':17}
USAGE_URL = 'https://quantum.cloud.ibm.com/docs/en/guides/estimate-job-run-time'
LIMITS_URL = 'https://quantum.cloud.ibm.com/docs/en/guides/job-limits'
CAP_URL = 'https://quantum.cloud.ibm.com/docs/en/guides/max-execution-time'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def safe_read(label, function, *args, **kwargs):
    # SDK exceptions and warning text may contain request/account details.
    try:
        with warnings.catch_warnings(record=True), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return function(*args, **kwargs)
    except Exception as exc:
        raise RuntimeError(f'{label} failed ({type(exc).__name__})') from None


def wire_time(circuit, target, *, aligned=False):
    """Independent ASAP critical path; includes the existing measurements.

    Alignment only adds waits to the scheduling estimate; it never edits the
    submitted/frozen circuit. Reset and rep_delay are added separately.
    """
    clocks = np.zeros(circuit.num_qubits)
    for inst in circuit.data:
        name = inst.operation.name
        wires = tuple(circuit.find_bit(q).index for q in inst.qubits)
        if not wires:
            continue
        if name == 'barrier':
            clocks[list(wires)] = max(clocks[list(wires)])
            continue
        prop = target[name].get(wires)
        if prop is None or prop.duration is None:
            raise ValueError(f'Missing instruction duration: {name}')
        duration = float(prop.duration)
        if duration < 0 or not math.isfinite(duration):
            raise ValueError('Invalid instruction duration')
        start = float(max(clocks[list(wires)]))
        if aligned and duration > 0:
            alignment = target.acquire_alignment if name == 'measure' else target.pulse_alignment
            quantum = max(int(alignment or 1), 1)*target.dt
            start = math.ceil(start/quantum-1e-9)*quantum
        clocks[list(wires)] = start+duration
    return float(max(clocks))


def preflight(plan_dir, output):
    root, output = Path(plan_dir), Path(output)
    output.mkdir(parents=True, exist_ok=False)
    logging.disable(logging.CRITICAL)
    started = time.perf_counter()
    checks = []
    def check(name, passed, value=None):
        record = {'name':name, 'passed':bool(passed), 'value':value}
        checks.append(record)
        if not passed:
            write_json(output/'failed_checks.json', checks)
            raise ValueError(f'Preflight check failed: {name}')
    frozen_hashes = json.loads((root/'sha256.json').read_text())
    for name, expected in frozen_hashes.items():
        path = (root/name).resolve()
        check('safe_frozen_path_'+name, path.is_relative_to(root.resolve()))
        check('frozen_sha256_'+name, digest(path)==expected)
    plan = json.loads((root/'manifest.json').read_text())
    check('backend_frozen', plan['backend_candidate']==BACKEND)
    check('same_user_budget',plan['budget']['existing_user_cap_seconds']==CAP_SECONDS)
    check('no_existing_submission',not (root/'submission_attempt.json').exists())
    with (root/'twirled_sampler_templates.qpy').open('rb') as handle:
        templates = qpy.load(handle)
    settings = {s['id']:s for s in plan['settings']}
    circuits, seen = [], set()
    for record in plan['records']:
        key = (record['setting_id'],record['twirl_id'])
        check('unique_record_'+str(key),key not in seen)
        seen.add(key)
        template = templates[record['template_index']]
        check('twirl_seed_'+str(key),template.metadata['twirl_seed']==record['seed'])
        check('readout_mask_'+str(key),template.metadata['readout_mask_little_endian']==record['readout_mask_little_endian'])
        value = record['parameter_values']
        setting = settings[record['setting_id']]
        check('time_binding_'+str(key), math.isclose(value['step_time'],setting['time']/plan['config']['steps'],abs_tol=1e-14))
        check('U_binding_'+str(key), math.isclose(value['interaction_phase'],setting['u_over_t']*plan['config']['hopping_t']*value['step_time'],abs_tol=1e-14))
        circuit = template.assign_parameters({p:value[p.name] for p in template.parameters})
        check('structure_'+str(key),skeleton(circuit)==skeleton(template))
        check('bound_'+str(key),circuit.num_parameters==0)
        # Mark result-order provenance in a prospective bound circuit only.
        circuit.metadata = {**circuit.metadata, 'setting_id':record['setting_id'],
                            'twirl_id':record['twirl_id']}
        circuits.append(circuit)
    check('frozen_setting_twirl_count',len(circuits)==80 and len(settings)==10)
    shots = sum(r['shots'] for r in plan['records'])
    check('frozen_total_shots',shots==5120,shots)
    print(json.dumps({'event':'frozen_inputs_verified','circuits':len(circuits),'shots':shots}),flush=True)

    provider_calls = ['QiskitRuntimeService(name)', 'service.backend', 'backend.status',
                      'backend.properties', 'service.usage']
    service = safe_read('IBM authentication',QiskitRuntimeService,name=ACCOUNT)
    backend = safe_read('IBM backend lookup',service.backend,BACKEND)
    status = safe_read('IBM backend status',backend.status)
    properties = safe_read('IBM backend properties',backend.properties)
    target = backend.target
    account = service.active_account()
    instance_fingerprint = hashlib.sha256(str(account.get('instance','')).encode()).hexdigest()
    usage = {}
    try:
        raw_usage = safe_read('IBM usage lookup',service.usage)
        usage = {k:float(raw_usage[k]) for k in ('usage_limit_seconds','usage_allocation_seconds',
            'usage_consumed_seconds','usage_remaining_seconds')
            if isinstance(raw_usage.get(k),numbers.Real) and not isinstance(raw_usage.get(k),bool)}
    except RuntimeError:
        usage = {'available':False}
    check('backend_operational',status.operational)
    check('backend_width',backend.num_qubits==circuits[0].num_qubits)
    layout = plan['initial_layout']
    faults = properties.faulty_qubits()
    check('selected_qubits_not_faulty',not set(layout).intersection(faults))
    # This is the installed SDK's LOCAL ISA validator, not a provider job.
    validate_isa_circuits(circuits,target)
    check('local_ISA_validator',True)
    check('no_faulty_gate_usage',all(
        not set(gate.qubits).issubset(layout) for gate in properties.faulty_gates()))

    rep_delay = float(backend.default_rep_delay)
    reset_durations = [target['reset'][(q,)].duration for q in layout]
    check('reset_durations_available',all(d is not None and d>=0 for d in reset_durations))
    reset_time = max(float(d) for d in reset_durations)
    rep_range = [float(v) for v in backend.rep_delay_range]
    check('default_rep_delay_in_range',rep_range[0]<=rep_delay<=rep_range[1])
    options = {'max_execution_time':CAP_SECONDS,'default_shots':64,
               'execution':{'init_qubits':True,'rep_delay':rep_delay,'meas_type':'classified'},
               'twirling':{'enable_gates':False,'enable_measure':False},
               'dynamical_decoupling':{'enable':False}}
    SamplerOptions(**options)  # Validation only; deliberately no Sampler instance.
    write_json(output/'proposed_sampler_options.json',options)

    timing, instruction_snapshot = [], {}
    low_level = np.zeros(backend.num_qubits,dtype=np.int64)
    total_cz = 0
    for circuit,record in zip(circuits,plan['records']):
        sdk = float(circuit.estimate_duration(target))
        manual = wire_time(circuit,target)
        aligned = wire_time(circuit,target,aligned=True)
        key = (record['setting_id'],record['twirl_id'])
        check('two_duration_methods_'+str(key),abs(sdk-manual)<1e-10,abs(sdk-manual))
        check('alignment_not_shorter_'+str(key),aligned>=manual-1e-12)
        operations = dict(circuit.count_ops())
        check('cz_exposure_'+str(key),operations.get('cz')==1008)
        check('per_circuit_gate_limits_'+str(key),operations.get('cz',0)<5_000_000 and
              operations.get('rz',0)<30_000_000 and operations.get('sx',0)<20_000_000)
        total_cz += operations.get('cz',0)
        for inst in circuit.data:
            name = inst.operation.name
            wires = tuple(circuit.find_bit(q).index for q in inst.qubits)
            low_level[list(wires)] += WEIGHTS[name]
            prop = target[name][wires]
            instruction_snapshot[(name,wires)] = {'name':name,'qubits':list(wires),
                'duration_seconds':prop.duration,'error':prop.error}
        timing.append({'setting_id':record['setting_id'],'twirl_id':record['twirl_id'],
                       'shots':record['shots'],'qiskit_duration_seconds':sdk,
                       'aligned_duration_seconds':aligned,'reset_seconds':reset_time,
                       'rep_delay_seconds':rep_delay,
                       'all_shots_seconds':record['shots']*(aligned+reset_time+rep_delay)})
    # Allow initialisation instructions once per circuit on every device qubit.
    low_level += 50*len(circuits)
    check('documented_instruction_memory_screen',int(max(low_level))<26_800_000,int(max(low_level)))
    check('documented_sampler_execution_limit',shots<10_000_000)
    execution = sum(r['all_shots_seconds'] for r in timing)
    scenarios = [{'sub_jobs':n,'assumed_overhead_seconds':2.*n,
                  'estimated_seconds':2.*n+execution,
                  'planning_rounded_up_seconds':math.ceil(2.*n+execution),
                  'within_5s_estimate':2.*n+execution<=CAP_SECONDS}
                 for n in (1,2,3)]
    write_json(output/'timing_by_record.json',timing)
    snapshot = {'captured_utc':datetime.now(timezone.utc).isoformat(), 'name':backend.name,
        'qubits':backend.num_qubits,'operational':status.operational,
        'pending_jobs_at_capture':status.pending_jobs,
        'properties_updated':str(properties.last_update_date),
        'dt_seconds':target.dt,'pulse_alignment_dt':target.pulse_alignment,
        'acquire_alignment_dt':target.acquire_alignment,
        'default_rep_delay_seconds':rep_delay,'rep_delay_range_seconds':rep_range,
        'selected_reset_duration_seconds':reset_time,'layout':layout,
        'faulty_qubits':faults,'used_instructions':list(instruction_snapshot.values())}
    write_json(output/'backend_timing_snapshot.json',snapshot)
    result = {'status':'READ_ONLY_PREFLIGHT_COMPLETE_NO_JOB_SUBMITTED',
        'captured_utc':snapshot['captured_utc'],'backend':BACKEND,'account_name':ACCOUNT,
        'credential_source':'saved_qiskit_account','instance_sha256':instance_fingerprint,
        'provider_calls':provider_calls,'QPU_seconds_used_for_this_check':0,
        'plan_dir':str(root),'plan_sha256':digest(root/'manifest.json'),
        'source_sha256':digest(__file__),'circuits':len(circuits),'settings':len(settings),
        'shots_per_setting':512,'total_shots_including_calibration':shots,
        'compiled_CZ_per_circuit':1008,'CZ_across_circuits_not_shot_weighted':total_cz,
        'execution_plus_reset_and_rep_delay_seconds':execution,
        'overhead_scenarios':scenarios,'provider_subjob_count_known':False,
        'provider_pre_submission_cost_quote_available':False,
        'local_usage_remaining':usage,'max_execution_time_seconds':CAP_SECONDS,
        'new_submission_authorized':False,'automatic_retries':False,
        'checks_passed':len(checks),'checks':checks,
        'versions':{'python':sys.version.split()[0],'qiskit':qiskit.__version__,
                    'qiskit_ibm_runtime':qiskit_ibm_runtime.__version__},
        'elapsed_local_and_API_seconds':time.perf_counter()-started,
        'claim_boundary':'Approximate local timing, not a guaranteed invoice or a hardware result. Unknown sub-job splitting can exceed the cap and cancel the job.',
        'sources':[USAGE_URL,LIMITS_URL,CAP_URL]}
    write_json(output/'budget_preflight.json',result)
    report = ('# TFLO budgetcontrole: geen QPU-job ingediend\n\n'
        f'Actuele backend: {BACKEND}, operationeel; {status.pending_jobs} wachtende jobs bij controle.\n'
        f'Kalibratiedatum: {properties.last_update_date}.\n\n'
        f'Plan: 10 instellingen x 8 expliciete twirls x 64 shots = {shots} shots, inclusief kalibratie. '
        f'Alle {len(circuits)} bevroren circuits passen op de actuele ISA; {len(checks)} controles geslaagd.\n\n'
        f'Shotuitvoering inclusief bestaande metingen, reset en standaard rep_delay: {execution:.6f} s. '
        f'De standaard rep_delay is {rep_delay*1e6:g} microseconde; niet verlaagd voor deze schatting.\n\n'
        '| Aantal interne subjobs | Raming inclusief opstartoverhead | Naar boven afgeronde planningswaarde |\n'
        '|---|---:|---:|\n'+''.join(f"| {r['sub_jobs']} | {r['estimated_seconds']:.3f} s | {r['planning_rounded_up_seconds']} s |\n" for r in scenarios)+
        '\nIBM beschrijft circa 2 s overhead per interne subjob. Het aantal subjobs is vooraf '
        'niet bevestigd; de tabel is een scenarioanalyse, geen bovengrens of prijsopgave. '
        'Afronden is hier een planningskeuze, geen geverifieerde facturatieregel.\n\n'
        'Een eventuele volgende run: een enkele job, harde max_execution_time=5, '
        'geen sessie/batch, geen automatische retry en geen backendwissel. '
        'Ingebouwde twirling blijft uit omdat de acht twirls al expliciet in de circuits staan. '
        'Geen extra ZNE/PEC of readout-learning toegevoegd. Ruwe bitstrings blijven vereist.\n\n'
        'Er is nog geen nieuwe submissietoestemming verondersteld. De 5-secondenlimiet '
        'kan tot annulering leiden als de werkelijke overhead groter is. Deze controle gebruikt '
        '0 QPU-seconden en toont geen mitigatieverbetering.\n\n'
        f'Bronnen: [IBM workload usage]({USAGE_URL}), [joblimieten]({LIMITS_URL}), '
        f'[uitvoeringstijdlimiet]({CAP_URL}).\n')
    (output/'BUDGET_REPORT.md').write_text(report,encoding='utf-8')
    write_json(output/'sha256.json',{p.name:digest(p) for p in output.iterdir() if p.is_file()})
    print(json.dumps({k:result[k] for k in ('status','backend','total_shots_including_calibration',
          'execution_plus_reset_and_rep_delay_seconds','overhead_scenarios','local_usage_remaining','checks_passed')}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan-dir',required=True)
    parser.add_argument('--outdir',required=True)
    args=parser.parse_args()
    try:
        preflight(args.plan_dir,args.outdir)
    except Exception as exc:
        # No raw exception text, traceback locals, or provider response payloads.
        print(json.dumps({'status':'PREFLIGHT_FAILED_NO_SUBMISSION','error_type':type(exc).__name__}),flush=True)
        raise SystemExit(1) from None
