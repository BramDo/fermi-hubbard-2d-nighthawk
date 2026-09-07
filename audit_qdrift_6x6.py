"""Bounded offline qDRIFT resource estimate and exact small-system pilot."""
from dataclasses import asdict
import io
import math
import platform
import shutil
import signal
import time
import unittest
import json
import networkx as nx
import numpy as np
import qiskit
from qiskit.quantum_info import Statevector
from qiskit_ibm_runtime.models import BackendProperties
import audit_bonsai_6x6 as archive
from audit_shallow_6x6 import Timing,metrics,guard,verify
from cuprate_2d_bonsai import Bonsai
from cuprate_2d_pa_mapping import occupations
from cuprate_2d_hubbard_pipeline import Cuprate2DConfig
from cuprate_2d_fermionic_mapping import build_network
from cuprate_2d_shallow_network import compact_bound
from cuprate_2d_tflo import explicit_twirl
from cuprate_2d_qdrift import (make_ensemble,circuit,trajectories,
    sparse_action_tables,occupation_hamiltonian,observables)
from test_cuprate_2d_bonsai import grid,fock_isometry

ROOT=archive.ROOT
OUT=ROOT/'results_cuprate_2d/qdrift_first_pilot_v1'
BONSAI=ROOT/'results_cuprate_2d/bonsai_xyz_6x6_v1'
T=.4
REPLICATES=256
ARMS=('pauli','grouped')
SMALL_N=(16,32,64,128,256,512)
LARGE_N=(128,256,512,1024)
read,save,digest=archive.read,archive.save,archive.digest


def summarize_samples(probabilities,values,exact,particles):
    result={}; raw={}
    for name in ('charge','spin','doublon'):
        samples=probabilities@values[name]
        reference=exact@values[name]
        mean=samples.mean(axis=0)
        se=samples.std(axis=0,ddof=1)/np.sqrt(len(samples))
        individual=np.sqrt(np.mean((samples-reference)**2,axis=1))
        result[name]={'reference':reference.tolist(),'ensemble_mean':mean.tolist(),
            'inter_circuit_MC_SE':se.tolist(),
            'RMSE_ensemble_vs_exact':float(np.sqrt(np.mean((mean-reference)**2))),
            'RMS_inter_circuit_MC_SE':float(np.sqrt(np.mean(se**2))),
            'single_circuit_RMSE_quantiles_10_50_90':np.quantile(individual,[.1,.5,.9]).tolist()}
        raw[name]=samples.tolist()
    number=probabilities@values['number']
    leakage=probabilities[:,values['number']!=particles].sum(axis=1)
    result['number']={'exact':particles,'ensemble_mean':float(number.mean()),
        'inter_circuit_MC_SE':float(number.std(ddof=1)/np.sqrt(len(number))),
        'single_circuit_min_max':[float(number.min()),float(number.max())]}
    result['sector_leakage']={'ensemble_mean':float(leakage.mean()),
        'inter_circuit_MC_SE':float(leakage.std(ddof=1)/np.sqrt(len(leakage))),
        'maximum_sample':float(leakage.max())}
    raw.update(number=number.tolist(),sector_leakage=leakage.tolist())
    return result,raw


