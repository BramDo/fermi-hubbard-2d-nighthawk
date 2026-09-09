"""Finish exactly one missing ZZ state; preserve all seven prior checkpoints."""
from pathlib import Path
import argparse,copy,io,json,resource,shutil,sys,time,unittest
import numpy as np
from qiskit import qpy
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from lmpf_2d.twirl1_zz import (ARCHIVE,read,write,TimedStep,analyze_gram,compare_levels,
                             guarded_overlap,zz_penalty,TESTS as OLD_TESTS)
from lmpf_2d.archive_3x3 import active_circuit,record_sign
from lmpf_2d.canonical_chain import evolve_canonical
from lmpf_2d.model import FrozenSurrogate,digest
from lmpf_2d.operators import compile_steps,fuse_steps
from lmpf_2d.tn_storage import save_tn,load_tn
from scripts.restore_archives import run as restore_run,safe_path
PARENT=ROOT/'results_cuprate_2d/lmpf_3x3_twirl1_zz_2026-09-09_v1'
TESTS=OLD_TESTS+('test_lmpf_resume_twirl1_zz',)
REUSED=[(128,arm) for arm in range(4)]+[(256,arm) for arm in range(3)]

def copy_verified(source,dest,expected):
    if digest(source)!=expected:raise ValueError('Source checksum mismatch')
    with source.open('rb') as inp,dest.open('xb') as out:
        shutil.copyfileobj(inp,out)
    if digest(dest)!=expected:raise ValueError('Copied checksum mismatch')

def missing_spec(plan):
    if (plan['twirl'],plan['observable'],plan['chi'],plan['support'])!=(1,22,[128,256],{'8':'Z','9':'Z'}):
        raise ValueError('Wrong resumed scientific scope')
    if plan['shot_allocation']!=[43,7,14] or plan['eta']!=1.:
        raise ValueError('Changed fixed penalty')
    if plan['max_contraction_flops']!=3e9 or plan['max_contraction_elements']!=2**22:
        raise ValueError('Changed contraction limits')
    records=[r for r in plan['inputs'] if r['factor']==3]
    if len(records)!=1 or records[0]['record_index']!=2 or records[0]['twirl']!=1:
        raise ValueError('Wrong missing native input')
    return {'chi':256,'arm':3,'factor':3,'record':records[0]}

def verify_parent():
    plan=read(PARENT/'plan.json');partial=read(PARENT/'partial_summary.json')
    if (partial['status'],partial['completed_states'],partial['missing_chi256_arm'])!=('INCOMPLETE_TIME_BUDGET',7,3):
        raise ValueError('Parent is not the approved partial run')
    manifest=read(PARENT/'partial_manifest.json')
    absent=[name for name in manifest if not safe_path(PARENT,name).is_file()]
    if absent:
        archived={r['path'] for r in read(PARENT/'archive/manifest.json')['original_files']}
        if not set(absent)<=archived:raise FileNotFoundError('Nonarchived parent files are missing')
        restore_run(PARENT,restore=True)
    for name,h in manifest.items():
        if digest(safe_path(PARENT,name))!=h:raise ValueError('Parent artifact changed: '+name)
    for name,h in plan['source_sha256'].items():
        if digest(ROOT/name)!=h or digest(PARENT/'source_snapshot'/Path(name).name)!=h:
            raise ValueError('Parent numerical source changed: '+name)
    for name,h in plan['input_sha256'].items():
        if digest(ROOT/name)!=h:raise ValueError('Parent input changed: '+name)
    return plan,manifest

