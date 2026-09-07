"""Bounded reproducible PA pilot: no IBM service construction or submission."""
from collections import Counter
from dataclasses import asdict
from pathlib import Path
import hashlib
import io
import json
import platform
import shutil
import signal
import time
import unittest
import numpy as np
import qiskit
from qiskit import QuantumCircuit, ClassicalRegister, transpile, qpy
from qiskit.quantum_info import StabilizerState, Pauli, Statevector
from qiskit.transpiler import CouplingMap
from qiskit_ibm_runtime import RuntimeDecoder
from qiskit_ibm_runtime.models import BackendProperties
from cuprate_2d_pa_mapping import PA, occupations
from cuprate_2d_hubbard_pipeline import Cuprate2DConfig
from cuprate_2d_tflo import explicit_twirl
from cuprate_2d_shallow_network import compact_bound, verify_cleanup
from audit_shallow_6x6 import Timing, metrics, verify, guard
from test_cuprate_2d_pa_mapping import even_isometry, independent_hop_image, mapped_hop, jw_same_events

ROOT=Path(__file__).resolve().parent
PARENT=ROOT/'results_cuprate_2d/hardware_readout_cz_folding_6x6_2026-09-06'
OUT=ROOT/'results_cuprate_2d/pa_ancilla_6x6_v2'


def read(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'),cls=RuntimeDecoder)
def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):
    with path.open('x',encoding='utf-8') as f:
        json.dump(value,f,indent=2,allow_nan=False); f.write('\n')


def circuit_file(name,circuit):
    path=OUT/'circuits'/(name+'.qpy')
    with path.open('xb') as f: qpy.dump(circuit,f)
    with path.open('rb') as f:
        copy=qpy.load(f)[0]
        if copy!=circuit or copy.metadata!=circuit.metadata: raise AssertionError('QPY roundtrip')
    return str(path.relative_to(OUT))


def structural(circuit):
    return {'qubits':circuit.num_qubits,'depth':circuit.depth(),
        'CZ_depth':circuit.depth(lambda i:i.operation.name=='cz'),
        'CZ':circuit.count_ops().get('cz',0),'operations':dict(circuit.count_ops())}


def compile_pa(circuit,coupling,seed=9,initial=None):
    return transpile(circuit,basis_gates=['rz','sx','x','cz'],coupling_map=coupling,
        initial_layout=initial,optimization_level=3,approximation_degree=1,
        seed_transpiler=seed,layout_method='sabre',routing_method='sabre')


def readout(circuit,mapping,final_index,mask=None):
    result=circuit.copy()
    classical=ClassicalRegister(mapping.modes,'meas'); result.add_register(classical)
    output=[final_index[mapping.data[m]] for m in range(mapping.modes)]
    result.measure(output,classical)
    result.metadata={**(circuit.metadata or {}),'logical_mode_to_physical':output,
        'logical_readout_mask':[0 if mask is None else int(mask[q]) for q in output],
        'no_hardware_authorization':True}
    return result


def verify_native(circuit,edges):
    for inst in circuit.data:
        if inst.operation.name not in {'rz','sx','x','cz','measure'}:
            raise AssertionError('Unexpected gate')
        if inst.operation.name=='cz':
            qs=tuple(sorted(circuit.find_bit(q).index for q in inst.qubits))
            if qs not in edges: raise AssertionError('CZ outside saved hardware connectivity')


