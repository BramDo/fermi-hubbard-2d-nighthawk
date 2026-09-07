"""Lossless QPY mirrors for a complete, size-bounded local Git checkpoint."""
import gzip,hashlib,json,shutil
from pathlib import Path
import run_tflo_dd6_once as r


def main():
    if (r.RUN/'delivery_sha256.json').exists():
        r.verify(r.RUN,'delivery_sha256.json')
        print('Delivery already sealed and verified; no files changed.')
        return
    r.verify(r.RUN,'frozen_inputs_sha256.json')
    r.verify(r.RUN,'hardware_archive_sha256.json')
    r.verify(r.RUN,'analysis_sha256.json')
    folder=r.RUN/'git_qpy_mirrors'; folder.mkdir(exist_ok=True)
    records=[]
    for path in sorted(r.RUN.rglob('*.qpy')):
        relative=path.relative_to(r.RUN)
        expected=r.digest(path)
        dest=folder/(str(relative)+'.gz'); dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists():
            with path.open('rb') as source,dest.open('xb') as output:
                with gzip.GzipFile(filename='',mode='wb',fileobj=output,mtime=0) as packed:
                    shutil.copyfileobj(source,packed)
        with gzip.open(dest,'rb') as source:
            actual=hashlib.file_digest(source,'sha256').hexdigest()
        if actual!=expected or r.digest(path)!=expected:
            raise ValueError('Compressed QPY verification mismatch')
        if dest.stat().st_size>10_000_000:
            raise ValueError('Compressed mirror still exceeds automatic Git staging size')
        records.append({'original':str(relative),'gzip':str(dest.relative_to(r.RUN)),
            'uncompressed_sha256':expected,'gzip_sha256':r.digest(dest),
            'original_bytes':path.stat().st_size,'gzip_bytes':dest.stat().st_size})
    r.safe.save_if_absent(folder/'manifest.json',{'lossless':True,'originals_deleted':False,'files':records,
        'restore_instruction':'Decompress each gzip to its original relative path only if missing; verify uncompressed_sha256. Never overwrite originals.'})
    r.safe.save_if_absent(r.RUN/'submission_attempt_snapshot.json',r.read(r.LOCK))
    (r.RUN/'LOG_at_delivery.md').write_bytes((r.RUN/'LOG.md').read_bytes())
    r.safe.save_if_absent(r.RUN/'package_source_sha256.json',{Path(__file__).name:r.digest(Path(__file__))})
    r.save(r.RUN/'delivery_sha256.json',{str(p.relative_to(r.RUN)):r.digest(p) for p in r.RUN.rglob('*')
        if p.is_file() and p.name!='LOG.md'})
    r.verify(r.RUN,'delivery_sha256.json')
    print(json.dumps({'QPY_files_losslessly_mirrored':len(records),
        'original_QPY_bytes':sum(x['original_bytes'] for x in records),
        'gzip_bytes':sum(x['gzip_bytes'] for x in records),'originals_deleted':False,
        'delivery_hashes_verified':len(r.read(r.RUN/'delivery_sha256.json'))}),flush=True)


if __name__=='__main__': main()
