"""Close v1 as provisional and v2 as the corrected primary sensitivity screen."""
from pathlib import Path
import shutil
import json
import numpy as np
from qiskit import qpy
import aer_cuprate_cz_half_v2 as v2
import analyze_aer_noise_components as analysis
import aer_cuprate_noise_components as c

def wire_trace(circuit):
    traces = [[] for _ in range(circuit.num_qubits)]
    for item in circuit.data:
        name = item.operation.name
        if name not in c.a.NATIVE:
            continue
        qubits = tuple(circuit.find_bit(q).index for q in item.qubits)
        entry = (name, qubits, tuple(float(p) for p in item.operation.params))
        for q in qubits:
            traces[q].append(entry)
    return traces

def main():
    first = c.a.RESULTS/'aer_nighthawk_full_cz_half_T04_v1'
    corrected = c.a.RESULTS/'aer_nighthawk_full_cz_half_T04_v2_disjoint_seeds'
    audit = c.a.RESULTS/'aer_seed_overlap_audit_2026-09-06'
    impact = c.a.RESULTS/'aer_seed_overlap_impact_2026-09-06'
    if (first/'COMPLETION.json').exists() or (corrected/'COMPLETION.json').exists():
        raise ValueError('Refuse re-finalization')
    checks = {}
    for root, manifest in [(first,'run_archive_sha256.json'),
                           (first/'analysis','sha256.json'),
                           (corrected,'run_archive_sha256.json'),
                           (corrected/'analysis','sha256.json'),
                           (audit,'sha256.json'),(impact,'sha256.json')]:
        checks[str(root.relative_to(c.a.ROOT))] = analysis.verify_files(root,manifest)
    for root in (first,corrected):
        for name, digest in c.a.read(root/'plan.json')['input_sha256'].items():
            assert c.a.digest(c.a.ROOT/name) == digest
    # Independently verify ordered gates on each wire, not only aggregate counts.
    for tid in range(8):
        circuits = []
        for root in (c.BASELINE,first,corrected):
            with (root/'circuits'/f'twirl_{tid}.qpy').open('rb') as handle:
                circuits.append(qpy.load(handle)[0])
        assert wire_trace(circuits[0]) == wire_trace(circuits[1]) == wire_trace(circuits[2])
    seed_labels = []
    for model in range(2):
        for tid in range(8):
            record = c.a.read(corrected/'blocks'/f'{model}_{tid}'/'record.json')
            assert record['seed'] == v2.seed_for(model,tid)
            seed_labels.extend(record['seed']+shot for shot in range(record['trajectories']))
    assert len(seed_labels) == len(set(seed_labels)) == 256
    data = c.a.read(corrected/'analysis/results.json')
    metrics = np.asarray(data['metrics'])[:,1]
    gains = data['primary_benefits']
    lower, upper = data['primary_benefit_ci95']['low'], data['primary_benefit_ci95']['high']
    intervals = data['metric_ci95']
    run_seconds = sum(data['run_seconds'].values())
    relative = 100*data['relative_spin_rmse_reduction']
    relative_ci = data['relative_spin_rmse_reduction_ci95']
    lines = ['# Gecorrigeerde Aer-test: halvering van CZ-restdepolarisatie', '',
        'Primaire vergelijking met gescheiden seedbereiken: hetzelfde 3x3 spinvolle',
        'Hubbard-circuit, U/t=8, T=0.4, twee Trotterstappen, 1008 CZ per twirl.',
        '128 ruistrajecten per model; alle acht twirls behouden. Referentie is',
        'het ideale eindige Trottercircuit, niet een extra claim over Trotterconvergentie.', '',
        '| Grootheid | Volledig model | Alleen CZ-restdepolarisatie half |',
        '|---|---:|---:|']
    for j,label in enumerate(['Lading-RMSE','Spin-RMSE','Doublon-RMSE','Spincontrast g']):
        lines.append(f'| {label} | {metrics[0,j]:.5f} | {metrics[1,j]:.5f} |')
    lines += ['', f'Spin-RMSE neemt af met {gains[1]:.5f}; puntgewijs 95%-interval',
        f'[{lower[1]:.5f}, {upper[1]:.5f}]. Relatieve afname {relative:.1f}%,',
        f'interval [{100*relative_ci["low"]:.1f}%, {100*relative_ci["high"]:.1f}%].',
        f'Spincontrast neemt toe met {gains[3]:.5f}; interval [{lower[3]:.5f}, {upper[3]:.5f}].',
        'Spin is n_up-n_down; g is projectie op het ideale spinprofiel, geen fidelity.',
        'Intervallen: 2000 fixed-twirl bootstraps van volledige trajectvectoren;',
        'alleen Monte-Carlo-onzekerheid binnen dit model, geen hardware/modelonzekerheid.', '',
        '## Wat is wel en niet aangetoond', '',
        ('De spinverbetering is in deze lokale modelscreen statistisch opgelost.'
         if lower[1] > 0 else
         'De spinverbetering is met dit trajectbudget nog niet statistisch opgelost.'),
        'Alle overige gemodelleerde fouten, inclusief CZ-T1/T2 en uitleesruis, zijn gelijk.',
        'De totale CZ-infideliteit halveert dus niet. Uitleesruis is eenmaal analytisch',
        'toegepast op premeasurement-expectaties; dit zijn geen hardware-bitshots.',
        'Lading/doublon-verbetering beoordelen op hun eigen intervallen in analysis/results.json.',
        'Dit is een hypothetische kanaalreductie, geen uitgevoerde ZNE of PEC,',
        'geen gemeten hardwareverbetering en geen bewijs van quantum advantage.',
        'Het model mist onder meer idle-gap-relaxatie, coherente/contextuele fouten,',
        'crosstalk, leakage, preparatiefouten en drift. Nighthawk voorspellen vereist',
        'nog een gecontroleerde koppeling aan hardwareobservabelen en modelvalidatie.', '',
        '## Verplichte correctie van eerdere onzekerheid', '',
        'In v1 en eerdere Aer-screens overlapten de runseeds over de shot-index.',
        'Dat is bevestigd in de vastgelegde Aer 0.17.2-bron en met een goedkope test.',
        'De eerdere bootstrapintervallen en daarop gebaseerde significantieclaims',
        'zijn daarom voorlopig; de originele data en puntwaarden zijn niet veranderd.',
        'V1: spin-RMSE 0.20802 -> 0.16801 (19.2%). Gebruik die oorspronkelijke',
        'foutmarges niet als bewijs; deze v2-herhaling is nu primair.',
        'De oudere 512-bitshotcontrole had g=0.58959, v1 had g=0.68522.',
        'De seed-cluster-schatting maakt hun standaardfouten circa 1.8x en 2.1x',
        'groter. Dat verklaart niet bewezen de hele controleafwijking. De afwijking',
        'wordt niet weggepoetst door naar een andere estimator te verwijzen.',
        'Zie AER_SEED_CORRECTION_2026-09-06.md en het afzonderlijke impact-archief.', '',
        '## Verificatie en kosten', '',
        f'{c.a.read(corrected/"analysis/verification.json")["tests"]} tests geslaagd.',
        'Alle 256 shot-seedlabels verschillend; geordende native gate-sporen op iedere',
        'wire identiek tussen oude controle, v1 en v2 voor alle acht twirls.',
        f'Onafhankelijke reconstructiefout observabelen: {data["independent_max_physical_error"]:.3g}.',
        'Volledig controlemodeI gelijk aan opgeslagen oorspronkelijke quantumkanalen',
        'tot 3.56e-15; readout op alle 18 modes identiek; noise-off maxfout 2.27e-14.',
        f'Aer run+result samen {run_seconds:.2f} s ({run_seconds/60:.2f} min) voor v2.',
        'Dit sluit opzet, preflight, tests, analyse en archiveren uit; geen end-to-end benchmark.',
        'Nieuwe QPU-seconden: 0. Oude hardwarejob en submit-lock niet veranderd.', '']
    (corrected/'BEVINDINGEN.md').write_text('\n'.join(lines),encoding='utf-8')
    shutil.copyfile(c.a.ROOT/'AER_SEED_CORRECTION_2026-09-06.md',corrected/'SEED_CORRECTION.md')
    shutil.copyfile(Path(__file__),corrected/'finalization_source.py')
    c.a.write(corrected/'cross_archive_verification.json', {
        'status':'PASS_DISJOINT_SEEDS_AND_NATIVE_TRACE_IDENTITY',
        'hash_counts': checks, 'native_wire_traces_identical_all_8_twirls': True,
        'unique_seed_labels': len(set(seed_labels)), 'new_qpu_seconds': 0,
        'historical_control_discrepancy_fully_resolved': False,
        'seed_impact_manifest_sha256': c.a.digest(impact/'sha256.json'),
        'seed_regression_manifest_sha256': c.a.digest(audit/'sha256.json')})
    c.a.write(first/'COMPLETION.json', {
        'status':'COMPLETE_BUT_INDEPENDENT_BOOTSTRAP_INVALID',
        'primary_replacement':str(corrected.relative_to(c.a.ROOT)),
        'all_original_samples_and_analyses_preserved':True, 'new_qpu_seconds':0,
        'reason':'Adjacent run seeds overlap per-shot RNG seeds; original independent-bootstrap confidence claims are withdrawn.'})
    c.a.write(first/'final_archive_sha256.json', {
        str(p.relative_to(first)): c.a.digest(p) for p in first.rglob('*') if p.is_file()})
    v2.finalize(corrected)
    print(json.dumps({'spin_rmse':metrics[:,1].tolist(),'spin_benefit_ci':[lower[1],upper[1]],
                      'relative_percent':relative,'spin_contrast':metrics[:,3].tolist(),
                      'run_seconds':run_seconds,'new_qpu_seconds':0}))

if __name__ == '__main__':
    main()
