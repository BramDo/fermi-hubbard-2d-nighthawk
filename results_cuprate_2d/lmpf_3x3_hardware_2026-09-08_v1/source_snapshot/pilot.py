"""Run an immutable offline 2D Hubbard L-MPF pilot. No IBM service exists here."""
from pathlib import Path
import argparse,dataclasses,datetime,io,json,sys,time,unittest,shutil
import importlib.metadata as md
import numpy as np
from qiskit import transpile,qpy
from qiskit.transpiler import CouplingMap
from qiskit.quantum_info import Statevector
from threadpoolctl import threadpool_limits

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from cuprate_2d_hubbard_pipeline import Cuprate2DConfig
from cuprate_2d_fermionic_dynamics import build_fermionic_circuit
from cuprate_2d_exact_sector_baseline import initial_masks
from lmpf_2d.operators import compile_steps,fuse_steps,evolve_dense,evolve_tn,gram_tn,expectation_tn,initial_functional
from lmpf_2d.model import FrozenSurrogate,PILOT_EDGES,native_edges_validate,sample_arm,features,physical_transform,moments,digest
from lmpf_2d.fit import fit_coefficients,linear_zne_weights,richardson_weights

def clean(x):
    if isinstance(x,dict):return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):return [clean(v) for v in x]
    if isinstance(x,np.ndarray):return clean(x.tolist())
    if isinstance(x,np.generic):return clean(x.item())
    if isinstance(x,float) and not np.isfinite(x):return None
    return x
def write(path,obj):Path(path).write_text(json.dumps(clean(obj),indent=2,allow_nan=False)+'\n')

def score_method(weights,means,covariances,sampled,ideal,shots,matrix,offset):
    weights=np.asarray(weights);value=np.sum(weights*means.T,axis=1)
    observed=np.sum(weights*sampled.T,axis=1)
    cov=sum(weights[:,a,None]*weights[None,:,a]*covariances[a]/shots[a] for a in range(len(shots)))
    phy=matrix@value+offset;sample_phy=matrix@observed+offset;reference=matrix@ideal+offset
    physical_cov=matrix@cov@matrix.T;sites=len(phy)//3;families={}
    for k,name in enumerate(['charge','spin','doublon']):
        sl=slice(k*sites,(k+1)*sites);bias=phy[sl]-reference[sl];var=np.diag(physical_cov)[sl]
        families[name]={'model_bias_rmse':float(np.sqrt(np.mean(bias**2))),
            'model_expected_rmse_with_shots':float(np.sqrt(np.mean(bias**2+var))),
            'single_seed_observed_rmse':float(np.sqrt(np.mean((sample_phy[sl]-reference[sl])**2)))}
    return {'pauli_expected':value,'pauli_sampled':observed,'physical_expected':phy,'physical_sampled':sample_phy,
        'physical_shot_standard_errors':np.sqrt(np.maximum(np.diag(physical_cov),0)),
        'families':families,'particle_number_expected':float(phy[:sites].sum()),
        'particle_number_sampled':float(sample_phy[:sites].sum()),
        'particle_number_shot_se':float(np.sqrt(max(physical_cov[:sites,:sites].sum(),0))),
        'physical_ranges_not_clipped':True}

