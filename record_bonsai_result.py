"""Consolidate the fixed-target Bonsai result without authorizing hardware."""
from pathlib import Path
import shutil
from audit_bonsai_6x6 import ROOT,PARENT,read,digest,save
from audit_shallow_6x6 import verify


def main():
    results=ROOT/'results_cuprate_2d'
    first=results/'bonsai_fixed_target_6x6_v1'
    second=results/'bonsai_xyz_6x6_v1'
    olddir=results/'shallow_6x6_delivery_v1'
    out=results/'bonsai_delivery_v1'
    if out.exists(): raise FileExistsError('Never overwrite a delivery')
    for directory in [first,second,olddir]: verify(directory,'sha256.json')
    verify(PARENT,'delivery_sha256.json')
    primary=read(first/'summary.json'); extra=read(second/'summary.json')
    old=read(olddir/'decision.json')['new']
    candidates=[r for data in [primary,extra] for r in data['circuits'] if r['name'].endswith('_twirl')]
    fastest=min(candidates,key=lambda r:r['snapshot_unaligned_duration_seconds'])
    fewest=min(candidates,key=lambda r:r['cz'])
    assert fastest['snapshot_unaligned_duration_seconds']>old['snapshot_unaligned_duration_seconds']
    assert all(r['depth']>old['depth'] and r['CZ_depth']>old['CZ_depth'] for r in candidates)
    assert primary['tests_passed']==extra['tests_passed']==7
    out.mkdir()
    decision={'status':'BONSAI_VALIDATED_FIXED_TARGET_BUT_NO_SHALLOW_CIRCUIT_GAIN',
        'tested_twirl_candidates':len(candidates),'best_duration_candidate':fastest,
        'fewest_CZ_candidate':fewest,'existing_compact':old,
        'CZ_count_reduction_fraction':1-fewest['cz']/old['cz'],
        'best_duration_ratio_to_existing':fastest['snapshot_unaligned_duration_seconds']/old['snapshot_unaligned_duration_seconds'],
        'all_candidates_preserve_model_and_old_finite_circuit':True,
        'encoding_qubits':72,'encoding_ancillas':0,
        'basic_tests_passed':7,'additional_XYZ_native_state_checks':2,
        'full72q_statevector_not_simulated':True,'qDRIFT_not_used':True,
        'readout_mitigation_and_ZNE_batch_not_prepared':True,
        'hardware_authorized':False,'QPU_seconds_used':0,
        'conclusion':'Lower count does not imply shallow depth. Current implementation does not win; Bonsai not ruled out as a family.',
        'next_decision':'Do not submit these circuits. Any different evolution decomposition needs a separate matched-reference/error study.'}
    save(out/'decision.json',decision)
    lines=['# Bonsai-proef: correct, maar niet shallow','',
        'Het volledige6x6-model en de oorspronkelijke eindige-circuit-evolutie zijn behouden. Geen nieuwe hardware-run.','',
        '| Representatief volledig circuit met controle-twirl | CZ | CZ-lagen | Totale diepte | Geraamde circuitduur |',
        '|---|---:|---:|---:|---:|']
    for name,row in [('Bestaand compact',old),('Bonsai: minste CZ',fewest),('Bonsai: kortste duur',fastest)]:
        lines.append(f"| {name} | {row['cz']} | {row['CZ_depth']} | {row['depth']} | {row['snapshot_unaligned_duration_seconds']*1e6:.3f} us |")
    lines += ['',f"De laagste CZ-telling is {decision['CZ_count_reduction_fraction']:.1%} lager. De kortste geschatte Bonsai-duur is nog {decision['best_duration_ratio_to_existing']:.2f} keer zo lang.",
        'Alle geteste Bonsai-varianten zijn dieper dan de bestaande compacte route.',
        f"Gemiddeld aantal CZ per CZ-laag: bestaand {old['cz']/old['CZ_depth']:.2f}; snelste Bonsai {fastest['cz']/fastest['CZ_depth']:.2f}. Dit toont het verlies aan parallelisme; het is geen fidelitymaat.",'',
        '## Wat is gebouwd en gecontroleerd?','',
        '- Hardware-afhankelijke ternaire bomen op de oude72-qubitselectie en een compacte72-qubitrechthoek.',
        '- Twee boomlabelingen; de tweede verlaagt de maximale bezettingspariteit van16 naar4 qubits op de rechthoek.',
        '- Annealing van Majoranaparen, zowel op poortkosten als met een extra straf voor de drukst belaste CZ-qubit.',
        '- Native lokale pariteitsnetwerken zonder SWAP-router; tijdelijke Steiner-wires blijven quantumdata en worden volledig hersteld.',
        '- Een X-only Fock-voorbereiding en de bijbehorende GF2-uitlezing voor lading, spin en doublons.',
        '- Zeven basistests plus aanvullende native2x2/2x3-toestandscontroles voor de tweede labeling.',
        '- Alle144 Majoranas zijn op de72-qubitmapping op anticommutatie gecontroleerd; geen volledige72-qubit-statevector gesimuleerd.','',
        'De maximale kleine-systeemtoestandsafwijkingen na nativecompilatie liggen onder1e-12. Alle Hamiltontermen, globale fasen, fermiontekens, beginbezettingen en T=0,4 blijven behouden.',
        'De cijfermatige testresultaten staan in de verification.json-bestanden van beide proefmappen.','',
        '## Interpretatie en beperkingen','',
        'Een boomgebaseerde mapping verkort sommige operatoren, maar het expliciet berekenen en terugherstellen van veel pariteiten laat poorten op gedeelde qubits na elkaar plaatsvinden.',
        'De telling daalt licht; de veel hogere CZ-diepte maakt de huidige implementatie ongeschikt als shallow opvolger.',
        'Dit is geen onmogelijkheidsbewijs voor Bonsai en geen volledige reproductie van de Boston-paper.',
        'Anders dan die paper is hier geen qDRIFT gebruikt en is de tijd of modelinhoud niet verkort.',
        'Dezelfde ideaal-eindige-circuitreferentie blijft dus bruikbaar; de niet-convergente chi64-referentie wordt daarmee niet exact.',
        'Duren komen uit de opgeslagen kalibratie en bevatten voorbereiding/uitlezing, maar geen reset, rep_delay, queue of nieuwe hardwaremeting.',
        'De nieuwe ruwe bits zijn geen directe fermionbezettingen. Masker en GF2-pariteiten zijn opgeslagen; hardware-readoutmitigatie en een nieuwe ZNE-meetbatch zijn nog niet gevalideerd.',
        'Er is geen quantumvoordeel, hardwarefidelitywinst of extra QPU-toestemming geclaimd.','',
        '## Bewaren en volgende beslissing','',
        'Alle8 controle-twirlkandidaten en hun ongetwirlde circuits blijven bewaard, inclusief minder goede varianten.',
        'De aanvullende labeling/load-proef is toegevoegd nadat de eerste labeling lange bezettingspariteiten liet zien; geen wijziging van de fysica.',
        'De physics-skill stuurde de onafhankelijke operator-, decoder-, toestands- en resourcecontroles.',
        'Geen nieuwe hardware indienen met deze kandidaten. Een andere tijdsevolutiedecompositie is een aparte keuze, met eigen referentie- en foutcontrole.',
        'Bronnen: [Bonsai](https://arxiv.org/abs/2212.09731), [Boston-paper](https://arxiv.org/html/2608.25024).','']
    (out/'RAPPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    source_names=['BONSAI_LOCAL_PROTOCOL.md','cuprate_2d_bonsai.py','test_cuprate_2d_bonsai.py',
        'audit_bonsai_6x6.py','bonsai_load_balancing.py','audit_bonsai_xyz_6x6.py','record_bonsai_result.py']
    artifact_hashes={str(p.relative_to(ROOT)):digest(p) for directory in [first,second]
                    for p in directory.rglob('*') if p.is_file()}
    artifact_hashes.update({name:digest(ROOT/name) for name in source_names})
    save(out/'all_Bonsai_artifacts_sha256.json',artifact_hashes)
    shutil.copyfile(Path(__file__),out/'record_source.py')
    save(out/'sha256.json',{p.name:digest(p) for p in out.iterdir() if p.is_file()})
    verify(out,'sha256.json')
    for name,expected in artifact_hashes.items():
        if digest(ROOT/name)!=expected: raise AssertionError('Bonsai archive mismatch')
    print({'status':decision['status'],'files_hashed':len(artifact_hashes),
           'fastest_depth':fastest['depth'],'fastest_us':fastest['snapshot_unaligned_duration_seconds']*1e6,
           'fewest_CZ':fewest['cz'],'QPU_seconds':0},flush=True)


if __name__=='__main__': main()
