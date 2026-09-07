"""Audit both local follow-up tracks and a post-hoc classical-only control.

The classical-only comparison never feeds back into the frozen filter choice.
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

from refine_cuprate_2d_tflo import BASE,PLAN,RUN,ROOT,read,digest
from cuprate_2d_tflo import physical_observables,write_json
from cuprate_2d_tflo_refinement import select_u0,evaluate_target,resample_paired
from analyze_cuprate_2d_tflo import load_archive


def audit():
    folder=ROOT/'audit'
    folder.mkdir(exist_ok=False)
    checks=[]
    def check(name,passed):
        checks.append({'name':name,'passed':bool(passed)})
        if not passed:
            write_json(folder/'failed_checks.json',checks)
            raise AssertionError(name)
    for origin in (ROOT/'reanalysis',ROOT/'optimization_v2'):
        for name,expected in read(origin/'sha256.json').items():
            p=(origin/name).resolve()
            check(f'path_{origin.name}_{name}',p.is_relative_to(origin.resolve()))
            check(f'hash_{origin.name}_{name}',digest(p)==expected)
    protocol=read(ROOT/'protocol.json')
    frozen=read(ROOT/'reanalysis/selected_filter_frozen.json')
    result=read(ROOT/'reanalysis/results.json')
    optimization=read(ROOT/'optimization_v2/summary.json')
    check('protocol_hash',frozen['protocol_sha256']==digest(ROOT/'protocol.json'))
    check('selection_frozen_hash',result['selected_filter_sha256']==digest(ROOT/'reanalysis/selected_filter_frozen.json'))
    check('optimization_checks',all(c['passed'] for c in read(ROOT/'optimization_v2/checks.json')))
    check('primary_analysis_preserved',(RUN/'analysis_not_valid.json').exists())
    check('submission_lock_preserved',(PLAN/'submission_attempt.json').exists())
    plan,raw,decoded,nup,ndown=load_archive(PLAN,RUN/'raw_bitstrings.json')
    cal=[s for s in plan['settings'] if s['u_over_t']==0]
    targets=[s for s in plan['settings'] if s['u_over_t']==8]
    cdata={s['id']:decoded[s['id']] for s in cal}
    tdata={s['id']:decoded[s['id']] for s in targets}
    winner,table=select_u0(cal,cdata,nup,ndown,protocol)
    check('independent_U0_selection_reproduced',winner==frozen['winner'] and table==frozen['candidates'])
    prediction=evaluate_target(winner,targets,tdata,nup,ndown)
    reference=np.array([s['reference'] for s in targets])
    mse=float(np.mean((prediction['corrected']-reference)**2))
    check('heldout_MSE_reproduced',abs(mse-result['global_U8_pauli_MSE']['corrected'])<1e-14)
    arrays=np.load(ROOT/'reanalysis/bootstrap_pauli_predictions.npz')
    check('bootstrap_all_finite',all(np.isfinite(arrays[k]).all() for k in arrays.files))
    check('bootstrap_400',arrays['raw'].shape==(400,2,27))
    gain=np.mean((arrays['raw']-reference)**2,axis=(1,2))-np.mean((arrays['corrected_reselected']-reference)**2,axis=(1,2))
    check('bootstrap_gain_interval_reproduced',np.allclose(np.quantile(gain,[.025,.975]),
        [result['paired_global_MSE_gain_ci95']['corrected_reselected'][k] for k in ('low','high')],rtol=0,atol=1e-14))
    check('all_bootstrap_choices_accounted',sum(result['bootstrap_selection_frequency'].values())==400)
    rng=np.random.default_rng(protocol['bootstrap_seed'])
    for b in range(3):
        sample=resample_paired(decoded,rng)
        choice,_=select_u0(cal,{s['id']:sample[s['id']] for s in cal},nup,ndown,protocol)
        pred=evaluate_target(choice,targets,{s['id']:sample[s['id']] for s in targets},nup,ndown)
        check(f'bootstrap_draw_{b}_reproduced',np.allclose(pred['corrected'],arrays['corrected_reselected'][b],rtol=0,atol=1e-12))

    # Additional non-selecting diagnostic: could a cheap U=0 prediction do as well?
    free=np.array([next(s['reference'] for s in cal if s['time']==t['time']) for t in targets])
    free_mse=float(np.mean((free-reference)**2))
    free_gain=free_mse-np.mean((arrays['corrected_reselected']-reference)**2,axis=(1,2))
    free_interval=np.quantile(free_gain,[.025,.975]).tolist()
    control={'posthoc_nonselecting_diagnostic':True,'control':'Exact U=0 FLO prediction, without target QPU data',
             'FLO_only_pooled_Pauli_MSE':free_mse,'TFLO_pooled_Pauli_MSE':mse,
             'FLO_only_minus_TFLO_gain_ci95':free_interval,
             'statistically_clear_gain_over_FLO_only':bool(free_interval[0]>0),
             'physical_RMSE_by_time':[{'time':t['time'],
                 'FLO_only_charge_spin_double':np.sqrt(np.mean((physical_observables(free[i])-physical_observables(reference[i]))**2,axis=0)).tolist()}
                  for i,t in enumerate(targets)],
             'warning':'U=0 is an approximate predictor for the interacting target, not a solution of its U=8 Hamiltonian. This control was not used to retune TFLO.'}
    write_json(folder/'classical_only_control.json',control)
    tests=subprocess.run([sys.executable,str(BASE/'test_cuprate_2d_tflo_refinement.py')],
                         cwd=BASE,capture_output=True,text=True,timeout=180)
    (folder/'unit_tests.txt').write_text(tests.stdout+tests.stderr,encoding='utf-8')
    check('seven_local_unit_tests',tests.returncode==0 and 'Ran 7 tests' in tests.stderr)
    verification={'all_passed':True,'audit_checks':len(checks),'checks':checks,
                  'optimization_checks':optimization['checks_passed'],'unit_tests':7,
                  'new_QPU_seconds':0,'classical_only_control':control,
                  'original_primary_result_unchanged':True,
                  'filesystem_retry_note':'First optimization attempt stopped on OSError 22 while overwriting a progress log; immutable per-twirl checkpoints and a final single-write log succeeded in optimization_v2.'}
    write_json(folder/'verification.json',verification)
    stats=optimization['stats']
    lines=['# TFLO vervolgstap: bestaande data en lokale circuitoptimalisatie','',
           '**Geen nieuwe QPU-job; extra QPU-verbruik 0 seconden.**', '',
           '## 1. Minder gate-overhead, nog niet op hardware getest', '',
           f"X+SX-gates verminderd met {100*optimization['XSX_reduction_fraction']:.1f}%.",
           f"X-gates: {min(s['before'].get('x',0) for s in stats)}-{max(s['before'].get('x',0) for s in stats)} naar {min(s['after'].get('x',0) for s in stats)}-{max(s['after'].get('x',0) for s in stats)}.",
           f"Diepte: {min(s['depth_before'] for s in stats)}-{max(s['depth_before'] for s in stats)} naar {min(s['depth_after'] for s in stats)}-{max(s['depth_after'] for s in stats)}. Alle circuits behouden 1008 CZ-gates.",
           f"{optimization['checks_passed']} controles geslaagd, maximale 18-qubit-statevectorafwijking {optimization['max_state_distance']:.3e}; QPY exact herlaadbaar.",
           '', '## 2. TFLO op de oude meetdata', '',
           'Filter gekozen uitsluitend met zes U=0 trainingsinstellingen en twee U=0 validatiepunten. '
           'Gekozen: abs(N_up-4)+abs(N_down-4)<=1. Het minimum van 32 shots bleef staan. '
           'De oorspronkelijke strikte analyse blijft als mislukt bewaard.', '',
           '| Tijd U=8 | Behouden shots | Charge RMSE voor -> na | Spin RMSE voor -> na | Doublon RMSE voor -> na |',
           '|---|---:|---|---|---|']
    for row in result['targets']:
        a=row['methods']['raw']['rmse_charge_spin_double']
        b=row['methods']['corrected']['rmse_charge_spin_double']
        lines.append(f"| {row['time']} | {row['retained_shots']} / 512 | {a[0]:.4f} -> {b[0]:.4f} | {a[1]:.4f} -> {b[1]:.4f} | {a[2]:.4f} -> {b[2]:.4f} |")
    lines += ['',f"Gemiddelde kwadratische Pauli-fout over beide U=8-punten: {result['global_U8_pauli_MSE']['raw']:.6f} -> {mse:.6f}.",
              'De verbetering ten opzichte van raw blijft positief in de 95%-bootstrapinterval inclusief herselectie van het filter op U=0. '
              '400 replicaties, geen mislukte bootstrapfits. De precieze filterkeuze is niet stabiel: meerdere toleranties worden vaak gekozen.',
              '', '## 3. Belangrijke klassieke controle', '',
              f"Een geheel klassieke U=0-FLO-voorspelling heeft op dezelfde U=8-doelen MSE {free_mse:.6f}, tegenover {mse:.6f} voor TFLO.",
              f"De 95%-bootstrapinterval voor de extra winst boven die klassieke voorspelling is [{free_interval[0]:.6f}, {free_interval[1]:.6f}] en bevat nul.",
              '**Dus: duidelijke foutreductie ten opzichte van de ruwe data, maar geen statistisch duidelijke extra winst boven deze goedkope klassieke voorspelling.** '
              'Dit is geen bewijs van quantum advantage.',
              '', '## Grenzen en verificatie', '',
              'Deze heranalyse is verkennend: U=8 werd niet gebruikt voor selectie/fitting, maar de ruwe U=8-resultaten waren al eerder bekeken. '
              'Bootstrap dekt geen systematische TFLO-transferbias. Referenties zijn dezelfde eindige Trotter-circuits. '
              'De opgeschoonde nieuwe circuits hebben geen nieuwe hardwaredata; hun gate-reductie is geen gemeten fidelitywinst.',
              f'{len(checks)} archief-/reproductiechecks en 7 unit-tests geslaagd. Alle oorspronkelijke data en de indieningsblokkering zijn ongewijzigd.',
              'De eerste optimalisatiepoging is bewaard; alleen de voortgangsopslag gaf een bestandsfout. De complete gevalideerde versie staat in optimization_v2.',
              '', '[IBM: one-qubit-optimalisatie](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.transpiler.passes.Optimize1qGatesDecomposition).']
    (ROOT/'FOLLOWUP_REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    write_json(folder/'sha256.json',{p.name:digest(p) for p in folder.iterdir() if p.is_file()})
    print(json.dumps({'audit_checks':len(checks),'optimization_checks':optimization['checks_passed'],
                     'unit_tests':7,'XSX_reduction_fraction':optimization['XSX_reduction_fraction'],
                     'FLO_only_control':control}),flush=True)


if __name__=='__main__':
    audit()
