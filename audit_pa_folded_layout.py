"""One fixed PA row-folding trial; preserves the validated layered circuit."""
from pathlib import Path
import io
import json
import shutil
import signal
import time
import unittest
from qiskit import transpile
from qiskit.transpiler import CouplingMap
from qiskit_ibm_runtime.models import BackendProperties
import audit_pa_ancilla_6x6 as a
from cuprate_2d_pa_mapping import PA, occupations
from cuprate_2d_pa_pair_synthesis import evolution
from cuprate_2d_hubbard_pipeline import Cuprate2DConfig
from cuprate_2d_tflo import explicit_twirl
from cuprate_2d_shallow_network import compact_bound
from audit_shallow_6x6 import Timing, metrics, verify


def folded_layout():
    """18x6 -> 9x12 row snake within 10x12 backend; max grid-edge stretch2."""
    layout=[]
    for q in range(108):
        y,x=divmod(q,18)
        row=2*y+(x>=9)
        col=x if x<9 else 17-x
        layout.append(10*row+col)
    assert len(set(layout))==108 and max(layout)<120
    for y in range(6):
        for x in range(18):
            q=18*y+x
            for r in ([q+1] if x<17 else [])+([q+18] if y<5 else []):
                u,v=layout[q],layout[r]
                distance=abs(u%10-v%10)+abs(u//10-v//10)
                assert distance<=2
    return layout


def main():
    out=a.ROOT/'results_cuprate_2d/pa_folded_6x6_v1'
    if out.exists(): raise FileExistsError('Never overwrite a trial')
    def stop(*_): raise TimeoutError('300s bound')
    signal.signal(signal.SIGALRM,stop); signal.alarm(300)
    started=time.perf_counter()
    verify(a.PARENT,'delivery_sha256.json')
    parent=a.read(a.PARENT/'plan.json'); cfg=Cuprate2DConfig(**parent['config'])
    props_dict=a.read(a.PARENT/'live_backend_properties.json')
    edges={tuple(sorted(g['qubits'])) for g in props_dict['gates'] if g['gate']=='cz'}
    coupling=CouplingMap([list(e) for u,v in sorted(edges) for e in [(u,v),(v,u)]])
    timing=Timing(BackendProperties.from_dict(props_dict))
    out.mkdir(); (out/'circuits').mkdir(); (out/'source_snapshot').mkdir()
    sources=['audit_pa_folded_layout.py','audit_pa_ancilla_6x6.py','cuprate_2d_pa_mapping.py',
             'cuprate_2d_pa_pair_synthesis.py','test_cuprate_2d_pa_mapping.py',
             'test_cuprate_2d_pa_pair_synthesis.py']
    for name in sources: shutil.copyfile(a.ROOT/name,out/'source_snapshot'/name)
    layout=folded_layout()
    a.save(out/'plan.json',{'prediction':'Row folding might reduce routing overhead; no presumed depth win.',
        'initial_layout':layout,'seed':9,'maximum_drawn_grid_edge_Manhattan_distance':2,
        'source_sha256':{name:a.digest(a.ROOT/name) for name in sources},
        'configuration':parent['config'],'no_provider_calls':True,'hardware_authorized':False,
        'same_layered_finite_circuit_as_PA_pilot':True})
    log=io.StringIO()
    tests=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.TestSuite([
        unittest.defaultTestLoader.loadTestsFromName(name) for name in
        ('test_cuprate_2d_pa_mapping','test_cuprate_2d_pa_pair_synthesis')]))
    (out/'unit_tests.txt').write_text(log.getvalue(),encoding='utf-8')
    if not tests.wasSuccessful(): raise AssertionError(log.getvalue())
    mapping=PA(6,6)
    full=mapping.preparation(occupations(cfg)).compose(evolution(mapping,cfg,'layered'))
    native=a.compile_pa(full,coupling,9,initial=layout)
    final=native.layout.final_index_layout()
    native.metadata={'family':'PA_shared_parity_rowfold','preparation_included':True,
        'same_old_network_finite_circuit':False,'same_PA_layered_finite_circuit':True,
        'hardware_authorized':False,'initial_layout':layout}
    measured=a.readout(native,mapping,final); a.verify_native(measured,edges)
    a.OUT=out
    row={'name':'folded_native',**metrics(measured,timing),'qpy':a.circuit_file('folded_native',measured)}
    print(json.dumps(row),flush=True)
    twirl,mask=explicit_twirl(native,seed=20260906); clean,proof=compact_bound(twirl)
    measured_twirl=a.readout(clean,mapping,final,mask); a.verify_native(measured_twirl,edges)
    twin={'name':'folded_twirl',**metrics(measured_twirl,timing),
          'qpy':a.circuit_file('folded_twirl',measured_twirl),'cleanup_proof':proof}
    summary={'status':'OFFLINE_FOLDED_PA_TRIAL_COMPLETE','tests_passed':tests.testsRun,
        'native':row,'twirl':twin,'seconds':time.perf_counter()-started,'QPU_seconds_used':0,
        'hardware_authorized':False,'preparation_included':True,'readout_included':True,
        'ZNE_protocol_not_prepared':True}
    a.save(out/'summary.json',summary)
    verify(a.PARENT,'delivery_sha256.json')
    a.save(out/'sha256.json',{str(p.relative_to(out)):a.digest(p) for p in out.rglob('*') if p.is_file()})
    verify(out,'sha256.json')
    print(json.dumps(summary),flush=True)


if __name__=='__main__': main()
