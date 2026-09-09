"""Apply exploratory L-MPF to existing 3x3 hardware; gate any 6x6 extension.

No hardware submission. Coefficients are determined solely from operator
overlaps. Reference accuracy is inspected only after coefficients are saved.
"""
from pathlib import Path
import argparse,io,json,sys,time,unittest,shutil
import numpy as np
from qiskit import QuantumCircuit,qpy
from qiskit_aer import AerSimulator
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from lmpf_2d.product import evolve_products,gram_mixtures,expectations
from lmpf_2d.operators import compile_steps,fuse_steps
from lmpf_2d.model import FrozenSurrogate,digest,physical_transform
from lmpf_2d.fit import fit_coefficients,linear_zne_weights,richardson_weights
from lmpf_2d.hardware_inputs import decode,moment_samples
from lmpf_2d.pilot import clean

ARCHIVE=ROOT/'results_cuprate_2d/hardware_readout_cz_folding_3x3_2026-09-06'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,obj):Path(p).write_text(json.dumps(clean(obj),indent=2,allow_nan=False)+'\n')

def active_circuit(qc,layout):
    """Discard only never-used device wires; retain every physical unitary gate."""
    mapping={q:i for i,q in enumerate(layout)};out=QuantumCircuit(len(layout));measured=[];ended=False
    for item in qc.data:
        op=item.operation;physical=[qc.find_bit(q).index for q in item.qubits]
        if op.name=='barrier':continue
        if any(q not in mapping for q in physical):raise ValueError('Unexpected active ancilla outside declared layout')
        if op.name=='measure':
            ended=True;measured.append((physical[0],qc.find_bit(item.clbits[0]).index));continue
        if ended:raise ValueError('Unitary gate after first measurement')
        if op.name not in ('rz','sx','x','cz') or op.num_clbits or op.is_parameterized():
            raise ValueError(f'Unsupported or nonunitary hardware operation: {op.name}')
        out.append(op,[mapping[q] for q in physical])
    if sorted(measured,key=lambda x:x[1])!=list(zip(layout,range(len(layout)))):
        raise ValueError('Physical measurement mapping disagrees with logical record order')
    out.global_phase=qc.global_phase
    return out

def pauli_moments(probabilities,n):
    index=np.arange(len(probabilities),dtype=np.uint64)
    z=np.column_stack([1.-2.*((index>>q)&1) for q in range(n)])
    return np.r_[probabilities@z,probabilities@(z[:,0::2]*z[:,1::2])]

def record_sign(mask):
    z=1-2*np.asarray(mask);return np.r_[z,z[0::2]*z[1::2]]

def rmse(physical,reference):
    return np.sqrt(np.mean((np.asarray(physical)-reference).reshape(3,9)**2,axis=1))

