"""Verify or restore all archived originals without overwriting mismatches."""
import argparse, hashlib, json, os, tempfile, zlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        while b:=f.read(1024*1024): h.update(b)
    return h.hexdigest()

def safe_path(root,name):
    rel=Path(name)
    if rel.is_absolute() or '..' in rel.parts: raise ValueError('Unsafe archive path')
    p=(root/rel).resolve()
    if p==root or not p.is_relative_to(root): raise ValueError('Path escapes repository')
    return p

def stream_object(root,obj,out=None):
    dec=zlib.decompressobj(16+zlib.MAX_WBITS); h=hashlib.sha256(); size=0
    for part in obj['parts']:
        p=safe_path(root,part['path'])
        if p.stat().st_size!=part['bytes'] or digest(p)!=part['sha256']: raise ValueError('Archive part checksum mismatch: '+part['path'])
        with p.open('rb') as inp:
            while b:=inp.read(1024*1024):
                data=dec.decompress(b); h.update(data); size+=len(data)
                if out is not None: out.write(data)
    data=dec.flush(); h.update(data); size+=len(data)
    if out is not None: out.write(data)
    if not dec.eof or dec.unused_data or size!=obj['uncompressed_bytes'] or h.hexdigest()!=obj['sha256']:
        raise ValueError('Restored object checksum mismatch')

def run(root,restore=False,selected=None):
    root=root.resolve(); manifest=json.loads((root/'archive/manifest.json').read_text())
    objects={o['sha256']:o for o in manifest['objects']}; verified=set(); restored=0; already=0
    chosen=[r for r in manifest['original_files'] if selected is None or r['path']==selected]
    if selected is not None and not chosen: raise ValueError('Selected path is absent from manifest')
    for rec in chosen:
        obj=objects[rec['sha256']]
        if rec['bytes']!=obj['uncompressed_bytes']: raise ValueError('Manifest size mismatch')
        target=safe_path(root,rec['path'])
        if restore and target.exists():
            if digest(target)!=rec['sha256']: raise FileExistsError('Refusing to overwrite mismatching file: '+rec['path'])
            already+=1
        elif restore:
            target.parent.mkdir(parents=True,exist_ok=True)
            fd,tmp=tempfile.mkstemp(prefix='.restore-',dir=target.parent)
            try:
                with os.fdopen(fd,'wb') as out: stream_object(root,obj,out)
                # Atomic hard-link creation fails safely if another writer created target.
                os.link(tmp,target); restored+=1
            finally:
                Path(tmp).unlink(missing_ok=True)
            verified.add(rec['sha256'])
        if rec['sha256'] not in verified:
            stream_object(root,obj); verified.add(rec['sha256'])
    return dict(status='PASS',selected_originals=len(chosen),verified_objects=len(verified),restored=restored,already_present=already)

if __name__=='__main__':
    ap=argparse.ArgumentParser(); group=ap.add_mutually_exclusive_group(required=True)
    group.add_argument('--verify',action='store_true'); group.add_argument('--restore',action='store_true')
    ap.add_argument('--path',help='Optional exact original path from manifest')
    a=ap.parse_args(); print(json.dumps(run(ROOT,a.restore,a.path)))