def run(args):
    started=time.monotonic();out=args.output
    if out.exists():raise ValueError('Refusing to overwrite an earlier pilot')
    out.mkdir(parents=True);(out/'source_snapshot').mkdir();(out/'operators').mkdir()
    sources=list((ROOT/'lmpf_2d').glob('*.py'))+[ROOT/'test_lmpf_2d.py',ROOT/'cuprate_2d_fermionic_dynamics.py',ROOT/'cuprate_2d_hubbard_pipeline.py']
    for p in sources:shutil.copyfile(p,out/'source_snapshot'/p.name)
    stream=io.StringIO();suite=unittest.defaultTestLoader.loadTestsFromName('test_lmpf_2d')
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    (out/'tests.txt').write_text(stream.getvalue())
    if not result.wasSuccessful():raise RuntimeError(stream.getvalue())
    profile=FrozenSurrogate();native_edges_validate(profile,PILOT_EDGES)
    cfg=Cuprate2DConfig(lx=2,ly=2,holes=1,hopping_t=1.,t_prime_over_t=-.25,u_over_t=8.,
        chemical_potential=0.,steps=2,dt=args.time/2,boundary_x='open',boundary_y='open',initial_state='stripe_neel',shots=args.shots)
    source=build_fermionic_circuit(cfg,prepare=False)
    edges=list(PILOT_EDGES)
    native=transpile(source,basis_gates=['rz','sx','x','cz'],coupling_map=CouplingMap(edges+[(b,a) for a,b in edges]),
        initial_layout=list(range(8)),optimization_level=3,seed_transpiler=args.seed)
    mapping=native.layout.final_index_layout(filter_ancillas=True)
    up,down=initial_masks(cfg);bits=[((up if q%2==0 else down)>>(q//2))&1 for q in range(8)]
    native_steps=compile_steps(native,profile.rate);steps=fuse_steps(native_steps)
    with (out/'native_dynamics.qpy').open('wb') as f:qpy.dump(native,f)
    plan={'schema':'lmpf-2d-offline-pilot-v1','paper':'https://arxiv.org/html/2609.05024v1',
        'config':dataclasses.asdict(cfg),'initial_bits_physical':bits,'logical_to_final_physical':mapping,
        'tn_edges':edges,'tn_cycles':3,'native_gate_counts':dict(native.count_ops()),'native_depth':native.depth(),
        'exact_classical_channel_blocks':len(steps),'qpu_circuit_not_shortened':True,
        'noise_scales':[1,2,3],'coefficient_sum':1,'clifford_rescaling_used':False,
        'shots_per_lmpf_arm':args.shots,'raw_equal_total_shots':3*args.shots,
        'union_simulated_bitshots':5*args.shots,'qpu_seconds':0,
        'noise':profile.metadata(),'chi_values':args.chi,'loop_size':args.loop_size,
        'max_observables':args.max_observables,'start_observable':args.start_observable,'seed':args.seed,'runtime_cap_seconds':args.budget_seconds,
        'target':'ideal finite circuit, not exact Hamiltonian evolution',
        'regularized_variant_ridge':1/args.shots,'versions':{p:md.version(p) for p in ['qiskit','qiskit-aer','quimb','numpy','scipy']},
        'source_sha256':{str(p.relative_to(ROOT)):digest(p) for p in sources},
        'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    write(out/'plan.json',plan)
    print('PREFLIGHT',json.dumps({'gates':plan['native_gate_counts'],'depth':native.depth(),'qubits':8,'layout':profile.layout}),flush=True)
    indices=np.arange(256);basis_bits=((indices[:,None]>>np.arange(8))&1)
    raw_features=features(basis_bits,mapping);corrected_features=features(basis_bits,mapping,profile.readout)
    p0=Statevector.from_label(''.join(map(str,reversed(bits)))).evolve(native).probabilities()
    ideal=p0@raw_features
    source_p=Statevector.from_label(''.join(map(str,reversed(bits)))).evolve(source).probabilities()
    reference_logical=source_p@features(basis_bits,list(range(8)))
    np.testing.assert_allclose(ideal,reference_logical,atol=1e-10)
    ptrue=[];pobs=[];sampled=[];raw_sampled=[];full_sampled=[];covs=[];means=[];ro_raw_means=[];ro_raw_covs=[]
    for arm,gamma in enumerate([1,2,3]):
        total=args.shots*3 if arm==0 else args.shots
        memory,quantum,observed,text=sample_arm(native,native_steps,bits,profile,gamma,total,args.seed+1000*arm)
        write(out/f'arm_{gamma}_memory.json',{'scale':gamma,'shots':total,'memory':text})
        corr=features(memory,mapping,profile.readout);raw=features(memory,mapping)
        mean,cov=moments(observed,corrected_features);rmean,rcov=moments(observed,raw_features)
        np.testing.assert_allclose(mean,quantum@raw_features,atol=1e-10)
        ptrue.append(quantum);pobs.append(observed);means.append(mean);covs.append(cov)
        ro_raw_means.append(rmean);ro_raw_covs.append(rcov)
        sampled.append(corr[:args.shots].mean(0));raw_sampled.append(raw.mean(0));full_sampled.append(corr.mean(0))
    means=np.array(means);covs=np.array(covs);sampled=np.array(sampled)
    matrix,offset=physical_transform(8)
    ones=np.ones((12,1))
    scores={
        'raw_equal_total_shots':score_method(ones,np.array(ro_raw_means[:1]),np.array(ro_raw_covs[:1]),np.array(raw_sampled[:1]),ideal,[3*args.shots],matrix,offset),
        'readout_equal_total_shots':score_method(ones,means[:1],covs[:1],np.array(full_sampled[:1]),ideal,[3*args.shots],matrix,offset)}
    for name,w in [('zne_linear',linear_zne_weights([1,2,3])),('zne_richardson',richardson_weights([1,2,3]))]:
        scores[name]=score_method(np.tile(w,(12,1)),means,covs,sampled,ideal,[args.shots]*3,matrix,offset)
    coefficient_sets={};classical={chi:np.full(12,np.nan) for chi in args.chi};failures=[]
    def add_coefficient(name,index,fit):
        coefficient_sets.setdefault(name,np.full((12,3),np.nan))[index]=fit.coefficients
    rho=initial_functional(bits).reshape(-1)
    supports=[{mapping[q]:'Z'} for q in range(8)]+[{mapping[2*s]:'Z',mapping[2*s+1]:'Z'} for s in range(4)]
    selection=supports[args.start_observable:args.start_observable+args.max_observables]
    for index,support in enumerate(selection,start=args.start_observable):
        t0=time.monotonic();print('OPERATOR',index,support,flush=True)
        vectors=np.array([evolve_dense(8,support,steps,gamma).reshape(-1) for gamma in [0,1,2,3]])
        f=vectors@vectors.T
        checks=vectors@rho
        np.testing.assert_allclose(checks,np.r_[ideal[index],means[:,index]],atol=1e-8)
        op={'index':index,'support':support,'exact_overlaps':f,'dense_heisenberg_forward_check':checks,'fits':{},'tensor_networks':{}}
        for label,ridge in [('lmpf_exact_overlap_oracle',0),('lmpf_exact_overlap_ridge',1/args.shots)]:
            fit=fit_coefficients(f,ridge=ridge);add_coefficient(label,index,fit);op['fits'][label]=fit.to_dict()
        # Sensitivity diagnostic only; not a hardware uncertainty interval.
        for model_scale in [.7,1.3]:
            wrong=np.array([vectors[0]]+[evolve_dense(8,support,steps,g*model_scale).reshape(-1) for g in [1,2,3]])
            fit=fit_coefficients(wrong@wrong.T)
            label=f'lmpf_noise_model_scale_{model_scale}';add_coefficient(label,index,fit);op['fits'][label]=fit.to_dict()
        for chi in args.chi:
            states=[];diagnostics=[];begin=time.monotonic()
            for gamma in [0,1,2,3]:
                state,info=evolve_tn(8,edges,support,steps,gamma,chi=chi,
                    deadline=started+args.budget_seconds,bp_iterations=30,bp_tolerance=1e-7)
                states.append(state);diagnostics.append(info)
            exact_contracted,_=gram_tn(states,exact=True)
            try:
                approximate,loop_info=gram_tn(states,loop_size=args.loop_size)
                loop_error=float(np.linalg.norm(approximate-exact_contracted))
            except (ValueError,FloatingPointError,np.linalg.LinAlgError) as error:
                approximate=None;loop_info=[{'rejected':True,'reason':str(error)}];loop_error=None
            classical[chi][index]=expectation_tn(states[0],bits)
            tn_result={'overlaps_lcbp':approximate,'overlaps_exact_contraction_same_tn':exact_contracted,
                'overlap_truncation_error_frobenius':float(np.linalg.norm(exact_contracted-f)),
                'overlap_loop_contraction_error_frobenius':loop_error,
                'classical_low_chi_expectation':classical[chi][index],'propagation':diagnostics,'loop_diagnostics':loop_info,
                'seconds':time.monotonic()-begin,'fits':{}}
            for kind,gram in [('lcbp',approximate),('exact_contract',exact_contracted)]:
                for suffix,ridge in [('',0),('_ridge',1/args.shots)]:
                    label=f'lmpf_2d_{kind}_chi{chi}{suffix}'
                    try:
                        if gram is None:raise ValueError('Loop-contraction failure; see loop_diagnostics')
                        fit=fit_coefficients(gram,ridge=ridge);add_coefficient(label,index,fit)
                        tn_result['fits'][label]=fit.to_dict()
                    except ValueError as e:
                        failure={'method':label,'observable':index,'reason':str(e)};failures.append(failure)
                        tn_result['fits'][label]={'rejected':True,'reason':str(e)}
            op['tensor_networks'][str(chi)]=tn_result
            write(out/'operators'/f'operator_{index:02d}.json',op)
            print('CHI_DONE',index,chi,round(tn_result['seconds'],3),flush=True)
        op['seconds']=time.monotonic()-t0;write(out/'operators'/f'operator_{index:02d}.json',op)
    for label,weights in coefficient_sets.items():
        if np.all(np.isfinite(weights)):
            scores[label]=score_method(weights,means,covs,sampled,ideal,[args.shots]*3,matrix,offset)
            scores[label]['weights']=weights
    for chi,values in classical.items():
        if np.all(np.isfinite(values)):
            phy=matrix@values+offset;reference=matrix@ideal+offset
            scores[f'classical_2d_tn_chi{chi}']={'physical_expected':phy,'families':{name:{'model_bias_rmse':float(np.sqrt(np.mean((phy[k*4:(k+1)*4]-reference[k*4:(k+1)*4])**2)))} for k,name in enumerate(['charge','spin','doublon'])}}
    status=('OFFLINE_PILOT_COMPLETED' if args.max_observables==12 else 'SMOKE_COMPLETED')
    if failures:status+='_WITH_REJECTED_FITS'
    summary={'status':status,
        'fully_evaluated_observables':args.max_observables,'ideal_paulis':ideal,'ideal_physical':matrix@ideal+offset,
        'methods':scores,'rejected_fits':failures,'seconds':time.monotonic()-started,'new_qpu_seconds':0,
        'noise_model_learned':False,'hardware_mitigation_validated':False,
        'claims':'Small matched-surrogate Aer validation only; no 6x6 mitigation or quantum advantage claim.'}
    write(out/'summary.json',summary)
    write(out/'input_output_sha256.json',{str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file()})
    print('DONE',out,round(summary['seconds'],3),flush=True)
    print(json.dumps(clean({k:v.get('families',{}) for k,v in scores.items()}),indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--shots',type=int,default=512)
    p.add_argument('--chi',type=int,nargs='+',default=[1,2,4]);p.add_argument('--loop-size',type=int,default=4)
    p.add_argument('--time',type=float,default=.4);p.add_argument('--seed',type=int,default=20260908)
    p.add_argument('--max-observables',type=int,default=12);p.add_argument('--budget-seconds',type=int,default=900)
    p.add_argument('--start-observable',type=int,default=0)
    args=p.parse_args()
    if not (0<=args.start_observable<12 and 1<=args.max_observables<=12-args.start_observable and 32<=args.shots<=8192 and 0<args.time<=.4 and max(args.chi)<=16):p.error('Pilot limits exceeded')
    try:
        with threadpool_limits(limits=1):run(args)
    except Exception as e:
        if args.output.exists():write(args.output/'failure.json',{'error_type':type(e).__name__,'error':str(e)})
        raise
