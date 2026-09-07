"""Bounded second-labeling/control-load trial after the frozen Bonsai pilot."""
from pathlib import Path
import io
import json
import shutil
import signal
import time
import unittest
import networkx as nx
import numpy as np
from qiskit.quantum_info import Statevector
from qiskit_ibm_runtime.models import BackendProperties
import audit_bonsai_6x6 as a
from cuprate_2d_bonsai import Bonsai,anneal
from bonsai_load_balancing import balance
from cuprate_2d_pa_mapping import occupations
from cuprate_2d_hubbard_pipeline import Cuprate2DConfig
from cuprate_2d_fermionic_mapping import build_network
from cuprate_2d_tflo import explicit_twirl
from cuprate_2d_shallow_network import compact_bound
from audit_shallow_6x6 import Timing,metrics,verify
from test_cuprate_2d_bonsai import grid,fock_isometry


def check_xyz():
    rng=np.random.default_rng(818); errors=[]
    for lx,ly in [(2,2),(2,3)]:
        cfg=Cuprate2DConfig(lx=lx,ly=ly,holes=0,steps=2,dt=.2,chemical_potential=.17)
        mapping=Bonsai(grid(ly,2*lx),'xyz'); mapping.set_assignment(rng.permutation(mapping.n).tolist())
        mapping.audit(); indices,phases=fock_isometry(mapping)
        vector=rng.normal(size=1<<mapping.n)+1j*rng.normal(size=1<<mapping.n); vector/=np.linalg.norm(vector)
        encoded=np.empty_like(vector); encoded[indices]=phases*vector
        native=a.compile_native(mapping.evolution(cfg),mapping.graph)
        actual=Statevector(encoded).evolve(native).data
        reference=Statevector(vector).evolve(build_network(cfg,prepare=False)).data
        error=float(np.max(np.abs(actual[indices]/phases-reference))); errors.append(error)
        if error>5e-10: raise AssertionError('XYZ native full-state equivalence failed')
    cfg=Cuprate2DConfig(lx=2,ly=2,holes=0,steps=2,dt=.2)
    mapping=Bonsai(grid(2,4),'xyz')
    result=balance(mapping,cfg,seed=9,proposals=200)
    assert result['best_score']<=result['initial_score']+1e-10
    mapping.audit()
    return {'XYZ_full_native_2x2_and_2x3_state_errors':errors,
        'load_balance_score_checked':True,'same_original_finite_circuit':True}


def main():
    out=a.ROOT/'results_cuprate_2d/bonsai_xyz_6x6_v1'
    first=a.ROOT/'results_cuprate_2d/bonsai_fixed_target_6x6_v1'
    if out.exists(): raise FileExistsError('Never overwrite')
    def stop(*_): raise TimeoutError('300-second XYZ trial bound')
    signal.signal(signal.SIGALRM,stop); signal.alarm(300); started=time.perf_counter()
    verify(first,'sha256.json'); verify(a.PARENT,'delivery_sha256.json')
    cfg=Cuprate2DConfig(**a.read(a.PARENT/'plan.json')['config'])
    props_dict=a.read(a.PARENT/'live_backend_properties.json'); timing=Timing(BackendProperties.from_dict(props_dict))
    edges={tuple(sorted(g['qubits'])) for g in props_dict['gates'] if g['gate']=='cz'}
    physical=[10*r+c for r in range(2,10) for c in range(9)]
    inv={q:i for i,q in enumerate(physical)}
    graph=nx.Graph(); graph.add_nodes_from(range(72))
    graph.add_edges_from((inv[u],inv[v]) for u,v in edges if u in inv and v in inv)
    out.mkdir(); (out/'circuits').mkdir(); (out/'source_snapshot').mkdir()
    sources=['audit_bonsai_xyz_6x6.py','bonsai_load_balancing.py','cuprate_2d_bonsai.py',
             'audit_bonsai_6x6.py','test_cuprate_2d_bonsai.py']
    for name in sources: shutil.copyfile(a.ROOT/name,out/'source_snapshot'/name)
    a.save(out/'plan.json',{'prediction':'XYZ labels shorten worst occupation parity; depth win remains unproven.',
        'labeling':'xyz','physical_layout':physical,'count_seed':9,'load_seed':27,'proposals_each':15000,
        'same_old_finite_circuit':True,'qDRIFT':False,'hardware_authorized':False,
        'prior_manifest_hash':a.digest(first/'sha256.json'),
        'source_hashes':{name:a.digest(a.ROOT/name) for name in sources}})
    log=io.StringIO(); tests=unittest.TextTestRunner(stream=log,verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromName('test_cuprate_2d_bonsai'))
    (out/'unit_tests.txt').write_text(log.getvalue(),encoding='utf-8')
    if not tests.wasSuccessful(): raise AssertionError(log.getvalue())
    evidence=check_xyz(); a.save(out/'verification.json',evidence)
    mapping=Bonsai(graph,'xyz'); a.save(out/'algebra.json',mapping.audit())
    count_result=anneal(mapping,cfg,seed=9,proposals=15000)
    a.save(out/'count_annealing.json',count_result)
    assignments=[('count',mapping.assignment.copy())]
    load_result=balance(mapping,cfg,seed=27,proposals=15000)
    a.save(out/'load_annealing.json',load_result)
    assignments.append(('load',mapping.assignment.copy()))
    print(json.dumps({'phase':'optimized','count_best':count_result['best_proxy'],
        'load_count':load_result['native_count_proxy'],'peak':load_result['peak_wire_CX_proxy']}),flush=True)
    records=[]; a.OUT=out
    for name,assignment in assignments:
        mapping.set_assignment(assignment); mapping.audit()
        prep=mapping.preparation(occupations(cfg)); evo=mapping.evolution(cfg)
        full=prep.compose(evo); full.metadata=evo.metadata
        native=a.compile_native(full,graph)
        measured=a.embed(native,physical,mapping); a.native_edges(measured,edges)
        row={'name':'XYZ_'+name,'scope':'full preparation+evolution+readout',
             **metrics(measured,timing),'qpy':a.circuit_file(name,measured)}
        records.append(row)
        twirl,mask=explicit_twirl(native,seed=20260906); clean,proof=compact_bound(twirl)
        measured_twirl=a.embed(clean,physical,mapping,mask); a.native_edges(measured_twirl,edges)
        twin={'name':'XYZ_'+name+'_twirl','scope':'full preparation+evolution+readout+one control twirl',
              **metrics(measured_twirl,timing),'qpy':a.circuit_file(name+'_twirl',measured_twirl),
              'cleanup_proof':proof}
        records.append(twin); a.save(out/(name+'_metrics.json'),{'native':row,'twirl':twin})
        print(json.dumps(twin),flush=True)
    a.save(out/'summary.json',{'status':'XYZ_LABEL_AND_LOAD_TRIAL_COMPLETE','circuits':records,
        'verification':evidence,'tests_passed':tests.testsRun,'additional_XYZ_native_state_checks':2,
        'same_old_finite_circuit':True,'QPU_seconds_used':0,'seconds':time.perf_counter()-started})
    verify(first,'sha256.json'); verify(a.PARENT,'delivery_sha256.json')
    a.save(out/'sha256.json',{str(p.relative_to(out)):a.digest(p) for p in out.rglob('*') if p.is_file()})
    verify(out,'sha256.json')
    print('XYZ trial complete',flush=True)


if __name__=='__main__': main()