def central_and_bootstrap(raw,weights,reference,replicates,seed):
    keyed={(r['setting_id'],r['twirl_id']):r for r in raw['records']};n=18
    cal=[decode(keyed[f'readout_all{i}',0]['bitstrings'],n) for i in (0,1)]
    counts=np.array([cal[0].sum(0),(1-cal[1]).sum(0)])
    totals=np.array([len(x) for x in cal])[:,None];fixed=(counts+.5)/(totals+1)
    groups=[]
    for factor in (1,2,3):
        group=[]
        for twirl in range(8):
            r=keyed[f'U8_T04_factor{factor}',twirl]
            bits=decode(r['bitstrings'],n);expected={1:64,2:7,3:14}[factor]
            if len(bits)!=expected:raise ValueError('Unexpected archived shot allocation')
            group.append((bits,np.array(r['readout_mask_little_endian'])))
        groups.append(group)
    a,offset=physical_transform(n);target=a@reference+offset
    names=['readout','zne_linear','zne_richardson',*weights]
    matrices={'zne_linear':np.tile(linear_zne_weights([1,2,3]),(27,1)),
              'zne_richardson':np.tile(richardson_weights([1,2,3]),(27,1)),**weights}
    def estimates(group_data,errors):
        arms=[];baseline=np.zeros(27)
        for k,group in enumerate(group_data):
            arm=np.zeros(27)
            for bits,mask in group:
                values=moment_samples(bits,mask,errors)
                if k==0:baseline+=values.mean(0)/8
                arm+=values[:43 if k==0 else len(values)].mean(0)/8
            arms.append(arm)
        arms=np.asarray(arms)
        result={'readout':baseline}
        result.update({name:np.einsum('ia,ai->i',w,arms) for name,w in matrices.items()})
        return result
    means=estimates(groups,fixed)
    physical={name:a@value+offset for name,value in means.items()}
    central={name:rmse(value,target) for name,value in physical.items()}
    rng=np.random.default_rng(seed);boot=np.empty((replicates,len(names),27));fixed_rmse=np.empty((replicates,len(names),3))
    for rep in range(replicates):
        e=rng.beta(counts+.5,totals-counts+.5);sample=[]
        for k,group in enumerate(groups):
            sg=[]
            for bits,mask in group:
                if k==0:
                    # Shared and baseline-only strata are resampled separately.
                    chosen=np.r_[rng.integers(0,43,43),rng.integers(43,64,21)]
                else:chosen=rng.integers(0,len(bits),len(bits))
                sg.append((bits[chosen],mask))
            sample.append(sg)
        all_estimates=estimates(sample,e);fixed_estimates=estimates(sample,fixed)
        for j,name in enumerate(names):
            boot[rep,j]=a@all_estimates[name]+offset
            fixed_rmse[rep,j]=rmse(a@fixed_estimates[name]+offset,target)
    boot_rmse=np.sqrt(np.mean((boot-target).reshape(replicates,len(names),3,9)**2,axis=3))
    results={}
    for j,name in enumerate(names):
        values=physical[name];paulis=means[name];zu=paulis[:18:2];zd=paulis[1:18:2];zz=paulis[18:]
        pairs=np.array([(1+zu+zd+zz)/4,(1+zu-zd-zz)/4,(1-zu+zd-zz)/4,(1-zu-zd+zz)/4])
        results[name]={'pauli_means':paulis,'physical_means':values,'rmse_charge_spin_doublon':central[name],
            'physical_bootstrap_sd':boot[:,j].std(0,ddof=1),'rmse_interval':np.quantile(boot_rmse[:,j],[.025,.975],axis=0),
            'N':float(values[:9].sum()),'minimum_reconstructed_local_probability':float(pairs.min()),
            'maximum_absolute_pauli':float(np.abs(paulis).max()),'clipped':False}
    primary='lmpf_ridge';j=names.index(primary);comparisons={}
    for name in ('readout','zne_linear'):
        b=names.index(name);delta=boot_rmse[:,b]-boot_rmse[:,j]
        comparisons[name]={'central_rmse_improvement':central[name]-central[primary],
            'paired_interval':np.quantile(delta,[.025,.975],axis=0),
            'fixed_calibration_paired_interval':np.quantile(fixed_rmse[:,b]-fixed_rmse[:,j],[.025,.975],axis=0)}
    return {'methods':results,'comparisons':comparisons,'ideal_physical':target,
        'bootstrap_replicates':replicates,'calibration_posterior_mean':fixed,
        'uncertainty_scope':'Paired fixed-twirl stratified bootstrap plus shared Jeffreys calibration posterior; no drift/model/TN coverage guarantee.'},boot_rmse

