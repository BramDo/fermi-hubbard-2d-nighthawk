"""One bounded twirl1 Z_down calculation; no target scores or cloud access."""
from pathlib import Path
import argparse, gc, importlib.metadata as md, io, json, resource
import shutil, sys, time, unittest
import numpy as np
from qiskit import qpy
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from lmpf_2d.archive_3x3 import ARCHIVE,active_circuit,record_sign
from lmpf_2d.canonical_chain import evolve_canonical
from lmpf_2d.chain_contract import chain_overlap
from lmpf_2d.tn_storage import save_tn,load_tn
from lmpf_2d.model import FrozenSurrogate,digest
from lmpf_2d.operators import compile_steps,fuse_steps
from lmpf_2d.shot_aware import variance_penalties
from lmpf_2d.twirl1_zup import TimedStep,analyze_gram,compare_levels
from lmpf_2d.twirl_reuse_check import TESTS as OLD_TESTS

REUSE=ROOT/'results_cuprate_2d/lmpf_3x3_twirl_reuse_2026-09-09_v1'
CAL_PARENT=ROOT/'results_cuprate_2d/lmpf_3x3_shot_aware_2026-09-09_v1'
PREVIOUS=ROOT/'results_cuprate_2d/lmpf_3x3_twirl1_zup_2026-09-09_v1'
TESTS=OLD_TESTS+('test_lmpf_twirl1_zup','test_lmpf_twirl1_zdown')
OBSERVABLE=9
CENTRAL_MODE_INDEX=1
SUPPORT={OBSERVABLE:'Z'}

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def write(path,value):
    with path.open('x',encoding='utf-8') as f:
        json.dump(value,f,indent=2,allow_nan=False);f.write('\n')

def zdown_penalty(errors,masks):
    e=np.asarray(errors,float);m=np.asarray(masks)
    if e.shape!=(2,2) or not np.isfinite(e).all() or np.any(e<0) or np.any(e>=1):
        raise ValueError('Two central modes and two calibration errors required')
    if m.shape!=(4,2) or not np.isin(m,[0,1]).all():
        raise ValueError('Four stratum masks for two central modes required')
    return variance_penalties(e[None],m)[:,CENTRAL_MODE_INDEX:CENTRAL_MODE_INDEX+1,:]

