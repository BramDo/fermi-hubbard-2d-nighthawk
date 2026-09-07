"""Preserve all originals, verify lossless QPY mirrors, seal completed pilot."""
import gzip,hashlib,io,json,shutil,time
from pathlib import Path
import numpy as np
import run_hardware_compact_tflo as r

def mirror_bootstrap():
    original=r.RUN/'analysis/bootstrap.npz'
    folder=r.RUN/'git_bootstrap_mirrors'; folder.mkdir(exist_ok=True)
    with np.load(original,allow_pickle=False) as src:
        physical=src['physical']; null=src['null_physical']
    restored_p=[]; restored_n=[]; files=[]
    for a,arm in enumerate(r.ARMS):
        path=folder/f'bootstrap_{arm}.npz'
        if not path.exists():
            with path.open('xb') as f: np.savez_compressed(f,physical=physical[:,a],null_physical=null[:,a])
        with np.load(path,allow_pickle=False) as check:
            restored_p.append(check['physical']); restored_n.append(check['null_physical'])
        r.require(np.array_equal(restored_p[-1],physical[:,a]) and np.array_equal(restored_n[-1],null[:,a]),'Bootstrap mirror mismatch')
        r.require(path.stat().st_size<=10_000_000,'Arm mirror exceeds staging limit')
        files.append(dict(arm=arm,file=str(path.relative_to(r.RUN)),sha256=r.digest(path),bytes=path.stat().st_size))
    # NumPy NPZ output is deterministic in this recorded environment. Verify
    # byte-exact regeneration of the untouched combined original, not just arrays.
    rebuilt=io.BytesIO()
    np.savez_compressed(rebuilt,physical=np.stack(restored_p,axis=1),null_physical=np.stack(restored_n,axis=1))
    r.require(hashlib.sha256(rebuilt.getvalue()).hexdigest()==r.digest(original),'Combined NPZ reconstruction not byte exact')
    r.safe.save_if_absent(r.RUN/'bootstrap_mirrors.json',dict(original='analysis/bootstrap.npz',
        original_sha256=r.digest(original),original_bytes=original.stat().st_size,original_retained=True,
        mirrors=files,byte_exact_reconstruction_verified=True,numpy_version=np.__version__,
        reconstruction='np.savez_compressed(out, physical=np.stack([original_arm_physical,compact_arm_physical],axis=1), null_physical=np.stack([original_arm_null,compact_arm_null],axis=1))'))
    return dict(byte_exact=True,files=files)

def mirror_qpy():
    r.require(not (r.RUN/'delivery_sha256.json').exists(),'Delivery already sealed')
    mirrors=r.RUN/'git_qpy_mirrors'; mirrors.mkdir(exist_ok=True); rows=[]
    for index,p in enumerate(sorted(r.RUN.rglob('*.qpy'))):
        relative=str(p.relative_to(r.RUN)); packed=mirrors/(relative.replace('/','__')+'.gz')
        if not packed.exists():
            with p.open('rb') as src,packed.open('xb') as dst:
                with gzip.GzipFile(filename='',mode='wb',fileobj=dst,mtime=0) as gz: shutil.copyfileobj(src,gz)
        original=r.digest(p)
        with gzip.open(packed,'rb') as f: restored=hashlib.file_digest(f,'sha256').hexdigest()
        r.require(original==restored,'Lossless mirror failed')
        rows.append(dict(original=relative,sha256=original,bytes=p.stat().st_size,
            gzip=str(packed.relative_to(r.RUN)),gzip_sha256=r.digest(packed),gzip_bytes=packed.stat().st_size))
        if index%16==0: r.log('lossless_mirror_verified',index=index)
    return rows

