"""Two independent local follow-ups: optimize future templates / reanalyze OLD data.

No provider calls, submission, retry or change to the original failed analysis.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from collections import Counter
from pathlib import Path

import numpy as np
from qiskit import qpy
from threadpoolctl import threadpool_limits

from cuprate_2d_hubbard_pipeline import Cuprate2DConfig
from cuprate_2d_tflo import bind,skeleton,physical_observables,write_json
from cuprate_2d_tflo_refinement import (cleanup_one_qubit,active_circuit,cz_trace,
    measurement_map,select_u0,refit_locked_u0,evaluate_target,resample_paired)
from analyze_cuprate_2d_tflo import load_archive

BASE=Path(__file__).resolve().parent
PLAN=BASE/'results_cuprate_2d/tflo_pilot_3x3_2026-09-05_ready'
RUN=BASE/'results_cuprate_2d/tflo_run_3x3_2026-09-05'
ROOT=BASE/'results_cuprate_2d/tflo_followup_2026-09-05'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def check_inputs():
    for root,filename in ((PLAN,'sha256.json'),(RUN,'complete_archive_sha256.json')):
        for name,expected in read(root/filename).items():
            target=(root/name).resolve()
            assert target.is_relative_to(root.resolve()) and digest(target)==expected
    protocol=read(ROOT/'protocol.json')
    assert protocol['new_QPU_jobs_authorized'] is False
    assert protocol['candidate_tolerances']==[0,1,2,3,4,18]
    assert protocol['ridge']==.001 and protocol['bootstrap_replicates']==400
    return protocol


def seal(folder):
    snapshot=folder/'source_snapshot'
    snapshot.mkdir()
    for name in (Path(__file__).name,'cuprate_2d_tflo_refinement.py','test_cuprate_2d_tflo_refinement.py'):
        (snapshot/name).write_bytes((BASE/name).read_bytes())
    write_json(folder/'sha256.json',{str(p.relative_to(folder)):digest(p)
               for p in sorted(folder.rglob('*')) if p.is_file()})


def optimize():
    from cuprate_2d_fermionic_pilot import simulator_state
    from validate_cuprate_2d_fermionic_dynamics import phase_distance
    protocol=check_inputs()
    folder=ROOT/'optimization'
    folder.mkdir(exist_ok=False)
    plan=read(PLAN/'manifest.json')
    cfg=Cuprate2DConfig(**plan['config'])
    layout=plan['initial_layout']
    with (PLAN/'twirled_sampler_templates.qpy').open('rb') as handle:
        originals=qpy.load(handle)
    checks,stats,optimized=[],[],[]
    def check(name,value,tolerance):
        row={'name':name,'value':float(value),'tolerance':tolerance,
             'passed':bool(np.isfinite(value) and value<=tolerance)}
        checks.append(row)
        write_json(folder/'checks.json',checks)
        if not row['passed']:
            raise AssertionError(name)
    for i,original in enumerate(originals):
        cleaned=cleanup_one_qubit(original)
        check(f'CZ_order_{i}',int(cz_trace(cleaned)!=cz_trace(original)),0)
        check(f'measurement_map_{i}',int(measurement_map(cleaned)!=measurement_map(original)),0)
        check(f'readout_mask_{i}',int(cleaned.metadata['readout_mask_little_endian']!=original.metadata['readout_mask_little_endian']),0)
        before,after=dict(original.count_ops()),dict(cleaned.count_ops())
        old_pulses=before.get('x',0)+before.get('sx',0)
        new_pulses=after.get('x',0)+after.get('sx',0)
        check(f'pulse_count_nonincrease_{i}',new_pulses-old_pulses,0)
        stats.append({'twirl':i,'before':before,'after':after,'depth_before':original.depth(),
                      'depth_after':cleaned.depth(),'XSX_before':old_pulses,'XSX_after':new_pulses})
        signature=skeleton(cleaned)
        for setting in plan['settings']:
            bound=bind(cleaned,cfg,setting['time'],setting['u_over_t'])
            check(f'structure_{i}_{setting["id"]}',int(skeleton(bound)!=signature),0)
        # All eight twirls at U=8,T=.2; all ten parameter settings for twirl 0.
        selected=plan['settings'] if i==0 else [s for s in plan['settings'] if s['id']=='interacting_holdout_U8_T0.2']
        for setting in selected:
            a=active_circuit(bind(original,cfg,setting['time'],setting['u_over_t']),layout)
            b=active_circuit(bind(cleaned,cfg,setting['time'],setting['u_over_t']),layout)
            distance=phase_distance(simulator_state(a),simulator_state(b))
            check(f'state_equivalence_{i}_{setting["id"]}',distance,2e-9)
        optimized.append(cleaned)
        print(json.dumps({'event':'twirl_validated',**stats[-1]}),flush=True)
    path=folder/'optimized_unbound_templates.qpy'
    with path.open('wb') as handle:
        qpy.dump(optimized,handle)
    with path.open('rb') as handle:
        restored=qpy.load(handle)
    check('qpy_count',abs(len(restored)-len(optimized)),0)
    for i,(a,b) in enumerate(zip(optimized,restored)):
        check(f'qpy_exact_{i}',int(a!=b),0)
    summary={'status':'LOCAL_ONLY_OPTIMIZED_NOT_HARDWARE_TESTED','new_QPU_seconds':0,
             'checks_passed':len(checks),'stats':stats,'protocol_sha256':digest(ROOT/'protocol.json'),
             'source_template_sha256':digest(PLAN/'twirled_sampler_templates.qpy'),
             'max_state_distance':max(r['value'] for r in checks if r['name'].startswith('state_equivalence')),
             'XSX_reduction_fraction':1-sum(s['XSX_after'] for s in stats)/sum(s['XSX_before'] for s in stats),
             'note':'Pulse counts are native input X+SX counts, not measured hardware error or speedup.'}
    write_json(folder/'summary.json',summary)
    lines=['# One-qubit cleanup: local validation only','',
           'CZ count and per-wire CZ ordering, readout mask and measurement mapping are preserved.',
           'Optimization was performed BEFORE parameter binding; calibration and interacting inputs keep one fixed structure per twirl.',
           '', '| Twirl | X before | X after | X+SX before | X+SX after | Depth before | Depth after |',
           '|---|---:|---:|---:|---:|---:|---:|']
    for s in stats:
        lines.append(f"| {s['twirl']} | {s['before'].get('x',0)} | {s['after'].get('x',0)} | {s['XSX_before']} | {s['XSX_after']} | {s['depth_before']} | {s['depth_after']} |")
    lines += ['',f"{len(checks)} checks passed; maximum full-statevector phase-aligned distance {summary['max_state_distance']:.3e}.",
              'QPY round-trip equality verified. No new QPU run and no claim of improved hardware fidelity.',
              'The old measurement data belong to the OLD circuits; the separate reanalysis cannot test these new circuits.',
              '', 'Optimizer reference: https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.transpiler.passes.Optimize1qGatesDecomposition']
    (folder/'OPTIMIZATION_REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    seal(folder)
    print(json.dumps({k:v for k,v in summary.items() if k!='stats'}),flush=True)


def interval(values):
    values=np.asarray(values)
    mask=np.isfinite(values).all(axis=tuple(range(1,values.ndim))) if values.ndim>1 else np.isfinite(values)
    values=values[mask]
    if not len(values):
        return None
    return {'low':np.quantile(values,.025,axis=0).tolist(),
            'high':np.quantile(values,.975,axis=0).tolist(),'valid_replicates':len(values)}


def reanalyze():
    protocol=check_inputs()
    folder=ROOT/'reanalysis'
    folder.mkdir(exist_ok=False)
    plan,raw,decoded,nup,ndown=load_archive(PLAN,RUN/'raw_bitstrings.json')
    calibration=[s for s in plan['settings'] if s['u_over_t']==0]
    cal_raw={s['id']:decoded[s['id']] for s in calibration}
    winner,candidates=select_u0(calibration,cal_raw,nup,ndown,protocol)
    # This file is written before target evaluation; no U=8 values entered selection.
    write_json(folder/'selected_filter_frozen.json',{
        'winner':winner,'candidates':candidates,'protocol_sha256':digest(ROOT/'protocol.json'),
        'selected_unix':time.time(),'U8_used_for_selection':False,
        'raw_data_sha256':digest(RUN/'raw_bitstrings.json')})
    print(json.dumps({'event':'U0_selection_frozen','winner':winner['id'],
                      'U0_validation_MSE':winner['score'],'candidates':candidates}),flush=True)
    targets=[s for s in plan['settings'] if s['u_over_t']==8]
    target_raw={s['id']:decoded[s['id']] for s in targets}
    central=evaluate_target(winner,targets,target_raw,nup,ndown)
    reference=np.array([s['reference'] for s in targets])
    B=protocol['bootstrap_replicates']
    rng=np.random.default_rng(protocol['bootstrap_seed'])
    shape=(B,)+central['raw'].shape
    draws={k:np.full(shape,np.nan) for k in ('raw','postselected_locked','corrected_locked','corrected_reselected')}
    frequencies=Counter()
    failures={'locked':0,'reselected':0}
    for b in range(B):
        sampled=resample_paired(decoded,rng)
        cdata={s['id']:sampled[s['id']] for s in calibration}
        tdata={s['id']:sampled[s['id']] for s in targets}
        try:
            fitted=refit_locked_u0(winner,calibration,cdata,nup,ndown,protocol)
            evaluation=evaluate_target(fitted,targets,tdata,nup,ndown)
            draws['raw'][b]=evaluation['raw']
            draws['postselected_locked'][b]=evaluation['postselected']
            draws['corrected_locked'][b]=evaluation['corrected']
        except ValueError:
            failures['locked']+=1
        try:
            selected,_=select_u0(calibration,cdata,nup,ndown,protocol)
            frequencies[selected['id']]+=1
            evaluation=evaluate_target(selected,targets,tdata,nup,ndown)
            draws['raw'][b]=evaluation['raw']
            draws['corrected_reselected'][b]=evaluation['corrected']
        except ValueError:
            failures['reselected']+=1
        if (b+1)%100==0:
            print(json.dumps({'event':'bootstrap','completed':b+1,'total':B}),flush=True)
    np.savez_compressed(folder/'bootstrap_pauli_predictions.npz',**draws)
    global_mse={k:float(np.mean((central[k]-reference)**2)) for k in ('raw','postselected','corrected')}
    raw_mse_draw=np.mean((draws['raw']-reference)**2,axis=(1,2))
    gain_intervals={k:interval(raw_mse_draw-np.mean((draws[k]-reference)**2,axis=(1,2)))
                    for k in ('corrected_locked','corrected_reselected')}
    rows=[]
    reference_physical=physical_observables(reference)
    physical_draws={k:physical_observables(v) for k,v in draws.items()}
    for i,setting in enumerate(targets):
        row={k:v for k,v in setting.items() if k!='reference'}
        row['retained_shots']=central['counts'][i]
        row['methods']={}
        for name,draw_name in [('raw','raw'),('postselected','postselected_locked'),('corrected','corrected_locked')]:
            values=physical_observables(central[name][i])
            samples=physical_draws[draw_name][:,i]
            row['methods'][name]={'observables':values.tolist(),
                'rmse_charge_spin_double':np.sqrt(np.mean((values-reference_physical[i])**2,axis=0)).tolist(),
                'conditional_ci95':interval(samples),
                'out_of_bounds_count':int(np.sum((values<[0.,-1.,0.])|(values>[2.,1.,1.])))}
        row['corrected_reselection_ci95']=interval(physical_draws['corrected_reselected'][:,i])
        rows.append(row)
    result={'status':'EXPLORATORY_REANALYSIS_OF_OLD_HARDWARE_DATA','job_id':raw['job_id'],
        'new_QPU_seconds':0,'original_primary_analysis_status':'FAILED_32_SHOT_FILTER_GATE_UNCHANGED',
        'selected_candidate':winner['id'],'selected_tolerance':winner['tolerance'],
        'uses_TFLO':winner['uses_TFLO'],'U0_only_selection':True,'candidates':candidates,
        'selected_filter_sha256':digest(folder/'selected_filter_frozen.json'),
        'global_U8_pauli_MSE':global_mse,'paired_global_MSE_gain_ci95':gain_intervals,
        'bootstrap_replicates':B,'bootstrap_failures':failures,
        'bootstrap_selection_frequency':dict(frequencies),'targets':rows,
        'uncertainty_boundary':'Includes shot/twirl/refit variability; reselection intervals also include filter choice. Neither covers transfer-model bias.',
        'independence_boundary':protocol['disclosure'],
        'circuit_boundary':'These data are from the old unoptimized circuits, not the new one-qubit-cleaned templates.'}
    write_json(folder/'results.json',result)
    lines=['# Exploratory relaxed-filter TFLO: existing data only','',
           f"Source job: {raw['job_id']}; new QPU usage: 0 seconds.",
           'The original failed strict-filter analysis remains unchanged. This is not a fresh blinded confirmatory test.',
           '',f"Selected on U=0 ONLY: {winner['id']}; tolerance {winner['tolerance']}.",
           'The six training settings fit the coefficients; the two separate U=0 holdout times select the filter.',
           'U=8 data and references were excluded from that choice and fitting; no physical clipping.',
           '', '| Candidate | Feasible | U=0 holdout Pauli MSE |','|---|---|---:|']
    for c in candidates:
        score=f"{c['U0_validation_pauli_MSE']:.6f}" if c['feasible'] else 'not fitted'
        lines.append(f"| {c['id']} | {c['feasible']} | {score} |")
    lines += ['', '| U=8 time | Retained | Method | Charge RMSE | Spin RMSE | Doublon RMSE |',
              '|---|---:|---|---:|---:|---:|']
    for row in rows:
        for name,entry in row['methods'].items():
            e=entry['rmse_charge_spin_double']
            lines.append(f"| {row['time']} | {row['retained_shots']} | {name} | {e[0]:.4f} | {e[1]:.4f} | {e[2]:.4f} |")
    gain=gain_intervals['corrected_reselected']
    lines += ['',f"Pooled U=8 Pauli MSE: raw={global_mse['raw']:.6f}; corrected={global_mse['corrected']:.6f}.",
              f"Paired raw-minus-corrected MSE gain, 95% bootstrap interval WITH U=0 filter reselection: {gain}.",
              f"Bootstrap selections: {dict(frequencies)}; failures: {failures}.",
              '', 'Intervals exclude systematic transfer bias and do not establish quantum advantage or calibrated future-circuit fidelity.',
              'The cleaner compiled circuits were NOT run on hardware. Their performance cannot be inferred as a measured result from this reanalysis.']
    (folder/'REANALYSIS_REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    seal(folder)
    print(json.dumps({k:result[k] for k in ('selected_candidate','global_U8_pauli_MSE',
          'paired_global_MSE_gain_ci95','bootstrap_selection_frequency','bootstrap_failures')}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['optimize','reanalyze'])
    args=parser.parse_args()
    with threadpool_limits(limits=1):
        globals()[args.action]()
