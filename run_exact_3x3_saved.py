"""Recompute the saved 3x3 Hubbard reference offline; never contact a QPU."""
from __future__ import annotations
import argparse, datetime, gzip, hashlib, json, os, platform, subprocess, sys, time
from dataclasses import asdict, replace
from pathlib import Path

ROOT=Path(__file__).resolve().parent
PILOT=ROOT/'results_cuprate_2d/fermionic_pilot_3x3_2026-09-05'
def save(path,value):
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def worker(out):
    started=time.perf_counter()
    import resource
    import numpy as np
    import scipy
    from scipy.linalg import expm
    from scipy.sparse import diags
    from scipy.sparse.linalg import expm_multiply
    from scipy.integrate import solve_ivp
    from threadpoolctl import threadpool_limits, threadpool_info
    from qiskit import qpy, transpile
    import qiskit
    from qiskit_aer import AerSimulator
    from cuprate_2d_hubbard_pipeline import Cuprate2DConfig, initial_site_rows, validate_config
    from cuprate_2d_exact_sector_baseline import sector_basis, build_hamiltonian, initial_state_vector, MODEL_FULL
    from validate_cuprate_2d_fermionic_dynamics import independent_hamiltonian
    imported=time.perf_counter()-started
    checks=[]; timings={'imports_seconds':imported}
    def check(name,value,tolerance):
        row=dict(check=name,value=float(value),tolerance=tolerance,passed=bool(np.isfinite(value) and value<=tolerance))
        checks.append(row)
        if not row['passed']:
            save(out/'checks.json',checks); raise AssertionError(row)
    def sparse_max(m): return float(np.max(np.abs(m.data))) if m.nnz else 0.0
    cfg=Cuprate2DConfig(**json.loads((PILOT/'config.json').read_text()))
    validate_config(cfg)
    assert (cfg.lx,cfg.ly,cfg.holes,cfg.hopping_t,cfg.t_prime,cfg.interaction_u,cfg.total_time)==(3,3,1,1.0,-0.25,8.0,0.2)
    frozen=json.loads((PILOT/'frozen_inputs_sha256.json').read_text())
    used=['config.json','logical_circuit.qpy','exact_hamiltonian_observables.json','exact_circuit_observables.json']
    for name in used: assert digest(PILOT/name)==frozen[name],('Historical input changed',name)
    sources=[Path(__file__),ROOT/'cuprate_2d_exact_sector_baseline.py',ROOT/'cuprate_2d_hubbard_pipeline.py',ROOT/'validate_cuprate_2d_fermionic_dynamics.py']+[PILOT/name for name in used]
    save(out/'source_sha256.json',{str(p.relative_to(ROOT)):digest(p) for p in sources})
    save(out/'config.json',dict(original_pilot_config=asdict(cfg),times=[0.0,0.1,0.2,0.4],shots_not_used=True,units='hbar=1; energies in t, model time in hbar/t',spin_convention='spin_z = n_up - n_down = 2 physical Sz',boundary='open',qpu_calls=0))
    with threadpool_limits(limits=1):
        t0=time.perf_counter(); basis,index,nup,ndn=sector_basis(cfg); timings['basis_setup_seconds']=time.perf_counter()-t0
        assert (len(basis),nup,ndn)==(15876,4,4)
        initial=initial_site_rows(cfg); assert [r['site'] for r in initial if r['hole']]==[4]
        t0=time.perf_counter(); h,hmeta=build_hamiltonian(cfg,MODEL_FULL); timings['hamiltonian_build_seconds']=time.perf_counter()-t0
        h.eliminate_zeros(); psi0=initial_state_vector(cfg,index)
        check('Hamiltonian_Hermitian',sparse_max(h-h.conj().T),1e-13)
        t0=time.perf_counter(); oracle=independent_hamiltonian(cfg,basis); timings['independent_hamiltonian_check_seconds']=time.perf_counter()-t0
        check('independent_Fock_Hamiltonian_agreement',sparse_max(h-oracle),1e-13)
        t0=time.perf_counter()
        occupied=((np.array(basis,dtype=np.int64)[:,None]>>np.arange(18))&1).astype(float)
        up=occupied[:,::2]; down=occupied[:,1::2]; doubles=up*down
        check('basis_fixed_N_up',np.max(np.abs(up.sum(axis=1)-4)),0)
        check('basis_fixed_N_down',np.max(np.abs(down.sum(axis=1)-4)),0)
        timings['observable_setup_seconds']=time.perf_counter()-t0
        def observe(psi):
            # Do not renormalise away numerical norm error before checking it.
            prob=np.abs(psi)**2; u=prob@up; d=prob@down; doublon=prob@doubles
            rows=[dict(site=i,x=i%3,y=i//3,n_up=float(u[i]),n_down=float(d[i]),charge=float(u[i]+d[i]),spin_z=float(u[i]-d[i]),double_occupancy=float(doublon[i]),p00=float(1-u[i]-d[i]+doublon[i]),p10=float(u[i]-doublon[i]),p01=float(d[i]-doublon[i]),p11=float(doublon[i])) for i in range(9)]
            summary=dict(norm=float(np.vdot(psi,psi).real),N_up=float(u.sum()),N_down=float(d.sum()),N=float((u+d).sum()),total_spin=float((u-d).sum()),mean_double_occupancy=float(doublon.mean()),mean_abs_spin=float(np.abs(u-d).mean()),spin_profile_rms=float(np.sqrt(np.mean((u-d)**2))),energy=float(np.vdot(psi,h@psi).real))
            return rows,summary
        states={'H_T0.0':psi0}; outputs={}; evolution_timings={}; initial_energy=float(np.vdot(psi0,h@psi0).real)
        for T in [0.0,0.1,0.2,0.4]:
            key=f'{T:.1f}'; samples=[]; observable_samples=[]
            for repeat in range(1 if T==0 else 5):
                t0=time.perf_counter(); psi=psi0.copy() if T==0 else expm_multiply(-1j*T*h,psi0); evolution=time.perf_counter()-t0
                t0=time.perf_counter(); rows,summary=observe(psi); elapsed_obs=time.perf_counter()-t0
                samples.append(evolution); observable_samples.append(elapsed_obs)
            states['H_T'+key]=psi.copy(); outputs[key]=dict(time=T,kind='exact_full_Hamiltonian',sites=rows,summary=summary)
            evolution_timings[key]=dict(repetitions=len(samples),evolution_seconds=samples,evolution_median_seconds=float(np.median(samples)),observables_seconds=observable_samples,evolution_plus_observables_median_seconds=float(np.median(np.array(samples)+observable_samples)))
            check('norm_T'+key,abs(summary['norm']-1),1e-11)
            for name,expected in [('N_up',4),('N_down',4),('N',8),('total_spin',0)]: check(name+'_T'+key,abs(summary[name]-expected),1e-10)
            check('energy_conservation_T'+key,abs(summary['energy']-initial_energy),1e-10)
            probabilities=np.array([[r[k] for k in ['p00','p10','p01','p11']] for r in rows])
            check('local_probability_bounds_T'+key,max(0,-float(probabilities.min()),float(probabilities.max())-1),1e-11)
            for name in ['charge','spin_z','double_occupancy']:
                for group,sites in [('corners',[0,2,6,8]),('edges',[1,3,5,7])]: check('D4_'+name+'_'+group+'_T'+key,float(np.ptp([rows[s][name] for s in sites])),1e-11)
            print(json.dumps(dict(event='exact_H_ready',T=T,summary=summary,evolution_median_seconds=evolution_timings[key]['evolution_median_seconds'])),flush=True)
        timings['exact_evolution']=evolution_timings
        old=json.loads((PILOT/'exact_hamiltonian_observables.json').read_text())
        check('saved_pilot_T02_observable_reproduction',max(abs(a[k]-b[k]) for a,b in zip(outputs['0.2']['sites'],old) for k in ['charge','spin_z','double_occupancy']),1e-10)
        t0=time.perf_counter()
        half=expm_multiply(-0.2j*h,psi0); twice=expm_multiply(-0.2j*h,half)
        check('one_step_vs_two_half_exponentials_T04',np.linalg.norm(states['H_T0.4']-twice),1e-10)
        reverse=expm_multiply(0.4j*h,states['H_T0.4'])
        check('time_reversal_T04',np.linalg.norm(reverse-psi0),1e-10)
        ode=solve_ivp(lambda t,y:-1j*(h@y),(0,0.4),psi0,method='DOP853',rtol=2e-11,atol=2e-13,t_eval=[0.4])
        assert ode.success
        check('independent_DOP853_vs_exponential_T04',np.linalg.norm(ode.y[:,-1]-states['H_T0.4']),1e-8)
        timings['exponential_and_ODE_crosschecks_seconds']=time.perf_counter()-t0
        t0=time.perf_counter(); h0=h-diags(cfg.interaction_u*doubles.sum(axis=1)); psi_u0=expm_multiply(-0.4j*h0,psi0)
        K=np.zeros((9,9))
        for a in range(9):
            for b in range(a+1,9):
                dx,dy=abs(a%3-b%3),abs(a//3-b//3)
                value=-1.0 if dx+dy==1 else (0.25 if dx==dy==1 else 0.0)
                K[a,b]=K[b,a]=value
        V=expm(-0.4j*K); u0=np.real(np.diag(V@np.diag([r['n_up_initial'] for r in initial])@V.conj().T)); d0=np.real(np.diag(V@np.diag([r['n_down_initial'] for r in initial])@V.conj().T))
        u0_rows,_=observe(psi_u0)
        check('U0_sparse_vs_9x9_Gaussian_charge_spin_doublon',max(max(abs(r['n_up']-u0[i]),abs(r['n_down']-d0[i]),abs(r['double_occupancy']-u0[i]*d0[i])) for i,r in enumerate(u0_rows)),1e-10)
        timings['U0_independent_control_seconds']=time.perf_counter()-t0
        # Execute the frozen local circuit, not any submit/prepare-provider path.
        t0=time.perf_counter()
        with (PILOT/'logical_circuit.qpy').open('rb') as stream: circuit=qpy.load(stream)[0]
        assert circuit.num_qubits==18 and circuit.count_ops().get('measure',0)==0
        simulator=AerSimulator(method='statevector',precision='double',max_parallel_threads=1,enable_truncation=False)
        circuit.save_statevector(); compiled=transpile(circuit,backend=simulator,optimization_level=0,seed_transpiler=9)
        answer=simulator.run(compiled,shots=1).result(); assert answer.success
        dense=np.asarray(answer.get_statevector(),dtype=complex); psi_c=dense[np.array(basis)]
        check('exact_circuit_norm',abs(np.vdot(dense,dense).real-1),1e-10)
        check('exact_circuit_sector_leakage',abs(np.vdot(dense,dense).real-np.vdot(psi_c,psi_c).real),1e-10)
        c_rows,c_summary=observe(psi_c); old_c=json.loads((PILOT/'exact_circuit_observables.json').read_text())
        check('saved_pilot_circuit_observable_reproduction',max(abs(a[k]-b[k]) for a,b in zip(c_rows,old_c) for k in ['charge','spin_z','double_occupancy']),1e-10)
        states['circuit_T0.2_steps2']=psi_c.copy(); timings['frozen_circuit_load_transpile_simulate_observe_seconds']=time.perf_counter()-t0
        comparison={k:dict(rms=float(np.sqrt(np.mean([(a[k]-b[k])**2 for a,b in zip(c_rows,outputs['0.2']['sites'])]))),max_abs=float(max(abs(a[k]-b[k]) for a,b in zip(c_rows,outputs['0.2']['sites'])))) for k in ['charge','spin_z','double_occupancy']}
        outputs['circuit_T0.2_steps2']=dict(time=0.2,kind='exact_finite_circuit_not_exact_Hamiltonian',sites=c_rows,summary=c_summary,trotter_bias_vs_exact_H=comparison)
        environment=dict(python=sys.version,numpy=np.__version__,scipy=scipy.__version__,qiskit=qiskit.__version__,platform=platform.platform(),threadpools=threadpool_info(),peak_rss_bytes=int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024,performance_scope='one thread; no claim that the whole machine was isolated')
    save(out/'observables.json',outputs); save(out/'checks.json',checks)
    state_payload=dict(basis=basis,ordering='row-major; up=2*site, down=2*site+1; little-endian occupied bits',states={k:dict(real=v.real.tolist(),imag=v.imag.tolist()) for k,v in states.items()})
    with gzip.open(out/'state_vectors.json.gz','wt',encoding='utf-8') as handle: json.dump(state_payload,handle,allow_nan=False,separators=(',',':'))
    with gzip.open(out/'state_vectors.json.gz','rt',encoding='utf-8') as handle: restored=json.load(handle)
    for key,value in states.items(): assert np.array_equal(np.array(restored['states'][key]['real'])+1j*np.array(restored['states'][key]['imag']),value)
    timings['worker_including_imports_checks_and_state_storage_seconds']=time.perf_counter()-started
    summary=dict(status='COMPLETE',calculation='3x3 exact full t-t-prime-U Hubbard evolution in the complete fixed sector',exact_meaning='No MPS truncation, no Trotter approximation for H evolution, no shots; floating-point exponential evaluated numerically and cross-checked; not a symbolic closed-form solution',basis_dimension=len(basis),n_up=nup,n_down=ndn,hamiltonian_nnz=int(h.nnz),times=[0.0,0.1,0.2,0.4],timings=timings,environment=environment,checks_passed=len(checks),checks_failed=0,ode_function_evaluations=ode.nfev,full_state_roundtrip_exact=True,qpu_seconds_used=0,no_provider_calls=True,headline_results={k:outputs[k]['summary'] for k in ['0.1','0.2','0.4']})
    save(out/'summary.json',summary)
    lines=['# Exacte 3x3 Hubbard-berekening','', 'Opnieuw lokaal uitgerekend; geen QPU gebruikt. De oude resultaten zijn niet overschreven.','',
           'Model: 3x3 open, 18 fermionmodi, N_up=N_down=4; een gat op middensite 4. t=1, t_prime=-0.25, U=8, mu=0. Modeltijd in hbar/t.',
           '', 'De volledige vaste sector telt C(9,4)^2 = 15.876 toestanden. We berekenen psi(T)=exp(-i H T) psi(0), zonder MPS-truncatie of Trotterbenadering. Exact betekent hier numeriek exact binnen de gecontroleerde drijvende-kommaprecisie, niet een symbolische formule.','',
           '## Waarden en gemeten tijden','', '| Modeltijd | N | Gemiddeld D/site | Spinprofiel-RMS | Evolutiekern, mediaan 5x (s) |','|---|---:|---:|---:|---:|']
    for key in ['0.1','0.2','0.4']:
        r=outputs[key]['summary']; lines.append(f"| {key} | {r['N']:.12f} | {r['mean_double_occupancy']:.12f} | {r['spin_profile_rms']:.12f} | {evolution_timings[key]['evolution_median_seconds']:.6f} |")
    lines+=['',f"Hamiltoniaan opbouwen: {timings['hamiltonian_build_seconds']:.6f} s; basis: {timings['basis_setup_seconds']:.6f} s. De evolutietijden hierboven sluiten opbouw, imports en onafhankelijke controles uit.",'', 'T=0.2 reproduceert de eerdere volledige fermionpilot. T=0.4 is een extra exacte kleine-roosterreferentie op de modeltijd van de latere 6x6-studie; het is niet dezelfde roosteropgave.','']
    for key in ['0.2','0.4']:
        lines += [f'## Lokale waarden bij T={key}','', '| Site (x,y) | Lading | Spin n_up-n_down | Doublon |','|---|---:|---:|---:|']
        for row in outputs[key]['sites']: lines.append(f"| {row['site']} ({row['x']},{row['y']}) | {row['charge']:.10f} | {row['spin_z']:.10f} | {row['double_occupancy']:.10f} |")
        lines.append('')
    lines += ['## Exact circuit is een andere referentie','', 'Het bewaarde 18-qubit circuit is ook zonder ruis opnieuw doorgerekend. Zijn eindige productformule benadert de continue Hamiltoniaandynamica. Het verschil hieronder is Trotterbias, geen hardwarefout.','',json.dumps(comparison,indent=2),'','## Opgeslagen bestanden','', '- observables.json: alle lokale waarden en samenvattingen, inclusief T=0 en T=0.1.','- state_vectors.json.gz: sectorbasis en volledige complexe toestanden, verliesloos gecontroleerd.','- config.json, source_sha256.json, summary.json: instellingen, herkomst en afzonderlijke tijdmetingen.','- checks.json en VERIFICATION.md: onafhankelijke numerieke controles.','', 'Deze 3x3-opgave is klassiek exact oplosbaar; dit is geen quantum-advantage-bewijs. De 6x6-resultaten worden hierdoor niet automatisch gevalideerd.']
    (out/'RESULTAAT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    verification=['# Numerical verification (executed)','',f'All {len(checks)} checks passed. No provider calls or hardware jobs.','',
      'Independent numerical oracle: scipy.integrate.solve_ivp(method="DOP853", rtol=2e-11, atol=2e-13) integrates dpsi/dT=-i H psi up to T=0.4 and is compared with scipy.sparse.linalg.expm_multiply(-0.4j*H, psi0). A separate 9x9 dense matrix exponential checks the exactly soluble U=0 limit. Two independently enumerated fermionic Hamiltonians are compared elementwise.','',
      'Units: every H term has energy units t; H*T/hbar is dimensionless. Spin uses n_up-n_down, not physical Sz. Conservation checks use absolute energy differences because initial energy is zero. Square-lattice orbit symmetry follows from the centre hole, checkerboard spin state and open isotropic couplings.','',
      'Reproduction command (choose a fresh output directory):','', '```bash', 'python -B run_exact_3x3_saved.py --outdir results_cuprate_2d/exact_3x3_recomputed_NEW', '```','', 'Executed numerical output:','', '```json',json.dumps(checks,indent=2),'```']
    (out/'VERIFICATION.md').write_text('\n'.join(verification)+'\n',encoding='utf-8')
    print(json.dumps(dict(event='complete',checks_passed=len(checks),timings=timings,results=summary['headline_results'])),flush=True)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--outdir',type=Path,required=True); ap.add_argument('--worker',action='store_true'); args=ap.parse_args()
    out=args.outdir.resolve()
    if args.worker: worker(out); return
    if out.exists(): raise FileExistsError('Use a fresh output directory; preserve all previous runs.')
    if ROOT not in out.parents: raise ValueError('Output must stay inside the Nighthawk project.')
    out.mkdir(parents=True)
    save(out/'attempt.json',dict(started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='STARTED',hardware_authorized=False,timeout_seconds=180,source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()))
    env=dict(os.environ); env.update({k:'1' for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS']}); env['PYTHONDONTWRITEBYTECODE']='1'
    t0=time.perf_counter()
    try: run=subprocess.run([sys.executable,'-B',str(Path(__file__).resolve()),'--outdir',str(out),'--worker'],cwd=ROOT,env=env,timeout=180)
    except subprocess.TimeoutExpired:
        save(out/'process.json',dict(status='TIMED_OUT',seconds=time.perf_counter()-t0,only_owned_child_stopped=True)); raise
    elapsed=time.perf_counter()-t0
    save(out/'process.json',dict(status='COMPLETE' if run.returncode==0 else 'FAILED',returncode=run.returncode,cold_worker_and_full_verification_wall_seconds=elapsed,includes_imports_and_all_checks=True,includes_Windows_WSL_launcher=False))
    if run.returncode: raise SystemExit(run.returncode)
    with (out/'RESULTAAT.md').open('a',encoding='utf-8') as f: f.write(f'\nHele verse Python-worker inclusief imports, drie tijdpunten, herhalingen, alle controles en opslag: {elapsed:.6f} s; exclusief de Windows/WSL-launcher. Dit is niet de korte evolutiekern alleen.\n')
    save(out/'artifact_sha256.json',{p.name:digest(p) for p in out.iterdir() if p.is_file()})
    print(json.dumps(dict(status='COMPLETE',output=str(out),cold_worker_and_full_verification_wall_seconds=elapsed,qpu_seconds_used=0)),flush=True)

if __name__=='__main__': main()
