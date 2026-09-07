"""Offline depth audit and exact-target shallow candidates. No provider calls."""
from collections import Counter
from dataclasses import asdict
import hashlib
import io
import json
import math
from pathlib import Path
import shutil
import signal
import time
import unittest
import numpy as np
import psutil
from qiskit import qpy
from qiskit_ibm_runtime.models import BackendProperties
from cuprate_2d_hubbard_pipeline import Cuprate2DConfig
from cuprate_2d_fermionic_mapping import pair_model
from cuprate_2d_tflo import compile_template,explicit_twirl
import cuprate_2d_shallow_network as s

ROOT=Path(__file__).resolve().parent
PARENT=ROOT/'results_cuprate_2d/hardware_readout_cz_folding_6x6_2026-09-06'
OUT=ROOT/'results_cuprate_2d/shallow_full6x6_T04_v1'

def read(path): return json.loads(Path(path).read_text())
def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):
    with path.open('x',encoding='utf-8') as f: json.dump(value,f,indent=2,allow_nan=False); f.write('\n')
def verify(root,manifest):
    for name,expected in read(root/manifest).items():
        path=(root/name).resolve()
        if not path.is_relative_to(root.resolve()) or digest(path)!=expected:
            raise ValueError('Frozen input changed')
def guard():
    if psutil.Process().memory_info().rss>2*1024**3: raise MemoryError('2GiB guard')

class Timing:
    def __init__(self,props): self.props=props; self.cache={}
    def duration(self,name,wires):
        key=name,tuple(wires)
        if key not in self.cache:
            if name=='rz': value=0.
            elif name=='measure': value=self.props.qubit_property(wires[0],'readout_length')[0]
            else:
                try: value=self.props.gate_length(name,tuple(wires))
                except KeyError:
                    if name!='cz': raise
                    value=self.props.gate_length(name,tuple(reversed(wires)))
            value=float(value)
            if not np.isfinite(value) or value<0: raise ValueError('Invalid duration')
            self.cache[key]=value
        return self.cache[key]
    def critical_path(self,circuit):
        clocks=np.zeros(circuit.num_qubits)
        for item in circuit.data:
            wires=tuple(circuit.find_bit(q).index for q in item.qubits)
            start=max(clocks[list(wires)])
            clocks[list(wires)]=start+self.duration(item.operation.name,wires)
        return float(max(clocks))

def metrics(circuit,timing):
    guard()
    ops=dict(circuit.count_ops())
    supports=Counter(tuple(circuit.find_bit(q).index for q in i.qubits)
        for i in circuit.data if i.operation.name=='cz')
    return {'operations':ops,'cz':ops.get('cz',0),'physical_X_SX':ops.get('x',0)+ops.get('sx',0),
        'depth':circuit.depth(),'CZ_depth':circuit.depth(lambda item:item.operation.name=='cz'),
        'snapshot_unaligned_duration_seconds':timing.critical_path(circuit),
        'exact_edgewise_factor2_possible':all(n%2==0 for n in supports.values())}

def save_circuit(name,circuit):
    path=OUT/'circuits'/(name+'.qpy')
    with path.open('xb') as f: qpy.dump(circuit,f)
    with path.open('rb') as f:
        restored=qpy.load(f)[0]
        if restored!=circuit or restored.metadata!=circuit.metadata: raise AssertionError('QPY roundtrip')
    return str(path.relative_to(OUT))

