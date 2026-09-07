"""Frozen, bounded Bonsai-vs-network resource experiment; zero QPU usage."""
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
import networkx as nx
import numpy as np
import qiskit
from qiskit import QuantumCircuit,ClassicalRegister,qpy,transpile
from qiskit.quantum_info import Statevector
from qiskit.transpiler import CouplingMap
from qiskit_ibm_runtime import RuntimeDecoder
from qiskit_ibm_runtime.models import BackendProperties
from cuprate_2d_bonsai import Bonsai,anneal
from cuprate_2d_pa_mapping import occupations
from cuprate_2d_hubbard_pipeline import Cuprate2DConfig
from cuprate_2d_fermionic_mapping import build_network
from cuprate_2d_tflo import explicit_twirl
from cuprate_2d_shallow_network import compact_bound,network_events
from audit_shallow_6x6 import Timing,metrics,guard,verify
from test_cuprate_2d_bonsai import grid,fock_isometry,jw_hop

ROOT=Path(__file__).resolve().parent
PARENT=ROOT/'results_cuprate_2d/hardware_readout_cz_folding_6x6_2026-09-06'
PREVIOUS=ROOT/'results_cuprate_2d/shallow_6x6_delivery_v1'
OUT=ROOT/'results_cuprate_2d/bonsai_fixed_target_6x6_v1'


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
        assert copy==circuit and copy.metadata==circuit.metadata
    return str(path.relative_to(OUT))


def embed(circuit,physical,mapping,mask=None):
    result=QuantumCircuit(120)
    result.compose(circuit,physical,inplace=True)
    classical=ClassicalRegister(mapping.n,'encoded'); result.add_register(classical)
    result.measure(physical,classical)
    result.metadata={**(circuit.metadata or {}),'physical_qubits':physical,
        'encoded_readout_mask_little_endian':[0]*mapping.n if mask is None else mask.tolist(),
        'occupation_decode_Z_supports':[[q for q in range(mapping.n) if row>>q&1] for row in mapping.decode_rows],
        'occupation_decode_GF2_rows_decimal':[str(row) for row in mapping.decode_rows],
        'mode_to_Majorana_pair':mapping.assignment,
        'do_not_interpret_raw_bits_as_occupations':True,
        'hardware_authorized':False}
    return result


def native_edges(circuit,edges):
    for inst in circuit.data:
        assert inst.operation.name in {'rz','sx','x','cz','measure'}
        if inst.operation.name=='cz':
            pair=tuple(sorted(circuit.find_bit(q).index for q in inst.qubits))
            if pair not in edges: raise AssertionError('Gate outside frozen device graph')


def compile_native(circuit,graph):
    cm=CouplingMap([list(e) for a,b in graph.edges for e in [(a,b),(b,a)]])
    native=transpile(circuit,basis_gates=['rz','sx','x','cz'],coupling_map=cm,
        initial_layout=list(range(len(graph))),routing_method='none',optimization_level=3,
        approximation_degree=1,seed_transpiler=9)
    if native.layout.final_index_layout()!=list(range(len(graph))):
        raise AssertionError('Native compiler changed encoded-wire ordering')
    return native


def numeric_evidence():
    cfg=Cuprate2DConfig(lx=2,ly=2,holes=0,steps=2,dt=.2,chemical_potential=.17)
    mapping=Bonsai(grid(2,4)); mapping.set_assignment([5,0,2,1,3,4,7,6])
    indices,phases=fock_isometry(mapping); W=np.zeros((256,256),complex)
    W[indices,np.arange(256)]=phases
    errors=[]
    from cuprate_2d_fermionic_mapping import pair_model
    for p,q in pair_model(cfg)[0]:
        errors.append(float(np.max(np.abs(sum(r.apply(W) for r in mapping.hopping(p,q))-W@jw_hop(8,p,q)))))
    initial=occupations(cfg)
    full=mapping.preparation(initial).compose(mapping.evolution(cfg))
    native=compile_native(full,mapping.graph)
    encoded=Statevector.from_instruction(native).data
    reference=Statevector.from_instruction(build_network(cfg)).data
    # Fock preparation omits one irrelevant global phase from the exact isometry.
    b=sum(bit<<i for i,bit in enumerate(initial))
    recovered=encoded[indices]/phases*phases[b]
    return {'all_2x2_hopping_intertwining_max_abs':max(errors),
        '2x2_full_native_state_vs_original_max_abs':float(np.max(np.abs(recovered-reference))),
        '2x2_isometry_unitarity_max_abs':float(np.max(np.abs(W.conj().T@W-np.eye(256)))),
        'phase_correction':'single Fock-input global phase only'}


