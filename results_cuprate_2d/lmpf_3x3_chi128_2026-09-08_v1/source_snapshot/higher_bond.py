"""Bounded chi=1/2/4 diagnostic on the actual 3x3 native circuits, offline only."""
from pathlib import Path
import argparse,io,json,shutil,sys,time,unittest
import numpy as np
from qiskit import qpy
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from lmpf_2d.archive_3x3 import ARCHIVE,active_circuit,record_sign
from lmpf_2d.model import FrozenSurrogate,digest
from lmpf_2d.operators import compile_steps,fuse_steps,evolve_tn,product_operator_tn,overlap_network,overlap
from lmpf_2d.tn_storage import save_tn,load_tn,bounded_contract,expectation_zero
from lmpf_2d.fit import fit_coefficients
from lmpf_2d.pilot import clean

BASE=ROOT/'results_cuprate_2d/lmpf_3x3_hardware_2026-09-08_v1'
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def write(path,obj):Path(path).write_text(json.dumps(clean(obj),indent=2,allow_nan=False)+'\n')

def stability_flags(low,high):
    for result in (low,high):
        fit=result.get('fits',{}).get('exact',{})
        if result.get('failure',True) or fit.get('rejected',False) or 'ridge' not in fit:
            return {'passes_local_flags':False,'reason':'Missing or rejected higher-bond calculation'}
    denominator=np.linalg.norm(high['overlaps_exact'])
    if denominator<=0:return {'passes_local_flags':False,'reason':'Zero reference Gram norm'}
    delta=float(np.linalg.norm(np.array(high['overlaps_exact'])-low['overlaps_exact'])/denominator)
    dc=float(np.sum(abs(np.array(high['fits']['exact']['ridge']['coefficients'])-low['fits']['exact']['ridge']['coefficients'])))
    return {'relative_gram_change':delta,'ridge_coefficient_l1_change':dc,'passes_local_flags':delta<=.01 and dc<=.05}

def product_checkpoint(index,scale,observable,edges):
    path=BASE/'states'/f'record_{index:02d}_rate_{scale:.1f}.npz'
    if digest(path)!=read(BASE/'sha256.json')[str(path.relative_to(BASE))]:raise ValueError('Changed chi=1 checkpoint')
    tn=product_operator_tn(18,edges,{})
    with np.load(path,allow_pickle=False) as data:
        local=data['local'][observable];amplitude=float(data['amplitude'][observable])
    for q in range(18):
        tensor=tn[f'I{q}'];tensor.modify(data=local[q].reshape(tensor.shape))
    tensor=tn['I0'];tensor.modify(data=amplitude*tensor.data)
    return tn,{'reused_chi1_checkpoint':str(path.relative_to(ROOT)),'sha256':digest(path),
               'bp_nonconverged_updates':0,'note':'Native chi=1 implementation cross-checked in the previous audit.'}

def grams(states):
    exact=np.zeros((4,4));loop=np.zeros((4,4));cost=[];loop_info=[];failure=None
    for i in range(4):
        for j in range(i,4):
            value,info=bounded_contract(overlap_network(states[i],states[j]));exact[i,j]=exact[j,i]=value
            cost.append({'i':i,'j':j,**info})
    for i in range(4):
        if failure:break
        for j in range(i,4):
            try:
                value,info=overlap(states[i],states[j]);loop[i,j]=loop[j,i]=value
                loop_info.append({'i':i,'j':j,**info})
            except (ValueError,FloatingPointError,np.linalg.LinAlgError) as error:
                failure={'i':i,'j':j,'reason':str(error)};break
    return exact,None if failure else loop,{'exact_contraction_costs':cost,'loop_info':loop_info,'loop_failure':failure}