def main():
    r.require(not (r.RUN/'delivery_sha256.json').exists(),'Delivery already sealed')
    r.verify(r.RUN,'frozen_inputs_sha256.json'); r.verify(r.RUN,'hardware_archive_sha256.json'); r.verify(r.RUN,'analysis_sha256.json')
    receipt=r.read(r.RUN/'job_receipt.json'); check=r.read(r.RUN/'retrieval_verification.json')
    cap=r.read(r.RUN/'provider_cap_verification.json'); metrics=r.read(r.RUN/'provider_metrics.json')
    r.require(check['job_id']==receipt['job_id']==cap['job_id'] and cap['verified'],'Receipt/cap mismatch')
    r.require(check['status']=='DONE_ARCHIVED_VERIFIED' and check['actual_shots']==38912 and check['provider_circuits_match']==76,'Incomplete retrieval')
    usage=metrics.get('usage',{})
    charge=usage.get('qpu_charge_time_seconds',usage.get('quantum_seconds'))
    if 'qpu_charge_time_seconds' in usage and 'quantum_seconds' in usage:
        r.require(usage['qpu_charge_time_seconds']==usage['quantum_seconds'],'Conflicting charge fields')
    r.require(isinstance(charge,(int,float)) and 0<=charge<=15,'Reported charge missing or above15s')
    started=time.perf_counter(); bootstrap=mirror_bootstrap(); rows=mirror_qpy()
    r.save(r.RUN/'qpy_mirrors.json',dict(files=rows,count=len(rows),originals_retained=True,
        original_bytes=sum(x['bytes'] for x in rows),gzip_bytes=sum(x['gzip_bytes'] for x in rows)))
    snap=r.RUN/'delivery_sources'; snap.mkdir()
    shutil.copyfile(Path(__file__),snap/Path(__file__).name)
    independent=r.read(r.RUN/'independent_result_verification.json')
    r.require(independent['status']=='PASS' and independent['source_sha256']==r.digest(r.ROOT/'verify_hardware_compact_result.py'),'Independent result check missing/changed')
    shutil.copyfile(r.ROOT/'verify_hardware_compact_result.py',snap/'verify_hardware_compact_result.py')
    result=r.read(r.RUN/'analysis/summary.json')
    r.save(r.RUN/'delivery_verification.json',dict(job_id=receipt['job_id'],cap_seconds=15,charged_quantum_seconds=charge,
        provider_circuits_verified=76,actual_shots=38912,tests_passed=r.read(r.RUN/'analysis_protocol.json')['tests_passed'],
        original_and_compact_TFLO_screen=result['holdout_screen_pass'],QPY_mirrors_verified=len(rows),
        complete_raw_results_saved=True,original_QPY_files_retained=True,old_archives_unchanged=True,
        combined_bootstrap_byte_exactly_recoverable=bootstrap['byte_exact'],
        independent_standard_library_result_check=independent,
        no_second_hardware_attempt=True,seconds=time.perf_counter()-started))
    attempt=r.read(r.LOCK)
    r.require(attempt['plan_sha256']==receipt['plan_sha256'] and attempt['authorization_consumed_on_attempt'],'Attempt provenance mismatch')
    r.save(r.RUN/'attempt_marker_copy.json',attempt)
    shutil.copyfile(r.RUN/'progress.jsonl',r.RUN/'progress_snapshot.jsonl')
    files=[p for p in r.RUN.rglob('*') if p.is_file() and p.name not in ('delivery_sha256.json','progress.jsonl')]
    r.save(r.RUN/'delivery_sha256.json',{str(p.relative_to(r.RUN)):r.digest(p) for p in files})
    r.verify(r.RUN,'delivery_sha256.json')
    # Only small non-QPY files and lossless mirrors enter Git; never delete originals.
    candidates=[p for p in files if p.suffix!='.qpy' and str(p.relative_to(r.RUN))!='analysis/bootstrap.npz']+[r.RUN/'delivery_sha256.json',r.LOCK]
    r.require(all(p.stat().st_size<=10_000_000 for p in candidates),'Individual file exceeds automatic staging cap')
    r.log('delivery_sealed',files=len(files),mirrors=len(rows),charged_quantum_seconds=charge)

if __name__=='__main__': main()