def main():
    if OUT.exists(): raise FileExistsError('Never overwrite an audit')
    def stop(*_): raise TimeoutError('600-second Bonsai pilot bound')
    signal.signal(signal.SIGALRM,stop); signal.alarm(600)
    started=time.perf_counter()
    verify(PARENT,'delivery_sha256.json'); verify(PREVIOUS,'sha256.json')
    parent=read(PARENT/'plan.json'); cfg=Cuprate2DConfig(**parent['config'])
    props_dict=read(PARENT/'live_backend_properties.json')
    props=BackendProperties.from_dict(props_dict); timing=Timing(props)
    edges={tuple(sorted(g['qubits'])) for g in props_dict['gates'] if g['gate']=='cz'}
    layouts={'original72':list(parent['layout']),
        'rectangle72':[10*r+c for r in range(2,10) for c in range(9)]}
    OUT.mkdir(); (OUT/'circuits').mkdir(); (OUT/'source_snapshot').mkdir()
    sources=['BONSAI_LOCAL_PROTOCOL.md','cuprate_2d_bonsai.py','test_cuprate_2d_bonsai.py',
        'audit_bonsai_6x6.py','cuprate_2d_pa_mapping.py','cuprate_2d_shallow_network.py',
        'cuprate_2d_fermionic_mapping.py','cuprate_2d_fermionic_dynamics.py',
        'cuprate_2d_hubbard_pipeline.py','cuprate_2d_tflo.py','cuprate_2d_tflo_refinement.py',
        'audit_shallow_6x6.py']
    for source in sources: shutil.copyfile(ROOT/source,OUT/'source_snapshot'/source)
    save(OUT/'plan.json',{'config':asdict(cfg),'physical_layouts':layouts,'labeling':'z_priority',
        'annealing_seeds':[9,27],'proposals_per_seed':15000,
        'proxy':'native adjacent parity-network CX count +0.10*XY basis changes; not depth',
        'same_network_events':True,'qDRIFT':False,'no_provider_calls':True,
        'QPU_seconds_used':0,'hardware_authorized':False,
        'runtime':{'python':platform.python_version(),'qiskit':qiskit.__version__,'numpy':np.__version__},
        'input_hashes':{source:digest(ROOT/source) for source in sources},
        'frozen_hardware_manifest_hash':digest(PARENT/'delivery_sha256.json'),
        'frozen_backend_hash':digest(PARENT/'live_backend_properties.json')})
    save(OUT/'physical_events.json',network_events(cfg))
    log=io.StringIO()
    tests=unittest.TextTestRunner(stream=log,verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromName('test_cuprate_2d_bonsai'))
    (OUT/'unit_tests.txt').write_text(log.getvalue(),encoding='utf-8')
    if not tests.wasSuccessful(): raise AssertionError(log.getvalue())
    evidence=numeric_evidence()
    if evidence['2x2_full_native_state_vs_original_max_abs']>3e-10:
        raise AssertionError('Full native state check failed')
    save(OUT/'verification.json',evidence)
    print(json.dumps({'phase':'tests_pass','tests':tests.testsRun,'evidence':evidence}),flush=True)
    records=[]; mappings={}
    for layout_name,physical in layouts.items():
        inverse={q:i for i,q in enumerate(physical)}
        graph=nx.Graph(); graph.add_nodes_from(range(72))
        graph.add_edges_from((inverse[a],inverse[b]) for a,b in edges if a in inverse and b in inverse)
        mapping=Bonsai(graph)
        algebra=mapping.audit()
        save(OUT/(layout_name+'_algebra.json'),algebra)
        assignments=[('naive',list(range(72)),None)]
        for seed in (9,27):
            mapping.set_assignment(list(range(72)))
            optimization=anneal(mapping,cfg,seed=seed,proposals=15000)
            save(OUT/(layout_name+f'_anneal{seed}.json'),optimization)
            assignments.append((f'anneal{seed}',mapping.assignment.copy(),optimization['best_proxy']))
            print(json.dumps({'phase':'annealed','layout':layout_name,'seed':seed,
                'initial_proxy':optimization['initial_proxy'],'best_proxy':optimization['best_proxy']}),flush=True)
        for assignment_name,assignment,proxy in assignments:
            guard(); mapping.set_assignment(assignment); mapping.audit()
            before=time.perf_counter()
            prep=mapping.preparation(occupations(cfg)); evolution=mapping.evolution(cfg)
            full=prep.compose(evolution); full.metadata=evolution.metadata
            if set(prep.count_ops())-{'x'}: raise AssertionError('Non-product preparation')
            native=compile_native(full,graph)
            native.metadata={**(native.metadata or {}),'layout_name':layout_name,
                'assignment_name':assignment_name,'preparation_included':True}
            measured=embed(native,physical,mapping); native_edges(measured,edges)
            name=layout_name+'_'+assignment_name
            row={'name':name,'layout':layout_name,'assignment':assignment_name,
                'proxy':proxy,'graph_edges':graph.number_of_edges(),'preparation_X':prep.count_ops().get('x',0),
                **metrics(measured,timing),'qpy':circuit_file(name,measured)}
            records.append(row)
            twirl,mask=explicit_twirl(native,seed=20260906); clean,proof=compact_bound(twirl)
            measured_twirl=embed(clean,physical,mapping,mask); native_edges(measured_twirl,edges)
            twin={'name':name+'_twirl','layout':layout_name,'assignment':assignment_name,
                'proxy':proxy,'graph_edges':graph.number_of_edges(),'preparation_X':row['preparation_X'],
                **metrics(measured_twirl,timing),'qpy':circuit_file(name+'_twirl',measured_twirl),
                'cleanup_proof':proof}
            records.append(twin)
            save(OUT/(name+'_metrics.json'),{'native':row,'twirl':twin})
            mappings[name]={'physical_layout':physical,'assignment':assignment,
                'Majoranas':[p.signed_label(72) for mode in range(72) for p in (mapping.gamma(mode,0),mapping.gamma(mode,1))],
                'number_parities':[v.signed_label(72) for v in mapping.vertices],
                'GF2_encode_rows':[str(r) for r in mapping.encode_rows],
                'GF2_decode_rows':[str(r) for r in mapping.decode_rows],
                'tree_edges':list(map(list,mapping.tree.edges)),'root':mapping.root}
            print(json.dumps({'phase':'compiled','row':twin,'seconds':time.perf_counter()-before}),flush=True)
    save(OUT/'mappings_and_readout.json',mappings)
    old=read(PREVIOUS/'decision.json')['new']
    twirls=[r for r in records if r['name'].endswith('_twirl')]
    fastest=min(twirls,key=lambda r:r['snapshot_unaligned_duration_seconds'])
    fewest=min(twirls,key=lambda r:r['cz'])
    summary={'status':'BONSAI_OFFLINE_FIXED_TARGET_PILOT_COMPLETE','tests_passed':tests.testsRun,
        'old_compact':old,'fastest_Bonsai':fastest,'fewest_CZ_Bonsai':fewest,
        'duration_improved':fastest['snapshot_unaligned_duration_seconds']<old['snapshot_unaligned_duration_seconds'],
        'CZ_count_improved':fewest['cz']<old['cz'],'circuits':records,'verification':evidence,
        'same_model_and_finite_network_target':True,'qDRIFT':False,
        'readout_decoder_changed':True,'readout_mitigation_not_validated':True,
        'complete_ZNE_batch_not_prepared':True,'full_72q_statevector_not_simulated':True,
        'hardware_authorized':False,'QPU_seconds_used':0,'seconds':time.perf_counter()-started}
    save(OUT/'summary.json',summary)
    lines=['# Bonsai 6x6: vaste model- en circuitvergelijking','',
        'Alleen lokaal; geen nieuwe QPU-run. Zelfde t,t-prime,U,fermiontekens,T=0,4 en oorspronkelijke fysieke eventvolgorde.',
        '72 encodingqubits, geen extra encoding-ancillas. Voorbereiding bestaat alleen uit X-poorten.',
        'Pariteitsnetwerken zijn op bestaande CZ-verbindingen gebouwd, zonder SWAP-router.',
        'Steiner-qubits blijven quantumdata en worden volledig terughersteld.','',
        f'{tests.testsRun} tests slagen, inclusief volledige2x2/2x3-dynamica, Majorana-algebra en GF2-uitlezing.',
        'Geen volledige72-qubit-statevector berekend.','',
        '| Volledig circuit, een controle-twirl | CZ | CZ-lagen | Diepte | Geschatte duur (us) |',
        '|---|---:|---:|---:|---:|',
        f"| Bestaande compacte variant | {old['cz']} | {old['CZ_depth']} | {old['depth']} | {old['snapshot_unaligned_duration_seconds']*1e6:.3f} |"]
    for r in twirls:
        lines.append(f"| {r['name']} | {r['cz']} | {r['CZ_depth']} | {r['depth']} | {r['snapshot_unaligned_duration_seconds']*1e6:.3f} |")
    lines += ['', 'Duren omvatten voorbereiding en uitlezing, niet reset/rep_delay/queue. Opgeslagen kalibratie, geen live fidelitymeting.',
        'De annealingkostenfunctie is uitsluitend een zoekproxy. Minder CZ is niet automatisch minder diepte.',
        'Andere fysieke subset is apart vermeld; daarmee is een kwaliteitsvergelijking niet automatisch hardwaregematcht.','',
        '## Uitlezing en vervolg','',
        'Ruwe bits zijn encoded Bonsai-bits, geen directe fermionbezettingen. Corrigeer eerst het vastgelegde fysieke readout-X-masker en decodeer vervolgens de GF2-pariteiten.',
        'Lading en doublons zijn op kleine systemen gecontroleerd. De bestaande hardware-readoutmitigatie moet nog aan de nieuwe pariteitsobservabelen worden aangepast.',
        'Geen qDRIFT of nieuwe klassieke modelbenadering toegepast. De bestaande ideale eindige-circuitreferentie blijft het doel.',
        'Geen complete ZNE-batch, verse calibratie/budgetcontrole of hardware-autorisatie aanwezig.','',
        '## Verificatie en afwijkingen','',
        'Geen fysische vereenvoudiging. Bonsai is aangepast aan de opgeslagen Nighthawk-grid, niet aan Boston heavy-hex.',
        'Lokale parity-tree-synthese en equal-visit kostenfunctie zijn implementatiekeuzes voor dit vaste Trotterdoel.',
        'De physics-skill stuurde de onafhankelijke teken-, unitairiteits-, voorbereidings- en uitleescontroles.',
        'Bronnen: https://arxiv.org/abs/2212.09731 en https://arxiv.org/html/2608.25024 .','']
    (OUT/'RAPPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    verify(PARENT,'delivery_sha256.json'); verify(PREVIOUS,'sha256.json')
    save(OUT/'sha256.json',{str(p.relative_to(OUT)):digest(p) for p in OUT.rglob('*') if p.is_file()})
    verify(OUT,'sha256.json')
    print(json.dumps({'phase':'done','fastest':fastest['name'],'fastest_depth':fastest['depth'],
        'fastest_us':fastest['snapshot_unaligned_duration_seconds']*1e6,
        'fewest_CZ':fewest['cz'],'seconds':summary['seconds']}),flush=True)


if __name__=='__main__': main()
