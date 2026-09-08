"""Read-only local API and archived-input inventory; never connects to IBM."""
from pathlib import Path
import inspect,json,sys,importlib.metadata as md
import quimb.tensor as qtn
from quimb.tensor.belief_propagation.d2bp import D2BP
from quimb.tensor.belief_propagation.l1bp import L1BP
from quimb.tensor.belief_propagation.d1bp import D1BP

root=Path(__file__).resolve().parents[1]
if '--source' in sys.argv:
    print(inspect.getsource(D2BP.gate_))
    print(inspect.getsource(D1BP.contract_loop_series_expansion))
    raise SystemExit
out={'versions':{m:md.version(m) for m in ['qiskit','qiskit-aer','quimb','cotengra']},'apis':{}}
for cls in [qtn.TensorNetworkGenVector,D2BP,L1BP,D1BP]:
    names=['__init__','view_as_','gate_simple_','gate_','gauge_all_simple_',
           'run','contract','contract_loop_series_expansion','contract_gloop_expand','compress','gauge_symmetric']
    for n in names:
        if not hasattr(cls,n):continue
        f=getattr(cls,n)
        if callable(f):
            try:out['apis'][cls.__name__+'.'+n]={'signature':str(inspect.signature(f)),'doc':(inspect.getdoc(f) or '')[:1600]}
            except ValueError:pass
out['archives']={}
for label in ['hardware_readout_cz_folding_3x3_2026-09-06','hardware_readout_cz_folding_6x6_2026-09-06']:
    folder=root/'results_cuprate_2d'/label
    plan=json.loads((folder/'plan.json').read_text(encoding='utf-8-sig'))
    out['archives'][label]={'plan_keys':list(plan),'plan':{k:v for k,v in plan.items() if k in ['schema','config','layout','initial_layout','settings','noise_factors','shots_per_factor','backend','job_id']},
        'result_keys':list(json.loads((folder/'raw_bitstrings.json').read_text(encoding='utf-8-sig')))}
print(json.dumps(out,indent=2,default=str))
