"""Copy a physics working tree without altering it; archive heavy files losslessly."""
import argparse, gzip, hashlib, json, os, re, shutil, subprocess, tempfile, time, zlib
from pathlib import Path

EXCLUDED_DIRS={'.git','.agents','.codex','__pycache__','.ipynb_checkpoints','.venv','_local_migration_backup'}
SECRET_NAMES={'auth.json','qiskit-ibm.json','credentials.json','hosts.yml'}
SECRET_PATTERNS=[rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',rb'gh[pousr]_[A-Za-z0-9]{30,}',rb'github_pat_[A-Za-z0-9_]{30,}',rb'AKIA[0-9A-Z]{16}',rb'(?i)(?:api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret)[\"\x27]?\s*[:=]\s*[\"\x27]([A-Za-z0-9_./+\-]{28,})[\"\x27]']
CHUNK=8_000_000

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        while block:=f.read(1024*1024): h.update(block)
    return h.hexdigest()

def write_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f: json.dump(value,f,indent=2,ensure_ascii=False)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--source',type=Path,required=True); ap.add_argument('--destination',type=Path,required=True); args=ap.parse_args()
    src=args.source.resolve(); dst=args.destination.resolve()
    if not (src/'.git').exists() or dst.exists() or src==dst or src in dst.parents: raise ValueError('Expected existing source repo and new separate destination')
    candidates=[]; excluded=[]
    for base,dirs,names in os.walk(src):
        dirs[:]=[d for d in dirs if d not in EXCLUDED_DIRS]
        for name in names:
            p=Path(base)/name; rel=p.relative_to(src)
            if name in SECRET_NAMES or name.startswith('.env') or p.suffix.lower() in ('.pyc','.pem','.key','.exe','.o','.mod'):
                excluded.append(str(rel)); continue
            candidates.append((p,rel))
    # Scan before creating a destination. Report paths and detector numbers only.
    issues=[]
    text_ext={'.py','.md','.json','.jsonl','.yaml','.yml','.toml','.txt','.ps1','.sh','.html','.ipynb','.ini','.cfg'}
    for p,rel in candidates:
        if p.suffix.lower() in text_ext and p.stat().st_size<30_000_000:
            blob=p.read_bytes()
            for i,pattern in enumerate(SECRET_PATTERNS):
                if re.search(pattern,blob): issues.append({'path':str(rel),'detector':i})
    if issues: print(json.dumps({'credential_scan':'BLOCKED','issues':issues})); raise RuntimeError('Review possible credentials before copying')
    dst.mkdir(parents=False); (dst/'migration').mkdir(); (dst/'archive/objects').mkdir(parents=True)
    head=subprocess.check_output(['git','-C',str(src),'rev-parse','HEAD'],text=True).strip()
    dirty=subprocess.check_output(['git','-C',str(src),'status','--porcelain','--untracked-files=no'],text=True)
    copied=[]; archived=[]; objects={}; last=time.monotonic()
    for number,(p,rel) in enumerate(sorted(candidates),1):
        # Disable inherited workflow auto-deployment while preserving its source.
        target_rel=Path('archive/legacy_workflows')/rel.relative_to('.github') if rel.parts[0]=='.github' else rel
        target=dst/target_rel; target.parent.mkdir(parents=True,exist_ok=True)
        before=p.stat(); h=hashlib.sha256()
        with p.open('rb') as inp,target.open('xb') as out:
            while block:=inp.read(1024*1024): out.write(block); h.update(block)
        original_hash=h.hexdigest(); after=p.stat()
        if before.st_size!=after.st_size or before.st_mtime_ns!=after.st_mtime_ns or sha(target)!=original_hash: raise RuntimeError('Copy/source stability mismatch: '+str(rel))
        rec={'source_path':str(rel),'destination_path':str(target_rel),'bytes':before.st_size,'sha256':original_hash}
        copied.append(rec)
        if p.suffix.lower() in ('.qpy','.npz','.h5','.pdf') or before.st_size>9_000_000:
            if original_hash not in objects:
                fd,tmpname=tempfile.mkstemp(prefix='nighthawk-archive-',suffix='.gz'); os.close(fd); tmp=Path(tmpname)
                with target.open('rb') as inp,tmp.open('wb') as raw:
                    with gzip.GzipFile(fileobj=raw,mode='wb',filename='',mtime=0,compresslevel=6) as out: shutil.copyfileobj(inp,out,1024*1024)
                parts=[]; decoder=zlib.decompressobj(16+zlib.MAX_WBITS); check=hashlib.sha256(); total=0
                with tmp.open('rb') as inp:
                    index=0
                    while chunk:=inp.read(CHUNK):
                        part=Path('archive/objects')/(original_hash+f'.gz.part{index:03d}')
                        with (dst/part).open('xb') as out: out.write(chunk)
                        decoded=decoder.decompress(chunk); check.update(decoded); total+=len(decoded)
                        parts.append({'path':str(part),'bytes':len(chunk),'sha256':hashlib.sha256(chunk).hexdigest()}); index+=1
                tail=decoder.flush(); check.update(tail); total+=len(tail)
                assert decoder.eof and not decoder.unused_data and total==before.st_size and check.hexdigest()==original_hash
                objects[original_hash]={'sha256':original_hash,'uncompressed_bytes':before.st_size,'parts':parts}; tmp.unlink()
            archived.append({'path':str(target_rel),'sha256':original_hash,'bytes':before.st_size})
        if time.monotonic()-last>20:
            print(json.dumps({'stage':'copy_and_archive','done':number,'files':len(candidates),'unique_archives':len(objects)}),flush=True); last=time.monotonic()
    write_json(dst/'migration/source_copy_manifest.json',{'source':str(src),'source_commit':head,'source_tracked_dirty_status':dirty,'excluded_directories':sorted(EXCLUDED_DIRS),'excluded_files':excluded,'copied':copied,'source_left_unchanged':True,'credential_pattern_scan':'PASS'})
    write_json(dst/'archive/manifest.json',{'format':'concatenated gzip bytes in ordered parts','chunk_limit_bytes':CHUNK,'original_files':archived,'objects':list(objects.values())})
    print(json.dumps({'status':'COPIED_AND_VERIFIED','files':len(copied),'bytes':sum(x['bytes'] for x in copied),'archived_originals':len(archived),'unique_objects':len(objects),'archive_bytes':sum(p['bytes'] for o in objects.values() for p in o['parts'])}),flush=True)

if __name__=='__main__': main()
