"""Offline diagnosis of the completed TFLO run; do not relax the frozen filter."""
import hashlib
import json
from pathlib import Path

import numpy as np

from run_cuprate_2d_tflo_once import PLAN,RUN,BASE,read,exclusive_json,digest
from analyze_cuprate_2d_tflo import load_archive
from cuprate_2d_tflo import sector_mask,pauli_samples,physical_observables


def diagnose():
    plan,raw,decoded,nup,ndown=load_archive(PLAN,RUN/'raw_bitstrings.json')
    metrics=read(RUN/'provider_metrics.json')
    budget=read(RUN/'provider_budget_verification.json')
    provider=read(RUN/'provider_input_verification.json')
    assert budget['verified'] and budget['provider_cost_field']==5
    assert provider['all_circuits_match'] and provider['all_result_metadata_match']
    assert provider['total_shots']==5120 and provider['scalar_pubs']==80
    rows=[]
    for setting in plan['settings']:
        blocks=decoded[setting['id']]
        bits=np.concatenate(list(blocks.values()))
        keep=sector_mask(bits,nup,ndown,0)
        reference=physical_observables(setting['reference'])
        observed=physical_observables(pauli_samples(bits).mean(axis=0))
        conditional=physical_observables(pauli_samples(bits[keep]).mean(axis=0)) if keep.any() else None
        rows.append({'id':setting['id'],'role':setting['role'],'time':setting['time'],
                     'u_over_t':setting['u_over_t'],'shots':len(bits),'retained':int(keep.sum()),
                     'retained_fraction':float(keep.mean()),'below_frozen_minimum':bool(keep.sum()<32),
                     'retained_by_twirl':{str(t):int(sector_mask(b,nup,ndown).sum()) for t,b in blocks.items()},
                     'raw_observables_charge_spin_double':observed.tolist(),
                     'raw_rmse_charge_spin_double':np.sqrt(np.mean((observed-reference)**2,axis=0)).tolist(),
                     'postselected_point_estimates_only':conditional.tolist() if conditional is not None else None,
                     'postselected_rmse_point_estimate_only':np.sqrt(np.mean((conditional-reference)**2,axis=0)).tolist() if conditional is not None else None})
    failed=[r['id'] for r in rows if r['below_frozen_minimum']]
    summary={'job_id':raw['job_id'],'status':'DONE','qpu_charge_time_seconds':metrics['usage']['qpu_charge_time_seconds'],
             'provider_max_execution_time':5,'all_5120_shots_received':True,
             'retained_total':sum(r['retained'] for r in rows),'min_retained':min(r['retained'] for r in rows),
             'max_retained':max(r['retained'] for r in rows),'frozen_minimum_per_setting':32,
             'settings_below_minimum':failed,'tflo_analysis_status':'REJECTED_INSUFFICIENT_POSTSELECTED_SAMPLES',
             'tflo_fit_performed':False,'filter_changed':False,'additional_QPU_jobs':0,
             'notes':['Retention fraction is not state fidelity.',
                      'Raw and conditional means are diagnostic point estimates, not certified accuracy.',
                      'Do not fit or tune the method to the held-out U=8 references.',
                      'The completed job was not truncated by the 5-second cap.'],
             'settings':rows,'raw_sha256':digest(RUN/'raw_bitstrings.json')}
    assert summary['qpu_charge_time_seconds']==4
    assert summary['retained_total']==374 and len(failed)==3
    exclusive_json(RUN/'sector_diagnosis.json',summary)
    lines=['# TFLO 3x3: hardwarejob voltooid, analyse gestopt','',
           f"Job: {raw['job_id']} op ibm_phoenix. Status DONE.",
           'Werkelijk verbruik: **4 QPU-seconden**; providerlimiet 5 seconden bevestigd.',
           'Alle 80 scalar PUBs x 64 shots = **5120 shots** ontvangen. Providerinputs en metadata zijn gecontroleerd.',
           '', '## Uitkomst van de vooraf vastgelegde analyse', '',
           'Strikte selectie op N_up=N_down=4 behoudt 374/5120 shots (7.30%): slechts 27-50 per instelling. '
           'Drie instellingen halen het vooraf gekozen minimum van 32 niet. De TFLO-fit is daarom niet uitgevoerd. '
           'Het filter en de minimumdrempel zijn niet achteraf aangepast.', '',
           '| Instelling | Behouden / 512 | Onder minimum 32 |','|---|---:|---|']
    for row in rows:
        lines.append(f"| {row['id']} | {row['retained']} | {'ja' if row['below_frozen_minimum'] else 'nee'} |")
    lines += ['', '## Interagerende referentiepunten: ruwe meetfout', '',
              '| Tijd | Charge RMSE | Spin RMSE | Doublon RMSE |', '|---|---:|---:|---:|']
    for row in rows:
        if row['role']=='interacting_holdout':
            error=row['raw_rmse_charge_spin_double']
            lines.append(f"| {row['time']} | {error[0]:.4f} | {error[1]:.4f} | {error[2]:.4f} |")
    lines += ['', 'Dit zijn fouten ten opzichte van dezelfde eindige ideale circuits. Spin is n_up-n_down, niet S_z. '
              'Retentie is geen fidelity; minder chargefout na sectorselectie alleen is geen bewijs van correcte dynamica.', '',
              '## Bewaard en vervolggrens', '',
              'De exacte aangeleverde en teruggelezen provider-circuits, opties, 5120 ruwe bitstrings, '
              'volledige providerresultaten, metrics, capverificatie, job-ID en indieningsblokkering zijn opgeslagen. '
              'Zes offline veiligheidstests en 80 QPY-herlaadchecks gingen aan de eenmalige submissie vooraf. '
              'HTTP-retries waren voor indiening uitgeschakeld.', '',
              'Geen tweede job gestart. Geen TFLO-verbetering of quantum advantage aangetoond. '
              'Een volgende analyse kan een vooraf beschreven versoepeld filter uitsluitend met U=0-kalibratie/validatie '
              'toetsen op deze bestaande data, maar dat is niet uitgevoerd en mag de mislukte bevroren analyse niet vervangen.']
    (RUN/'RESULT_REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    exclusive_json(RUN/'complete_archive_sha256.json',{
        str(p.relative_to(RUN)):digest(p) for p in sorted(RUN.rglob('*')) if p.is_file()})
    print(json.dumps({k:summary[k] for k in ('job_id','status','qpu_charge_time_seconds','retained_total',
          'settings_below_minimum','tflo_analysis_status')}),flush=True)


if __name__=='__main__':
    diagnose()