def run(out):
    start=time.monotonic();deadline=start+290.
    if out.exists():raise FileExistsError('Preserve previous resumption')
    if shutil.disk_usage(ROOT).free<500_000_000:raise RuntimeError('Insufficient storage')
    parent,manifest=verify_parent();spec=missing_spec(parent)
    out.mkdir(parents=True);(out/'states').mkdir();(out/'source_snapshot').mkdir()
    extras=[ROOT/'lmpf_2d'/n for n in ('resume_twirl1_zz.py','verify_resumed_twirl1_zz.py')]
    extras += [ROOT/'test_lmpf_resume_twirl1_zz.py',PARENT/'NEXT_MISSING_ARM.md']
    sources=[ROOT/name for name in parent['source_sha256']]+extras
    for source in sources:
        copy_verified(source,out/'source_snapshot'/source.name,digest(source))
    stream=io.StringIO();suite=unittest.TestSuite()
    for name in TESTS:suite.addTests(unittest.defaultTestLoader.loadTestsFromName(name))
    tests=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    (out/'tests.txt').write_text(stream.getvalue(),encoding='utf-8')
    if not tests.wasSuccessful():raise RuntimeError('Prerequisite tests failed')
    print('TESTS_PASSED',tests.testsRun,flush=True)
    reused=[]
    for chi,arm in REUSED:
        names=[f'states/obs22_chi{chi}_arm{arm}{ext}' for ext in ('.json','.npz')]
        names += [f'state_chi{chi}_arm{arm}.json']
        for name in names:copy_verified(PARENT/name,out/name,manifest[name])
        reused.append({'chi':chi,'arm':arm,'files':{name:manifest[name] for name in names}})
    copy_verified(PARENT/'failure.json',out/'parent_failure.json',manifest['failure.json'])
    record=spec['record'];path=ROOT/record['qpy']
    if digest(path)!=record['qpy_sha256'] or digest(ARCHIVE/'bound_inputs'/path.name)!=record['qpy_sha256']:
        raise ValueError('Wrong missing-arm circuit')
    profile=FrozenSurrogate(ARCHIVE/'live_backend_properties.json',parent['layout'])
    if json.loads(json.dumps(profile.metadata()))!=parent['noise']:
        raise ValueError('Changed frozen noise model')
    with path.open('rb') as f:circuits=qpy.load(f)
    if len(circuits)!=1:raise ValueError('Expected one circuit')
    qc=active_circuit(circuits[0],parent['layout'])
    if qc.count_ops().get('cz')!=3024:raise ValueError('Wrong factor3 CZ count')
    steps=fuse_steps(compile_steps(qc,profile.rate))
    if {s.qubits for s in steps if len(s.qubits)==2}!={(q,q+1) for q in range(17)}:
        raise ValueError('Native graph changed')
    steps=[TimedStep(s,deadline) for s in steps]
    penalty=zz_penalty(parent['calibration_errors'],parent['stratum_masks'])
    np.testing.assert_array_equal(penalty[0,0],parent['penalty'])
    plan=copy.deepcopy(parent)
    plan.update(schema='twirl1-zz-resumed-one-arm-v1',process_timeout_seconds=300,
        block_deadline_seconds=290,new_states_maximum=1,
        reused_from=str(PARENT.relative_to(ROOT)),reused_state_count=7,reused_states=reused,
        parent_manifest_sha256=digest(PARENT/'partial_manifest.json'),
        parent_process_timeout_seconds=600,parent_timeout_preserved=True,
        authorization='User approved only the missing arm with at most five additional local calculation minutes; no QPU.',
        source_sha256={str(p.relative_to(ROOT)):digest(p) for p in sources})
    plan['input_sha256'].update({str((PARENT/name).relative_to(ROOT)):digest(PARENT/name)
        for name in ('plan.json','partial_manifest.json','partial_summary.json','failure.json')})
    write(out/'plan.json',plan)
    print('REUSED_STATES_VERIFIED',len(reused),flush=True)
    t0=time.monotonic()
    tn=evolve_canonical(18,{8:'Z',9:'Z'},steps,1.,256)
    sign=int(record_sign(record['mask'])[22]);tensor=tn['I0'];tensor.modify(data=sign*tensor.data)
    prefix=out/'states/obs22_chi256_arm3';save_tn(prefix,tn);restored=load_tn(prefix)
    error=abs(guarded_overlap(tn,tn)[0]-guarded_overlap(restored,restored)[0])
    if error>1e-10:raise ValueError('New-state roundtrip mismatch')
    elapsed=time.monotonic()-t0
    meta={'chi':256,'arm':3,'native_factor':3,'unmask_sign':sign,'seconds':elapsed,
        'roundtrip_norm_error':error,'npz_sha256':digest(prefix.with_suffix('.npz')),
        'metadata_sha256':digest(prefix.with_suffix('.json'))}
    write(out/'state_chi256_arm3.json',meta)
    print('MISSING_STATE_DONE',round(elapsed,3),flush=True)
    del tn,restored
    levels={}
    for chi in (128,256):
        if time.monotonic()>=deadline:raise TimeoutError('Resumption budget before Gram completion')
        t0=time.monotonic();states=[load_tn(out/'states'/f'obs22_chi{chi}_arm{arm}') for arm in range(4)]
        gram=np.empty((4,4));costs=[]
        for i in range(4):
            for j in range(i,4):
                value,info=guarded_overlap(states[i],states[j])
                gram[i,j]=gram[j,i]=value;costs.append(info)
        if chi==128:np.testing.assert_allclose(gram,read(PARENT/'chi128.json')['raw_gram'],atol=1e-12)
        result=analyze_gram(gram,penalty)
        result.update(states=[read(out/f'state_chi{chi}_arm{arm}.json') for arm in range(4)],
            contraction_costs=costs,gram_and_fit_seconds_this_run=time.monotonic()-t0,
            state_seconds_scope='Original generation time; seven states reused without propagation')
        write(out/f'chi{chi}.json',result);levels[str(chi)]=result
        del states
    summary={'status':'TWIRL1_ZZ_RESUMPTION_COMPLETE',
        'stability':compare_levels(levels['128'],levels['256']),
        'tests_run':tests.testsRun,'new_states':1,'reused_states':7,'assembled_states':8,
        'missing_state_seconds':elapsed,'seconds':time.monotonic()-start,
        'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        'parent_timeout_preserved':True,'new_qpu_seconds':0,
        'hardware_weights_applied':False,'hardware_accuracy_validated':False,
        'full_3x3_or_8_twirl_validation':False,'six_by_six_go':False}
    write(out/'summary.json',summary)
    # Check parent immutable evidence again; copied data remain byte-for-byte equal.
    for item in reused:
        for name,h in item['files'].items():
            if digest(PARENT/name)!=h or digest(out/name)!=h:raise ValueError('Reuse changed data')
    write(out/'sha256.json',{str(p.relative_to(out)):digest(p) for p in sorted(out.rglob('*')) if p.is_file()})
    print('DONE',json.dumps(summary),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    if args.output.exists():p.error('Preserve existing output; no automatic retry')
    try:
        with threadpool_limits(limits=1):run(args.output)
    except Exception as error:
        if args.output.exists():write(args.output/'failure.json',{'type':type(error).__name__,
            'reason':str(error),'automatic_retry':False,'new_qpu_seconds':0})
        raise
