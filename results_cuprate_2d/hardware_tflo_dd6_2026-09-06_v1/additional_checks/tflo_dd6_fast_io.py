"""Resume unchanged frozen intent with byte-exact QPY checks; never submit."""
import argparse,hashlib,io,json,logging,shutil,time
from pathlib import Path
from qiskit import qpy,QuantumCircuit
from qiskit.primitives.containers import SamplerPub
from qiskit_ibm_runtime import QiskitRuntimeService
from cuprate_2d_hubbard_pipeline import Cuprate2DConfig
from cuprate_2d_tflo import bind,embed_measurement,decode_bitstrings
import cuprate_2d_tflo_dd6 as m
import run_tflo_dd6_once as r


def qpy_bytes(circuit):
    b=io.BytesIO(); qpy.dump(circuit,b); return b.getvalue()


def native_equal(a,b):
    """Exact native instruction comparison; no graph-isomorphism search."""
    if (a.num_qubits,a.num_clbits,len(a.data),a.metadata)!=(b.num_qubits,b.num_clbits,len(b.data),b.metadata): return False
    if float(a.global_phase)!=float(b.global_phase): return False
    for x,y in zip(a.data,b.data):
        if x.operation.name!=y.operation.name or x.operation.label!=y.operation.label: return False
        if x.operation.base_class!=y.operation.base_class: return False
        if getattr(x.operation,'condition',None)!=getattr(y.operation,'condition',None): return False
        if tuple(x.operation.params)!=tuple(y.operation.params): return False
        if x.operation.name=='delay' and x.operation.unit!=y.operation.unit: return False
        if [a.find_bit(q).index for q in x.qubits]!=[b.find_bit(q).index for q in y.qubits]: return False
        if [a.find_bit(q).index for q in x.clbits]!=[b.find_bit(q).index for q in y.clbits]: return False
    return True


def save_checked(path,circuit):
    wanted=qpy_bytes(circuit)
    if path.exists():
        actual=path.read_bytes()
        if actual!=wanted:
            old=qpy.load(io.BytesIO(actual))[0]
            if not native_equal(old,circuit): raise ValueError('Existing native circuit changed; refuse overwrite')
    else:
        with path.open('xb') as file: file.write(wanted)
        actual=wanted
    restored=qpy.load(io.BytesIO(actual))[0]
    if qpy_bytes(restored)!=actual: raise ValueError('QPY byte roundtrip changed')
    if restored.metadata!=circuit.metadata: raise ValueError('Metadata changed')
    return hashlib.sha256(actual).hexdigest()


def resume():
    r.require(not r.LOCK.exists(),'Hardware attempt already exists')
    r.require(not (r.RUN/'frozen_inputs_sha256.json').exists(),'Inputs already sealed')
    plan=r.read(r.RUN/'plan.json'); ph=r.digest(r.RUN/'plan.json')
    m.validate_records(plan['records'])
    for name,h in plan['source_sha256'].items(): r.require(r.digest(r.ROOT/name)==h,'Original source changed')
    cfg=Cuprate2DConfig(**plan['config']); templates={}
    for dd in (False,True):
        for twirl in range(4):
            path=r.RUN/'local_only'/f'scheduled_dd{int(dd)}_twirl{twirl}.qpy'
            raw=path.read_bytes(); c=qpy.load(io.BytesIO(raw))[0]
            r.require(qpy_bytes(c)==raw,'Scheduled template byte roundtrip failed')
            templates[dd,twirl]=c
    records=[]; begun=time.perf_counter()
    for index,rec in enumerate(plan['records']):
        if rec['role']=='calibration':
            c=QuantumCircuit(72)
            if rec['state']: c.x(range(72))
            c=embed_measurement(c,plan['layout72'],120)
        else:
            c=bind(templates[rec['dd'],rec['twirl_id']],cfg,rec['T'],rec['U'])
        c.metadata={**rec,'pilot_index':index,'pilot_plan_sha256':ph,'pilot_tag':plan['tag']}
        r.check_input(c,rec,index,ph)
        h=save_checked(r.RUN/'bound_inputs'/f'circuit_{index:03d}.qpy',c)
        records.append({'index':index,'qpy_sha256':h,'byte_roundtrip':True})
        if index%10==0: r.log('fast_bound_archived',index=index,circuits=m.PUBS)
    extra=r.RUN/'additional_checks'; extra.mkdir(exist_ok=True)
    shutil.copyfile(Path(__file__),extra/Path(__file__).name)
    r.save(r.RUN/'io_revision.json',{'original_plan_sha256':ph,'plan_changed':False,'physics_changed':False,
        'reason':'Replace expensive generic circuit equivalence by exact native/byte comparison',
        'source_sha256':r.digest(Path(__file__)),'seconds':time.perf_counter()-begun,'checks':records})
    r.save(r.RUN/'frozen_inputs_sha256.json',{str(p.relative_to(r.RUN)):r.digest(p)
        for p in r.RUN.rglob('*') if p.is_file() and p.name!='LOG.md'})
    r.verify(r.RUN,'frozen_inputs_sha256.json')
    r.log('prepared_not_submitted',circuits=m.PUBS,shots=m.TOTAL,cap=m.CAP,qpu_seconds=0)