def small_numeric_checks():
    mapping=PA(2,2); basis,W=even_isometry(mapping)
    cfg=Cuprate2DConfig(lx=2,ly=2,holes=0,steps=2,dt=.2)
    errors=[]
    for term in mapping.model_terms(cfg):
        if term['kind']=='hop':
            errors.append(float(np.max(np.abs(mapped_hop(W,term['p'],term['q'],mapping)
                -independent_hop_image(basis,W,term['p'],term['q'])))))
    bits=occupations(cfg); prep=mapping.preparation(bits)
    initial=Statevector.from_instruction(prep)
    grid=CouplingMap.from_grid(3,4)
    evolution=mapping.evolution(cfg,'layered')
    full=prep.compose(evolution)
    native=compile_pa(full,grid)
    compiled=Statevector.from_instruction(native).data
    final_index=native.layout.final_index_layout()
    indices=np.arange(1<<mapping.n)
    physical=sum(((indices>>q)&1)<<final_index[q] for q in range(mapping.n))
    target=Statevector.from_instruction(full).data
    error=float(np.max(np.abs(compiled[physical]-target)))
    if error>2e-10: raise AssertionError('Routed small-system unitary/layout check failed')
    old=initial.evolve(mapping.evolution(cfg,'network')).data
    return {'small_all_hopping_intertwining_max_abs':max(errors),
        'small_encoding_isometry_max_abs':float(np.max(np.abs(W.conj().T@W-np.eye(len(basis))))),
        'small_native_state_and_output_permutation_max_abs':error,
        'small_layered_vs_old_network_state_distance':float(np.linalg.norm(target-old)),
        'state_distance_is_Trotter_order_change_not_mapping_error':True}


