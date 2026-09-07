"""Finalize verified 6x6 artifacts, without provider calls or new experiments."""
from pathlib import Path
import json
import shutil
import numpy as np
import run_hardware_6x6_rocz_once as h

def main():
    out=h.RUN
    if (out/'delivery_sha256.json').exists(): raise FileExistsError('Delivery already frozen')
    h.verify_files(out,'verified_archive_sha256.json')
    classical=h.ROOT/'results_cuprate_2d/classical_full_6x6_mps_T04_chi64_v1'
    h.verify_files(classical,'sha256.json')
    hw=h.safe.read(out/'analysis/results.json'); audit=h.safe.read(out/'VERIFICATION.json')
    cs=h.safe.read(classical/'summary.json'); c64=cs['result']
    c32=h.safe.read(h.CLASSICAL/'6x6_chi32_threads1/result.json')
    blocks=[]
    for rec in h.safe.read(out/'raw_bitstrings.json')['records']:
        if rec.get('factor')!=1: continue
        bits=np.array([[int(x) for x in s[::-1]] for s in rec['bitstrings']],dtype=int)
        blocks.append((bits^np.array(rec['readout_mask_little_endian'])).sum(axis=1).astype(float))
    mean=float(np.mean([x.mean() for x in blocks]))
    se=float(np.sqrt(sum(x.var(ddof=1)/len(x) for x in blocks)/64))
    ratio=c64['kernel_seconds']/c32['kernel_seconds']
    estimate={'chi32_seconds':c32['kernel_seconds'],'chi64_seconds':c64['kernel_seconds'],
        'observed_ratio':ratio,'chi128_same_ratio_seconds':c64['kernel_seconds']*ratio,
        'chi128_cubic_seconds':8*c64['kernel_seconds'],'user_15_times_150_seconds':2250,
        'chi128_measured':False,'chi128_started':False,'rough_planning_minutes':[12,25],
        'not_a_confidence_interval_or_guaranteed_upper_bound':True,
        'chi64_timing_with_concurrent_local_work':True,
        'generic_MPS_SVD_scaling_source':'https://arxiv.org/abs/1901.05824'}
    shot={'factor1_shots':4096,'mean_N':mean,'expected_N':32,'conditional_shot_SE':se,
        'normal_approx_95_interval':[mean-1.96*se,mean+1.96*se],
        'deviation_in_conditional_SE_units':(mean-32)/se,
        'scope':'Independent shots at fixed8 twirls; no drift/SPAM model.',
        'readout_zne_N95_hybrid':hw['arms'][2]['N_95pct_interval']}
    h.safe.exclusive_json(out/'shot_uncertainty_check.json',shot)
    h.safe.exclusive_json(out/'chi128_time_estimate.json',estimate)
    comp=next(x for x in audit['classical_comparisons'] if x['chi']==64)
    delta=cs['comparisons']['chi64_minus_chi32_threads1']
    names=['Ruw, factor1','Readout, factor1','Readout + CZ-ZNE','ZNE zonder readout (diagnostisch)']
    lines=['# 6x6-resultaten: opgehaald en onafhankelijk gecontroleerd','',
        f"Job {audit['job_id']} op ibm_phoenix: alle13312 metingen en26 uitgevoerde circuits gecontroleerd.",
        'IBM rapporteert5 QPU-seconden, binnen de ingestelde limiet15. Geen nieuwe job of herhaling.','',
        '## Hoofdbevinding','',
        'Geen quantum-advantagedemonstratie: het ideale circuit bewaart exact32 deeltjes, maar de ruwe en gemitigeerde data geven beide circa35,77.',
        'Readout + CZ-ZNE herstelt dit behoud niet. De lokale spinprofielen zijn vrijwel vlak; dit zegt niet dat de volledige quantumtoestand is gereconstrueerd.','',
        '| Methode | Shots inclusief kalibratie | N | 95%-bootstrapinterval N |',
        '|---|---:|---:|---|']
    for name,row in zip(names,hw['arms']):
        lo,hi=row['N_95pct_interval']
        lines.append(f"| {name} | {row['shot_cost']} | {row['N']:.6f} | [{lo:.6f}, {hi:.6f}] |")
    lines+=['','Geen gelijk shotbudget:4096 ruw tegenover13312 voor readout+ZNE.',
        'Intervallen:2000 whole-shot replicaties bij vaste twirls plus gedeelde onafhankelijke Jeffreys-uitleeskalibratietrekkingen.',
        'Niet gelijktijdig of dekkingsgecertificeerd; drift, gecorreleerde SPAM, extrapolatiebias, Trotterfout en MPS-truncatie ontbreken.','',
        '## Alleen te weinig shots?','',
        f"De ruwe shot-standaardfout van N is{se:.5f}; de afwijking van32 is{mean-32:.5f}.",
        f"De normale shot-only95%-benadering is[{mean-1.96*se:.5f}, {mean+1.96*se:.5f}].",
        'Louter eindige onafhankelijke shotstatistiek verklaart deze afwijking niet.',
        'Meer shots verkleinen de statistische spreiding als1/sqrt(shots), maar verwijderen op zichzelf geen systematische verschuiving. De foutbron is hiermee niet volledig geïdentificeerd.','',
        '## Parallelle klassieke controle','',
        f"Chi64: {c64['kernel_seconds']:.3f}s rekenkern; {cs['process_timing']['cold_worker_seconds']:.3f}s cold worker; één BLAS-thread.",
        'Gemeten tijdens ander lokaal werk, niet als geïsoleerde prestatiebenchmark.','',
        '| Verschil chi64 minus chi32 (één thread) | Lading | Spin | Dubbele bezetting |',
        '|---|---:|---:|---:|',
        '| RMS | '+' | '.join(f'{x:.6f}' for x in delta['rms_charge_spin_doublon'])+' |',
        '| Maximaal per site | '+' | '.join(f'{x:.6f}' for x in delta['max_abs_charge_spin_doublon'])+' |',
        '',f"Vooraf vastgelegde stabiliteitsscreen geslaagd: {delta['heuristic_screen_pass']}.",
        'Chi64 is niet als gecertificeerde referentie gebruikt. De opgeslagen72-mode-MPS is onafhankelijk met NumPy gecontracteerd; momentverschil kleiner dan4,2e-15.','',
        '## Hardware versus de benaderende chi64-referentie','',
        '| Methode | RMS verschil lading | RMS verschil spin | RMS verschil dubbele bezetting |',
        '|---|---:|---:|---:|']
    for name,row in zip(names,comp['RMS_discrepancies_charge_spin_doublon_by_arm']):
        lines.append('| '+name+' | '+' | '.join(f'{x:.6f}' for x in row)+' |')
    limits=comp['raw_minus_readoutZNE_discrepancy_hybrid95']
    lines+=['','Dit zijn verschillen tegenover een benadering, geen fouten tegenover een exact antwoord.',
        f"Spinverschilreductie door readout+ZNE: {comp['raw_minus_readoutZNE_discrepancy'][1]:.6f}; hybride95%-interval [{limits[0][1]:.6f}, {limits[1][1]:.6f}].",
        'Geen overtuigend positief mitigatie-effect aangetoond. Alle chi-referenties zijn opgenomen in VERIFICATION.json.','',
        '## Raming chi128','',
        f"Gemeten chi32: {c32['kernel_seconds']:.3f}s; chi64: {c64['kernel_seconds']:.3f}s; verhouding {ratio:.3f}.",
        f"Nogmaals dezelfde verhouding: {estimate['chi128_same_ratio_seconds']/60:.1f}minuten. Kubisch model (8x): {estimate['chi128_cubic_seconds']/60:.1f}minuten.",
        'Voorlopig12-25minuten plannen, geen gemeten tijd of gegarandeerde bovengrens. Meer tijd is mogelijk.',
        '15x150s is37,5minuten, maar factor15 volgt niet uit deze metingen. Chi128 is niet gestart.',
        'Generieke kubische MPS-SVD-kosten: tabel1 van [Paeckel et al.](https://arxiv.org/abs/1901.05824). De minutenraming is onze eigen extrapolatie, niet een resultaat uit dat artikel.','',
        '## Tijd en bewijs','',
        f"QPU-gebruik:5s; IBM aanmaak-tot-afronding: {audit['provider_created_to_finished_seconds']:.3f}s.",
        f"Eenmalige lokale circuitvoorbereiding: {audit['local_prepare_seconds']:.3f}s; archivering/analyse komen daar nog bij.",
        'Geen end-to-end of matched-accuracy-snelheidsvoordeel vastgesteld.',
        f"Alle41 gezamenlijke tests geslaagd; onafhankelijke native-readoutmatrixinversie plus aparte lineaire fit wijkt maximaal {audit['independent_native_readout_inverse_and_OLS_max_error']:.3g} af.",
        'Physics- en veilige-API-skills stuurden de onafhankelijke controles, vaste fit, claimgrenzen en het behoud van eerdere gegevens.',
        'Ruwe bitstrings, providerresultaat, werkelijk uitgevoerde QPY-circuits, kalibratie, bootstrapdata, broncodekopieën en controlesommen zijn bewaard.','']
    (out/'BEVINDINGEN.md').write_text('\n'.join(lines),encoding='utf-8')
    completion={'status':'COMPLETE_RETRIEVED_ANALYZED_CLASSICAL64_CHECKED','job_id':audit['job_id'],
        'hardware_shots':13312,'provider_circuits_verified':26,'qpu_charge_seconds':5,'qpu_cap_seconds':15,
        'no_new_hardware_job':True,'no_resubmission':True,'classical_chi64_complete':True,
        'classical_chi128_started':False,'classical_reference_certified':False,
        'matched_accuracy_advantage_demonstrated':False,'particle_number_target':32,
        'readout_zne_N':hw['arms'][2]['N'],'readout_zne_N95_hybrid':hw['arms'][2]['N_95pct_interval'],
        'tests':41,'classical_summary_sha256':h.safe.digest(classical/'summary.json'),
        'classical_verification_sha256':h.safe.digest(classical/'INDEPENDENT_VERIFICATION.json')}
    h.safe.exclusive_json(out/'COMPLETION.json',completion)
    shutil.copyfile(Path(__file__),out/'finalization_source.py')
    h.safe.exclusive_json(out/'delivery_sha256.json',{str(p.relative_to(out)):h.safe.digest(p)
        for p in out.rglob('*') if p.is_file() and p.name!='status_history.jsonl'})
    h.verify_files(out,'delivery_sha256.json')
    print(json.dumps({**completion,'chi128_minutes_same_ratio':estimate['chi128_same_ratio_seconds']/60,
        'chi128_minutes_cubic':estimate['chi128_cubic_seconds']/60}),flush=True)

if __name__=='__main__': main()