def small_pilot():
    cfg=Cuprate2DConfig(lx=2,ly=2,holes=1,steps=2,dt=.2)
    mapping=Bonsai(grid(2,4),'xyz'); bits=occupations(cfg)
    b=sum(int(x)<<i for i,x in enumerate(bits)); particles=sum(bits)
    H=occupation_hamiltonian(cfg)
    assert np.max(np.abs(H-H.conj().T))<1e-13
    evals,evecs=np.linalg.eigh(H)
    initial_logical=np.eye(1<<cfg.qubits,dtype=complex)[:,b]
    exact_logical=evecs@(np.exp(-1j*T*evals)*(evecs.conj().T@initial_logical))
    # Independent expm reference checks the spectral exponentiation numerically.
    from scipy.linalg import expm
    expm_error=float(np.max(np.abs(expm(-1j*T*H)@initial_logical-exact_logical)))
    assert expm_error<3e-12
    indices,phases=fock_isometry(mapping)
    exact=np.zeros(1<<cfg.qubits,complex)
    exact[indices]=phases*exact_logical/phases[b]
    exact_prob=np.abs(exact)**2
    initial=Statevector.from_instruction(mapping.preparation(bits)).data
    values=observables(mapping)
    assert float(exact_prob[values['number']!=particles].sum())<1e-22
    old_logical=Statevector.from_instruction(build_network(cfg)).data
    old=np.zeros_like(exact); old[indices]=phases*old_logical/phases[b]
    old_result={name:{'reference':(exact_prob@values[name]).tolist(),
        'old_two_step_mean':(np.abs(old)**2@values[name]).tolist(),
        'RMSE_vs_continuous_exact':float(np.sqrt(np.mean(
            ((np.abs(old)**2-exact_prob)@values[name])**2)))}
        for name in ('charge','spin','doublon')}
    save(OUT/'small_exact_reference.json',{'config':asdict(cfg),'T':T,
        'logical_initial_bits_little_endian':bits,'particles':particles,
        'logical_state_real':exact_logical.real.tolist(),
        'logical_state_imag':exact_logical.imag.tolist(),
        'encoded_probabilities':exact_prob.tolist(),'basis_decode':{k:v.tolist() for k,v in values.items()},
        'expm_vs_eigh_max_abs':expm_error,'old_two_step_error':old_result,
        'spin_convention':'n_up-n_down, not divided by 2'})
    records=[]; native_checks={}
    for arm_index,arm in enumerate(ARMS):
        ensemble=make_ensemble(mapping,cfg,arm)
        tables=sparse_action_tables(ensemble,cfg.qubits)
        probe,_=circuit(mapping,ensemble,T,32,19,bits)
        compiled=archive.compile_native(probe,mapping.graph)
        actual=Statevector.from_instruction(compiled).data
        expected=Statevector.from_instruction(probe).data
        native_checks[arm]=float(np.max(np.abs(actual-expected)))
        assert native_checks[arm]<3e-11
        for N in SMALL_N:
            guard(); started=time.perf_counter(); seed=20260906+10000*arm_index+N
            psi=trajectories(ensemble,cfg.qubits,T,N,seed,initial,REPLICATES,tables)
            result,raw=summarize_samples(np.abs(psi)**2,values,exact_prob,particles)
            fidelity=np.abs(psi@exact.conj())**2
            row={'arm':arm,'N':N,'replicates':REPLICATES,'seed':seed,
                'lambda':ensemble.lam,'tau':ensemble.lam*T/N,**result,
                'mean_fidelity_to_continuous_exact':float(fidelity.mean()),
                'seconds':time.perf_counter()-started}
            if arm=='grouped':
                assert result['sector_leakage']['maximum_sample']<1e-22
                assert max(abs(x-particles) for x in result['number']['single_circuit_min_max'])<1e-9
            save(OUT/f'small_{arm}_N{N}.json',{'summary':row,'per_circuit_observables':raw,
                'per_circuit_fidelity':fidelity.tolist()})
            records.append(row)
            print(json.dumps({'phase':'small','arm':arm,'N':N,
                'RMSE':{k:result[k]['RMSE_ensemble_vs_exact'] for k in ('charge','spin','doublon')},
                'number':result['number']['ensemble_mean'],
                'leakage':result['sector_leakage']['ensemble_mean']}),flush=True)
    save(OUT/'small_summary.json',{'rows':records,'native_state_checks':native_checks,
        'old_two_step_error':old_result,'expm_vs_eigh_max_abs':expm_error,
        'no_hardware_or_shot_noise':True,'not_a_6x6_accuracy_certificate':True})
    return records,old_result,native_checks


