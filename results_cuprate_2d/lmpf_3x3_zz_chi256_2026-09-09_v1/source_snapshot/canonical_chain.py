"""Independent canonical-MPS propagation for a verified native chain only."""
from pathlib import Path
import argparse,json,sys,time
import numpy as np
import quimb.tensor as qtn
from qiskit import qpy
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from lmpf_2d.archive_3x3 import ARCHIVE,active_circuit,record_sign
from lmpf_2d.model import FrozenSurrogate,digest
from lmpf_2d.operators import compile_steps,fuse_steps,overlap_network
from lmpf_2d.tn_storage import load_tn,save_tn,bounded_contract,expectation_zero

def evolve_canonical(n,support,steps,scale,chi):
    mps=qtn.MPS_product_state([np.eye(4)['IXYZ'.index(support.get(q,'I'))] for q in range(n)])
    info={'cur_orthog':(0,n-1)}
    for step in reversed(steps):
        where=step.qubits
        if len(where)==2 and where[1]!=where[0]+1:raise ValueError('Requires ascending nearest-neighbour chain gates')
        mps.canonicalize_(where,info=info)
        if len(where)==1:
            mps.gate_(step.channel(scale),where,contract=True);info['cur_orthog']=(where[0],where[0])
        else:
            mps.gate_split_(step.channel(scale),where,max_bond=chi,cutoff=1e-12,
                cutoff_mode='rsum2',renorm=0,absorb='right')
            info['cur_orthog']=(where[1],where[1])
    return mps

def run(folder):
    dest=folder/'canonical_crosscheck'
    if dest.exists():raise FileExistsError('Preserve prior cross-check')
    dest.mkdir();plan=json.loads((ARCHIVE/'plan.json').read_text(encoding='utf-8-sig'))
    layout=plan['layout'];profile=FrozenSurrogate(ARCHIVE/'live_backend_properties.json',layout)
    index=next(i for i,r in enumerate(plan['records']) if r.get('factor')==1 and r['twirl_id']==0)
    with (ARCHIVE/'provider_inputs'/f'circuit_{index:03d}.qpy').open('rb') as f:qc=active_circuit(qpy.load(f)[0],layout)
    steps=fuse_steps(compile_steps(qc,profile.rate));records=[]
    for chi in (2,4):
        for arm,scale in ((0,0.),(1,1.)):
            start=time.monotonic();tn=evolve_canonical(18,{8:'Z'},steps,scale,chi)
            tensor=tn['I0'];tensor.modify(data=record_sign(plan['records'][index]['readout_mask_little_endian'])[8]*tensor.data)
            save_tn(dest/f'obs08_chi{chi}_arm{arm}',tn)
            bp=load_tn(folder/'states'/f'obs08_chi{chi}_arm{arm}')
            nn=bounded_contract(overlap_network(tn,tn))[0];bb=bounded_contract(overlap_network(bp,bp))[0]
            nb=bounded_contract(overlap_network(tn,bp))[0]
            distance_squared=nn+bb-2*nb
            records.append({'observable':8,'chi':chi,'arm':arm,'seconds':time.monotonic()-start,
                'canonical_norm_squared':nn,'bp_norm_squared':bb,'distance_squared':distance_squared,
                'relative_hs_distance':float(np.sqrt(max(distance_squared,0)/max(nn,1e-30))),
                'canonical_expectation_zero':expectation_zero(tn),'bp_expectation_zero':expectation_zero(bp)})
    report={'method':'mixed-canonical MPS, independent of D2BP messages','native_graph':'18 vertices, 17 adjacent edges, no loops',
        'source_sha256':digest(Path(__file__)),'new_qpu_seconds':0,'records':records}
    (dest/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('folder',type=Path);args=p.parse_args()
    with threadpool_limits(limits=1):run(args.folder)
