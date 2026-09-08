"""Read only the bound native hardware circuits; never instantiate a service."""
from pathlib import Path
import json,sys
from qiskit import qpy
ROOT=Path(__file__).resolve().parents[1]

if __name__=='__main__':
    folder=ROOT/'results_cuprate_2d'/('hardware_readout_cz_folding_'+sys.argv[1]+'_2026-09-06')
    plan=json.loads((folder/'plan.json').read_text(encoding='utf-8-sig'))
    for factor in (1,2,3):
        index=next(i for i,r in enumerate(plan['records']) if r.get('factor')==factor and r['twirl_id']==0)
        with (folder/'provider_inputs'/f'circuit_{index:03d}.qpy').open('rb') as f:qc=qpy.load(f)[0]
        measurements=[(qc.find_bit(x.qubits[0]).index,qc.find_bit(x.clbits[0]).index) for x in qc.data if x.operation.name=='measure']
        active=sorted({qc.find_bit(q).index for x in qc.data if x.operation.name!='barrier' for q in x.qubits})
        print(json.dumps({'index':index,'factor':factor,'width':qc.num_qubits,'active':active,
            'depth':qc.depth(),'operations':dict(qc.count_ops()),'measurements':measurements,
            'first_operations':[(x.operation.name,[qc.find_bit(q).index for q in x.qubits]) for x in qc.data[:12]],
            'last_operations':[(x.operation.name,[qc.find_bit(q).index for q in x.qubits]) for x in qc.data[-24:]]}))
