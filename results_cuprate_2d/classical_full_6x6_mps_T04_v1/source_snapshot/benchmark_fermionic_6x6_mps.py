"""CPU-only bounded MPS convergence/timing screen for the full fermionic circuit."""
import argparse
from dataclasses import asdict
from functools import lru_cache
import io
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
import unittest
import numpy as np
import psutil
import quimb
import quimb.tensor as qtn
from threadpoolctl import threadpool_limits,threadpool_info
from cuprate_2d_hubbard_pipeline import Cuprate2DConfig
from cuprate_2d_fermionic_mapping import network_schedule,pair_model
from cuprate_2d_tflo import initial_occupations,physical_observables,flo_reference
import aer_cuprate_nighthawk_smoke as files

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results_cuprate_2d/classical_full_6x6_mps_T04_v1'
REFERENCE=ROOT/'results_cuprate_2d/hardware_readout_cz_folding_3x3_2026-09-06/plan.json'
SOURCES=['benchmark_fermionic_6x6_mps.py','test_benchmark_fermionic_6x6_mps.py',
    'CLASSICAL_6X6_MPS_PROTOCOL.md','cuprate_2d_tflo.py','cuprate_2d_fermionic_mapping.py',
    'cuprate_2d_fermionic_dynamics.py','cuprate_2d_hubbard_pipeline.py','aer_cuprate_nighthawk_smoke.py']
Z=np.diag([1.,-1.]); ZZ=np.kron(Z,Z)

@lru_cache(maxsize=64)
def fused_gate(c,onsite_u,dt):
    """Quimb order is irrelevant here: each symmetric block commutes with SWAP."""
    theta=np.pi+c*dt
    co=np.cos(theta/2); si=np.sin(theta/2)
    return np.array([[1,0,0,0],[0,1j*co,si,0],[0,si,1j*co,0],
                     [0,0,0,-np.exp(-1j*onsite_u*dt/2)]],dtype=complex)

def cfg_for(size):
    return Cuprate2DConfig(lx=size,ly=size,holes={2:0,3:1,6:4}[size],
        steps=2,dt=.2,u_over_t=8,t_prime_over_t=-.25,shots=512)

def fused_layers(cfg):
    if cfg.chemical_potential!=0: raise ValueError('mu=0 only in this benchmark')
    hops,onsite=pair_model(cfg); schedule=network_schedule(cfg.qubits)
    result=[]
    for _ in range(cfg.steps):
        for sweep in [schedule,list(reversed(schedule))]:
            for layer in sweep:
                result.append([(a,b,fused_gate(float(hops.get(modes,0)),
                    float(onsite.get(modes,0)),cfg.dt)) for a,b,modes in layer])
    return result

def observables(psi,info):
    terms={(q,):Z for q in range(psi.L)}
    terms.update({(q,q+1):ZZ for q in range(0,psi.L,2)})
    values=psi.compute_local_expectation_canonical(terms,return_all=True,normalized=True,inplace=True,info=info)
    p=np.array([values[q,] for q in range(psi.L)]+[values[q,q+1] for q in range(0,psi.L,2)])
    if np.max(np.abs(p.imag))>1e-10: raise ArithmeticError('Complex Hermitian expectation')
    return p.real

