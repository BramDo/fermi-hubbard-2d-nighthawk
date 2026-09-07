"""Validate fermion routing, scout Phoenix paths, and compile alternatives. No submit."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import time
from dataclasses import asdict,replace
from pathlib import Path

import numpy as np
from scipy.sparse.linalg import expm_multiply
from qiskit import QuantumCircuit,transpile
from qiskit.quantum_info import Operator,Statevector

from cuprate_2d_hubbard_pipeline import Cuprate2DConfig
from cuprate_2d_fermionic_dynamics import build_fermionic_circuit
from cuprate_2d_fermionic_mapping import build_network,build_adaptive,add_fswap,NETWORK_FAMILY
from cuprate_2d_qiskit_circuit import load_config
from cuprate_2d_exact_sector_baseline import sector_basis,initial_state_vector,diagonal_site_rows
from validate_cuprate_2d_fermionic_dynamics import independent_hamiltonian,phase_distance
from prepare_cuprate_2d_fermionic_sweep import circuit_summary,save_qpy,observables,pauli_records


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')


def validate(outdir):
    checks=[]; dynamics=[]
    def check(name,value,tolerance=1e-10,minimum=False):
        passed=value>=tolerance if minimum else value<=tolerance
        record={'check':name,'value':float(value),'threshold':tolerance,'minimum':minimum,'passed':bool(passed)}
        checks.append(record); print(json.dumps(record),flush=True)
        if not passed:
            save(outdir/'failed_validation.json',checks)
            raise AssertionError(name)
    qc=QuantumCircuit(2);add_fswap(qc,0,1)
    expected=np.array([[1,0,0,0],[0,0,1,0],[0,1,0,0],[0,0,0,-1]],dtype=complex)
    check('fswap_includes_minus_for_double_occupation',np.max(np.abs(Operator(qc).data-expected)))
    cfg=Cuprate2DConfig(lx=2,ly=2,holes=0,steps=2,chemical_potential=0.17)
    reference=Operator(build_fermionic_circuit(cfg,prepare=False)).data
    for strategy in ('left','look4','look12'):
        candidate=Operator(build_adaptive(cfg,prepare=False,strategy=strategy)).data
        check(f'adaptive_{strategy}_exact_reference_unitary',np.max(np.abs(candidate-reference)))
    tiny=replace(cfg,steps=1,dt=1e-6)
    unitary=Operator(build_network(tiny,prepare=False)).data
    h=independent_hamiltonian(cfg,list(range(1<<cfg.qubits))).toarray()
    check('parallel_network_full_H_generator',np.max(np.abs(1j*(unitary-unitary.conj().T)/(2*tiny.dt)-h)),2e-7)
    actual=build_network(cfg,prepare=False)
    unitary=Operator(actual).data
    check('network_unitarity',np.max(np.abs(unitary.conj().T@unitary-np.eye(len(unitary)))))
    for spin in (0,1):
        number=np.array([sum((state>>(2*s+spin))&1 for s in range(cfg.sites)) for state in range(1<<cfg.qubits)])
        check(f'network_N_spin_{spin}',np.max(np.abs((number[:,None]-number[None,:])*unitary)))
    line=[[i,i+1] for i in range(cfg.qubits-1)]+[[i+1,i] for i in range(cfg.qubits-1)]
    compiled=transpile(actual,basis_gates=['rz','sx','x','cz'],coupling_map=line,
                       initial_layout=list(range(cfg.qubits)),routing_method='none',optimization_level=3)
    check('native_CZ_compilation_equivalence',np.max(np.abs(Operator.from_circuit(compiled).data-unitary)))
    for lx,ly,holes in ((2,2,0),(2,3,2)):
        c=Cuprate2DConfig(lx=lx,ly=ly,holes=holes,steps=1)
        basis,index,_,_=sector_basis(c); h=independent_hamiltonian(c,basis); init=initial_state_vector(c,index)
        for steps in (2,4,8):
            case=replace(c,steps=steps)
            exact=expm_multiply(-1j*h*case.total_time,init)
            refrows=diagonal_site_rows(case,basis,exact,steps,case.total_time,'exact')
            for name,builder in [('reference',build_fermionic_circuit),('adaptive',build_adaptive),('network',build_network)]:
                q=builder(case); vector=Statevector.from_instruction(q).data[basis]
                check(f'{name}_sector_{lx}x{ly}_s{steps}',abs(1-float(np.vdot(vector,vector).real)),2e-10)
                rows=diagonal_site_rows(case,basis,vector,steps,case.total_time,name)
                result={'lattice':f'{lx}x{ly}','method':name,'steps':steps,'time':case.total_time,
                        'state_distance':phase_distance(vector,exact)}
                for key in ('charge','spin_z','double_occupancy'):
                    result[key+'_rmse']=float(np.sqrt(np.mean([(a[key]-b[key])**2 for a,b in zip(rows,refrows)])))
                dynamics.append(result)
        errors=[]
        for steps in (4,8,16):
            case=replace(c,steps=steps,dt=0.4/steps)
            exact=expm_multiply(-0.4j*h,init)
            vector=Statevector.from_instruction(build_network(case)).data[basis]
            errors.append(phase_distance(vector,exact))
        for i in range(2):check(f'network_second_order_{lx}x{ly}_{i}',errors[i]/errors[i+1],3.4,minimum=True)
        check(f'network_fine_dt_error_{lx}x{ly}',errors[-1],0.01)
    from cuprate_2d_mps_circuit_baseline import apply_circuit_mps,site_rows
    c=Cuprate2DConfig(lx=2,ly=2,holes=2,steps=2)
    psi,_,_=apply_circuit_mps(c,circuit_family=NETWORK_FAMILY,max_bond=64,cutoff=0.0)
    mps=site_rows(c,psi,profile='mps')
    basis,_,_,_=sector_basis(c)
    sv=Statevector.from_instruction(build_network(c)).data[basis]
    exact=diagonal_site_rows(c,basis,sv,c.steps,c.total_time,'exact_circuit')
    check('network_MPS_vs_statevector',max(abs(a[k]-b[k]) for a,b in zip(mps,exact) for k in ('n_up','n_down','double_occupancy')))
    sources=['cuprate_2d_fermionic_mapping.py','cuprate_2d_fermionic_dynamics.py',
             'cuprate_2d_qiskit_circuit.py','optimize_cuprate_2d_fermionic_mapping.py']
    result={'passed':True,'checks':checks,'dynamics':dynamics,
            'source_sha256':{p:hashlib.sha256(Path(__file__).with_name(p).read_bytes()).hexdigest() for p in sources},
            'boundary':'Small open-lattice checks. Network changes the second-order term ordering; adaptive is exact to reference.'}
    save(outdir/'validation.json',result)
    return result


def find_paths(backend,width,attempts=48):
    edges={tuple(sorted(e)) for e in backend.coupling_map.get_edges()}
    adjacency={q:[] for q in range(backend.num_qubits)}
    for a,b in edges:adjacency[a].append(b);adjacency[b].append(a)
    error={}
    for a,b in edges:
        prop=backend.target['cz'].get((a,b),backend.target['cz'].get((b,a)))
        error[(a,b)]=float(prop.error) if prop is not None and prop.error is not None else None
    paths=[];seen=set()
    for seed in range(attempts):
        rng=random.Random(seed+20260905)
        start=rng.choice(list(adjacency)); path=[start]; used={start}; visits=0
        def search():
            nonlocal visits
            visits+=1
            if len(path)==width:return True
            if visits>12000:return False
            available=[q for q in adjacency[path[-1]] if q not in used]
            rng.shuffle(available)
            available.sort(key=lambda q:sum(n not in used for n in adjacency[q]))
            for q in available:
                used.add(q);path.append(q)
                if search():return True
                path.pop();used.remove(q)
            return False
        if search():
            signature=min(tuple(path),tuple(reversed(path)))
            if signature in seen:continue
            seen.add(signature)
            values=[error[tuple(sorted((a,b)))] for a,b in zip(path,path[1:])]
            # Calibration ranking only; this is not a fidelity prediction.
            score=sum(-math.log1p(-min(v if v is not None else 0.02,0.999)) for v in values)
            paths.append({'path':list(path),'search_seed':seed+20260905,'score':score,
                          'missing_edge_errors':sum(v is None for v in values)})
    if not paths:raise RuntimeError('No valid 72-qubit path found in bounded search')
    paths.sort(key=lambda p:p['score'])
    return paths,{'coupling_edges':[list(e) for e in sorted(edges)],
                 'cz_errors':[{'qubits':list(e),'error':error[e]} for e in sorted(error)]}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--outdir',type=Path,required=True)
    parser.add_argument('--backend',default='ibm_phoenix')
    parser.add_argument('--account-name',default='qiskit-runtime-q9')
    parser.add_argument('--validate-only',action='store_true')
    args=parser.parse_args(); args.outdir.mkdir(parents=True,exist_ok=True)
    validation=validate(args.outdir)
    if args.validate_only:return
    from ibm_staged_fermi_hubbard_runner import build_runtime_service
    backend=build_runtime_service(args.account_name).backend(args.backend)
    cfg=load_config(args.config)
    paths,snapshot=find_paths(backend,cfg.qubits)
    save(args.outdir/'layout_candidates.json',paths)
    save(args.outdir/'backend_snapshot.json',{'backend':backend.name,'captured_unix':time.time(),**snapshot})
    path=paths[0]['path']
    print(json.dumps({'paths_found':len(paths),'selected_path_score':paths[0]['score']}),flush=True)
    methods={'adaptive_look4':lambda c:build_adaptive(c,strategy='look4'),
             'adaptive_look12':lambda c:build_adaptive(c,strategy='look12'),
             'network':build_network}
    candidates=[];circuits={}
    for name,builder in methods.items():
        logical=builder(replace(cfg,steps=2))
        for level in (1,3):
            print(f'Compiling {name}, level {level}',flush=True)
            start=time.perf_counter()
            isa=transpile(logical,backend=backend,initial_layout=path,routing_method='none',
                          optimization_level=level,seed_transpiler=9,approximation_degree=1.0)
            summary=circuit_summary(isa)
            key=f'{name}_opt{level}'
            directory=args.outdir/'candidates'/key;directory.mkdir(parents=True,exist_ok=True)
            qhash=save_qpy(directory/'isa_circuit.qpy',isa)
            record={'candidate':key,'method':name,'optimization_level':level,'compile_seconds':time.perf_counter()-start,
                    **summary,'qpy_sha256':qhash,'routing_swaps_added':False,
                    'same_reference_product_formula':name.startswith('adaptive')}
            candidates.append(record);circuits[key]=(logical,isa)
            save(directory/'summary.json',record);print(json.dumps(record),flush=True)
    # Control: what does just raising the optimizer level do to the old circuit?
    print('Compiling the original parity-star reference at optimization level 3',flush=True)
    ref=build_fermionic_circuit(replace(cfg,steps=2))
    ref_isa=transpile(ref,backend=backend,optimization_level=3,seed_transpiler=9,approximation_degree=1.0)
    save_qpy(args.outdir/'reference_opt3.qpy',ref_isa)
    control={'candidate':'reference_opt3',**circuit_summary(ref_isa)}
    save(args.outdir/'reference_opt3.json',control)
    # Predeclared objective: reduce depth for coherent dynamics, break ties by count.
    winner=min(candidates,key=lambda r:(r['two_qubit_depth'],r['two_qubit_count']))
    save(args.outdir/'candidate_comparison.json',{'selection_rule':'minimum two-qubit depth, then two-qubit count',
         'winner':winner,'candidates':candidates,'reference_opt3':control})
    rows=[]
    for steps in (2,4,8):
        case=replace(cfg,steps=steps,shots=512)
        if steps==2:logical,isa=circuits[winner['candidate']]
        else:
            print(f'Compiling winner for steps={steps}',flush=True)
            logical=methods[winner['method']](case)
            isa=transpile(logical,backend=backend,initial_layout=path,routing_method='none',
                          optimization_level=winner['optimization_level'],seed_transpiler=9,approximation_degree=1.0)
        directory=args.outdir/f'steps{steps}';directory.mkdir(exist_ok=True)
        hashes={'logical':save_qpy(directory/'logical_circuit.qpy',logical),'isa':save_qpy(directory/'isa_circuit.qpy',isa)}
        records=[{**record,'paulis':pauli_records(op.apply_layout(isa.layout))} for record,op in observables(case)]
        save(directory/'observables.json',records)
        summary=circuit_summary(isa)
        try:duration=float(isa.estimate_duration(backend.target,unit='s'))
        except Exception:duration=None
        plan={'submitted':False,'backend':backend.name,'winner':winner['candidate'],'config':asdict(case),
              'logical_metadata':logical.metadata,'isa':summary,'initial_layout':path,
              'final_index_layout':isa.layout.final_index_layout(filter_ancillas=True),'qpy_sha256':hashes,
              'observable_count':len(records),'gate_only_duration_estimate_s':duration,
              'future_zne_settings':{'shots_per_noise_factor':512,'noise_factors':[1,3,5],'max_execution_time':5},
              'boundary':'No hardware results. New ordering needs its own 6x6 tensor baseline and dt convergence.'}
        save(directory/'plan.json',plan)
        rows.append({'steps':steps,'time':case.total_time,**summary,'duration_s':duration})
        print(json.dumps(rows[-1]),flush=True)
    original_root=Path('results_cuprate_2d/fermionic_dynamics_2026-09-05/sweep')
    report=['# Fermionic mapping and routing optimization','',
            f"Selected {winner['candidate']} from {len(candidates)} compiled candidates; {len(paths)} valid physical paths found.",
            f"All {len(validation['checks'])} numerical checks passed.",
            'The adaptive method preserves the old product formula exactly. The parallel network uses another second-order ordering of the same Hamiltonian.',
            '', '| steps | original CZ | optimized CZ | original depth | optimized depth |',
            '|---|---:|---:|---:|---:|']
    for r in rows:
        old=json.loads((original_root/f"steps{r['steps']}"/'plan.json').read_text())['isa']
        report.append(f"| {r['steps']} | {old['two_qubit_count']} | {r['two_qubit_count']} | {old['depth']} | {r['depth']} |")
    report += ['',f"Optimizer-only control (2 steps): {control['two_qubit_count']} CZ, depth {control['depth']}.",
               'Physical path ranking uses calibration errors as a heuristic, not a predicted circuit fidelity.',
               'No extra routing SWAPs are needed. The fermionic mode order is restored after every symmetric step.',
               'Full circuit, layout, observable, calibration, validation and candidate records are saved. No QPU job submitted.',
               'Future settings retain 512 shots per noise factor and a maximum of 5 seconds. Gate-only duration is not billed runtime.',
               'This is an engineering improvement, not a measured accuracy or quantum-advantage result.',
               '', 'Background: https://arxiv.org/abs/1711.04789 (fermionic swap networks; no resource bound from that paper is claimed for this implementation).']
    (args.outdir/'optimization.md').write_text('\n'.join(report)+'\n')
    save(args.outdir/'artifact_sha256.json',[{'path':str(p.relative_to(args.outdir)),
         'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(args.outdir.rglob('*'))
         if p.is_file() and p.name!='artifact_sha256.json'])


if __name__=='__main__':main()
