"""Seal the offline candidate archive without any hardware access."""
import gzip,hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent
RUN=ROOT/'results_cuprate_2d/quantum_compact_tflo_2026-09-07_v1'
def read(p): return json.loads(p.read_text())
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def verify(manifest):
    for name,h in read(manifest).items(): assert digest(RUN/name)==h,name
def main():
    final=RUN/'delivery_sha256.json'
    if final.exists(): verify(final); print('Delivery verified; no files changed.'); return
    verify(RUN/'analysis_sha256.json')
    for name,h in read(RUN/'plan.json')['input_sha256'].items(): assert digest(ROOT/name)==h,name
    assert read(RUN/'independent_verification.json')['status']=='PASS'
    assert read(RUN/'summary.json')['hardware_seconds_used']==0
    for row in read(RUN/'qpy_mirrors.json'):
        assert digest(RUN/row['file'])==row['sha256']
        assert digest(RUN/row['gzip'])==row['gzip_sha256']
        with gzip.open(RUN/row['gzip'],'rb') as f: assert hashlib.file_digest(f,'sha256').hexdigest()==row['sha256']
    extra=RUN/'verification_sources'; extra.mkdir()
    for name in ('verify_compact_symbolic_tflo.py','seal_compact_symbolic_tflo.py','cuprate_2d_shallow_network.py','cuprate_2d_tflo_refinement.py'):
        shutil.copyfile(ROOT/name,extra/name); assert digest(ROOT/name)==digest(extra/name)
    files={str(p.relative_to(RUN)):digest(p) for p in RUN.rglob('*') if p.is_file()}
    with final.open('x',encoding='utf-8') as f: json.dump(files,f,indent=2); f.write('\n')
    verify(final)
    print(json.dumps({'delivery_hashes_verified':len(files),'QPY_lossless_mirrors':len(read(RUN/'qpy_mirrors.json')),'hardware_seconds_used':0}),flush=True)
if __name__=='__main__': main()
