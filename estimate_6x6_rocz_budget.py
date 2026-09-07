"""Offline resource estimate from saved calibration; never submits or authenticates."""
from dataclasses import asdict
import json
from pathlib import Path
import time
import numpy as np
from qiskit import QuantumCircuit,qpy
from qiskit_ibm_runtime.models import BackendProperties
from cuprate_2d_fermionic_mapping import build_network
from cuprate_2d_tflo import compile_template,explicit_twirl,embed_measurement
import benchmark_fermionic_6x6_mps as benchmark
import aer_cuprate_cz_zne as folding
import aer_cuprate_nighthawk_smoke as files

ROOT=Path(__file__).resolve().parent
DEST=ROOT/'results_cuprate_2d/full6x6_T04_rocz_offline_budget_v1'
HARDWARE=ROOT/'results_cuprate_2d/hardware_readout_cz_folding_3x3_2026-09-06'
MAPPING=ROOT/'results_cuprate_2d/fermionic_mapping_2026-09-05/steps2/plan.json'

def main():
    if DEST.exists(): raise FileExistsError('Refuse overwrite')
    tick=time.perf_counter(); cfg=benchmark.cfg_for(6)
    logical=build_network(cfg)
    native=compile_template(logical)
    print(json.dumps({'stage':'COMPILED','cz':native.count_ops().get('cz'),'depth':native.depth()}),flush=True)
    layout=files.read(MAPPING)['initial_layout']
    props=BackendProperties.from_dict(files.read(HARDWARE/'live_backend_properties.json'))
    pre=files.read(HARDWARE/'live_preflight.json')
    reset=pre['reset_seconds']; rep=pre['options']['execution']['rep_delay']
    def duration(qc):
        clocks=np.zeros(120)
        for item in qc.data:
            name=item.operation.name; qs=tuple(qc.find_bit(q).index for q in item.qubits)
            if name=='rz': dt=0.
            elif name=='measure': dt=float(props.qubit_property(qs[0],'readout_length')[0])
            else:
                try: dt=float(props.gate_length(name,qs))
                except Exception:
                    if name!='cz': raise
                    dt=float(props.gate_length(name,tuple(reversed(qs))))
            clocks[list(qs)]=max(clocks[list(qs)])+dt
        return float(max(clocks))
    twirled,mask=explicit_twirl(native,202609040)
    factors=[]; circuits=[]
    for factor in [1,2,3]:
        local,audit=folding.fold_cz(twirled,factor,2026300000)
        physical=embed_measurement(local,layout,120)
        dt=duration(physical)
        factors.append({'factor':factor,'cz':physical.count_ops().get('cz'),
            'depth':physical.depth(),'unaligned_circuit_seconds':dt,'one_shot_seconds':dt+reset+rep})
        circuits.append(physical)
    calibration=[]
    for state in [0,1]:
        local=QuantumCircuit(72)
        if state: local.x(range(72))
        physical=embed_measurement(local,layout,120)
        calibration.append(duration(physical)+reset+rep)
    cases=[]
    for shots,cal,name in [([512,56,112],64,'808-shot union, like current small pilot'),
            ([512]*3,256,'512 per factor'),([2048]*3,512,'2048 per factor'),
            ([4096]*3,512,'4096 per factor'),([8192]*3,1024,'8192 per factor')]:
        execution=sum(n*f['one_shot_seconds'] for n,f in zip(shots,factors))+cal*sum(calibration)
        cases.append({'name':name,'shots_per_factor':shots,'calibration_per_state':cal,
            'total_shots':sum(shots)+2*cal,'shot_execution_seconds':execution,
            'estimated_qpu_seconds_by_subjobs':{str(n):2*n+execution for n in [1,2,3,4]}})
    DEST.mkdir()
    for k,c in enumerate(circuits,1):
        with (DEST/f'representative_factor{k}.qpy').open('wb') as f: qpy.dump(c,f)
    sources=[Path(__file__),ROOT/'benchmark_fermionic_6x6_mps.py',ROOT/'cuprate_2d_tflo.py',
        ROOT/'cuprate_2d_fermionic_mapping.py',ROOT/'cuprate_2d_fermionic_dynamics.py',
        HARDWARE/'live_backend_properties.json',HARDWARE/'live_preflight.json',MAPPING]
    result={'status':'OFFLINE_ESTIMATE_ONLY_NO_JOB','config':asdict(cfg),'backend':'ibm_phoenix',
        'calibration_updated':str(props.last_update_date),'layout':layout,'factors':factors,'cases':cases,
        'new_qpu_seconds':0,'authorization_to_increase_budget':False,'reset_seconds':reset,'rep_delay':rep,
        'assumptions':['One representative explicit uncompressed Pauli twirl, not all8 compiled PUBs.',
            'Saved calibration, not a fresh live ISA or faulty-qubit validation.',
            'Unaligned ASAP timing; final alignment/scheduling may increase it.',
            'Assumes recorded reset timing applies to all72 selected wires.',
            'Internal subjob count is unknown;2s per subjob is approximate.',
            'These are runtime scenarios, not a guaranteed invoice or accuracy prediction.'],
        'input_sha256':{str(p.relative_to(ROOT)):files.digest(p) for p in sources},
        'local_preparation_seconds':time.perf_counter()-tick}
    files.write(DEST/'estimate.json',result)
    print(json.dumps(result),flush=True)

if __name__=='__main__': main()
