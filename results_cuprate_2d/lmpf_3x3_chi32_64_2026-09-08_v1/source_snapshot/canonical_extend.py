"""Continue the fixed three-operator diagnostic at chi32/64; reuse chi16."""
from pathlib import Path
import argparse,copy,io,json,shutil,sys,time,unittest
import numpy as np
from qiskit import qpy
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from lmpf_2d.archive_3x3 import ARCHIVE,active_circuit,record_sign
from lmpf_2d.canonical_refine import read,write
from lmpf_2d.canonical_chain import evolve_canonical
from lmpf_2d.chain_contract import chain_overlap,chain_expectation_zero
from lmpf_2d.model import FrozenSurrogate,digest
from lmpf_2d.operators import compile_steps,fuse_steps
from lmpf_2d.tn_storage import save_tn,load_tn,bounded_contract
from lmpf_2d.fit import fit_coefficients
from lmpf_2d.higher_bond import stability_flags

PARENT=ROOT/'results_cuprate_2d/lmpf_3x3_canonical_refine_2026-09-08_v1'
def run(out):
    if out.exists():raise FileExistsError('Preserve previous chi32/64 run')
    out.mkdir(parents=True);(out/'states').mkdir();(out/'source_snapshot').mkdir();start=time.monotonic()
    sources=[ROOT/'lmpf_2d'/name for name in ('canonical_extend.py','canonical_chain.py','chain_contract.py','canonical_refine.py',
        'higher_bond.py','operators.py','tn_storage.py','fit.py','model.py','archive_3x3.py','PLAN_CHI32_64.md')]
    tests_names=('test_lmpf_2d','test_lmpf_hardware_inputs','test_lmpf_product','test_lmpf_tn_storage','test_lmpf_canonical_chain','test_lmpf_chain_contract')
    sources+=[ROOT/f'{name}.py' for name in tests_names]
    for path in sources:shutil.copyfile(path,out/'source_snapshot'/path.name)
    suite=unittest.TestSuite();stream=io.StringIO()
    for name in tests_names:suite.addTests(unittest.defaultTestLoader.loadTestsFromName(name))
    tests=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite);(out/'tests.txt').write_text(stream.getvalue())
    if not tests.wasSuccessful():raise RuntimeError('Prerequisite tests failed')
    parent=read(PARENT/'plan.json');original=read(ARCHIVE/'plan.json');layout=original['layout']
    profile=FrozenSurrogate(ARCHIVE/'live_backend_properties.json',layout)
    if profile.metadata()['calibration_sha256']!=parent['noise']['calibration_sha256']:raise ValueError('Changed surrogate calibration')
    for path,h in read(PARENT/'sha256.json').items():
        if digest(PARENT/path)!=h:raise ValueError('Changed parent checkpoint '+path)
    native={};inputs=[]
    for factor in (1,2,3):
        index=next(i for i,r in enumerate(original['records']) if r.get('factor')==factor and r['twirl_id']==0)
        path=ARCHIVE/'provider_inputs'/f'circuit_{index:03d}.qpy';old=next(r for r in parent['inputs'] if r['factor']==factor)
        if digest(path)!=old['qpy_sha256'] or digest(path)!=digest(ARCHIVE/'bound_inputs'/path.name):raise ValueError('Changed native input')
        with path.open('rb') as f:qc=active_circuit(qpy.load(f)[0],layout)
        steps=fuse_steps(compile_steps(qc,profile.rate))
        if {s.qubits for s in steps if len(s.qubits)==2}!={(q,q+1) for q in range(17)}:raise ValueError('Not the verified open chain')
        native[factor]=(steps,record_sign(original['records'][index]['readout_mask_little_endian']))
        inputs.append({'factor':factor,'record_index':index,'qpy_sha256':digest(path)})
    plan={'schema':'native-chain-chi32-64-v1','observables':[8,9,22],'chi':[16,32,64],'comparison_levels':[32,64],
        'backend':profile.backend,'job_id':parent['job_id'],'twirl':0,'inputs':inputs,'noise':profile.metadata(),
        'native_graph':{'vertices':18,'edges':17,'cycles':0},'parent':str(PARENT.relative_to(ROOT)),
        'parent_manifest_sha256':digest(PARENT/'sha256.json'),'ridge':1/56,'budget_seconds':600,
        'budget_checked_between_states':True,'relative_gram_change_tolerance':.01,'coefficient_l1_change_tolerance':.05,
        'overlap_contraction':'raw_tn_for_independent_audit','primary_overlap_method':'explicit_left_to_right_chain_environment',
        'max_contraction_elements':2**22,'max_contraction_flops':2e9,'hardware_weights_applied':False,'new_qpu_seconds':0,
        'source_sha256':{str(p.relative_to(ROOT)):digest(p) for p in sources}}
    write(out/'plan.json',plan);summaries=[];resource_failures=[]
    for obs in plan['observables']:
        previous=read(PARENT/f'observable_{obs:02d}.json');reused=copy.deepcopy(previous['chi_results']['16'])
        reused['reused_from_parent']=True;reused['source_seconds']=reused['seconds'];reused['seconds']=0.
        record={'observable_index':obs,'exact_ideal_reference':previous['exact_ideal_reference'],'chi_results':{'16':reused}}
        for arm in range(4):
            for suffix in ('.json','.npz'):
                file=f'obs{obs:02d}_chi16_arm{arm}{suffix}';shutil.copyfile(PARENT/'states'/file,out/'states'/file)
        support={obs:'Z'} if obs<18 else {2*(obs-18):'Z',2*(obs-18)+1:'Z'}
        for chi in (32,64):
            begin=time.monotonic();states=[]
            for arm in range(4):
                if time.monotonic()>start+600:raise TimeoutError('Chi32/64 time budget reached')
                steps,sign=native[max(arm,1)];state_start=time.monotonic()
                tn=evolve_canonical(18,support,steps,0. if arm==0 else 1.,chi)
                tensor=tn['I0'];tensor.modify(data=sign[obs]*tensor.data)
                prefix=out/'states'/f'obs{obs:02d}_chi{chi}_arm{arm}';save_tn(prefix,tn)
                restored=load_tn(prefix)
                if abs(chain_overlap(tn,tn)[0]-chain_overlap(restored,restored)[0])>1e-10:raise ValueError('Checkpoint norm mismatch')
                states.append(restored);print('STATE_DONE',obs,chi,arm,round(time.monotonic()-state_start,3),flush=True)
            f=np.zeros((4,4));cost=[]
            for i in range(4):
                for j in range(i,4):
                    value,info=chain_overlap(states[i],states[j]);f[i,j]=f[j,i]=value;cost.append(info)
            # Independent scalar check before fitting, without local bra/ket precontraction.
            independent,independent_cost=bounded_contract(states[0].H & states[1])
            if abs(independent-f[0,1])>1e-9:raise ValueError('Independent raw-TN overlap mismatch')
            record['chi_results'][str(chi)]={'failure':None,'overlaps_exact':f,
                'fits':{'exact':{'unregularized':fit_coefficients(f).to_dict(),'ridge':fit_coefficients(f,ridge=1/56).to_dict()}},
                'ideal_tn_expectation':chain_expectation_zero(states[0]),'contraction_costs':cost,
                'independent_overlap_error':abs(independent-f[0,1]),'independent_overlap_cost':independent_cost,
                'seconds':time.monotonic()-begin,'method':'canonical MPS with exact open-chain contraction'}
            write(out/f'observable_{obs:02d}.json',record);print('CHI_DONE',obs,chi,round(time.monotonic()-begin,3),flush=True)
        record['previous_step_stability']=stability_flags(record['chi_results']['16'],record['chi_results']['32'])
        record['stability']=stability_flags(record['chi_results']['32'],record['chi_results']['64'])
        write(out/f'observable_{obs:02d}.json',record);summaries.append({'observable':obs,**record['stability']})
    summary={'status':'CANONICAL_CHI32_64_FINISHED','observables':summaries,'local_stability_flags_pass':all(x['passes_local_flags'] for x in summaries),
        'full_27_observable_8_twirl_validation':False,'noise_model_validated':False,'six_by_six_started':False,
        'hardware_weights_applied':False,'new_qpu_seconds':0,'tests_passed':tests.testsRun,'seconds':time.monotonic()-start}
    write(out/'summary.json',summary);write(out/'sha256.json',{str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file()})
    print('DONE',json.dumps(summary),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    try:
        with threadpool_limits(limits=1):run(args.output)
    except Exception as error:
        if args.output.exists():write(args.output/'failure.json',{'error_type':type(error).__name__,'reason':str(error),'six_by_six_started':False})
        raise