def main():
    if OUT.exists(): raise FileExistsError('Never overwrite an audit')
    def stop(*_): raise TimeoutError('600-second offline audit bound')
    signal.signal(signal.SIGALRM,stop); signal.alarm(600)
    started=time.perf_counter()
    verify(PARENT,'delivery_sha256.json'); verify(PARENT,'report_sha256.json')
    parent=read(PARENT/'plan.json'); cfg=Cuprate2DConfig(**parent['config']); layout=parent['layout']
    log=io.StringIO()
    tests=unittest.TextTestRunner(stream=log,verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromName('test_cuprate_2d_shallow_network'))
    if not tests.wasSuccessful(): raise AssertionError(log.getvalue())
    props=BackendProperties.from_dict(read(PARENT/'live_backend_properties.json'))
    timing=Timing(props)
    hops,onsite=pair_model(cfg)
    routing_blocks=cfg.steps*cfg.qubits*(cfg.qubits-1)
    physics_blocks=2*cfg.steps*(len(hops)+len(onsite))
    all_edges={tuple(sorted(g.qubits)) for g in props.gates if g.gate=='cz'}
    selected_edges={e for e in all_edges if set(e).issubset(layout)}
    path_edges={tuple(sorted((a,b))) for a,b in zip(layout,layout[1:])}
    if not path_edges<=selected_edges: raise AssertionError('Original path not in calibration')
    attribution={'modes':72,'sites':36,'steps':2,'time':.4,'hopping_pairs':len(hops),
        'onsite_pairs':len(onsite),'all_pairs_per_sweep':72*71//2,
        'logical_fswap_blocks':routing_blocks,'blocks_with_physics':physics_blocks,
        'pure_routing_blocks':routing_blocks-physics_blocks,
        'pure_routing_fraction_before_compiler':(routing_blocks-physics_blocks)/routing_blocks,
        'selected_physical_CZ_edges':len(selected_edges),'used_path_edges':len(path_edges),
        'unused_selected_edges':len(selected_edges-path_edges),
        'T1_seconds_min_median_max':np.quantile([props.t1(q) for q in layout],[0,.5,1]).tolist(),
        'T2_seconds_min_median_max':np.quantile([props.t2(q) for q in layout],[0,.5,1]).tolist(),
        'snapshot_not_live_preflight':True,'does_not_predict_fidelity':True}
    sources=['audit_shallow_6x6.py','cuprate_2d_shallow_network.py','test_cuprate_2d_shallow_network.py',
        'cuprate_2d_fermionic_mapping.py','cuprate_2d_fermionic_dynamics.py',
        'cuprate_2d_tflo.py','cuprate_2d_tflo_refinement.py','cuprate_2d_hubbard_pipeline.py']
    OUT.mkdir(); (OUT/'circuits').mkdir(); (OUT/'source_snapshot').mkdir()
    plan={'config':asdict(cfg),'scope':'same ideal original-network target, no hardware run',
        'predictions_before_candidate_runs':['One-qubit cleanup should cut pulses with identical CZ trace.',
            'Sparse routing may cut CZ counts but can increase serial depth; measure both.',
            'No physical error/advantage improvement inferred from counts or calibration alone.'],
        'hardware_authorized':False,'no_provider_calls':True,'no_classical_chi128':True,
        'limit_seconds':600,'rss_guard_bytes':2*1024**3,
        'input_sha256':{name:digest(ROOT/name) for name in sources},
        'parent_plan_sha256':digest(PARENT/'plan.json'),
        'calibration_sha256':digest(PARENT/'live_backend_properties.json')}
    save(OUT/'plan.json',plan); save(OUT/'routing_attribution.json',attribution)
    (OUT/'unit_tests.txt').write_text(log.getvalue(),encoding='utf-8')
    for name in sources: shutil.copyfile(ROOT/name,OUT/'source_snapshot'/name)
    rows=[]; proofs=[]
    with (PARENT/'native_template.qpy').open('rb') as f: native=qpy.load(f)[0]
    before=s.embed_with_logical_readout(native,layout,list(range(72)))
    rows.append({'name':'original_native_no_twirls',**metrics(before,timing)})
    for factor in (1,2,3):
        index=next(i for i,r in enumerate(parent['records']) if r.get('factor')==factor and r['twirl_id']==0)
        with (PARENT/'bound_inputs'/f'circuit_{index:03d}.qpy').open('rb') as f: original=qpy.load(f)[0]
        rows.append({'name':f'original_factor{factor}_twirl0',**metrics(original,timing)})
        compact,proof=s.compact_bound(original)
        compact.metadata={'prototype':'shallow_full6x6_T04_v1','source_job':read(PARENT/'job_receipt.json')['job_id'],
            'factor':factor,'twirl_id':0,'readout_mask_little_endian':parent['records'][index]['readout_mask_little_endian'],
            'logical_output_layout':layout,'hardware_tested':False,'new_submission_authorized':False}
        path=save_circuit(f'compact_factor{factor}_twirl0',compact)
        row={'name':f'compact_factor{factor}_twirl0','qpy':path,**metrics(compact,timing)}
        rows.append(row); proofs.append({'name':row['name'],**proof})
        print(json.dumps(row),flush=True)
    # Validate all remaining factor1 twirls; do not assume the seed0 reduction transfers.
    for t in range(1,8):
        index=next(i for i,r in enumerate(parent['records']) if r.get('factor')==1 and r['twirl_id']==t)
        with (PARENT/'bound_inputs'/f'circuit_{index:03d}.qpy').open('rb') as f: original=qpy.load(f)[0]
        compact,proof=s.compact_bound(original)
        compact.metadata={'prototype':'shallow_full6x6_T04_v1','factor':1,'twirl_id':t,
            'logical_output_layout':layout,'readout_mask_little_endian':parent['records'][index]['readout_mask_little_endian'],
            'hardware_tested':False,'new_submission_authorized':False}
        name=f'compact_factor1_twirl{t}'
        rows.append({'name':name,'qpy':save_circuit(name,compact),**metrics(compact,timing)})
        proofs.append({'name':name,**proof})
        print(json.dumps({'completed_compact_twirl':t}),flush=True)
    sparse=[]
    for strategy in ('left','look4','look12'):
        guard()
        logical,ledger=s.build_sparse(cfg,strategy=strategy,restore=False)
        slotmap=logical.metadata['slot_for_mode']
        compiled=compile_template(logical)
        twirled,mask=explicit_twirl(compiled,202609040)
        compact,proof=s.compact_bound(twirled)
        physical=s.embed_with_logical_readout(compact,layout,slotmap,mask)
        name='sparse_'+strategy
        physical.metadata.update(prototype='shallow_full6x6_T04_v1',new_submission_authorized=False)
        row={'name':name,'routing_fswaps':logical.metadata['routing_fswaps'],
            'original_physics_events_preserved':len(ledger),
            'final_readout_permutation_required':True,
            'qpy':save_circuit(name,physical),**metrics(physical,timing)}
        rows.append(row); sparse.append(row); proofs.append({'name':name,**proof})
        save(OUT/(name+'_event_ledger.json'),ledger)
        print(json.dumps(row),flush=True)
    baseline=next(r for r in rows if r['name']=='original_factor1_twirl0')
    candidates=[r for r in rows if r['name']=='compact_factor1_twirl0' or r['name'].startswith('sparse_')]
    fastest=min(candidates,key=lambda r:r['snapshot_unaligned_duration_seconds'])
    summary={'status':'OFFLINE_SHALLOW_CANDIDATES_VERIFIED_NOT_SUBMITTED','tests':tests.testsRun,
        'config':asdict(cfg),'routing_attribution':attribution,'circuits':rows,
        'cleanup_proofs':proofs,'fastest_snapshot_candidate':fastest['name'],
        'fastest_duration_reduction_fraction':1-fastest['snapshot_unaligned_duration_seconds']/baseline['snapshot_unaligned_duration_seconds'],
        'exact_72q_statevector_simulated':False,
        'equivalence_scope':'Full2x2 unitaries and2x3 state verified; full72 event ledger preserved. All cleanup blocks independently2x2 checked, with CZ traces and global phase.',
        'no_hardware_calls':True,'hardware_error_improvement_measured':False,
        'old_job_permission_not_reusable':True,'elapsed_seconds':time.perf_counter()-started}
    save(OUT/'summary.json',summary)
    lines=['# Ondiepere 6x6-circuits: alleen offline getest','',
        'Zelfde Hamiltoniaan, fermiontekens, oorspronkelijke interactievolgorde en T=0,4. Geen QPU-job.',
        'De oorspronkelijke meetdata en circuits zijn niet gewijzigd.','',
        f"Routing vóór compilatie: {routing_blocks-physics_blocks}/{routing_blocks} blokken bevatten geen fysische interactie.",
        f"Op de geselecteerde qubits zijn {len(selected_edges)} CZ-verbindingen beschikbaar; de oude route gebruikt een pad van {len(path_edges)} verbindingen.",
        'Dit zijn routingdiagnostieken, geen berekende fideliteiten.','',
        '| Circuit | CZ | X+SX | Totale diepte | CZ-diepte | Tijd (µs, snapshot) |',
        '|---|---:|---:|---:|---:|---:|']
    for row in rows:
        lines.append(f"| {row['name']} | {row['cz']} | {row['physical_X_SX']} | {row['depth']} | {row['CZ_depth']} | {row['snapshot_unaligned_duration_seconds']*1e6:.3f} |")
    lines+=['',f"Snelste kandidaat volgens opgeslagen kalibratie: {fastest['name']}.",
        'Sparse varianten behouden een bekende laatste fermionpermutatie: gebruik hun opgeslagen logical_output_layout en readout_mask, nooit de oude uitleesmapping.',
        'De klassieke exacte doelobservabelen blijven gelijk; een χ-afgekapt MPS-resultaat blijft een benadering.',
        'Geen lagere hardwarefout of quantumvoordeel aangetoond. Verse ISA/budgetcontrole en nieuwe expliciete toestemming blijven vereist.',
        'Geen algemene optimalisatie na CZ-folding: die kan de ingevoegde identiteitsparen verwijderen.',
        'De één-qubit-opschoning controleert juist dat alle CZ-poorten en hun volgorde per draad behouden blijven.','']
    (OUT/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    verify(PARENT,'delivery_sha256.json')
    save(OUT/'sha256.json',{str(p.relative_to(OUT)):digest(p) for p in OUT.rglob('*') if p.is_file()})
    signal.alarm(0)
    print(json.dumps({'status':summary['status'],'fastest':fastest,'elapsed_seconds':summary['elapsed_seconds']}),flush=True)

if __name__=='__main__': main()