def evolve(cfg,chi,*,cutoff=1e-10,deadline=None,progress=None,verify_norm=False):
    tick=time.perf_counter(); cpu_tick=time.process_time()
    layers=fused_layers(cfg)
    occupation=initial_occupations(cfg)
    psi=qtn.MPS_computational_state(''.join(str(int(x)) for x in occupation),dtype='complex128')
    info={'cur_orthog':(0,0)}
    initialization=time.perf_counter()-tick; evolution_tick=time.perf_counter()
    log_retained=0.; largest_bond=1; rows=[]; applied=0
    for j,layer in enumerate(layers):
        if deadline is not None and time.perf_counter()>deadline: raise TimeoutError('Kernel deadline')
        for a,b,gate in layer:
            psi.gate_with_auto_swap_(gate,(a,b),info=info,max_bond=chi,cutoff=cutoff,
                cutoff_mode='rel',method='svd',renorm=0)
            applied+=1
        center=info['cur_orthog'][0]
        center_data=psi[center].data
        norm2=float(np.vdot(center_data,center_data).real)
        if not np.isfinite(norm2) or norm2<=0 or norm2>1+1e-8:
            raise ArithmeticError('Invalid retained layer norm')
        if verify_norm:
            full=float(np.real(psi.H@psi))
            if abs(full-norm2)>1e-9: raise ArithmeticError('Canonical-center norm mismatch')
        log_retained+=float(np.log(norm2))
        psi[center].modify(data=center_data/np.sqrt(norm2))
        largest_bond=max(largest_bond,int(psi.max_bond()))
        if (j+1)%12==0 or j+1==len(layers):
            rss=psutil.Process().memory_info().rss
            if rss>2*1024**3: raise MemoryError('2GiB RSS guard')
            row={'completed_layers':j+1,'total_layers':len(layers),'updates':applied,
                'seconds':time.perf_counter()-tick,'max_bond':largest_bond,
                'log_retained_norm':log_retained,'rss_bytes':rss}
            rows.append(row)
            if progress: progress(row)
    evolution=time.perf_counter()-evolution_tick
    if deadline is not None and time.perf_counter()>deadline: raise TimeoutError('Deadline before observables')
    obs_tick=time.perf_counter(); p=observables(psi,info)
    norm=float(np.real(psi.H@psi))
    if abs(norm-1)>1e-9: raise ArithmeticError('Final norm not one')
    physical=physical_observables(p)
    if np.max(np.abs(p))>1+1e-9: raise ArithmeticError('Unphysical moments')
    occupation_count=float(physical[:,0].sum())
    observable_time=time.perf_counter()-obs_tick
    result={'status':'COMPLETE','config':asdict(cfg),'chi':chi,'cutoff':cutoff,'cutoff_mode':'rel',
        'moments':p.tolist(),'physical_means':physical.tolist(),'normalized_state_norm':norm,
        'number_expectation':occupation_count,'number_error':occupation_count-cfg.electrons,
        'total_spin':float(physical[:,1].sum()),'max_bond_observed':largest_bond,
        'fused_two_qubit_updates':applied,'layer_count':len(layers),'log_retained_norm':log_retained,
        'truncation_diagnostic_not_error_bound':True,'initialization_seconds':initialization,
        'evolution_seconds':evolution,'observable_seconds':observable_time,
        'kernel_seconds':time.perf_counter()-tick,'process_cpu_seconds':time.process_time()-cpu_tick,
        'rss_bytes':psutil.Process().memory_info().rss,'progress':rows}
    if deadline is not None and time.perf_counter()>deadline: raise TimeoutError('Deadline during observables')
    return psi,result

def verify_plan(out):
    plan=files.read(out/'plan.json')
    for name,h in plan['input_sha256'].items():
        if files.digest(ROOT/name)!=h: raise ValueError('Frozen source changed '+name)
    return plan

