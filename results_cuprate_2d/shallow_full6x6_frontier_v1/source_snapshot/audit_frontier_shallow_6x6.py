"""Bounded offline commutation-frontier compiler; zero hardware requests."""
import io
import json
from pathlib import Path
import shutil
import signal
import time
import unittest
from qiskit import qpy
from qiskit_ibm_runtime.models import BackendProperties
from cuprate_2d_hubbard_pipeline import Cuprate2DConfig
from cuprate_2d_tflo import compile_template,explicit_twirl
from cuprate_2d_shallow_network import compact_bound,embed_with_logical_readout
from cuprate_2d_shallow_frontier import build_frontier
import audit_shallow_6x6 as a

ROOT=a.ROOT; OUT=ROOT/'results_cuprate_2d/shallow_full6x6_frontier_v1'

def main():
    if OUT.exists(): raise FileExistsError('Do not overwrite')
    def stop(*_): raise TimeoutError('600-second frontier compilation bound')
    signal.signal(signal.SIGALRM,stop); signal.alarm(600)
    tick=time.perf_counter()
    a.verify(a.PARENT,'delivery_sha256.json'); a.verify(a.OUT,'sha256.json')
    plan=a.read(a.PARENT/'plan.json'); cfg=Cuprate2DConfig(**plan['config']); layout=plan['layout']
    timing=a.Timing(BackendProperties.from_dict(a.read(a.PARENT/'live_backend_properties.json')))
    log=io.StringIO()
    tests=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(
        ['test_cuprate_2d_shallow_network','test_cuprate_2d_shallow_frontier']))
    if not tests.wasSuccessful(): raise AssertionError(log.getvalue())
    OUT.mkdir(); (OUT/'circuits').mkdir(); (OUT/'source_snapshot').mkdir()
    names=['cuprate_2d_shallow_frontier.py','test_cuprate_2d_shallow_frontier.py','audit_frontier_shallow_6x6.py',
        'cuprate_2d_shallow_network.py','audit_shallow_6x6.py','cuprate_2d_tflo.py',
        'cuprate_2d_tflo_refinement.py','cuprate_2d_fermionic_mapping.py']
    a.save(OUT/'plan.json',{'config':plan['config'],'no_provider_calls':True,'new_hardware_authorization':False,
        'same_original_modewise_physics_order_required':True,
        'permitted_reordering':'Disjoint even-parity fermionic physical terms only.',
        'predicted_before_compilation':'Lower routing cost possible; depth improvement is not assumed.',
        'policies':['distance','critical','asap'],'limit_seconds':600,
        'source_sha256':{n:a.digest(ROOT/n) for n in names},
        'original_plan_sha256':a.digest(a.PARENT/'plan.json')})
    (OUT/'unit_tests.txt').write_text(log.getvalue(),encoding='utf-8')
    for name in names: shutil.copyfile(ROOT/name,OUT/'source_snapshot'/name)
    rows=[]; compiled_by_policy={}
    for policy in ('distance','critical','asap'):
        a.guard()
        qc,ledger=build_frontier(cfg,policy=policy,restore=False)
        slotmap=qc.metadata['slot_for_mode']
        print(json.dumps({'policy':policy,'routing_fswaps':qc.metadata['routing_fswaps'],'events':len(ledger)}),flush=True)
        native=compile_template(qc); compiled_by_policy[policy]=(native,slotmap,qc.metadata)
        with (OUT/'circuits'/f'{policy}_native.qpy').open('xb') as f: qpy.dump(native,f)
        twirl,mask=explicit_twirl(native,202609040)
        compact,proof=compact_bound(twirl)
        physical=embed_with_logical_readout(compact,layout,slotmap,mask)
        physical.metadata.update(prototype='frontier-v1',new_submission_authorized=False)
        path=OUT/'circuits'/f'{policy}_twirl0.qpy'
        with path.open('xb') as f: qpy.dump(physical,f)
        with path.open('rb') as f:
            restored=qpy.load(f)[0]
            if restored!=physical or restored.metadata!=physical.metadata: raise AssertionError('QPY roundtrip')
        row={'policy':policy,'routing_fswaps':qc.metadata['routing_fswaps'],
            'modewise_order_verified':True,'qpy':str(path.relative_to(OUT)),
            'cleanup_proof':proof,**a.metrics(physical,timing)}
        rows.append(row)
        a.save(OUT/f'{policy}_event_ledger.json',ledger)
        print(json.dumps(row),flush=True)
    best=min(rows,key=lambda r:r['snapshot_unaligned_duration_seconds'])
    native,slotmap,metadata=compiled_by_policy[best['policy']]
    twirl_rows=[{**best,'twirl_id':0}]
    for t in range(1,8):
        twirl,mask=explicit_twirl(native,202609040+t)
        compact,proof=compact_bound(twirl)
        physical=embed_with_logical_readout(compact,layout,slotmap,mask)
        physical.metadata.update(prototype='frontier-v1',twirl_id=t,new_submission_authorized=False)
        path=OUT/'circuits'/f"selected_twirl{t}.qpy"
        with path.open('xb') as f: qpy.dump(physical,f)
        with path.open('rb') as f:
            if qpy.load(f)[0]!=physical: raise AssertionError('QPY roundtrip')
        twirl_rows.append({'twirl_id':t,'qpy':str(path.relative_to(OUT)),
            'cleanup_proof':proof,**a.metrics(physical,timing)})
    old=a.read(a.OUT/'summary.json')
    baseline=next(r for r in old['circuits'] if r['name']=='original_factor1_twirl0')
    compact_old=next(r for r in old['circuits'] if r['name']=='compact_factor1_twirl0')
    beats=best['snapshot_unaligned_duration_seconds']<compact_old['snapshot_unaligned_duration_seconds']
    summary={'status':'OFFLINE_FRONTIER_CANDIDATES_VERIFIED','tests':tests.testsRun,'candidates':rows,
        'best_frontier_policy':best['policy'],'selected_twirl_metrics':twirl_rows,
        'beats_existing_one_qubit_cleanup':beats,'original_baseline':baseline,
        'existing_cleanup':compact_old,'CZ_reduction_fraction':1-best['cz']/baseline['cz'],
        'duration_reduction_fraction':1-best['snapshot_unaligned_duration_seconds']/baseline['snapshot_unaligned_duration_seconds'],
        'hardware_error_improvement_measured':False,'hardware_submission_authorized':False,
        'exact_72q_statevector_checked':False,'full72_modewise_event_trace_verified':True,
        'readout_mapping':'Use logical_output_layout and reordered readout mask stored in each QPY.',
        'fold2_warning':'Do not assume edgewise exact factor2 folding if counts on some supports are odd.',
        'elapsed_seconds':time.perf_counter()-tick}
    a.save(OUT/'summary.json',summary)
    lines=['# Exacte ondiepere 6x6-kandidaten: commuterende interacties','',
        'Zelfde ideale oorspronkelijke T=0,4-doel; alleen niet-overlappende even-fermioninteracties zijn herschikt.',
        'De volgorde van alle interacties op iedere fermionmodus is exact behouden.',
        'Geen QPU-run en geen gemeten foutverbetering.','',
        '| Variant | CZ | Totale diepte | CZ-diepte | Duur (µs, opgeslagen kalibratie) |',
        '|---|---:|---:|---:|---:|']
    for label,row in [('Uitgevoerd',baseline),('Alleen 1q-opschoning',compact_old)]+[(r['policy'],r) for r in rows]:
        lines.append(f"| {label} | {row['cz']} | {row['depth']} | {row['CZ_depth']} | {row['snapshot_unaligned_duration_seconds']*1e6:.3f} |")
    lines+=['',f"Beste frontier-kandidaat: {best['policy']}; sneller dan bestaande 1q-opschoning: {beats}.",
        'Alle acht twirls van die kandidaat zijn gebouwd en lokaal gecontroleerd.',
        'De finale fermionpermutatie wordt via de vastgelegde uitleesmapping verwerkt; niet de oude mapping gebruiken.',
        'Volledige kleine-systeemunitariteiten, een willekeurige 2x3-toestand en lokale opschoningsblokken zijn gecontroleerd.',
        'Geen exacte72-qubit-statevectorberekening; wel volledige structurele modevolgordecontrole.',
        'Nieuwe hardware vraagt een apart meetprotocol, verse backendcontrole en nieuwe expliciete toestemming.','']
    (OUT/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    a.verify(a.PARENT,'delivery_sha256.json'); a.verify(a.OUT,'sha256.json')
    a.save(OUT/'sha256.json',{str(p.relative_to(OUT)):a.digest(p) for p in OUT.rglob('*') if p.is_file()})
    signal.alarm(0)
    print(json.dumps({'status':summary['status'],'best':best,'beats_1q_cleanup':beats,
        'elapsed_seconds':summary['elapsed_seconds']}),flush=True)

if __name__=='__main__': main()