def main():
    if OUT.exists(): raise FileExistsError('Never overwrite a PA pilot')
    def stop(*_): raise TimeoutError('PA pilot 600-second bound')
    signal.signal(signal.SIGALRM,stop); signal.alarm(600)
    start=time.perf_counter()
    verify(PARENT,'delivery_sha256.json')
    parent=read(PARENT/'plan.json'); cfg=Cuprate2DConfig(**parent['config'])
    props_dict=read(PARENT/'live_backend_properties.json')
    props=BackendProperties.from_dict(props_dict); timing=Timing(props)
    edges={tuple(sorted(g['qubits'])) for g in props_dict['gates'] if g['gate']=='cz'}
    expected={(q,q+1) for q in range(120) if q%10<9}|{(q,q+10) for q in range(110)}
    if edges!=expected: raise AssertionError('Saved backend is not the expected 10x12 grid')
    coupling=CouplingMap([list(e) for a,b in sorted(edges) for e in [(a,b),(b,a)]])
    OUT.mkdir(); (OUT/'source_snapshot').mkdir(); (OUT/'circuits').mkdir()
    sources=['PA_ANCILLA_PROTOCOL.md','cuprate_2d_pa_mapping.py','test_cuprate_2d_pa_mapping.py',
             'audit_pa_ancilla_6x6.py','cuprate_2d_shallow_network.py','cuprate_2d_fermionic_mapping.py',
             'cuprate_2d_fermionic_dynamics.py','cuprate_2d_hubbard_pipeline.py',
             'cuprate_2d_tflo.py','cuprate_2d_tflo_refinement.py','audit_shallow_6x6.py']
    for source in sources: shutil.copyfile(ROOT/source,OUT/'source_snapshot'/source)
    save(OUT/'plan.json',{'config':asdict(cfg),'scope':'PA correctness and offline native resource pilot',
        'no_provider_calls':True,'QPU_seconds_used':0,'hardware_authorized':False,
        'runtime':{'python':platform.python_version(),'qiskit':qiskit.__version__},
        'compile_seeds':[9,27],'saved_backend_qubits':120,'saved_backend_edges':len(edges),
        'source_sha256':{name:digest(ROOT/name) for name in sources},
        'parent_manifest_sha256':digest(PARENT/'delivery_sha256.json'),
        'backend_properties_sha256':digest(PARENT/'live_backend_properties.json')})
    log=io.StringIO()
    tests=unittest.TextTestRunner(stream=log,verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromName('test_cuprate_2d_pa_mapping'))
    (OUT/'unit_tests.txt').write_text(log.getvalue(),encoding='utf-8')
    if not tests.wasSuccessful(): raise AssertionError(log.getvalue())
    checks=small_numeric_checks()
    mapping=PA(6,6); algebra=mapping.audit()
    bits=occupations(cfg); prep=mapping.preparation(bits)
    tableau=StabilizerState(prep)
    loop_values=[float(tableau.expectation_value(Pauli(s.signed_label(mapping.n))).real)
                 for s in mapping.stabilizers]
    data_values=[float(tableau.expectation_value(Pauli(mapping.vertex(m).label(mapping.n))).real)
                 for m in range(mapping.modes)]
    assert loop_values==[1.]*len(loop_values)
    assert data_values==[(-1.)**bit for bit in bits]
    checks['all_6x6_preparation_loop_expectations']=loop_values
    checks['all_6x6_preparation_data_expectations_correct']=True
    save(OUT/'verification.json',checks)
    save(OUT/'algebra.json',algebra)
    save(OUT/'mapping.json',{'logical_mode_to_PA_wire':mapping.data,'ancilla_wires':mapping.anc,
        'elementary_edges':[{'modes':[a,b],'pauli':mapping.edges[a,b].signed_label(mapping.n)}
                            for a,b in mapping.graph.edges],
        'stabilizers':[s.signed_label(mapping.n) for s in mapping.stabilizers]})
    print(json.dumps({'phase':'validated','tests':tests.testsRun,'algebra':algebra,'small':checks}),flush=True)
    records=[]
    preparation_native=compile_pa(prep,coupling,9)
    verify_native(preparation_native,edges)
    row={'name':'preparation_only','scope':'separate compilation, not additive',
         **metrics(preparation_native,timing),'qpy':circuit_file('preparation_only',preparation_native)}
    records.append(row); save(OUT/'preparation_metrics.json',row)
    for ordering,seeds in [('network',[9]),('layered',[9,27])]:
        evolution=mapping.evolution(cfg,ordering)
        # Guard every mapped Pauli against every loop constraint on the actual 108-wire encoding.
        weights=Counter()
        for term in mapping.model_terms(cfg):
            if term['kind']=='hop':
                for pauli in mapping.hopping(term['p'],term['q']):
                    assert all(pauli.commutes(s) for s in mapping.stabilizers)
                    weights[len(pauli.support)]+=1
        save(OUT/(ordering+'_events.json'),mapping.events(cfg,ordering))
        # All-to-all reference excludes physical routing but includes native gate decomposition.
        local=transpile(evolution,basis_gates=['rz','sx','x','cz'],optimization_level=3,
                        approximation_degree=1,seed_transpiler=9)
        save(OUT/(ordering+'_unrouted_evolution.json'),
             {'scope':'diagnostic only; excludes preparation and hardware routing',
              **structural(local),'Pauli_weight_histogram':dict(weights)})
        for seed in seeds:
            guard()
            full=prep.compose(evolution)
            native=compile_pa(full,coupling,seed)
            final=native.layout.final_index_layout()
            native.metadata={**evolution.metadata,'compile_seed':seed,'encoding_qubits':mapping.n,
                'ancilla_qubits':len(mapping.anc),'preparation_included':True,
                'logical_mode_to_physical':[final[mapping.data[m]] for m in range(mapping.modes)]}
            measured=readout(native,mapping,final)
            verify_native(measured,edges)
            name=f'{ordering}_seed{seed}'
            row={'name':name,'ordering':ordering,'seed':seed,'scope':'full preparation+evolution+data readout',
                 **metrics(measured,timing),'qpy':circuit_file(name,measured)}
            records.append(row)
            twirled,mask=explicit_twirl(native,seed=20260906)
            compact,proof=compact_bound(twirled)
            twirled_readout=readout(compact,mapping,final,mask)
            verify_native(twirled_readout,edges)
            twin={'name':name+'_twirl','ordering':ordering,'seed':seed,'scope':row['scope']+'+one Pauli twirl',
                  **metrics(twirled_readout,timing),'qpy':circuit_file(name+'_twirl',twirled_readout),
                  'cleanup_proof':proof}
            records.append(twin)
            save(OUT/(name+'_metrics.json'),{'native':row,'twirl':twin})
            print(json.dumps({'phase':'compiled','native':row,'twirl':twin}),flush=True)
    best=min((r for r in records if r['name'].endswith('_twirl')),
             key=lambda r:r['snapshot_unaligned_duration_seconds'])
    summary={'status':'PA_PILOT_COMPILED_NOT_HARDWARE_READY','tests_passed':tests.testsRun,
        'algebra':algebra,'small_checks':checks,'circuits':records,'best_candidate':best['name'],
        'new_classical_reference_required_for_layered':True,
        'full_6x6_statevector_not_simulated':True,'XYZ_paper_schedule_not_reproduced':True,
        'ZNE_batch_not_prepared':True,'hardware_authorized':False,'QPU_seconds_used':0,
        'seconds':time.perf_counter()-start}
    save(OUT/'summary.json',summary)
    report=['# PA-ancilla pilot 6x6','',
        'Volledig lokaal. Geen nieuwe hardware-run. Correctness-first PA, niet de XYZ-diepte uit het paper.','',
        f'Encoding: {mapping.modes} fermionmodi + {len(mapping.anc)} ancillas = {mapping.n} qubits.',
        f'{tests.testsRun} tests geslaagd; alle 25 loopconstraints en 72 bezettingen van de volledige voorbereiding gecontroleerd.',
        'De resterende 11 hulpvrijheidsgraden zijn deterministisch vastgelegd door de Clifford-voorbereiding.',
        'Op 2x2 zijn alle Hubbardtermen in beide pariteitssectoren tegen onafhankelijke JW-tekens gecontroleerd.',
        'Geen volledige 108-qubit-statevector gesimuleerd.','',
        '| Kandidaat | CZ | CZ-lagen | Totale diepte | Duur, microseconden |',
        '|---|---:|---:|---:|---:|']
    for r in records:
        report.append(f"| {r['name']} | {r['cz']} | {r['CZ_depth']} | {r['depth']} | {r['snapshot_unaligned_duration_seconds']*1e6:.3f} |")
    report += ['', 'Preparation-only is apart gecompileerd en mag niet van de totale tijd worden afgetrokken.',
        'Alle andere kandidaten bevatten voorbereiding, volledige t-t-prime-U evolutie en data-uitlezing.',
        'Twirl-kandidaten bevatten een enkele controle-twirl, geen complete readout/ZNE-meetbatch.',
        'Duren zijn geschat met de opgeslagen kalibratie, zonder reset/rep_delay/queue; geen live metingen.','',
        '## Interpretatie','',
        'Network behoudt de oorspronkelijke fysieke eventvolgorde en het ideale eindige-stappendoel.',
        'Layered behoudt alle termen, tijd en symmetrische orde, maar verandert niet-commuterende termvolgordes.',
        'Daarvoor is een nieuwe circuitgematchte klassieke referentie en Trotter-convergentiecheck nodig.',
        'Een lager aantal abstracte lagen is geen bewijs van betere hardware-observabelen.',
        'De PA-tekening is 18x6, de opgeslagen chip 10x12. Hardware-routing is daarom expliciet meegenomen.',
        'De physics-skill stuurde de teken-, code-subruimte-, voorbereidings- en mappingcontroles.','',
        '## Afwijkingen van plan','',
        'Auto-fixed integration bug: v1 treated compact_bound output as a circuit instead of (circuit,proof).',
        'The failed v1 output and source snapshot remain intact. No physics tests failed.',
        'Geen modelvereenvoudiging. De laagdiepe XYZ-synthese is nog niet geimplementeerd; de native cijfers gelden alleen voor deze correctness-first synthese.','',
        'Bron: https://arxiv.org/html/2302.01862v3 (PA, secties4/5.2; native-gate caveat sectie6).','']
    (OUT/'RAPPORT.md').write_text('\n'.join(report),encoding='utf-8')
    verify(PARENT,'delivery_sha256.json')
    save(OUT/'sha256.json',{str(p.relative_to(OUT)):digest(p) for p in OUT.rglob('*') if p.is_file()})
    verify(OUT,'sha256.json')
    print(json.dumps({'phase':'done','best':best,'seconds':summary['seconds']}),flush=True)


if __name__=='__main__': main()
