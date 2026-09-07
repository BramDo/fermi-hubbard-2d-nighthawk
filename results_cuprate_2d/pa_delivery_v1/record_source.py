"""Seal the PA finding, including failed attempts; no provider calls."""
from pathlib import Path
import json
import shutil
from audit_pa_ancilla_6x6 import read,digest,save,ROOT,PARENT
from audit_shallow_6x6 import verify


def main():
    out=ROOT/'results_cuprate_2d/pa_delivery_v1'
    if out.exists(): raise FileExistsError('Never overwrite a delivery')
    results=ROOT/'results_cuprate_2d'
    pilot=results/'pa_ancilla_6x6_v3'; folded=results/'pa_folded_6x6_v1'
    previous=results/'shallow_6x6_delivery_v1'
    for directory in [pilot,folded,previous]: verify(directory,'sha256.json')
    verify(PARENT,'delivery_sha256.json')
    old=read(previous/'decision.json')['new']
    a=read(pilot/'summary.json'); b=read(folded/'summary.json')
    candidates=[r for r in a['circuits'] if r['name'].endswith('_twirl')]+[b['twirl']]
    best=min(candidates,key=lambda r:r['snapshot_unaligned_duration_seconds'])
    if any(r['depth']<old['depth'] or r['CZ_depth']<old['CZ_depth'] or
           r['snapshot_unaligned_duration_seconds']<old['snapshot_unaligned_duration_seconds']
           for r in candidates):
        raise AssertionError('Revisit conclusion: a tested PA circuit won a depth metric')
    if a['tests_passed']!=11 or b['tests_passed']!=11: raise AssertionError('Tests not complete')
    out.mkdir()
    decision={'status':'PA_IMPLEMENTED_AND_SMALL_SYSTEM_VALIDATED_BUT_NO_NATIVE_DEPTH_WIN',
        'selected_hardware_candidate':'none; keep previous 72-mode compact circuit as comparison',
        'PA_modes':72,'PA_ancillas':36,'PA_total_qubits':108,
        'best_tested_PA':best,'previous_compact':old,'distinct_tests_passed':11,
        'full_6x6_preparation_stabilizers_checked':25,
        'full_6x6_preparation_occupations_checked':72,
        'small_term_intertwining_max_abs':a['small_checks']['small_all_hopping_intertwining_max_abs'],
        'small_transpiled_state_max_abs':a['small_checks']['small_native_state_and_output_permutation_max_abs'],
        'layered_requires_new_classical_reference':True,
        'full_108_qubit_statevector_not_simulated':True,'paper_XYZ_schedule_not_reproduced':True,
        'no_new_hardware_authorization':True,'QPU_seconds_used':0,
        'phi_model_not_simplified':True,
        'interpretation':'Implementation/routing result, not an impossibility result for PA.',
        'remaining_work':'PA-specific low-depth block synthesis and preparation/routing co-design; no depth promise.'}
    save(out/'decision.json',decision)
    lines=['# PA: correct prototype, nog geen shallow Nighthawk-circuit','',
        'PA is geimplementeerd met 72 datamodi en 36 ancillas. De uitgevoerde offline resourceproef levert geen betere hardwarekandidaat.','',
        '| Volledig circuit met controle-twirl | Vorige compacte variant | Beste geteste PA |',
        '|---|---:|---:|',
        f"| Qubits in encoding | 72 | 108 |",
        f"| CZ-poorten | {old['cz']} | {best['cz']} |",
        f"| CZ-lagen | {old['CZ_depth']} | {best['CZ_depth']} |",
        f"| Totale diepte | {old['depth']} | {best['depth']} |",
        f"| Geraamde circuitduur | {old['snapshot_unaligned_duration_seconds']*1e6:.3f} us | {best['snapshot_unaligned_duration_seconds']*1e6:.3f} us |",
        '', 'De tabel telt voorbereiding en data-uitlezing mee. De nieuwe kandidaten gebruiken een controle-twirl, geen volledige ZNE-batch.',
        'Dit zijn circuitresources uit opgeslagen kalibratie, geen nieuwe hardwaremetingen, foutmarges of advantage-resultaten.',
        'De beste PA gebruikt een andere symmetrische Trottervolgorde. Dit is dus geen matched-accuracy speed comparison.','',
        '## Wat is wel gevalideerd?','',
        '11 verschillende tests slagen. PA-edgealgebra is op 2x2, 2x3 en 6x6 gecontroleerd.',
        'Op 2x2 komen alle Hubbard-hoppingtermen en onsite-interacties in beide pariteitssectoren overeen met een onafhankelijke occupation-basisreferentie.',
        'De volledige kleine-systeemdynamica klopt met de eigen JW-referentie. Tests omvatten chemische potentiaal, willekeurige toestanden en globale fase.',
        'De 6x6-voorbereiding is met een Clifford-tableau op alle 25 loopstabilisatoren en 72 beginbezettingen gecontroleerd.',
        'De 11 extra rand-/gauge-vrijheidsgraden zijn deterministisch aangevuld door de stabilizer-synthese; dit zijn geen extra fermionmodi.',
        'Geen volledige 108-qubit-statevector is gesimuleerd.','',
        '## Waar verdwijnt de winst?','',
        'Gedeelde pariteitssynthese vermindert in de oorspronkelijke eventvolgorde de ongerouteerde evolutie van 11.411 naar 6.194 CZ-poorten.',
        'De laaggegroepeerde ongerouteerde evolutie heeft 5.996 CZ-poorten, 454 CZ-lagen en totale diepte 1.112, maar sluit voorbereiding en chip-routing uit.',
        'Na voorbereiding en routing worden deze cijfers veel slechter. De afzonderlijk gecompileerde voorbereiding alleen heeft al 852 CZ-poorten en 375 CZ-lagen.',
        'De gerichte row-fold-layout eindigt met 25.786 CZ-poorten, 4.613 CZ-lagen en totale twirl-diepte 14.404; ook die is afgewezen.',
        'Ancillas geven dus geen automatische dieptewinst. Dit beperkt de huidige synthese/layout, niet PA als methode.','',
        '## Wat ontbreekt?','',
        'De paper-specifieke XYZ-bloksynthese, een passende volledige PA-layout en een ondiepe gezamenlijke ancilla-voorbereiding zijn nog niet gerealiseerd.',
        'De paperdiepte van 35 fSIM-lagen per Trotterstap is niet gereproduceerd en mag niet als Nighthawk-CZ-diepte worden gebruikt.',
        'Voor de gewijzigde layered-volgorde blijven een nieuwe klassieke referentie en Trotterconvergentie noodzakelijk.',
        'Alle t, t-prime, U en fermiontekens zijn behouden. Geen nieuwe hardware of chi=128 gestart.','',
        '## Bewaren en afwijkingen','',
        'v1 en v2 bevatten behouden softwarefouten in de rapportage/testinterface, beschreven in FAILED.md. De fysische modeltests faalden niet.',
        'v3 en de gevouwen-layoutproef zijn volledig afgerond en hebben hashmanifests.',
        'De physics-skill stuurde de code-subruimte-, teken-, voorbereidings- en onafhankelijkheidscontroles.',
        'Bron: [Algaba et al., Quantum 8,1327](https://arxiv.org/html/2302.01862v3).','']
    (out/'RAPPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    archives=['pa_ancilla_6x6_v1','pa_ancilla_6x6_v2','pa_ancilla_6x6_v3','pa_folded_6x6_v1']
    manifest={str(p.relative_to(ROOT)):digest(p) for name in archives for p in (results/name).rglob('*') if p.is_file()}
    sources=['PA_ANCILLA_PROTOCOL.md','cuprate_2d_pa_mapping.py','test_cuprate_2d_pa_mapping.py',
        'cuprate_2d_pa_pair_synthesis.py','test_cuprate_2d_pa_pair_synthesis.py',
        'audit_pa_ancilla_6x6.py','audit_pa_folded_layout.py','record_pa_pilot_result.py']
    manifest.update({name:digest(ROOT/name) for name in sources})
    save(out/'all_PA_artifacts_sha256.json',manifest)
    shutil.copyfile(Path(__file__),out/'record_source.py')
    save(out/'sha256.json',{p.name:digest(p) for p in out.iterdir() if p.is_file()})
    verify(out,'sha256.json')
    for name,expected in manifest.items():
        if digest(ROOT/name)!=expected: raise AssertionError('PA archive mismatch')
    print(json.dumps({'status':decision['status'],'best_PA_depth':best['depth'],
        'best_PA_CZ':best['cz'],'files_hashed':len(manifest),'QPU_seconds':0}),flush=True)


if __name__=='__main__': main()
