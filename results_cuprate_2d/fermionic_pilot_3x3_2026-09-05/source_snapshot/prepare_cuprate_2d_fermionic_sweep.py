"""Prepare full-fermion 2/4/8-step circuits and optional IBM routing, never submit."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import time
from dataclasses import asdict, replace
from pathlib import Path

import qiskit
from qiskit import qpy, transpile
from qiskit.quantum_info import SparsePauliOp

from cuprate_2d_qiskit_circuit import load_config
from cuprate_2d_fermionic_dynamics import CIRCUIT_FAMILY, build_fermionic_circuit
from cuprate_2d_hubbard_pipeline import all_hopping_bonds


def circuit_summary(qc):
    return {'qubits':qc.num_qubits,'depth':qc.depth(),'operations':dict(qc.count_ops()),
            'two_qubit_count':sum(len(i.qubits)==2 for i in qc.data),
            'two_qubit_depth':qc.depth(filter_function=lambda i:len(i.qubits)==2)}


def save_qpy(path, circuit):
    with path.open('wb') as handle:
        qpy.dump(circuit,handle)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def observables(cfg):
    ops=[]
    for site in range(cfg.sites):
        def label(qubits):
            values=['I']*cfg.qubits
            for q in qubits:
                values[cfg.qubits-1-q]='Z'
            return ''.join(values)
        identity,up,dn,zz=label([]),label([2*site]),label([2*site+1]),label([2*site,2*site+1])
        for name,terms in [('n_up',[(identity,0.5),(up,-0.5)]),
                           ('n_down',[(identity,0.5),(dn,-0.5)]),
                           ('double_occupancy',[(identity,0.25),(up,-0.25),(dn,-0.25),(zz,0.25)])]:
            ops.append(({'site':site,'x':site%cfg.lx,'y':site//cfg.lx,'observable':name},SparsePauliOp.from_list(terms)))
    return ops


def pauli_records(operator):
    return [[label, float(complex(coefficient).real)]
            for label, coefficient in operator.to_list()]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--validation',type=Path,required=True)
    parser.add_argument('--outdir',type=Path,required=True)
    parser.add_argument('--steps',type=int,nargs='+',default=[2,4,8])
    parser.add_argument('--shots',type=int,default=512)
    parser.add_argument('--max-execution-time',type=int,default=5)
    parser.add_argument('--backend',default=None,help='Optional read-only backend access for real transpilation.')
    parser.add_argument('--account-name',default='qiskit-runtime-q9')
    args=parser.parse_args()
    if args.shots <= 0 or not 0 < args.max_execution_time <= 5 or any(s<=0 for s in args.steps):
        raise ValueError('Positive steps/shots and the agreed maximum of 5 s are required')
    validation=json.loads(args.validation.read_text())
    if validation.get('passed') is not True:
        raise ValueError('Numerical fermion validation must pass first')
    for name,expected in validation['source_sha256'].items():
        actual=hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f'Validation is stale for {name}; rerun it')
    args.outdir.mkdir(parents=True,exist_ok=True)
    (args.outdir/'validation_snapshot.json').write_text(json.dumps(validation,indent=2)+'\n')
    cfg=load_config(args.config)
    backend=None
    if args.backend:
        from ibm_staged_fermi_hubbard_runner import build_runtime_service
        backend=build_runtime_service(args.account_name).backend(args.backend)
        status=backend.status()
        (args.outdir/'backend_snapshot.json').write_text(json.dumps({
            'backend':backend.name,'qubits':backend.num_qubits,'operational':status.operational,
            'pending_jobs':status.pending_jobs,'captured_unix':time.time()},indent=2)+'\n')
    options={'default_shots':args.shots,'max_execution_time':args.max_execution_time,
             'resilience_level':0,'resilience':{'measure_mitigation':False,'pec_mitigation':False,
             'zne_mitigation':True,'zne':{'amplifier':'gate_folding','noise_factors':[1,3,5],
             'extrapolator':['linear','fallback'],'extrapolated_noise_factors':[0]}}}
    from qiskit_ibm_runtime.options import EstimatorOptions
    EstimatorOptions(**options)  # Validate future job options without submitting.
    rows=[]
    for steps in args.steps:
        selected=replace(cfg,steps=steps,shots=args.shots)
        circuit=build_fermionic_circuit(selected)
        directory=args.outdir/f'steps{steps}'
        directory.mkdir(exist_ok=True)
        logical_hash=save_qpy(directory/'logical_circuit.qpy',circuit)
        logical=circuit_summary(circuit)
        ops=observables(selected)
        records=[{**record,'paulis':pauli_records(op)} for record,op in ops]
        isa_summary=None
        isa_hash=None
        physical_order=None
        if backend is not None:
            print(f'Transpiling full fermionic steps={steps}, logical gates={circuit.size()}',flush=True)
            isa=transpile(circuit,backend=backend,optimization_level=1,seed_transpiler=9)
            isa_summary=circuit_summary(isa)
            isa_hash=save_qpy(directory/'isa_circuit.qpy',isa)
            physical_order=isa.layout.final_index_layout(filter_ancillas=True)
            records=[{**record,'paulis':pauli_records(op.apply_layout(isa.layout))} for record,op in ops]
        (directory/'observables.json').write_text(json.dumps(records,indent=2)+'\n')
        plan={'submitted':False,'submission_available_in_this_script':False,'circuit_family':CIRCUIT_FAMILY,
              'config':asdict(selected),'time':selected.total_time,'backend':args.backend,
              'logical':logical,'isa':isa_summary,'logical_qpy_sha256':logical_hash,'isa_qpy_sha256':isa_hash,
              'logical_to_physical_final':physical_order,'estimator_options_for_future_job':options,
              'observable_count':len(records),'sampling_shots_all_noise_factors':args.shots*3,
              'budget_note':'5 s is a future runtime cap, not a predicted cost or a quality guarantee.',
              'validation_scope':'Exact small open lattices; 6x6 tensor convergence and routed fidelity remain to be tested.',
              'hardware_ready_for_physics_claim':False,'python_version':platform.python_version(),
              'qiskit_version':qiskit.__version__}
        (directory/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
        row={'steps':steps,'time':selected.total_time,'logical_depth':logical['depth'],
             'logical_two_qubit_count':logical['two_qubit_count'],
             'isa_depth':isa_summary['depth'] if isa_summary else '',
             'isa_two_qubit_count':isa_summary['two_qubit_count'] if isa_summary else '',
             'isa_two_qubit_depth':isa_summary['two_qubit_depth'] if isa_summary else ''}
        rows.append(row)
        print(json.dumps(row),flush=True)
    with (args.outdir/'sweep_resources.csv').open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    report=['# Full-fermion 2D dynamics preparation','',f'Circuit family: {CIRCUIT_FAMILY}. All t, t-prime and U terms included.',
            'Only classical circuit construction and optional read-only backend transpilation were performed. No QPU job was submitted.',
            '', '| steps | time | logical 2q | routed 2q | routed depth |', '|---|---:|---:|---:|---:|']
    for r in rows:
        report.append(f"| {r['steps']} | {r['time']:.2f} | {r['logical_two_qubit_count']} | {r['isa_two_qubit_count']} | {r['isa_depth']} |")
    report += ['', 'Future ZNE setting: 512 shots per factor, factors 1/3/5, maximum execution time 5 s.',
               'The old t-only MPS/hardware results are not references for these corrected circuits.',
               'Before hardware physics: establish dt and MPS-bond convergence for the chosen time and assess the much deeper routed circuit.',
               'Source validation and circuit/observable inputs are preserved beside every plan.']
    (args.outdir/'preparation.md').write_text('\n'.join(report)+'\n')


if __name__=='__main__':
    main()
