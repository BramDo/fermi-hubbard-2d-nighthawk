"""Independent standard-library verification and immutable package seal."""
import hashlib,json,math,statistics
from pathlib import Path

ROOT=Path(__file__).resolve().parent
RUN=ROOT/'results_cuprate_2d/classical_mean6_timing_2026-09-06_v1'
def read(path): return json.loads(path.read_text())
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):
    with path.open('x',encoding='utf-8') as file:
        json.dump(value,file,indent=2,allow_nan=False); file.write('\n')

def main():
    if (RUN/'delivery_sha256.json').exists():
        for name,expected in read(RUN/'delivery_sha256.json').items(): assert digest(RUN/name)==expected,name
        print('Sealed package verified; no changes.'); return
    result=read(RUN/'summary.json'); raw=read(RUN/'windows_timings.json')
    runs=[read(RUN/f'worker_{i}.json') for i in range(5)]
    assert runs==raw['runs']
    for name,expected in read(RUN/'source_sha256.json').items():
        assert digest(ROOT/name)==expected,name
        assert digest(RUN/'source_snapshot'/name)==expected,name
    for name,expected in result['source_artifact_sha256'].items(): assert digest(ROOT/name)==expected,name
    ref=read(ROOT/'results_cuprate_2d/classical_full_6x6_mps_T04_chi64_v1/summary.json')['result']['physical_means']
    pred=runs[0]['worker']['prediction']
    rms=[math.sqrt(math.fsum((pred[i][j]-ref[i][j])**2 for i in range(36))/36) for j in range(3)]
    delta=max(abs(x-y) for x,y in zip(rms,result['classical_control_RMS_charge_spin_doublon']))
    assert delta<1e-14
    for key,record in result['timings'].items():
        values=[r['windows_call_seconds'] if key=='windows_wsl_python_complete' else r['worker'][key] for r in runs]
        assert record['all_seconds']==values
        assert record['median_seconds']==statistics.median(values)
        assert record['minimum_seconds']==min(values) and record['maximum_seconds']==max(values)
        assert all(math.isfinite(x) and x>0 for x in values)
    assert all(r['windows_call_seconds']>r['worker']['python_including_checks_seconds']>=r['worker']['python_to_result_ready_seconds']>r['worker']['kernel_seconds'] for r in runs)
    record=dict(independent_scalar_RMS_max_abs=delta,all_timing_statistics_exact=True,
        timing_boundary_order_valid=True,five_individual_records_match_aggregate=True,
        source_snapshots_verified=len(read(RUN/'source_sha256.json')),
        old_input_artifact_hashes_still_match=len(result['source_artifact_sha256']),
        finalizer_source_sha256=digest(Path(__file__)))
    save(RUN/'independent_verification.json',record)
    save(RUN/'delivery_sha256.json',{str(p.relative_to(RUN)):digest(p) for p in RUN.rglob('*') if p.is_file()})
    for name,expected in read(RUN/'delivery_sha256.json').items(): assert digest(RUN/name)==expected,name
    print(json.dumps({**record,'delivery_hashes_verified':len(read(RUN/'delivery_sha256.json'))}),flush=True)

if __name__=='__main__': main()
