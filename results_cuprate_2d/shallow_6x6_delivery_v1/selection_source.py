"""Seal a checked shallow-circuit choice without any hardware submission."""
from pathlib import Path
import json
import shutil
import audit_shallow_6x6 as a

ROOT=a.ROOT
FRONTIER=ROOT/'results_cuprate_2d/shallow_full6x6_frontier_v1'
OUT=ROOT/'results_cuprate_2d/shallow_6x6_delivery_v1'

def main():
    if OUT.exists(): raise FileExistsError('Delivery already exists')
    a.verify(a.PARENT,'delivery_sha256.json')
    a.verify(a.OUT,'sha256.json'); a.verify(FRONTIER,'sha256.json')
    first=a.read(a.OUT/'summary.json'); second=a.read(FRONTIER/'summary.json')
    before=next(r for r in first['circuits'] if r['name']=='original_factor1_twirl0')
    chosen=next(r for r in first['circuits'] if r['name']=='compact_factor1_twirl0')
    alternate=[r for r in first['circuits'] if r['name'].startswith('sparse_')]+second['candidates']
    if any(r['snapshot_unaligned_duration_seconds']<chosen['snapshot_unaligned_duration_seconds'] for r in alternate):
        raise AssertionError('Selection no longer matches measured best')
    if not chosen['cz']==before['cz']==15400 or chosen['CZ_depth']!=before['CZ_depth']:
        raise AssertionError('CZ trace/count invariant changed')
    depth_gain=1-chosen['depth']/before['depth']
    pulse_gain=1-chosen['physical_X_SX']/before['physical_X_SX']
    duration_gain=1-chosen['snapshot_unaligned_duration_seconds']/before['snapshot_unaligned_duration_seconds']
    decision={'status':'COMPACT_CANDIDATE_BUILT_CZ_BOTTLENECK_UNRESOLVED',
        'selected_method':'one-qubit-only cleanup of original CZ trace',
        'all8_original_factor1_twirls_preserved':True,
        'factor2_and_factor3_prototypes':'Only twirl0 prepared; full new hardware batch not prepared.',
        'old':before,'new':chosen,'depth_reduction_fraction':depth_gain,
        'pulse_reduction_fraction':pulse_gain,'snapshot_duration_reduction_fraction':duration_gain,
        'original_Hamiltonian_time_and_finite_circuit_preserved':True,
        'physics_terms_dropped':False,'Trotter_steps_reduced':False,
        'hardware_error_improvement_measured':False,'new_hardware_submission_authorized':False,
        'new_QPU_seconds':0,'classical_chi128_started':False,
        'exactness':'14 distinct tests plus per-wire2x2 segment and global-phase checks on full72-mode cleanup.',
        'rejected_routing_candidates':6,'remaining_bottleneck':'15400 CZ gates,564 CZ layers in baseline.',
        'input_manifest_sha256':{
            'hardware':a.digest(a.PARENT/'delivery_sha256.json'),
            'first_round':a.digest(a.OUT/'sha256.json'),
            'frontier_round':a.digest(FRONTIER/'sha256.json')}}
    OUT.mkdir()
    a.save(OUT/'decision.json',decision)
    lines=['# Quantumcontrole 6×6: compacter, maar CZ-belasting blijft hoog','',
        'Geen nieuwe QPU-run; geen wijziging van bestaande hardwaredata of van de klassieke χ=64-resultaten.','',
        '## Wat is aangepast?','',
        'Alleen opeenvolgende één-qubitbewerkingen rond de bestaande CZ-poorten zijn samengevoegd.',
        'De volledige Hamiltoniaan met t, t-prime, U en fermiontekens, T=0,4 en twee Trotterstappen blijven behouden.',
        'Alle CZ-poorten, hun volgorde per qubit en de uitleesmapping zijn behouden.',
        'Dit is een gelijkwaardige ideale berekening, geen verkorting van de fysieke evolutie.','',
        '| Eigenschap, representatieve twirl | Uitgevoerd | Compacter |',
        '|---|---:|---:|',
        f"| CZ-poorten | {before['cz']} | {chosen['cz']} |",
        f"| X/SX-pulsen | {before['physical_X_SX']} | {chosen['physical_X_SX']} |",
        f"| Totale diepte | {before['depth']} | {chosen['depth']} |",
        f"| CZ-diepte | {before['CZ_depth']} | {chosen['CZ_depth']} |",
        f"| Geraamde circuitduur | {before['snapshot_unaligned_duration_seconds']*1e6:.3f} µs | {chosen['snapshot_unaligned_duration_seconds']*1e6:.3f} µs |",
        '',f"Dat is {depth_gain:.1%} minder totale diepte, {pulse_gain:.1%} minder fysieke één-qubitpulsen en {duration_gain:.1%} kortere geraamde circuitduur.",
        'Alle acht oorspronkelijke twirls zijn opgebouwd en gecontroleerd. Hun nieuwe dieptes liggen tussen 2020 en 2044.',
        'De circuitduur gebruikt de opgeslagen backendkalibratie en is geen nieuwe hardwaremeting of QPU-factuurvoorspelling.','',
        '## Waarom is 1D gunstiger?','',
        'Een werkelijk 1D-model koppelt vooral naaste buren. De 6×6-2D-lattice heeft daarnaast verticale en diagonale koppelingen.',
        'Onze 6×6 blijft een 2D-fysisch model, ook wanneer de fermionmodi in een 1D-keten worden gerouteerd.',
        'Die ketenmapping gebruikt 71 verbindingen, terwijl binnen de geselecteerde fysieke qubits 108 CZ-verbindingen beschikbaar zijn.',
        'De 37 overige verbindingen zijn niet automatisch gratis bruikbaar: ook bij een andere mapping moeten de fermionpariteiten behouden blijven.','',
        'Vóór compilatie bevat het oorspronkelijke netwerk 10.224 fSWAP-blokken, waarvan 9.200 zonder fysische interactie.',
        'Dat betekent niet dat 90% van de uiteindelijke CZ-poorten zomaar kan worden geschrapt. Routing kan nodig zijn om koppelingen lokaal te maken; de compiler verwijdert al een deel van de overhead.','',
        '## Andere routes zijn getest, niet blind overgenomen','',
        'Drie gerichte swaproutes en drie planners die alleen disjuncte even-fermioninteracties herschikken zijn gecontroleerd.',
        'De gatevolgorde op iedere fermionmodus bleef behouden. Alle alternatieven waren langzamer dan de één-qubit-opschoning.',
        'Bijvoorbeeld: de look12-route verlaagt CZ van 15.400 naar 14.168, maar verhoogt de totale diepte naar 7.722 en de geraamde duur naar 274,52 µs. Dat is geen shallow verbetering.','',
        '## Grenzen en volgende beslissing','',
        'De beste gevonden variant heeft nog steeds 15.400 CZ-poorten en 564 CZ-lagen. Het belangrijke twee-qubitprobleem is dus niet opgelost.',
        'Opgeslagen T2-waarden van de geselecteerde qubits: minimum 7,49 µs, mediaan 136,05 µs. Dit onderstreept dat circuitduur relevant is, maar is geen berekening van de circuitfideliteit.',
        'De waargenomen hardwarefout kan hiermee niet uitsluitend aan één oorzaak worden toegeschreven.',
        'Voor verdere reductie is een andere 2D-gerichte decompositie/routing een logische kandidaat. Als daarbij niet-commuterende Trottertermen anders worden geordend, verandert het ideale eindige-stappencircuit en moet ook de klassieke referentie opnieuw worden gemaakt.',
        'Nieuwe hardware vereist een apart compleet meetprotocol, verse backend-/budgetcontrole en nieuwe expliciete toestemming. De oude autorisatie wordt niet hergebruikt.','',
        '## Verificatie en archief','',
        '14 tests zijn geslaagd: volledige kleine-systeemunitariteiten, een willekeurige 2×3-toestand, fermionpermutaties, uitleesmapping en de commutatie van disjuncte even-fermioninteracties.',
        'Op de volledige 72-modecircuits zijn de één-qubitsegmenten afzonderlijk als 2×2-matrices gecontroleerd, inclusief globale fase en onveranderde CZ-volgorde.',
        'Er is geen volledige 72-qubit-statevector gesimuleerd. Geen hardwarefoutverbetering of quantumvoordeel geclaimd.',
        'De physics-skill heeft de gelijkwaardigheidscontroles en het gescheiden bewaren van minder goede kandidaten gestuurd.',
        'Methode: [Qiskit Optimize1qGatesDecomposition](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.transpiler.passes.Optimize1qGatesDecomposition).',
        'De twee volledige proefrondes staan in shallow_full6x6_T04_v1 en shallow_full6x6_frontier_v1; de oorspronkelijke resultaten blijven onaangeroerd.','']
    (OUT/'RAPPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    shutil.copyfile(Path(__file__),OUT/'selection_source.py')
    a.save(OUT/'sha256.json',{p.name:a.digest(p) for p in OUT.iterdir() if p.is_file()})
    a.verify(OUT,'sha256.json')
    print(json.dumps({'status':decision['status'],'depth_gain':depth_gain,'duration_gain':duration_gain,
        'CZ_remaining':15400,'QPU_seconds_used':0}),flush=True)

if __name__=='__main__': main()

