"""Exact rational time-series coefficients for the saved full 3x3 Hubbard model.

No fitting, numerical eigensolver or time propagator is used to construct or
evaluate these formulas. The saved numerical solution is read only afterwards.
"""
from __future__ import annotations
import argparse, datetime, hashlib, json, math, os, subprocess, sys, time
from fractions import Fraction as F
from pathlib import Path

ROOT=Path(__file__).resolve().parent
REFERENCE=ROOT/'results_cuprate_2d/exact_3x3_recomputed_2026-09-07_v1'
def save(path,data): path.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def integer_powers(rows,initial,degree,progress=False):
    values=[initial]
    for k in range(1,degree+1):
        previous=values[-1]
        values.append([sum(c*previous[j] for j,c in row) for row in rows])
        if progress and k%10==0: print(json.dumps(dict(event='integer_power',order=k,largest_integer_bits=max(abs(v).bit_length() for v in values[-1]))),flush=True)
    return values
def observable_series(powers,labels,weights,degree,progress=False,callback=None):
    series={name:[] for name in weights}; categories=len(next(iter(weights.values())))
    for m in range(degree//2+1):
        k=2*m; accumulated=[0]*categories
        for a in range(m+1):
            b=k-a; buckets=[0]*categories
            for x,y,label in zip(powers[a],powers[b],labels): buckets[label]+=x*y
            multiplier=(-1 if a%2 else 1)*math.comb(k,a)*(1 if a==b else 2)
            for label,value in enumerate(buckets): accumulated[label]+=multiplier*value
        denominator=4**k*math.factorial(k); sign=-1 if m%2 else 1
        for name,ws in weights.items(): series[name].append(F(sign*sum(w*v for w,v in zip(ws,accumulated)),denominator))
        if callback: callback(series,m)
        if progress and k%10==0: print(json.dumps(dict(event='exact_coefficient',degree=k,mean_D=str((4*series['D_corner'][-1]+4*series['D_edge'][-1]+series['D_centre'][-1])/9))),flush=True)
    return series
def evaluate_series(coefficients,T,degree=None):
    selected=coefficients if degree is None else coefficients[:degree//2+1]
    value=F(0); z=T*T
    for c in reversed(selected): value=value*z+c
    return value
def even_tail_bound(B,T,degree,operator_norm=1):
    x=2*B*abs(T); r=degree+2; ratio=x*x/F((r+1)*(r+2))
    if ratio>=1: return None
    return operator_norm*x**r/F(math.factorial(r))/(1-ratio)

def self_tests():
    import sympy as sp
    T=sp.symbols('T',real=True)
    base=[[(1,4)],[(0,4)]]; init=[1,0]
    weights={'probability':[0,1],'norm':[1,1]}
    coefficients=observable_series(integer_powers(base,init,12),[0,1],weights,12)
    exact=sp.series(sp.sin(T)**2,T,0,14).removeO().expand()
    for m,c in enumerate(coefficients['probability']): assert sp.Rational(c.numerator,c.denominator)==exact.coeff(T,2*m)
    assert coefficients['norm']==[F(1)]+[F(0)]*6
    shifted=[[(0,-64),(1,4)],[(0,4),(1,-64)]]
    assert observable_series(integer_powers(shifted,init,12),[0,1],weights,12)==coefficients
    diagonal=[[(0,12)],[(1,-20)]]
    constants=observable_series(integer_powers(diagonal,init,12),[0,1],{'O':[2,-1]},12)
    assert constants['O']==[F(2)]+[F(0)]*6
    return dict(sin_squared_exact_SymPy_series=True,scalar_shift_invariance=True,diagonal_H_constant_observable=True,normalisation_identity=True)

def worker(out):
    started=time.perf_counter(); tests=self_tests()
    import numpy as np
    import sympy as sp
    import resource
    from threadpoolctl import threadpool_limits
    from cuprate_2d_hubbard_pipeline import Cuprate2DConfig
    from cuprate_2d_exact_sector_baseline import sector_basis, initial_masks, full_mask_from_spin_masks, build_hamiltonian, MODEL_FULL
    cfg=Cuprate2DConfig(**json.loads((ROOT/'results_cuprate_2d/fermionic_pilot_3x3_2026-09-05/config.json').read_text()))
    assert (cfg.lx,cfg.ly,cfg.holes,cfg.hopping_t,cfg.t_prime,cfg.interaction_u,cfg.chemical_potential)==(3,3,1,1.0,-0.25,8.0,0.0)
    timings={'imports_and_symbolic_unit_tests_seconds':time.perf_counter()-started}
    with threadpool_limits(limits=1):
        mark=time.perf_counter(); basis,index,nup,ndown=sector_basis(cfg); h,_=build_hamiltonian(cfg,MODEL_FULL)
        assert (len(basis),nup,ndown)==(15876,4,4)
        scaled=h*4
        assert np.all(scaled.data.imag==0) and np.array_equal(scaled.data.real,scaled.data.real.astype(np.int64))
        A=scaled.real.astype(np.int64); A.setdiag(A.diagonal()-64); A.eliminate_zeros()
        difference=A-A.T; assert difference.nnz==0
        rows=[[(int(j),int(c)) for j,c in zip(A.indices[A.indptr[i]:A.indptr[i+1]],A.data[A.indptr[i]:A.indptr[i+1]])] for i in range(len(basis))]
        L=max(sum(abs(c) for _,c in row) for row in rows); B=F(L,4); Tmax=F(2,5)
        degree=next(n for n in range(12,129,2) if even_tail_bound(B,Tmax,n,2) is not None and even_tail_bound(B,Tmax,n,2)<F(1,10**12))
        initial=[0]*len(basis); up,down=initial_masks(cfg); initial[index[full_mask_from_spin_masks(cfg,up,down)]]=1
        labels=[((s>>0)&3)+4*((s>>2)&3)+16*((s>>8)&3) for s in basis]
        weights={'norm':[1]*64}
        for pos,group in enumerate(['corner','edge','centre']):
            states=[(label>>(2*pos))&3 for label in range(64)]
            weights['C_'+group]=[(s&1)+((s>>1)&1) for s in states]
            weights['S_'+group]=[(s&1)-((s>>1)&1) for s in states]
            weights['D_'+group]=[int(s==3) for s in states]
        timings['Hamiltonian_and_integer_setup_seconds']=time.perf_counter()-mark
        save(out/'plan.json',dict(dimension=len(basis),degree=degree,energy_shift=16,integer_scale=4,row_sum_bound_L=L,H_shifted_norm_bound=str(B),T_max=str(Tmax),uniform_charge_remainder_bound=str(even_tail_bound(B,Tmax,degree,2)),units='T in hbar/t, t=1; U=8, t_prime=-1/4',constructed_without_fitting=True))
        print(json.dumps(dict(event='symbolic_plan',degree=degree,B=str(B),max_charge_error_bound=float(even_tail_bound(B,Tmax,degree,2)))),flush=True)
        mark=time.perf_counter(); powers=integer_powers(rows,initial,degree,True); timings['exact_integer_powers_seconds']=time.perf_counter()-mark
        identities=[]
        def invariants(s,m):
            assert s['norm'][m]==(1 if m==0 else 0)
            assert 4*s['C_corner'][m]+4*s['C_edge'][m]+s['C_centre'][m]==(8 if m==0 else 0)
            assert 4*s['S_corner'][m]+4*s['S_edge'][m]+s['S_centre'][m]==0
            if m==0:
                assert [s['C_'+g][0] for g in ['corner','edge','centre']]==[1,1,0]
                assert [s['S_'+g][0] for g in ['corner','edge','centre']]==[1,-1,0]
                assert all(s['D_'+g][0]==0 for g in ['corner','edge','centre'])
            if m==1:
                assert (4*s['D_corner'][1]+4*s['D_edge'][1]+s['D_centre'][1])/9==F(16,9)
                assert s['C_centre'][1]==F(17,4) and s['S_centre'][1]==F(-15,4)
                assert s['C_corner'][1]==F(-1,16) and s['C_edge'][1]==-1
            identities.append(dict(degree=2*m,norm_identity=True,N_identity=True,total_spin_identity=True))
        mark=time.perf_counter(); series=observable_series(powers,labels,weights,degree,True,invariants); timings['exact_observable_coefficients_seconds']=time.perf_counter()-mark
    del powers
    series['mean_D']=[(4*a+4*b+c)/9 for a,b,c in zip(series['D_corner'],series['D_edge'],series['D_centre'])]
    # Save exact formulas BEFORE loading any previous numerical values.
    save(out/'coefficients.json',dict(variable='T',degree=degree,only_even_powers=True,parameter_scope='Fixed 3x3 U=8 t=1 t_prime=-1/4 instance; T remains symbolic',coefficients={name:[str(c) for c in values] for name,values in series.items()}))
    T=sp.symbols('T',real=True)
    expressions={name:sum(sp.Rational(c.numerator,c.denominator)*T**(2*m) for m,c in enumerate(cs)) for name,cs in series.items()}
    (out/'full_formulas.txt').write_text('\n\n'.join(name+'(T) = '+str(sp.horner(expr,T)) for name,expr in expressions.items())+'\n\nN(T) = 8\nTotal_spin(T) = 0\nSpin_RMS(T) = sqrt((4*S_corner(T)**2 + 4*S_edge(T)**2 + S_centre(T)**2)/9)\n',encoding='utf-8')
    (out/'full_formulas.tex').write_text('\n\n'.join('\\['+name.replace('_','\\_')+'(T) = '+sp.latex(expr)+'\\]' for name,expr in expressions.items())+'\n',encoding='utf-8')
    source_names=['run_symbolic_3x3.py','theory/SYMBOLIC_3X3_DERIVATION.md','cuprate_2d_exact_sector_baseline.py','cuprate_2d_hubbard_pipeline.py','results_cuprate_2d/fermionic_pilot_3x3_2026-09-05/config.json']
    save(out/'source_sha256.json',{name:digest(ROOT/name) for name in source_names})
    reference=json.loads((REFERENCE/'observables.json').read_text())
    evaluations=[]; convergence=[]; max_error=0.0; evaluation_times={}
    orbit=['corner','edge','corner','edge','centre','edge','corner','edge','corner']
    for t in [F(1,10),F(1,5),F(2,5)]:
        key=str(float(t)); repeats=[]
        for _ in range(5):
            mark=time.perf_counter(); values={name:evaluate_series(cs,t) for name,cs in series.items()}
            rms_squared=(4*values['S_corner']**2+4*values['S_edge']**2+values['S_centre']**2)/9
            rms=sp.sqrt(sp.Rational(rms_squared.numerator,rms_squared.denominator)).evalf(50)
            repeats.append(time.perf_counter()-mark)
        evaluation_times[key]=dict(samples_seconds=repeats,median_seconds=float(np.median(repeats)))
        rows=[]
        for site,group in enumerate(orbit):
            row=dict(site=site,x=site%3,y=site//3,charge=float(values['C_'+group]),spin_z=float(values['S_'+group]),double_occupancy=float(values['D_'+group]))
            row['max_difference_from_numeric_reference']=max(abs(row[name]-reference[key]['sites'][site][name]) for name in ['charge','spin_z','double_occupancy'])
            max_error=max(max_error,row['max_difference_from_numeric_reference']); rows.append(row)
            C,S,D=row['charge'],row['spin_z'],row['double_occupancy']
            probabilities=[D,(C+S)/2-D,(C-S)/2-D,1-C+D]
            assert min(probabilities)>-1e-10 and max(probabilities)<1+1e-10
        result=dict(T_rational=str(t),time=float(t),sites=rows,N_exact='8',total_spin_exact='0',mean_D_50_digits=str(sp.Rational(values['mean_D'].numerator,values['mean_D'].denominator).evalf(50)),spin_RMS_50_digits=str(rms),uniform_local_charge_error_bound=float(even_tail_bound(B,t,degree,2)),uniform_local_spin_and_doublon_error_bound=float(even_tail_bound(B,t,degree,1)))
        evaluations.append(result)
        for n in sorted(set([4,8,12,20,32,48,64,degree])):
            if n>degree: continue
            estimate=evaluate_series(series['mean_D'],t,n)
            convergence.append(dict(time=float(t),degree=n,mean_D=float(estimate),difference_from_numeric=float(estimate)-reference[key]['summary']['mean_double_occupancy'],rigorous_remainder_bound=None if even_tail_bound(B,t,n) is None else float(even_tail_bound(B,t,n))))
    assert max_error<1e-10,(max_error,'Series did not reproduce the independent numeric reference')
    for result in evaluations:
        old=reference[str(result['time'])]['summary']
        assert abs(float(result['mean_D_50_digits'])-old['mean_double_occupancy'])<1e-10
        assert abs(float(result['spin_RMS_50_digits'])-old['spin_profile_rms'])<1e-10
    save(out/'evaluations.json',evaluations); save(out/'convergence.json',convergence)
    checks=dict(analytic_unit_tests=tests,coefficientwise_identities=identities,first_T2_hopping_count_checks=True,exact_integer_conversion_and_Hermiticity=True,no_fit=True,prior_reference_loaded_after_coefficients_saved=True,max_site_difference_from_numeric_reference=max_error)
    save(out/'verification.json',checks)
    leading={name:sp.latex(sum(sp.Rational(c.numerator,c.denominator)*T**(2*m) for m,c in enumerate(cs[:5]))) for name,cs in series.items() if name!='norm'}
    timings['formula_evaluation']=evaluation_times; timings['worker_total_seconds']=time.perf_counter()-started
    summary=dict(status='COMPLETE',method='Exact rational Taylor coefficients, not a compact closed elementary formula',degree=degree,coefficient_arithmetic='arbitrary-precision integers and exact fractions',uniform_local_charge_error_bound_T_le_04=float(even_tail_bound(B,Tmax,degree,2)),max_difference_from_numeric_reference=max_error,low_order_latex=leading,timings=timings,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,sympy_version=sp.__version__,numerical_propagator_called=False,qpu_seconds_used=0)
    save(out/'summary.json',summary)
    low=sp.latex(sum(sp.Rational(c.numerator,c.denominator)*T**(2*m) for m,c in enumerate(series['mean_D'][:5])))
    lines=['# Symbolische 3x3-formules: dezelfde getallen teruggevonden','', 'De parameters zijn vast: 3x3 open, N_up=N_down=4, middengat, t=1, t_prime=-1/4, U=8. T blijft een symbolische variabele in eenheden hbar/t. Er is niet op de eerder berekende getallen gefit.','', '## Een expliciete formule','', 'De gemiddelde dubbelbezetting begint als:', '', '$$', '\\overline D(T) = '+low+' + O(T^{10}).', '$$', '',f'Dit zijn alleen de eerste termen. Voor de getallen hieronder is de volledige polynoom tot en met T^{degree} gebruikt, met exact rationale coëfficiënten. De oneindige reeks is exact; de eindige polynoom heeft een gecontroleerde afkapfout. De korte formule hierboven mag dus niet zonder meer bij T=0.4 worden afgekapt.','', '## Resultaten','', '| T | D/site uit formule | Spinprofiel-RMS uit formule | Evaluatie, mediaan (s) |','|---|---:|---:|---:|']
    for result in evaluations:
        lines.append(f"| {result['time']} | {float(result['mean_D_50_digits']):.12f} | {float(result['spin_RMS_50_digits']):.12f} | {evaluation_times[str(result['time'])]['median_seconds']:.6f} |")
    lines += ['',f'Grootste verschil over alle 27 lokale observabelen en de drie tijdstippen met de eerdere numerieke referentie: {max_error:.3e}.',f'De rationeel berekende uniforme afkapgrens voor iedere lokale ladingswaarde op |T|<=0.4 is {float(even_tail_bound(B,Tmax,degree,2)):.3e}; voor lokale spin en doublon is de grens de helft. Dit is een grens op de reeksafkap, niet op de oude numerieke referentie.','', 'Door symmetrie zijn de vier hoeken gelijk en de vier randmiddens gelijk. Het centrum is de derde groep. Alle negen sites worden daarmee beschreven, zonder de volledige sector te verkleinen.','', 'Exacte identiteiten op elke berekende orde: N(T)=8, totale spin=0 en norm=1. Spin_RMS is sqrt((4*S_corner^2+4*S_edge^2+S_centre^2)/9).','', '## Wat voor symbolische oplossing is dit?','', 'De coëfficiënten volgen uit machten van de gehele matrix A=4(H-16I). De scalaire verschuiving verandert alleen een globale fase. Geen numerieke eigenwaarden, matrixexponentiële tijdsolver of fitting is gebruikt om de polynomen te bouwen of in te vullen. SymPy controleert de exact oplosbare tweetoestandstest sin(T)^2.','', 'Dit is een expliciete symbolische machtreeks voor het interagerende model, geen korte eindige combinatie van sinussen en cosinussen. Een volledige gesloten elementaire oplossing van het 15.876-dimensionale probleem is hiermee niet gevonden.','', '## Tijd en opslag','',f"Exacte gehele matrixmachten: {timings['exact_integer_powers_seconds']:.3f} s. Coëfficiënten afleiden: {timings['exact_observable_coefficients_seconds']:.3f} s. Hele worker: {timings['worker_total_seconds']:.3f} s. De kleine evaluatietijden in de tabel sluiten deze eenmalige afleiding uit.",'', '- coefficients.json: alle exacte breukcoëfficiënten.','- full_formulas.txt / full_formulas.tex: de volledige expliciete polynomen.','- evaluations.json: alle lokale waarden.','- convergence.json: wat er verandert bij afkappen op lagere orde.','- verification.json / VERIFICATION.md: algebraïsche en numerieke controles.','- theory/SYMBOLIC_3X3_DERIVATION.md: afleiding, eenheden en foutgrens.','', 'Geen QPU gebruikt. Dit resultaat geldt voor deze 3x3-instantie, niet automatisch voor 6x6.']
    (out/'RESULTAAT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (out/'VERIFICATION.md').write_text('# Executed symbolic verification\n\nIndependent CAS oracle: SymPy expands sin(T)^2 and matches every exact coefficient of the two-level test. Scalar shifts leave those coefficients unchanged; a diagonal H gives constant observables.\n\nFor the 3x3 result, exact coefficientwise norm, particle and spin identities hold. Leading coefficients match independently counted one-hop amplitudes. The previous sparse-exponential reference is used only after all rational coefficients have been saved.\n\n```json\n'+json.dumps(checks,indent=2)+'\n```\n\nThe rigorous remainder uses the exact row-sum upper bound for the shifted Hermitian Hamiltonian and an even-series geometric tail. All rational bounds are in plan.json and all lower-order errors in convergence.json.\n',encoding='utf-8')
    print(json.dumps(dict(event='complete',degree=degree,max_error=max_error,remainder_bound=float(even_tail_bound(B,Tmax,degree,2)),leading_mean_D=low,timings=timings)),flush=True)

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--outdir',type=Path); parser.add_argument('--worker',action='store_true'); parser.add_argument('--self-test',action='store_true'); args=parser.parse_args()
    if args.self_test: print(json.dumps(self_tests())); return
    if args.outdir is None: parser.error('--outdir required')
    out=args.outdir.resolve()
    if args.worker: worker(out); return
    if out.exists(): raise FileExistsError('Preserve existing attempts; choose a fresh directory.')
    if ROOT not in out.parents: raise ValueError('Output must stay within this project.')
    out.mkdir(parents=True); save(out/'attempt.json',dict(status='STARTED',started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),timeout_seconds=360,source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()))
    env=dict(os.environ); env.update({k:'1' for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']}); env['PYTHONDONTWRITEBYTECODE']='1'
    start=time.perf_counter()
    try: result=subprocess.run([sys.executable,'-B',str(Path(__file__).resolve()),'--outdir',str(out),'--worker'],cwd=ROOT,env=env,timeout=360)
    except subprocess.TimeoutExpired:
        save(out/'process.json',dict(status='TIMED_OUT',elapsed_seconds=time.perf_counter()-start,only_owned_child_stopped=True)); raise
    save(out/'process.json',dict(status='COMPLETE' if result.returncode==0 else 'FAILED',returncode=result.returncode,elapsed_seconds=time.perf_counter()-start,includes_imports_and_checks=True,includes_Windows_WSL_launcher=False))
    if result.returncode: raise SystemExit(result.returncode)
    save(out/'artifact_sha256.json',{p.name:digest(p) for p in out.iterdir() if p.is_file()})
    print(json.dumps(dict(status='COMPLETE',output=str(out))),flush=True)

if __name__=='__main__': main()