def main():
    if OUT.exists(): raise FileExistsError('Never overwrite an audit')
    def stop(*_): raise TimeoutError('600-second local pilot limit')
    signal.signal(signal.SIGALRM,stop); signal.alarm(600)
    started=time.perf_counter()
    verify(archive.PARENT,'delivery_sha256.json')
    verify(archive.PREVIOUS,'sha256.json'); verify(BONSAI,'sha256.json')
    parent=read(archive.PARENT/'plan.json'); cfg=Cuprate2DConfig(**parent['config'])
    assert cfg.qubits==72 and sum(occupations(cfg))==32
    props_dict=read(archive.PARENT/'live_backend_properties.json')
    timing=Timing(BackendProperties.from_dict(props_dict))
    edges={tuple(sorted(g['qubits'])) for g in props_dict['gates'] if g['gate']=='cz'}
    physical=[10*r+c for r in range(2,10) for c in range(9)]
    inverse={q:i for i,q in enumerate(physical)}
    graph=nx.Graph(); graph.add_nodes_from(range(72))
    graph.add_edges_from((inverse[a],inverse[b]) for a,b in edges if a in inverse and b in inverse)
    mapping=Bonsai(graph,'xyz')
    mapping.set_assignment(read(BONSAI/'count_annealing.json')['assignment'])
    algebra=mapping.audit()
    OUT.mkdir(); (OUT/'source_snapshot').mkdir(); (OUT/'circuits').mkdir()
    archive.OUT=OUT
    sources=['QDRIFT_PILOT_PROTOCOL.md','cuprate_2d_qdrift.py','test_cuprate_2d_qdrift.py',
        'audit_qdrift_6x6.py','cuprate_2d_bonsai.py','test_cuprate_2d_bonsai.py',
        'cuprate_2d_pa_mapping.py','cuprate_2d_hubbard_pipeline.py','cuprate_2d_fermionic_mapping.py',
        'cuprate_2d_fermionic_dynamics.py','cuprate_2d_shallow_network.py',
        'cuprate_2d_tflo.py','cuprate_2d_tflo_refinement.py','audit_shallow_6x6.py','audit_bonsai_6x6.py']
    for name in sources: shutil.copyfile(ROOT/name,OUT/'source_snapshot'/name)
    shutil.copyfile(archive.PARENT/'live_backend_properties.json',OUT/'frozen_backend_properties.json')
    save(OUT/'plan.json',{'full_config':asdict(cfg),'T':T,'small_N':SMALL_N,'large_N':LARGE_N,
        'replicates_small':REPLICATES,'arms':ARMS,'large_seed':20260906,
        'physical_qubits':physical,'local_edges':list(map(list,graph.edges)),
        'Bonsai_labeling':'xyz','mode_assignment':mapping.assignment,
        'mapping_optimized_for_old_Trotter_not_qDRIFT':True,'algebra':algebra,
        'source_hashes':{n:digest(ROOT/n) for n in sources},
        'assignment_source_hash':digest(BONSAI/'count_annealing.json'),
        'frozen_backend_hash':digest(archive.PARENT/'live_backend_properties.json'),
        'hardware_authorized':False,'QPU_seconds_used':0,'package_installed':False,
        'runtime':{'python':platform.python_version(),'qiskit':qiskit.__version__,'numpy':np.__version__},
        'limits':{'wall_seconds':600,'RSS_GiB':2},
        'reference':'continuous exp(-iHT); different from old finite two-step circuit',
        'spin_convention':'n_up-n_down'})
    ensembles={arm:make_ensemble(mapping,cfg,arm) for arm in ARMS}
    estimates={arm:{'lambda':e.lam,'identity':e.identity,'sampled_operators':len(e.operators),
        '2_lambdaT_squared':2*(e.lam*T)**2,
        'leading_worst_case_reference_N_epsilon0_1':math.ceil(2*(e.lam*T)**2/.1),
        'leading_worst_case_reference_N_epsilon0_02':math.ceil(2*(e.lam*T)**2/.02),
        'angles_by_N':{str(N):e.lam*T/N for N in LARGE_N}}
        for arm,e in ensembles.items()}
    estimates['Qiskit_pauli_default_reps1_N']=math.ceil(2*(ensembles['pauli'].lam*T)**2)
    estimates['caveat']='Worst-case leading-order reference scale, not a lower bound, tight guarantee or observed accuracy requirement.'
    estimates['tighter_bound_normalization']='arXiv:2506.17199 Theorem1 channel is E(T/r)^(r Gamma); r is not total executed random steps.'
    save(OUT/'estimates.json',estimates)
    log=io.StringIO()
    tests=unittest.TextTestRunner(stream=log,verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromName('test_cuprate_2d_qdrift'))
    (OUT/'unit_tests.txt').write_text(log.getvalue(),encoding='utf-8')
    if not tests.wasSuccessful(): raise AssertionError(log.getvalue())
    print(json.dumps({'phase':'estimates','estimates':estimates,'tests':tests.testsRun}),flush=True)
    small,old_small,native_checks=small_pilot()
    rows=[]; old=read(archive.PREVIOUS/'decision.json')['new']
    for arm in ARMS:
        for N in LARGE_N:
            guard(); before=time.perf_counter()
            logical,draws=circuit(mapping,ensembles[arm],T,N,20260906,occupations(cfg))
            native=archive.compile_native(logical,graph)
            twirl,mask=explicit_twirl(native,seed=20260906)
            clean,proof=compact_bound(twirl)
            measured=archive.embed(clean,physical,mapping,mask)
            archive.native_edges(measured,edges)
            name=f'{arm}_N{N}_control_twirl'
            row={'name':name,'arm':arm,'N':N,'lambda':ensembles[arm].lam,
                'tau':ensembles[arm].lam*T/N,'seed':20260906,**metrics(measured,timing),
                'qpy':archive.circuit_file(name,measured),'cleanup_proof':proof,
                'sampled_indices':draws.tolist(),'preparation_and_readout_included':True,
                'full_ZNE_ensemble':False,'seconds':time.perf_counter()-before}
            row['duration_ratio_vs_old_compact']=row['snapshot_unaligned_duration_seconds']/old['snapshot_unaligned_duration_seconds']
            row['CZ_ratio_vs_old_compact']=row['cz']/old['cz']
            save(OUT/f'{name}_metrics.json',row); rows.append(row)
            print(json.dumps({'phase':'compiled','arm':arm,'N':N,'cz':row['cz'],
                'CZ_depth':row['CZ_depth'],'depth':row['depth'],
                'us':row['snapshot_unaligned_duration_seconds']*1e6,'seconds':row['seconds']}),flush=True)
    summary={'status':'LOCAL_QDRIFT_FIRST_PILOT_COMPLETE','resource_rows':rows,
        'small_system_rows':small,'old_compact_resources':old,'old_small_two_step_errors':old_small,
        'estimates':estimates,'tests_passed':tests.testsRun,'small_native_state_checks':native_checks,
        'hardware_improvement_measured':False,'6x6_accuracy_measured':False,
        'QPU_seconds_used':0,'new_package_installed':False,'hardware_authorized':False,
        'seconds':time.perf_counter()-started}
    save(OUT/'summary.json',summary)
    lines=['# qDRIFT: eerste lokale schatting en exact kleine-systeemproef','',
        'Geen extra package nodig: QDrift zit in de gebruikte Qiskit 2.5.2. Geen installatie of QPU-run uitgevoerd.',
        'Het aantal willekeurige evolutiestappen N is niet hetzelfde als Qiskit reps of het aantal meetshots.',
        'De eigen expliciet-N sampler is tegen de geinstalleerde QDrift gecontroleerd; zes tests slagen.','',
        '## 6x6 circuitresources: voorbeelden, geen nauwkeurigheidsbewijs','',
        'Volledig t=1, t-prime=-0.25, U=8, mu=0, T=0.4; 72 modes, 32 deeltjes. Alle Hamiltoniaantermen blijven in de samplingverdeling.',
        'Per kort circuit worden willekeurige termen gekozen; elke afzonderlijke term hoeft daarin niet voor te komen.',
        'Zelfde opgeslagen Nighthawk-kalibratie en Bonsai XYZ/count-rectangle. Een vaste seed, voorbereiding, controle-twirl en uitlezing inbegrepen.',
        'CZ-basis; geen native RZZ aangenomen. De assignment is niet opnieuw voor qDRIFT geoptimaliseerd.','',
        '| Variant | N random stappen | CZ | CZ-lagen | Totale diepte | Duur (us) |',
        '|---|---:|---:|---:|---:|---:|',
        f"| Bestaand compact twee-stappencircuit | - | {old['cz']} | {old['CZ_depth']} | {old['depth']} | {old['snapshot_unaligned_duration_seconds']*1e6:.3f} |"]
    for r in rows:
        lines.append(f"| {r['arm']} | {r['N']} | {r['cz']} | {r['CZ_depth']} | {r['depth']} | {r['snapshot_unaligned_duration_seconds']*1e6:.3f} |")
    lines += ['', 'Geschatte onafgeronde kritieke circuitduur, niet de gefactureerde QPU-tijd: geen reset, rep_delay, queue of volledige ZNE/kalibratiebatch.',
        'Resources van een sample voorspellen geen kwaliteitswinst. Minder hardwarefout kan worden ingeruild voor meer qDRIFT-fout.','',
        '## Exacte 2x2-proef','',
        'Een gat, drie deeltjes, dezelfde t/t-prime/U/T. Referentie is exp(-iHT) in de bezettingsbasis, onafhankelijk opgebouwd en op twee manieren geexponentieerd.',
        'Per rij 256 onafhankelijke noiseless circuits. RMSE over de vier lokale observabelen na middelen over circuits; geen meetshot- of hardwarefout.',
        'Spin is n_up-n_down. De volledige lokale waarden, spreiding, Monte Carlo standaardfouten en resultaten per circuit zijn opgeslagen.','',
        '| Variant | N | RMSE lading | RMSE spin | RMSE doublon | Gemiddeld deeltjesaantal | Sectorlekkage |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for r in small:
        lines.append(f"| {r['arm']} | {r['N']} | {r['charge']['RMSE_ensemble_vs_exact']:.6f} | {r['spin']['RMSE_ensemble_vs_exact']:.6f} | {r['doublon']['RMSE_ensemble_vs_exact']:.6f} | {r['number']['ensemble_mean']:.6f} | {r['sector_leakage']['ensemble_mean']:.6f} |")
    lines += ['', 'Ter vergelijking: het oude twee-stappencircuit op ditzelfde 2x2-systeem heeft tegenover de continue exacte evolutie:',
        ', '.join(f"{k} RMSE {v['RMSE_vs_continuous_exact']:.6f}" for k,v in old_small.items())+'.',
        'Dit is uitsluitend de kleine-systeemvergelijking; oude 6x6 chi64-uitkomsten zijn geen exacte qDRIFT-referentie.','',
        'Losse Pauli-qDRIFT behoudt het aantal deeltjes niet per circuit. Gegroepeerde hopping/onsite-qDRIFT doet dat wel, maar kost meer rotaties per random stap.',
        'Meer shots op hetzelfde random circuit verwijderen de algoritmische fout niet; onafhankelijke circuits middelen de random variatie, maar niet de eindige-N kanaalbias.',
        'N is dus een andere knop dan shots. Een goede lading hoeft geen goede spin of doublons te betekenen.','',
        '## Schaal en garanties','',
        '6x6: Pauli lambda=361 (identity 72 apart), grouped lambda=433. 2x2: Pauli lambda=33, grouped lambda=41.',
        'De random rotatiehoek is lambda*T/N. Hetzelfde N is op 6x6 dus geen vergelijkbare benaderingsnauwkeurigheid.',
        f"Qiskit reps=1 zou voor de 6x6 Pauli-decompositie al {estimates['Qiskit_pauli_default_reps1_N']} random Pauli-rotaties kiezen.",
        f"Conservatieve leidende-orde referentieschaal N~2(lambda*T)^2/epsilon: Pauli epsilon=0.1 geeft circa {estimates['pauli']['leading_worst_case_reference_N_epsilon0_1']:,} stappen.",
        'Dit is geen praktische ondergrens, geen scherpe eindige-N garantie en geen bewijs dat lokale observabelen zoveel nodig hebben.',
        'Normalisatiekanttekening: arXiv:2506.17199 Theorem 1 gebruikt E(T/r)^(r Gamma). Het aantal feitelijke kanaaltoepassingen is r*Gamma; r mag niet direct als fysiek aantal random poorten N worden gebruikt.',
        'Daarom wordt de lineaire-lambda interpretatie uit Boston Appendix B hier niet als hardware-garantie toegepast.','',
        '## Oordeel en vervolg','',
        'qDRIFT levert een instelbare diepte/benaderingsfout-afruil, geen automatische verbetering door een package.',
        'Nog geen 6x6 noiseless/noisy nauwkeurigheidsvalidatie, aangepaste Bonsai readoutmitigatie, volledige ZNE-batch of hardwaremeting.',
        'Een eventuele vervolgkeuze moet deeltjesbehoud, spin/doublonfout en totaal aantal circuits/shots tegelijk toetsen.',
        'De physics-skill stuurde het vooraf vastleggen van aannames, onafhankelijke teken/nummercontroles en bron/resultaatarchivering.','',
        'Bronnen: [Qiskit QDrift](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.synthesis.QDrift), [Campbell](https://arxiv.org/abs/1811.08017), [tighter bounds](https://arxiv.org/html/2506.17199), [Boston](https://arxiv.org/html/2608.25024).','']
    (OUT/'RAPPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    verify(archive.PARENT,'delivery_sha256.json'); verify(archive.PREVIOUS,'sha256.json')
    verify(BONSAI,'sha256.json')
    save(OUT/'sha256.json',{str(p.relative_to(OUT)):digest(p) for p in OUT.rglob('*') if p.is_file()})
    verify(OUT,'sha256.json')
    print(json.dumps({'phase':'done','seconds':summary['seconds'],'output':str(OUT)}),flush=True)


if __name__=='__main__': main()