def worker(out,size,chi,threads):
    folder=out/f'{size}x{size}_chi{chi}_threads{threads}'
    if folder.exists(): raise FileExistsError('Refuse repeated profile')
    verify_plan(out); folder.mkdir()
    limit=180 if size==6 else 120
    start=time.perf_counter()
    def progress(row):
        with (folder/'progress.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(row)+'\n')
        print(json.dumps({'size':size,'chi':chi,'threads':threads,**row}),flush=True)
    with threadpool_limits(limits=threads):
        try:
            psi,result=evolve(cfg_for(size),chi,deadline=start+limit,progress=progress)
            result['threads']=threads; result['threadpools']=threadpool_info()
            if size==3:
                exact=np.array(files.read(REFERENCE)['target']['reference'])
                diff=np.array(result['physical_means'])-physical_observables(exact)
                result['exact_rmse_charge_spin_doublon']=np.sqrt(np.mean(diff**2,axis=0)).tolist()
                result['exact_max_spin_error']=float(np.max(np.abs(diff[:,1])))
            result['quimb']=quimb.__version__; result['numpy']=np.__version__
            files.write(folder/'result.json',result)
            np.savez_compressed(folder/'mps_arrays.npz',**{f'site_{i}':a for i,a in enumerate(psi.arrays)})
            files.write(folder/'mps_metadata.json',{'shape':'lrp','L':size*size*2,
                'note':'Open-boundary Quimb arrays; use array axis shape from psi.shape',
                'tensor_inds':[list(t.inds) for t in psi.tensors]})
            print(json.dumps({'profile_complete':folder.name,'kernel_seconds':result['kernel_seconds'],
                'number_error':result['number_error'],'max_bond':result['max_bond_observed']}),flush=True)
        except (TimeoutError,MemoryError) as exc:
            files.write(folder/'INCOMPLETE.json',{'status':'INCOMPLETE','error_type':type(exc).__name__,
                'elapsed_seconds':time.perf_counter()-start,'no_final_estimate':True})
            raise

def run_profile(out,size,chi,threads):
    folder=out/f'{size}x{size}_chi{chi}_threads{threads}'
    env=dict(os.environ)
    for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMBA_NUM_THREADS']:
        env[key]=str(threads)
    env['CUDA_VISIBLE_DEVICES']=''
    command=[sys.executable,'-B',str(Path(__file__)),'worker','--output',str(out),
        '--size',str(size),'--chi',str(chi),'--threads',str(threads)]
    tick=time.perf_counter()
    try: process=subprocess.run(command,env=env,timeout=(210 if size==6 else 150),check=False)
    except subprocess.TimeoutExpired:
        folder.mkdir(exist_ok=True)
        files.write(folder/'PROCESS_TIMEOUT.json',{'status':'PROCESS_TIMEOUT','wall_seconds':time.perf_counter()-tick,
            'only_this_owned_worker_terminated':True,'no_final_estimate':True})
        return False
    files.write(folder/'process_timing.json',{'returncode':process.returncode,'cold_worker_seconds':time.perf_counter()-tick,
        'includes_imports':True,'includes_Windows_WSL_launcher':False})
    return process.returncode==0 and (folder/'result.json').exists()

def driver(out):
    if out.exists(): raise FileExistsError('Refuse overwrite')
    out.mkdir(parents=True); (out/'source_snapshot').mkdir()
    inputs=[ROOT/n for n in SOURCES]+[REFERENCE]
    for name in SOURCES: shutil.copyfile(ROOT/name,out/'source_snapshot'/name)
    plan={'schema':'full6x6-mps-bounded-v1','config':asdict(cfg_for(6)),
        'host_cpu':'AMD Ryzen 5 3500U','host_physical_cores':4,'host_logical_threads':8,
        'host_ram_bytes':14903533568,'wsl_cpus':os.cpu_count(),'affinity':sorted(os.sched_getaffinity(0)),
        'wsl_ram_bytes':psutil.virtual_memory().total,'python':platform.python_version(),
        'quimb':quimb.__version__,'numpy':np.__version__,'main_threads':3,'main_chi':[8,16,32],
        'three_by_three_validation_chi':[16,32,64],'limits_seconds':{'kernel6x6':180,'worker6x6':210,'kernel3x3':120},
        'no_qpu_seconds':0,'input_sha256':{str(p.relative_to(ROOT)):files.digest(p) for p in inputs}}
    files.write(out/'plan.json',plan)
    log=io.StringIO()
    with threadpool_limits(limits=3):
        tests=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('test_benchmark_fermionic_6x6_mps'))
    (out/'unit_tests.txt').write_text(log.getvalue(),encoding='utf-8')
    if not tests.wasSuccessful(): raise AssertionError(log.getvalue())
    print(json.dumps({'unit_tests_pass':tests.testsRun,'stage':'3x3_exact_validation_then_6x6'}),flush=True)
    validation=[run_profile(out,3,chi,3) for chi in [16,32,64]]
    if not all(validation):
        files.write(out/'STOPPED.json',{'reason':'3x3 validation incomplete','no_hardware':True}); return
    success=True
    for chi in [8,16,32]:
        success=run_profile(out,6,chi,3)
        if not success: break
    if success: run_profile(out,6,32,1)
    summarize(out)