def run(out):
    start=time.monotonic();deadline=start+590.
    if out.exists():raise FileExistsError('Preserve previous run')
    if shutil.disk_usage(ROOT).free<500_000_000:raise RuntimeError('Insufficient disk headroom')
    out.mkdir(parents=True);(out/'states').mkdir();(out/'source_snapshot').mkdir()
    names=('twirl1_zdown.py','verify_twirl1_zdown.py','twirl1_zup.py',
        'canonical_chain.py','chain_contract.py',
        'tn_storage.py','archive_3x3.py','model.py','operators.py','product.py','fit.py',
        'norm_control.py','shot_aware.py','single_twirl.py','hardware_inputs.py',
        'twirl_reuse_check.py','verify_twirl_reuse.py','verify_shot_aware.py',
        'verify_single_twirl.py')
    sources=[ROOT/'lmpf_2d'/name for name in names]
    sources += [ROOT/(name+'.py') for name in TESTS]+[PREVIOUS/'NEXT_ZDOWN.md']
    for source in sources:shutil.copyfile(source,out/'source_snapshot'/source.name)
    previous=read(PREVIOUS/'summary.json')
    if digest(PREVIOUS/'summary.json')!=read(PREVIOUS/'sha256.json')['summary.json']:
        raise ValueError('Changed previous operator gate')
    if not previous['stability']['exact_norm_local_flags_pass']:
        raise ValueError('Previous Z_up gate not passed')
    original=read(ARCHIVE/'plan.json');receipt=read(ARCHIVE/'job_receipt.json')
    if digest(ARCHIVE/'plan.json')!=receipt['plan_sha256']:raise ValueError('Plan receipt mismatch')
    layout=original['layout'];profile=FrozenSurrogate(ARCHIVE/'live_backend_properties.json',layout)
    if profile.backend!=original['backend'] or receipt['backend']!=original['backend'] or len(layout)!=18:
        raise ValueError('Backend/width mismatch')
    frozen=CAL_PARENT/'frozen_rule_and_weights.json'
    if digest(frozen)!=read(CAL_PARENT/'sha256.json')['frozen_rule_and_weights.json']:
        raise ValueError('Changed calibration-source artifact')
    # This file contains only calibration, TN Grams and frozen rules/weights:
    # no target bitstrings, target means or exact target expectations.
    errors=np.asarray(read(frozen)['calibration_errors'])
    old_inputs=read(REUSE/'summary.json')['records']
    native={};inputs=[];masks=[]
    for factor,expected_index in ((1,25),(2,19),(3,2)):
        record=original['records'][expected_index]
        if record.get('factor')!=factor or record['twirl_id']!=1:
            raise ValueError('Fixed twirl1 identity changed')
        path=ARCHIVE/'provider_inputs'/f'circuit_{expected_index:03d}.qpy'
        old=next(r for r in old_inputs if r['factor']==factor and r['twirl']==1)
        if digest(path)!=old['provider_sha256'] or digest(path)!=digest(ARCHIVE/'bound_inputs'/path.name):
            raise ValueError('Provider/bound/reuse-check mismatch')
        with path.open('rb') as f:circuits=qpy.load(f)
        if len(circuits)!=1:raise ValueError('Expected one provider circuit')
        qc=active_circuit(circuits[0],layout)
        if qc.count_ops().get('cz')!=1008*factor:raise ValueError('Native folding mismatch')
        mask=record['readout_mask_little_endian']
        if len(mask)!=18 or set(mask)-{0,1}:raise ValueError('Invalid native mask')
        steps=fuse_steps(compile_steps(qc,profile.rate))
        edges={s.qubits for s in steps if len(s.qubits)==2}
        if edges!={(q,q+1) for q in range(17)}:raise ValueError('Not the verified open chain')
        native[factor]=([TimedStep(s,deadline) for s in steps],int(record_sign(mask)[OBSERVABLE]))
        masks.append(np.asarray(mask)[[8,9]])
        inputs.append({'factor':factor,'record_index':expected_index,'twirl':1,
            'qpy':str(path.relative_to(ROOT)),'qpy_sha256':digest(path),'mask':mask,
            'native_gates':dict(qc.count_ops()),'depth':qc.depth(),'classical_blocks':len(steps)})
    masks=np.array([masks[0],masks[0],masks[1],masks[2]])
    penalty=zdown_penalty(errors,masks)
    plan={'schema':'twirl1-central-zdown-chi64-128-v1','job_id':receipt['job_id'],
        'backend':profile.backend,'twirl':1,'observable':OBSERVABLE,'support':{str(OBSERVABLE):'Z'},
        'central_calibration_mode_index':CENTRAL_MODE_INDEX,
        'physical_mode':layout[OBSERVABLE],'layout':layout,'chi':[64,128],
        'arms':['ideal_factor1','noisy_factor1','noisy_factor2','noisy_factor3'],
        'inputs':inputs,'noise':profile.metadata(),'calibration_errors':errors.tolist(),
        'stratum_masks':masks.tolist(),'penalty':penalty[0,0].tolist(),
        'shot_allocation':[43,7,14],'eta':1.,'new_states_maximum':8,
        'process_timeout_seconds':600,'block_deadline_seconds':590,
        'relative_tolerance':.01,'coefficient_l1_tolerance':.05,
        'max_contraction_elements':2**22,'max_contraction_flops':2e9,
        'target_bitstrings_read':False,'reference_expectations_used':False,
        'twirl0_states_reused':False,'zup_states_reused':False,'new_qpu_seconds':0,
        'source_sha256':{str(p.relative_to(ROOT)):digest(p) for p in sources},
        'input_sha256':{str(p.relative_to(ROOT)):digest(p) for p in
            (ARCHIVE/'plan.json',ARCHIVE/'job_receipt.json',profile.path,frozen,
             CAL_PARENT/'sha256.json',REUSE/'summary.json',
             PREVIOUS/'summary.json',PREVIOUS/'sha256.json')},
        'versions':{name:md.version(name) for name in ('numpy','scipy','qiskit','quimb','cotengra')}}
    write(out/'plan.json',plan)
    stream=io.StringIO();suite=unittest.TestSuite()
    for name in TESTS:suite.addTests(unittest.defaultTestLoader.loadTestsFromName(name))
    tests=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    (out/'tests.txt').write_text(stream.getvalue(),encoding='utf-8')
    if not tests.wasSuccessful():raise RuntimeError('Prerequisite tests failed')
    print('TESTS_PASSED',tests.testsRun,flush=True)
    levels={}
    for chi in (64,128):
        begin=time.monotonic();states=[];state_metadata=[]
        for arm in range(4):
            if time.monotonic()>=deadline:raise TimeoutError('Deadline before next state')
            steps,sign=native[max(arm,1)];t0=time.monotonic()
            tn=evolve_canonical(18,SUPPORT,steps,0. if arm==0 else 1.,chi)
            tensor=tn['I0'];tensor.modify(data=sign*tensor.data)
            prefix=out/'states'/f'obs{OBSERVABLE:02d}_chi{chi}_arm{arm}'
            save_tn(prefix,tn);restored=load_tn(prefix)
            error=abs(chain_overlap(tn,tn)[0]-chain_overlap(restored,restored)[0])
            if error>1e-10:raise ValueError('Checkpoint roundtrip failure')
            meta={'chi':chi,'arm':arm,'native_factor':max(arm,1),'unmask_sign':sign,
                'seconds':time.monotonic()-t0,'roundtrip_norm_error':error,
                'npz_sha256':digest(prefix.with_suffix('.npz')),
                'metadata_sha256':digest(prefix.with_suffix('.json'))}
            write(out/f'state_chi{chi}_arm{arm}.json',meta)
            states.append(restored);state_metadata.append(meta)
            del tn
            print('STATE_DONE',chi,arm,round(meta['seconds'],3),flush=True)
        gram=np.empty((4,4));costs=[]
        for i in range(4):
            for j in range(i,4):
                value,cost=chain_overlap(states[i],states[j])
                gram[i,j]=gram[j,i]=value;costs.append(cost)
        result=analyze_gram(gram,penalty)
        result.update(states=state_metadata,contraction_costs=costs,seconds=time.monotonic()-begin)
        write(out/f'chi{chi}.json',result);levels[str(chi)]=result
        print('CHI_DONE',chi,'raw_F00',gram[0,0],'weights',result['weights'],flush=True)
        del states,restored;gc.collect()
    flags=compare_levels(levels['64'],levels['128'])
    summary={'status':'TWIRL1_ZDOWN_OPERATOR_CHECK_FINISHED','stability':flags,
        'tests_run':tests.testsRun,'new_states':8,'seconds':time.monotonic()-start,
        'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        'new_qpu_seconds':0,'hardware_weights_applied':False,
        'hardware_accuracy_validated':False,'full_3x3_or_8_twirl_validation':False,
        'six_by_six_go':False,'next_candidate_if_local_flags_pass':'twirl1 onsite ZZ; not started'}
    write(out/'summary.json',summary)
    write(out/'sha256.json',{str(p.relative_to(out)):digest(p) for p in sorted(out.rglob('*')) if p.is_file()})
    print('DONE',json.dumps(summary),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():parser.error('Output exists; no automatic retry')
    try:
        with threadpool_limits(limits=1):run(args.output)
    except Exception as error:
        if args.output.exists():
            write(args.output/'failure.json',{'type':type(error).__name__,'reason':str(error),
                'new_qpu_seconds':0,'automatic_retry':False,'six_by_six_go':False})
        raise
