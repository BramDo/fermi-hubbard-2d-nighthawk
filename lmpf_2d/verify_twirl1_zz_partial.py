"""Preserve and independently verify the seven completed ZZ states after timeout."""
from pathlib import Path
import argparse,json,shutil,sys,time
import numpy as np
import quimb.tensor as qtn
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from lmpf_2d.model import digest
from lmpf_2d.tn_storage import load_tn,bounded_contract
from lmpf_2d.verify_twirl1_zz import assignment_zz_penalty,kkt
from lmpf_2d.portable_archive import pack

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def write(path,value):
    with path.open('x',encoding='utf-8') as f:
        json.dump(value,f,indent=2,allow_nan=False);f.write('\n')

def run(out):
    started=time.monotonic();plan=read(out/'plan.json');failure=read(out/'failure.json')
    if (plan['observable'],plan['twirl'],plan['chi'])!=(22,1,[128,256]):
        raise ValueError('Unexpected operator scope')
    if failure['type']!='TimeoutError' or failure['reason']!='Local block deadline reached':
        raise ValueError('Not the recorded budget stop')
    if (out/'summary.json').exists() or (out/'chi256.json').exists():
        raise ValueError('Do not relabel a complete calculation as partial')
    if plan['max_contraction_flops']!=3e9 or plan['max_contraction_elements']!=2**22:
        raise ValueError('Changed resource guard')
    for name,h in plan['source_sha256'].items():
        if digest(ROOT/name)!=h or digest(out/'source_snapshot'/Path(name).name)!=h:
            raise ValueError('Changed frozen source '+name)
    for name,h in plan['input_sha256'].items():
        if digest(ROOT/name)!=h:raise ValueError('Changed frozen input '+name)
    expected={(128,i) for i in range(4)}|{(256,i) for i in range(3)}
    checkpointed=set()
    for path in out.glob('state_chi*_arm*.json'):
        item=read(path);checkpointed.add((item['chi'],item['arm']))
    if checkpointed!=expected:raise ValueError('Unexpected completed-state set')
    expected_files={f'obs22_chi{chi}_arm{arm}{ext}' for chi,arm in expected for ext in ('.json','.npz')}
    if {p.name for p in (out/'states').iterdir()}!=expected_files:
        raise ValueError('Unexpected or incomplete state file; inspect without removing it')
    calibration=plan['calibration_errors'];masks=plan['stratum_masks']
    penalty=assignment_zz_penalty(calibration,masks)
    np.testing.assert_allclose(penalty,plan['penalty'],atol=1e-14)
    grams={};peak=0;flops=0.;overlaps=0;gram_error=0.;weight_error=0.
    for chi,narms in ((128,4),(256,3)):
        states=[]
        for arm in range(narms):
            prefix=out/'states'/f'obs22_chi{chi}_arm{arm}'
            meta=read(out/f'state_chi{chi}_arm{arm}.json')
            if digest(prefix.with_suffix('.npz'))!=meta['npz_sha256'] or digest(prefix.with_suffix('.json'))!=meta['metadata_sha256']:
                raise ValueError('Changed saved state')
            rec=next(r for r in plan['inputs'] if r['factor']==max(arm,1))
            source=ROOT/rec['qpy']
            if digest(source)!=rec['qpy_sha256']:raise ValueError('Changed QPY')
            mask=rec['mask']
            if meta['unmask_sign']!=(-1)**(mask[8]+mask[9]):raise ValueError('Wrong joint mask')
            states.append(load_tn(prefix))
        gram=np.empty((narms,narms))
        for i in range(narms):
            for j in range(i,narms):
                raw=states[i].H & states[j]
                network=qtn.TensorNetwork([t.copy() for t in reversed(raw.tensors)])
                network.exponent=raw.exponent
                value,info=bounded_contract(network,max_elements=2**22,max_flops=3e9)
                gram[i,j]=gram[j,i]=value;overlaps+=1
                peak=max(peak,info['max_elements']);flops=max(flops,info['estimated_flops'])
        if not np.isfinite(gram).all() or np.linalg.eigvalsh(gram).min() < -1e-8:
            raise ValueError('Invalid saved-state Gram')
        if chi==128:
            saved=read(out/'chi128.json')
            gram_error=float(np.max(abs(gram-np.asarray(saved['raw_gram']))))
            np.testing.assert_allclose(gram,saved['raw_gram'],atol=1e-10,rtol=1e-9)
            corrected=gram.copy();corrected[0,0]=1.
            np.testing.assert_allclose(corrected,saved['exact_norm_gram'],atol=1e-10,rtol=1e-9)
            weights=kkt(corrected,penalty)
            weight_error=float(np.max(abs(weights-saved['weights'])))
            if weight_error>1e-9 or abs(weights.sum()-1)>1e-12:raise ValueError('Saved fit mismatch')
        grams[str(chi)]={'arms':list(range(narms)),'raw_gram':gram.tolist(),
            'minimum_eigenvalue':float(np.linalg.eigvalsh(gram).min()),
            'all_four_arms_available':narms==4,'high_chi_fit_performed':False}
    # No fit to the reduced three-arm submatrix; missing factor3 is not a zero.
    write(out/'partial_grams.json',grams)
    write(out/'partial_verification.json',{
        'status':'PARTIAL_SAVED_EVIDENCE_VERIFIED_NOT_CONVERGENCE',
        'completed_states':7,'missing_state':{'chi':256,'arm':3,'factor':3},
        'independent_overlaps':overlaps,'independent_complete_low_chi_fits':1,
        'maximum_low_chi_gram_error':gram_error,'maximum_low_chi_weight_error':weight_error,
        'largest_intermediate_elements':peak,'largest_estimated_flops':flops,
        'full_chi128_256_stability_available':False,'hardware_accuracy_validated':False,
        'new_qpu_seconds':0,'audit_seconds':time.monotonic()-started,
        'source_sha256':digest(Path(__file__))})
    archive_start=time.monotonic()
    large=[f'states/obs22_chi256_arm{arm}.npz' for arm in range(3)]
    if any((out/name).stat().st_size<10_000_000 for name in large):
        raise ValueError('Expected only the three large completed states')
    archived=pack(out,large)
    archived['seconds']=time.monotonic()-archive_start
    write(out/'archive/verification.json',archived)
    shutil.copyfile(Path(__file__),out/'source_snapshot'/Path(__file__).name)
    summary={'status':'INCOMPLETE_TIME_BUDGET','completed_states':7,'planned_states':8,
        'completed_chi128_arms':[0,1,2,3],'completed_chi256_arms':[0,1,2],
        'missing_chi256_arm':3,'missing_factor':3,'process_cap_seconds':600,
        'block_deadline_seconds':590,'automatic_retry':False,'tests_run':72,
        'partial_saved_evidence_verified':True,'archive_verified':archived['status']=='PASS',
        'full_stability_flags':None,'high_chi_coefficients':None,
        'hardware_accuracy_validated':False,'six_by_six_go':False,'new_qpu_seconds':0,
        'next_step':'Only missing twirl1 ZZ chi256 factor3 state, then full audits; not started'}
    write(out/'partial_summary.json',summary)
    write(out/'partial_manifest.json',{str(p.relative_to(out)):digest(p) for p in sorted(out.rglob('*')) if p.is_file()})
    print(json.dumps({'summary':summary,'verification':read(out/'partial_verification.json'),
                      'archive':archived}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path)
    with threadpool_limits(limits=1):run(p.parse_args().output)