def summarize(out):
    verify_plan(out)
    results=[]
    for folder in sorted(out.glob('*x*_chi*_threads*')):
        if not (folder/'result.json').exists(): continue
        row=files.read(folder/'result.json')
        row['profile']=folder.name; row['process_timing']=files.read(folder/'process_timing.json')
        results.append(row)
    main=[next((r for r in results if r['profile']==f'6x6_chi{chi}_threads3'),None) for chi in [8,16,32]]
    deltas=[]
    for lo,hi in zip(main,main[1:]):
        if lo is None or hi is None: continue
        d=np.array(hi['physical_means'])-np.array(lo['physical_means'])
        rmse=np.sqrt(np.mean(d*d,axis=0)); maximum=float(np.max(np.abs(d[:,1])))
        deltas.append({'from_chi':lo['chi'],'to_chi':hi['chi'],'rmse_charge_spin_doublon':rmse.tolist(),
            'max_spin_difference':maximum,'screen_pass':bool(np.all(rmse<=.01) and maximum<=.03 and abs(hi['number_error'])<=.01)})
    gate=bool(len(deltas)==2 and all(x['screen_pass'] for x in deltas))
    summary={'status':'BENCHMARK_SCREEN_COMPLETE','results':results,'adjacent_chi_differences':deltas,
        'heuristic_stability_screen_pass':gate,'certified_6x6_error_bound':False,'no_qpu_seconds':0,
        'not_optimized_all8_host_threads':True,'no_6x6_hardware_comparison_yet':True}
    files.write(out/'summary.json',summary)
    lines=['# Klassieke volledige 6x6-MPS-benchmark','',
        'Volledige fermionische t-t\'-U-route, T=0,4 en twee netwerkstappen. Geen QPU-run.',
        'Ryzen 5 3500U: 4 cores/8 threads; de bestaande WSL-omgeving ziet 3 CPU\'s.',
        'Tijd omvat initialisatie, evolutie en lokale observabelen. Cold-worker tijd omvat ook imports.','',
        '| Grootte | chi | Threads | Rekenkern (s) | Cold worker (s) | N-afwijking |',
        '|---|---:|---:|---:|---:|---:|']
    for x in results:
        lines.append(f"| {x['config']['lx']}x{x['config']['ly']} | {x['chi']} | {x['threads']} | {x['kernel_seconds']:.3f} | {x['process_timing']['cold_worker_seconds']:.3f} | {x['number_error']:.5g} |")
    lines+=['','## Convergentie','',json.dumps(deltas,indent=2),
        '',f'Heuristische stabiliteitsscreen geslaagd: {gate}. Geen gecertificeerde foutgrens.',
        'Een timeout is geen bewijs dat alle klassieke methoden falen.',
        'De 3-QPU-secondenmeting betrof3x3 en is geen6x6-snelheidsvergelijking.',
        'Een lokale snelheidsclaim vereist dezelfde6x6-taak, nauwkeurigheid en expliciete timingdefinitie.','']
    (out/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    files.write(out/'sha256.json',{str(p.relative_to(out)):files.digest(p) for p in out.rglob('*') if p.is_file()})
    print(json.dumps({'profiles_complete':len(results),'stability_screen':gate,'deltas':deltas}),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['run','worker','summarize'])
    parser.add_argument('--output',type=Path,default=OUT)
    parser.add_argument('--size',type=int,choices=[3,6]); parser.add_argument('--chi',type=int)
    parser.add_argument('--threads',type=int,choices=[1,3],default=3)
    args=parser.parse_args(); out=args.output.resolve()
    if args.stage=='run': driver(out)
    elif args.stage=='worker': worker(out,args.size,args.chi,args.threads)
    else: summarize(out)
