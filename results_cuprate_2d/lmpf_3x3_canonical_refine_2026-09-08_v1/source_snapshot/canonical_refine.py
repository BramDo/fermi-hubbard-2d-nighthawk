"""Bounded canonical-chain chi=4/8/16 diagnosis after failed chi=2/4 flags."""
from pathlib import Path
import argparse,json,sys,time,shutil,io,unittest
import numpy as np
from qiskit import qpy
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from lmpf_2d.archive_3x3 import ARCHIVE,active_circuit,record_sign
from lmpf_2d.model import FrozenSurrogate,digest
from lmpf_2d.canonical_chain import evolve_canonical
from lmpf_2d.operators import compile_steps,fuse_steps,overlap_network
from lmpf_2d.tn_storage import save_tn,bounded_contract,expectation_zero
from lmpf_2d.higher_bond import stability_flags
from lmpf_2d.fit import fit_coefficients
from lmpf_2d.pilot import clean

def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def write(path,obj):path.write_text(json.dumps(clean(obj),indent=2,allow_nan=False)+'\n')
def run(out):
    if out.exists():raise FileExistsError('Preserve earlier refinement')
    out.mkdir(parents=True);(out/'states').mkdir();(out/'source_snapshot').mkdir();start=time.monotonic()
    sources=[ROOT/'lmpf_2d'/name for name in ('canonical_refine.py','canonical_chain.py','higher_bond.py','operators.py','tn_storage.py','model.py','fit.py','archive_3x3.py')]+[ROOT/'test_lmpf_canonical_chain.py']
    for path in sources:shutil.copyfile(path,out/'source_snapshot'/path.name)
    stream=io.StringIO();suite=unittest.TestSuite()
    for name in ('test_lmpf_canonical_chain','test_lmpf_tn_storage','test_lmpf_product','test_lmpf_2d','test_lmpf_hardware_inputs'):suite.addTests(unittest.defaultTestLoader.loadTestsFromName(name))
    tests=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite);(out/'tests.txt').write_text(stream.getvalue())
    if not tests.wasSuccessful():raise RuntimeError('Failed prerequisite tests')
    original=read(ARCHIVE/'plan.json');layout=original['layout'];profile=FrozenSurrogate(ARCHIVE/'live_backend_properties.json',layout)
    native={};inputs=[]
    for factor in (1,2,3):
        index=next(i for i,r in enumerate(original['records']) if r.get('factor')==factor and r['twirl_id']==0)
        path=ARCHIVE/'provider_inputs'/f'circuit_{index:03d}.qpy'
        if digest(path)!=digest(ARCHIVE/'bound_inputs'/path.name):raise ValueError('Native circuit mismatch')
        with path.open('rb') as f:qc=active_circuit(qpy.load(f)[0],layout)
        steps=fuse_steps(compile_steps(qc,profile.rate));edges={tuple(s.qubits) for s in steps if len(s.qubits)==2}
        if edges!={(q,q+1) for q in range(17)}:raise ValueError('This refinement is valid only for the verified native path')
        native[factor]=(steps,record_sign(original['records'][index]['readout_mask_little_endian']))
        inputs.append({'factor':factor,'record_index':index,'qpy_sha256':digest(path)})
    plan={'schema':'native-chain-refinement-v1','observables':[8,9,22],'chi':[4,8,16],'comparison_levels':[8,16],
        'backend':original['backend'],'job_id':read(ARCHIVE/'job_receipt.json')['job_id'],
        'native_graph':{'vertices':18,'edges':17,'cycles':0},'twirl':0,'inputs':inputs,'noise':profile.metadata(),
        'ridge':1/56,'relative_gram_change_tolerance':.01,'coefficient_l1_change_tolerance':.05,
        'budget_seconds':300,'budget_checked_between_states':True,'hardware_weights_applied':False,
        'reason':'Diagnose failed chi=2/4 test with an independently tested canonical path backend.',
        'source_sha256':{str(p.relative_to(ROOT)):digest(p) for p in sources},'new_qpu_seconds':0}
    write(out/'plan.json',plan);summaries=[]
    for obs in plan['observables']:
        support={obs:'Z'} if obs<18 else {2*(obs-18):'Z',2*(obs-18)+1:'Z'}
        record={'observable_index':obs,'exact_ideal_reference':original['target']['reference'][obs],'chi_results':{}}
        for chi in plan['chi']:
            begin=time.monotonic();states=[]
            for arm in (0,1,2,3):
                if time.monotonic()>start+300:raise TimeoutError('Canonical refinement time budget reached')
                steps,sign=native[max(arm,1)];tn=evolve_canonical(18,support,steps,0. if arm==0 else 1.,chi)
                tensor=tn['I0'];tensor.modify(data=sign[obs]*tensor.data)
                save_tn(out/'states'/f'obs{obs:02d}_chi{chi}_arm{arm}',tn);states.append(tn)
            f=np.zeros((4,4));cost=[]
            for i in range(4):
                for j in range(i,4):
                    value,info=bounded_contract(overlap_network(states[i],states[j]));f[i,j]=f[j,i]=value;cost.append(info)
            record['chi_results'][str(chi)]={'failure':None,'overlaps_exact':f,
                'fits':{'exact':{'unregularized':fit_coefficients(f).to_dict(),'ridge':fit_coefficients(f,ridge=1/56).to_dict()}},
                'ideal_tn_expectation':expectation_zero(states[0]),'contraction_costs':cost,'seconds':time.monotonic()-begin,
                'method':'exact contraction of a chi-truncated mixed-canonical MPS; no BP approximation'}
            write(out/f'observable_{obs:02d}.json',record);print('CANONICAL_CHI_DONE',obs,chi,round(time.monotonic()-begin,2),flush=True)
        record['stability']=stability_flags(record['chi_results']['8'],record['chi_results']['16'])
        write(out/f'observable_{obs:02d}.json',record);summaries.append({'observable':obs,**record['stability']})
    summary={'status':'CANONICAL_REFINEMENT_FINISHED','observables':summaries,'local_stability_flags_pass':all(x['passes_local_flags'] for x in summaries),
        'full_27_observable_8_twirl_validation':False,'noise_model_validated':False,'six_by_six_started':False,
        'new_qpu_seconds':0,'tests_passed':tests.testsRun,'seconds':time.monotonic()-start}
    write(out/'summary.json',summary);write(out/'sha256.json',{str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file()})
    print('DONE',json.dumps(clean(summary)),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    try:
        with threadpool_limits(limits=1):run(args.output)
    except Exception as error:
        if args.output.exists():write(args.output/'failure.json',{'error_type':type(error).__name__,'reason':str(error),'six_by_six_started':False})
        raise