def run(args):
    started=time.monotonic();out=args.output
    if out.exists():raise FileExistsError('Preserve earlier outputs')
    out.mkdir(parents=True);(out/'states').mkdir();(out/'source_snapshot').mkdir()
    sources=[ROOT/'lmpf_2d'/name for name in ['archive_3x3.py','product.py','operators.py','fit.py','model.py','hardware_inputs.py','pilot.py']]
    sources+=[ROOT/'test_lmpf_product.py',ROOT/'lmpf_2d/PLAN_3X3_TO_6X6.md']
    for p in sources:shutil.copyfile(p,out/'source_snapshot'/p.name)
    stream=io.StringIO();suite=unittest.TestSuite()
    for name in ('test_lmpf_product','test_lmpf_2d','test_lmpf_hardware_inputs'):suite.addTests(unittest.defaultTestLoader.loadTestsFromName(name))
    tests=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite);(out/'tests.txt').write_text(stream.getvalue())
    if not tests.wasSuccessful():raise RuntimeError('Tests failed')
    plan=read(ARCHIVE/'plan.json');raw=read(ARCHIVE/'raw_bitstrings.json');receipt=read(ARCHIVE/'job_receipt.json')
    if receipt['job_id']!=raw['job_id'] or digest(ARCHIVE/'plan.json')!=receipt['plan_sha256']:raise ValueError('Job/plan identity failure')
    layout=plan['layout'];profile=FrozenSurrogate(ARCHIVE/'live_backend_properties.json',layout)
    if len(layout)!=18 or profile.backend!=plan['backend']:raise ValueError('Only the actual 18-qubit archive is in scope')
    supports=[{q:'Z'} for q in range(18)]+[{2*s:'Z',2*s+1:'Z'} for s in range(9)]
    runplan={'schema':'lmpf-3x3-native-chi1-v1','job_id':raw['job_id'],'backend':plan['backend'],
        'archive':str(ARCHIVE.relative_to(ROOT)),'noise':profile.metadata(),'source_sha256':{str(p.relative_to(ROOT)):digest(p) for p in sources},
        'input_sha256':{str(p.relative_to(ROOT)):digest(p) for p in [ARCHIVE/'plan.json',ARCHIVE/'raw_bitstrings.json',ARCHIVE/'job_receipt.json']},
        'chi':1,'rate_sensitivity':[.7,1.,1.3],'ridge':1/56,'target_shots':[344,56,112],
        'readout_baseline_target_shots':512,'shared_calibration_shots':128,'equal_total_shots_per_method':640,
        'all_archived_shots_preserved':808,'qpu_seconds':0,'initial_state_before_physical_gates':'all zero',
        'physical_layout':layout,'reference_used_in_optimizer':False,'deadline_seconds':args.budget_seconds,
        'higher_bond_and_device_noise_gate_required_before_6x6':True}
    write(out/'plan.json',runplan)
    ideals=[];mixtures={scale:[[],[],[]] for scale in (.7,1.,1.3)};native_info=[];exact_checks=[]
    for index,record in enumerate(plan['records']):
        if record.get('role')!='target':continue
        if time.monotonic()>started+args.budget_seconds:raise TimeoutError('Archive run budget reached')
        factor=record['factor'];twirl=record['twirl_id'];path=ARCHIVE/'provider_inputs'/f'circuit_{index:03d}.qpy'
        if digest(path)!=digest(ARCHIVE/'bound_inputs'/path.name):raise ValueError('Provider/bound circuit mismatch')
        with path.open('rb') as f:full=qpy.load(f)[0]
        qc=active_circuit(full,layout)
        if qc.count_ops().get('cz')!=1008*factor:raise ValueError('CZ factor identity failed')
        steps=fuse_steps(compile_steps(qc,profile.rate));sign=record_sign(record['readout_mask_little_endian'])
        item={'record_index':index,'factor':factor,'twirl':twirl,'qpy_sha256':digest(path),
            'native_depth':qc.depth(),'gates':dict(qc.count_ops()),'classical_blocks':len(steps)}
        native_info.append(item)
        if twirl==0:
            checked=qc.copy();checked.save_probabilities(label='probabilities')
            result=AerSimulator(method='statevector',max_parallel_threads=1).run(checked,shots=1).result()
            if not result.success:raise RuntimeError('Ideal statevector check failed')
            probabilities=np.asarray(result.data(0)['probabilities'])
            expected=pauli_moments(probabilities,18)*sign
            discrepancy=float(np.max(abs(expected-np.asarray(plan['target']['reference']))))
            exact_checks.append({'factor':factor,'twirl':twirl,'max_error_vs_saved_reference':discrepancy,'probability_sum':float(probabilities.sum())})
            if discrepancy>1e-9:raise ValueError('Native ideal circuit reference check failed')
        for scale in ([0.,.7,1.,1.3] if factor==1 else [.7,1.,1.3]):
            begin=time.monotonic();state=evolve_products(18,supports,steps,scale,deadline=started+args.budget_seconds)
            state.amplitude*=sign
            np.savez_compressed(out/'states'/f'record_{index:02d}_rate_{scale:.1f}.npz',
                local=state.local,amplitude=state.amplitude,truncation_bound=state.truncation_bound,minimum_schmidt_gap=state.minimum_schmidt_gap)
            if scale==0:ideals.append(state)
            else:mixtures[scale][factor-1].append(state)
            print('STATE',factor,twirl,scale,round(time.monotonic()-begin,3),flush=True)
        write(out/'native_inputs.json',native_info);write(out/'ideal_checks.json',exact_checks)
    weights={};fit_records={};all_grams={}
    for scale,arms in mixtures.items():
        if len(ideals)!=8 or any(len(x)!=8 for x in arms):raise ValueError('Missing twirl operator states')
        f=gram_mixtures([ideals,*arms]);all_grams[str(scale)]=f
        variants=[('lmpf_unregularized',0),('lmpf_ridge',1/56)] if scale==1 else [(f'lmpf_ridge_rate_{scale}',1/56)]
        for name,ridge in variants:
            fits=[fit_coefficients(matrix,ridge=ridge) for matrix in f]
            weights[name]=np.array([fit.coefficients for fit in fits]);fit_records[name]=[fit.to_dict() for fit in fits]
    write(out/'overlaps.json',all_grams);write(out/'coefficients.json',fit_records)
    # Coefficients have now been frozen, before reference-error scoring.
    analysis,bootstrap=central_and_bootstrap(raw,weights,np.asarray(plan['target']['reference']),args.bootstrap,args.seed)
    np.savez_compressed(out/'bootstrap_rmse.npz',rmse=bootstrap)
    primary=analysis['methods']['lmpf_ridge'];comparisons=analysis['comparisons']
    central_ok=all(np.min(c['central_rmse_improvement'])>=-.02 for c in comparisons.values())
    resolved=np.logical_and(*[c['paired_interval'][0]>0 for c in comparisons.values()]).any()
    sensitivity=max(np.max(abs(analysis['methods'][f'lmpf_ridge_rate_{s}']['physical_means']-primary['physical_means'])) for s in (.7,1.3))
    gates={'native_ideal_checks':True,'finite_psd_coefficient_fits':True,
        'no_family_worsens_more_than_0.02_vs_readout_and_zne':bool(central_ok),
        'same_family_resolved_improvement_vs_both':bool(resolved),
        'rate_sensitivity_max_observable_shift':float(sensitivity),
        'higher_bond_stability_validated':False,'device_noise_model_independently_validated':False}
    classical=np.mean([expectations(p,[0]*18) for p in ideals],axis=0)
    a,offset=physical_transform(18)
    analysis.update({'status':'3X3_EXPLORATORY_HARDWARE_LMPF_COMPLETED','gates':gates,
        'preliminary_accuracy_gate':bool(central_ok and resolved),'go_for_6x6':False,
        'six_by_six_started':False,'classical_chi1_paulis':classical,
        'classical_chi1_rmse':rmse(a@classical+offset,np.asarray(analysis['ideal_physical'])),
        'seconds':time.monotonic()-started,'tests_passed':tests.testsRun,'new_qpu_seconds':0,
        'hardware_mitigation_validated':False,'scope':'Applied to actual archived hardware; exploratory model-dependent coefficients, no 6x6 or advantage claim.'})
    write(out/'summary.json',analysis)
    write(out/'sha256.json',{str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file()})
    print('DONE',json.dumps(clean({k:analysis[k] for k in ('gates','seconds','preliminary_accuracy_gate','go_for_6x6')})),flush=True)
    print(json.dumps(clean({name:v['rmse_charge_spin_doublon'] for name,v in analysis['methods'].items()})),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--budget-seconds',type=int,default=1200);p.add_argument('--bootstrap',type=int,default=2000);p.add_argument('--seed',type=int,default=202609091)
    args=p.parse_args()
    try:
        with threadpool_limits(limits=1):run(args)
    except Exception as error:
        if args.output.exists():write(args.output/'failure.json',{'error_type':type(error).__name__,'error':str(error),'six_by_six_started':False})
        raise
