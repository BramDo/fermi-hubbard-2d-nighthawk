"""Preserve and verify the completed probe; never execute more physics."""
import hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent
RUN=ROOT/'results_cuprate_2d/spin_correlations_T04_2026-09-06_v1'
def read(p): return json.loads(p.read_text())
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def verify(base,manifest):
    for name,expected in read(manifest).items(): assert digest(base/name)==expected,name

def main():
    delivery=RUN/'delivery_sha256.json'
    if delivery.exists(): verify(RUN,delivery); print('Sealed delivery verified; no changes.'); return
    verify(RUN,RUN/'analysis_sha256.json')
    for name,h in read(RUN/'plan.json')['inputs_sha256'].items(): assert digest(ROOT/name)==h,name
    assert read(RUN/'independent_verification.json')['status']=='PASS'
    assert read(RUN/'summary.json')['hardware_seconds_added']==0
    extra=RUN/'verification_sources'; extra.mkdir()
    for name in ('verify_spin_correlation_probe.py','seal_spin_correlation_probe.py'):
        shutil.copyfile(ROOT/name,extra/name)
        assert digest(ROOT/name)==digest(extra/name)
    with delivery.open('x',encoding='utf-8') as f:
        files={str(p.relative_to(RUN)):digest(p) for p in RUN.rglob('*') if p.is_file() and p!=delivery}
        json.dump(files,f,indent=2); f.write('\n')
    verify(RUN,delivery)
    print(json.dumps({'delivery_hashes_verified':len(files),'old_inputs_verified':28,'old_archives_modified':False}),flush=True)

if __name__=='__main__': main()