def retrieve():
    receipt=r.read(r.RUN/'job_receipt.json')
    r.require(receipt['plan_sha256']==r.digest(r.RUN/'plan.json'),'Receipt mismatch')
    service=r.safe.safe_provider('Retrieval authentication',QiskitRuntimeService,name=r.ACCOUNT)
    job=r.safe.safe_provider('Existing job',service.job,receipt['job_id'])
    status=r.safe.safe_provider('Job status',job.status); status=str(getattr(status,'name',status))
    r.log('job_status',job_id=receipt['job_id'],status=status); r.verify_cap(job)
    if status not in ('DONE','ERROR','CANCELED','CANCELLED'): return
    metrics=r.safe.safe_provider('Job metrics',job.metrics)
    r.safe.save_if_absent(r.RUN/'provider_metrics.json',metrics)
    if status!='DONE':
        r.safe.save_if_absent(r.RUN/'FAILED.json',{'status':status,'usage':metrics.get('usage'),'resubmit_allowed':False})
        return
    plan,expected=r.frozen()
    inputs=r.safe.safe_provider('Provider inputs',lambda:job.inputs)
    actual=[SamplerPub.coerce(p) for p in inputs['pubs']]
    r.require(len(actual)==len(expected)==m.PUBS,'PUB count changed')
    folder=r.RUN/'provider_inputs'; folder.mkdir(exist_ok=True)
    for i,(got,wanted) in enumerate(zip(actual,expected)):
        r.require(got.shape==wanted.shape==() and got.shots==wanted.shots==m.SHOTS,'Exposure changed')
        gb,wb=qpy_bytes(got.circuit),qpy_bytes(wanted.circuit)
        r.require(gb==wb or native_equal(got.circuit,wanted.circuit),'Actual provider circuit changed')
        save_checked(folder/f'circuit_{i:03d}.qpy',got.circuit)
        if i%10==0: r.log('provider_circuit_verified',index=i)
    r.safe.save_if_absent(folder/'options.json',{k:v for k,v in inputs.items() if k!='pubs'})
    result=r.safe.safe_provider('Completed result',job.result)
    r.require(len(result)==m.PUBS,'Missing result')
    r.safe.save_if_absent(r.RUN/'provider_result_complete.json',result)
    rows=[]
    for i,(pub,rec) in enumerate(zip(result,plan['records'])):
        meta=pub.metadata.get('circuit_metadata',{})
        r.require(meta.get('pilot_index')==i and meta.get('pilot_plan_sha256')==receipt['plan_sha256'],'Result provenance')
        r.require(all(meta.get(k)==v for k,v in rec.items()),'Result metadata changed')
        bits=pub.data.meas
        r.require(bits.shape==() and bits.num_bits==72 and bits.num_shots==m.SHOTS,'Result shape changed')
        strings=bits.get_bitstrings(); decode_bitstrings(strings,72,rec['readout_mask_little_endian'])
        rows.append({**rec,'bitstrings':strings})
    r.safe.save_if_absent(r.RUN/'raw_bitstrings.json',{'job_id':receipt['job_id'],'width':72,'records':rows})
    r.safe.save_if_absent(r.RUN/'retrieval_verification.json',{'status':'DONE_ARCHIVED_VERIFIED','job_id':receipt['job_id'],
        'actual_shots':sum(len(x['bitstrings']) for x in rows),'provider_circuits_match':m.PUBS,
        'verification':'byte equality or exact native instruction fields; no graph-isomorphism shortcut',
        'usage':metrics.get('usage')})
    r.safe.save_if_absent(r.RUN/'hardware_archive_sha256.json',{str(p.relative_to(r.RUN)):r.digest(p)
        for p in r.RUN.rglob('*') if p.is_file() and p.name!='LOG.md'})
    r.log('retrieved',shots=m.TOTAL,usage=metrics.get('usage'))


def tests():
    import tempfile
    c=QuantumCircuit(2,2); c.x(0); c.rz(.2,1); c.cz(0,1); c.measure([0,1],[0,1]); c.metadata={'test':True}
    d=qpy.load(io.BytesIO(qpy_bytes(c)))[0]
    assert native_equal(c,d)
    with tempfile.TemporaryDirectory() as folder:
        p=Path(folder)/'test.qpy'; save_checked(p,c); save_checked(p,c)
        bad=c.copy(); bad.x(1)
        try: save_checked(p,bad)
        except ValueError: pass
        else: raise AssertionError('Changed circuit accepted')
        assert p.read_bytes()==qpy_bytes(c)
    bad=c.copy(); bad.global_phase=.1; assert not native_equal(c,bad)
    bad=c.copy(); bad.metadata={'test':False}; assert not native_equal(c,bad)
    print('Fast I/O tests passed: byte roundtrip, preservation, changed gates/phase/metadata rejected.',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('action',choices=['resume','retrieve','test'])
    args=parser.parse_args(); logging.disable(logging.CRITICAL)
    if args.action=='test': tests()
    else: globals()[args.action]()
