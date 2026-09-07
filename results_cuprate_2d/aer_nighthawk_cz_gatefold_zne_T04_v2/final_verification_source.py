"""Independent frozen-circuit and bootstrap audit, then finalize the ZNE pilot."""
from pathlib import Path
import argparse
import json
import shutil
import numpy as np
from qiskit import qpy
import aer_cuprate_cz_zne as z
import analyze_aer_noise_components as helper
import analyze_aer_cuprate_cz_zne as analysis

def canonical_parameter(value):
    # QPY converts NumPy scalars to native Python scalars. Compare values,
    # not their different repr strings; preserve exact numeric equality.
    if isinstance(value,np.generic):
        return value.item()
    if isinstance(value,(list,tuple,np.ndarray)):
        return tuple(canonical_parameter(v) for v in value)
    return value

def signature(circuit):
    return [(item.operation.name,tuple(circuit.find_bit(q).index for q in item.qubits),
             tuple(circuit.find_bit(c).index for c in item.clbits),canonical_parameter(item.operation.params))
            for item in circuit.data]

def verify(out):
    if (out/'COMPLETION.json').exists() or (out/'final_verification.json').exists():
        raise ValueError('Refuse overwrite')
    helper.verify_files(out,'run_archive_sha256.json')
    helper.verify_files(out/'analysis','sha256.json')
    plan=z.c.a.read(out/'plan.json')
    z.verify_inputs(plan)
    preflight=z.c.a.read(out/'preflight.json')
    pre={(r['group'],r['twirl']):r for r in preflight['checks']}
    checks=[]
    total_new_cz=0
    for tid in range(8):
        with (z.c.BASELINE/'circuits'/f'twirl_{tid}.qpy').open('rb') as handle:
            measured=qpy.load(handle)[0]
        base=z.prepare_base(measured)
        original=signature(base)
        for group in (1,2,3):
            entry=pre[group,tid]
            selected=set(entry['folding']['selected_original_indices'])
            # Reconstruct from saved positions, without calling fold_cz.
            expected=[]
            for index,row in enumerate(original):
                expected.append(row)
                if index in selected:
                    assert row[0]=='cz'
                    expected.extend([('cz',row[1],(),())]*2)
            with (out/'circuits'/f'{group}_{tid}.qpy').open('rb') as handle:
                saved=qpy.load(handle)[0]
            assert signature(saved)==expected
            count=saved.count_ops()['cz']
            assert count==1008*({1:2,2:3,3:1}[group])
            record=z.c.a.read(out/'blocks'/f'{group}_{tid}'/'record.json')
            raw=z.c.a.read(out/'blocks'/f'{group}_{tid}'/'aer_result.json')
            assert raw['success'] and record['trajectories']==16
            assert record['seed']==z.seed_for(group,tid)
            assert raw['results'][0]['seed_simulator']==record['seed']
            assert raw['results'][0]['shots']==16
            assert raw['results'][0]['metadata']['noise']=='kraus'
            assert raw['results'][0]['metadata']['method']=='statevector'
            total_new_cz+=count*16
            checks.append({'group':group,'twirl':tid,'cz':count,
                'raw_seed_verified':record['seed'],'serialized_instruction_replay':True})
    seeds={z.seed_for(g,t)+s for g in range(4) for t in range(8) for s in range(16)}
    assert len(seeds)==512
    data=z.c.a.read(out/'analysis/results.json')
    archive=np.load(out/'analysis/bootstrap_draws.npz')
    source=archive['source_means']
    methods=archive['method_means']
    assert source.shape==methods.shape==(2000,4,2,27)
    independent_linear=(4*source[:,0]+source[:,1]-2*source[:,2])/3
    linear_error=float(np.max(np.abs(independent_linear-methods[:,1])))
    assert linear_error<1e-12
    exact=np.asarray(plan['setting']['reference'])
    ideal_spin=(exact[1:18:2]-exact[0:18:2])/2
    raw_spin=(source[:,0,1,1:18:2]-source[:,0,1,0:18:2])/2
    zne_spin=(independent_linear[:,1,1:18:2]-independent_linear[:,1,0:18:2])/2
    reduction=np.sqrt(np.mean((raw_spin-ideal_spin)**2,axis=1))-np.sqrt(np.mean((zne_spin-ideal_spin)**2,axis=1))
    bounds=np.quantile(reduction,[.025,.975])
    expected_bounds=[data['primary_benefit_ci95']['low'][1],data['primary_benefit_ci95']['high'][1]]
    np.testing.assert_allclose(bounds,expected_bounds,atol=1e-13,rtol=0)
    primary=np.asarray(data['metrics'])[:,1]
    lo,hi=bounds
    relative=data['relative_spin_rmse_reduction_ci95']
    run=data['run_summary']
    times=run['group_run_seconds']
    zne_new_seconds=times[z.GROUPS[1]]+times[z.GROUPS[2]]
    checks_out={'status':'PASS_INDEPENDENT_CIRCUIT_AND_INFERENCE_AUDIT',
        'checks':checks,'independent_linear_draw_max_error':linear_error,
        'primary_spin_ci_independently_reproduced':bounds.tolist(),
        'actual_unique_seed_labels_including_reused_control':len(seeds),
        'new_cz_applications_including_diagnostic':total_new_cz,
        'logical_zne_cz_applications_including_reused_control':128*(1008+2016+3024),
        'raw128_cz_applications':128*1008,
        'new_qpu_seconds':0,'all_prior_archives_unchanged':True}
    z.c.a.write(out/'final_verification.json',checks_out)
    shutil.copyfile(Path(__file__),out/'final_verification_source.py')
    lines=['# Uitkomst: echte CZ-gatefolding ZNE in Aer','',
        f'Primaire spin-RMSE: {primary[0,1]:.5f} zonder ZNE -> {primary[1,1]:.5f} met lineaire ZNE.',
        f'Relatieve verandering: {100*data["relative_spin_rmse_reduction"]:.1f}% minder fout.',
        f'95%-interval relatieve verbetering: [{100*relative["low"]:.1f}%, {100*relative["high"]:.1f}%].',
        f'Absolute spin-RMSE-afname: {data["primary_benefits"][1]:.5f}, interval [{lo:.5f}, {hi:.5f}].',
        ('Verbetering zichtbaar binnen de conditionele Monte-Carlo-onzekerheid van dit model.'
         if lo>0 else 'Verbetering is niet statistisch opgelost bij dit budget; niet als succes claimen.'),'',
        '| Grootheid | Raw128 | Lineaire ZNE (primair) |',
        '|---|---:|---:|']
    for j,name in enumerate(['Lading-RMSE','Spin-RMSE','Doublon-RMSE','Spincontrast g']):
        lines.append(f'| {name} | {primary[0,j]:.5f} | {primary[1,j]:.5f} |')
    lines += ['', '## Interpretatie','',
        'Dezelfde 3x3, 18-qubit, U/t=8, T=0.4, twee-Trotterstappen en acht twirls.',
        'Factoren 1,2,3 hebben 1008,2016,3024 echte CZ-applicaties per circuit.',
        'Elk extra CZ-paar is ideaal de identiteit, maar behoudt de volledige gekalibreerde',
        'gatefout. Dit is daadwerkelijke digitale gatefolding in de simulator.',
        'Het schaalt CZ-gateaantallen; het is niet gegarandeerd een uniforme vermenigvuldiging',
        'van het effectieve ruiskanaal. T1/T2-ruis hoeft niet met de CZ te commuteren.',
        'De extrapolator en plaatsingsseeds waren vooraf vastgelegd; geen selectie op succes.',
        'Alleen CZ-ruis wordt versterkt. Eenqubit- en uitleesfouten blijven bestaan.',
        f'De afzonderlijke CZ-noise-off-controle geeft spin-RMSE {primary[3,1]:.5f} en g={primary[3,3]:.5f}.',
        'Deze controle is zelf een Monte-Carlo-schatting, geen exact of hardwarebereikbaar resultaat.',
        f'Lineaire ZNE wijkt bij {len(data["selective_floor_check"]["coordinates_excluding_zero"])} van 27 momenten af',
        'van CZ-off buiten de gezamenlijke 95%-Monte-Carlo-band; dit toetst resterende extrapolatiebias.',
        f'Kwadratische ZNE geeft spin-RMSE {primary[2,1]:.5f}; uitsluitend een secundaire gevoeligheidscheck.',
        'Methodeafhankelijkheid en ontbrekende modelruis vallen niet binnen de vermelde intervallen.',
        f'Onfysische negatieve twee-modekansen bij de primaire puntschatting: {data["ranges_primary"]["zne_linear_PRIMARY"]["negative_two_mode_probabilities"]}.',
        'Er is niets geclipt. ZNE-momenten hoeven geen positieve dichtheidsmatrix te vormen.',
        f'Standaardfout spincontrast wordt circa {data["g_se_amplification_vs_raw"]:.2f}x die van raw128.',
        'Dit zijn conditionele ruistrajecten met analytische readout, geen echte 512-shotmeting;',
        'de extra uiteindelijke bitstring-meetvariantie is hier niet gesimuleerd.','',
        '## Budget en validatie','',
        '384 nieuwe productietrajecten: 128 bij factor2, 128 bij factor3, 128 diagnostisch.',
        'Factor1 hergebruikt de 128 gecontroleerde trajecten met gescheiden seeds.',
        'ZNE gebruikt 3x zoveel trajecten en 6x zoveel CZ-applicaties als raw128.',
        'Dus geen conclusie over winst bij gelijk tijd-/shotbudget of binnen de oude 5s-QPU-limiet.',
        f'Nieuwe ZNE-run+result-simulatietijd: {zne_new_seconds:.2f} s; diagnostiek: {times[z.GROUPS[3]]:.2f} s.',
        f'Totaal nieuw: {sum(times.values()):.2f} s ({sum(times.values())/60:.2f} min), exclusief opzet en audits.',
        'Nieuwe QPU-seconden: 0; geen submit-lock of hardwarejob aangepast.',
        f'{z.c.a.read(out/"analysis/verification.json")["tests"]} regressietests; alle 24 noise-off circuits gecontroleerd.',
        f'Maximale noise-off-afwijking {max(r["max_noise_off_error"] for r in preflight["checks"]):.3g};',
        f'onafhankelijke observabelefout {data["independent_physical_max_error"]:.3g}.',
        'Bootstrap-foutpropagatie en bewaarde gatevolgordes nogmaals onafhankelijk gereproduceerd.',
        'Alle code en resultaten bewaard, inclusief mislukte preflight-v1 en diens oorspronkelijke broncode.',
        'De QPY save-expval-compatibiliteit is hersteld via reconstructie uit de oorspronkelijke meetcircuits.',
        'Een kunstmatige Kraus-depolarisatietest met geforceerde fusion faalde numeriek;',
        'die bevinding blijft gedocumenteerd. Exacte depolarisatie- en Kraus-relaxatietests slagen.',
        'Geen modelparameter aangepast wegens die testfout.','',
        'Dit is nog geen aangetoonde Nighthawk-hardwaremitigatie of quantum advantage.',
        'Volledige tabellen, kromming, geneste steekproefchecks en onzekerheden: analysis/results.json.',
        'Protocol: AER_CZ_ZNE_PROTOCOL.md.','']
    (out/'BEVINDINGEN.md').write_text('\n'.join(lines),encoding='utf-8')
    analysis.finalize(out)
    print(json.dumps({'raw_spin_rmse':primary[0,1],'zne_spin_rmse':primary[1,1],
        'spin_reduction_relative':data['relative_spin_rmse_reduction'],
        'relative_ci95':relative,'new_run_seconds':sum(times.values()),'new_qpu_seconds':0}),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    verify(args.output.resolve())