def run(args):
    started=time.monotonic();out=args.output
    if out.exists():raise FileExistsError('Preserve earlier run')
    out.mkdir(parents=True);(out/'source_snapshot').mkdir();(out/'states').mkdir()
    sources=[ROOT/'lmpf_2d'/name for name in ['higher_bond.py','tn_storage.py','operators.py','archive_3x3.py','product.py','model.py','fit.py','PLAN_HIGHER_BOND.md']]+[ROOT/'test_lmpf_tn_storage.py']
    for p in sources:shutil.copyfile(p,out/'source_snapshot'/p.name)
    stream=io.StringIO();suite=unittest.TestSuite()
    for name in ('test_lmpf_2d','test_lmpf_product','test_lmpf_hardware_inputs','test_lmpf_tn_storage'):suite.addTests(unittest.defaultTestLoader.loadTestsFromName(name))
    tests=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite);(out/'tests.txt').write_text(stream.getvalue())
    if not tests.wasSuccessful():raise RuntimeError('Tests failed')
    original=read(ARCHIVE/'plan.json');profile=FrozenSurrogate(ARCHIVE/'live_backend_properties.json',original['layout'])
    if profile.metadata()['calibration_sha256']!=read(BASE/'plan.json')['noise']['calibration_sha256']:
        raise ValueError('Changed calibration model')
    native={};inputs=[]
    for factor in (1,2,3):
        index=next(i for i,r in enumerate(original['records']) if r.get('factor')==factor and r['twirl_id']==0)
        path=ARCHIVE/'provider_inputs'/f'circuit_{index:03d}.qpy'
        if digest(path)!=digest(ARCHIVE/'bound_inputs'/path.name):raise ValueError('Changed native circuit')
        with path.open('rb') as f:qc=active_circuit(qpy.load(f)[0],original['layout'])
        steps=fuse_steps(compile_steps(qc,profile.rate));edges=sorted({tuple(sorted(s.qubits)) for s in steps if len(s.qubits)==2})
        native[factor]=(index,steps,edges,record_sign(original['records'][index]['readout_mask_little_endian']))
        inputs.append({'factor':factor,'record_index':index,'qpy_sha256':digest(path),'cz':qc.count_ops().get('cz'),
            'native_depth':qc.depth(),'classical_blocks':len(steps),'edges':edges})
    plan={'schema':'3x3-higher-bond-local-diagnostic-v1','job_id':read(ARCHIVE/'job_receipt.json')['job_id'],
        'backend':original['backend'],'observables':args.observables,'twirl':0,'chi':[1,2,4],
        'noise':profile.metadata(),'inputs':inputs,'ridge':1/56,'bp_tolerance':1e-7,'bp_iterations':50,
        'relative_gram_change_tolerance':.01,'coefficient_l1_change_tolerance':.05,
        'max_contraction_elements':2**22,'max_contraction_flops':2e9,'budget_seconds':args.budget_seconds,
        'reference_used_for_fitting':False,'hardware_weights_applied':False,'new_qpu_seconds':0,
        'source_sha256':{str(p.relative_to(ROOT)):digest(p) for p in sources}}
    write(out/'plan.json',plan)
    summaries=[]
    for observable in args.observables:
        support={observable:'Z'} if observable<18 else {2*(observable-18):'Z',2*(observable-18)+1:'Z'}
        op={'observable_index':observable,'support':support,'exact_ideal_reference':original['target']['reference'][observable],'chi_results':{}}
        for chi in (1,2,4):
            print('START',observable,chi,flush=True);begin=time.monotonic();states=[];propagation=[];failure=None
            for arm in (0,1,2,3):
                factor=max(arm,1);scale=0. if arm==0 else 1.;index,steps,edges,sign=native[factor]
                try:
                    if chi==1:tn,info=product_checkpoint(index,scale,observable,edges)
                    else:
                        tn,info=evolve_tn(18,edges,support,steps,scale,chi=chi,
                            bp_tolerance=1e-7,bp_iterations=50,deadline=started+args.budget_seconds)
                        tensor=tn['I0'];tensor.modify(data=sign[observable]*tensor.data)
                    prefix=out/'states'/f'obs{observable:02d}_chi{chi}_arm{arm}'
                    save_tn(prefix,tn);loaded=load_tn(prefix)
                    # Confirm serialisation preserved the contracted norm.
                    norm_before,_=bounded_contract(overlap_network(tn,tn));norm_after,_=bounded_contract(overlap_network(loaded,loaded))
                    if abs(norm_before-norm_after)>1e-10:raise ValueError('TN checkpoint changed operator norm')
                    states.append(loaded);propagation.append({'arm':arm,**info})
                    print('STATE_DONE',observable,chi,arm,round(time.monotonic()-begin,2),flush=True)
                    if info['bp_nonconverged_updates']:raise ValueError('Propagation failed strict BP convergence')
                except (ValueError,FloatingPointError,np.linalg.LinAlgError,TimeoutError) as error:
                    failure={'arm':arm,'reason':str(error)};break
            result={'propagation':propagation,'failure':failure,'fits':{},'seconds':time.monotonic()-begin}
            if failure is None:
                try:
                    exact,loop,diagnostic=grams(states)
                    result.update({'overlaps_exact':exact,'overlaps_lcbp':loop,'diagnostic':diagnostic,
                        'loop_vs_exact_frobenius':None if loop is None else float(np.linalg.norm(loop-exact)),
                        'ideal_tn_expectation':expectation_zero(states[0])})
                    for name,f in [('exact',exact),('lcbp',loop)]:
                        if f is None:result['fits'][name]={'rejected':True,'reason':'Invalid loop contraction'};continue
                        try:result['fits'][name]={'unregularized':fit_coefficients(f).to_dict(),'ridge':fit_coefficients(f,ridge=1/56).to_dict()}
                        except ValueError as error:result['fits'][name]={'rejected':True,'reason':str(error)}
                except (ValueError,FloatingPointError,np.linalg.LinAlgError) as error:result['failure']={'stage':'contraction','reason':str(error)}
            result['seconds']=time.monotonic()-begin;op['chi_results'][str(chi)]=result
            write(out/f'observable_{observable:02d}.json',op)
            print('CHI_DONE',observable,chi,round(result['seconds'],2),'FAIL' if result['failure'] else 'DONE',flush=True)
            if time.monotonic()>started+args.budget_seconds:break
        low=op['chi_results'].get('2',{});high=op['chi_results'].get('4',{})
        op['stability']=stability_flags(low,high)
        write(out/f'observable_{observable:02d}.json',op);summaries.append({'observable':observable,**op['stability']})
        if time.monotonic()>started+args.budget_seconds:break
    summary={'status':'HIGHER_BOND_DIAGNOSTIC_FINISHED','observables':summaries,
        'all_requested_observables_evaluated':len(summaries)==len(args.observables),
        'local_stability_flags_pass':len(summaries)==len(args.observables) and all(s['passes_local_flags'] for s in summaries),
        'full_27_observable_8_twirl_validation':False,'noise_model_validated':False,
        'six_by_six_started':False,'new_qpu_seconds':0,'tests_passed':tests.testsRun,'seconds':time.monotonic()-started}
    write(out/'summary.json',summary);write(out/'sha256.json',{str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file()})
    print('DONE',json.dumps(clean(summary)),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--observables',type=int,nargs='+',default=[8,9,22]);p.add_argument('--budget-seconds',type=int,default=1200)
    args=p.parse_args()
    if any(i not in range(27) for i in args.observables):p.error('Invalid observable')
    with threadpool_limits(limits=1):run(args)
