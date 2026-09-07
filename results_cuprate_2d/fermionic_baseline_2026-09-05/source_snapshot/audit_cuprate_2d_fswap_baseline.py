"""Check and archive completed baseline diagnostics; never promote an untested reference."""
import argparse
import hashlib
import json
from pathlib import Path

from validate_cuprate_2d_fswap_baseline import differences, save


def audit(root):
    repo = Path(__file__).resolve().parent
    folders = ('time0p2_dt0p1', 'time0p2_dt0p1_mpo')
    cases = []
    timeouts = []
    checks = {}
    for folder in folders:
        directory = root / folder
        validation = json.loads((directory/'engine_validation.json').read_text())
        assert validation['passed'] and all(c['passed'] for c in validation['checks'])
        manifest = json.loads((directory/'run_manifest.json').read_text())
        assert not manifest['submitted'] and manifest['matching_qpy']['logical_circuit_equal']
        qpy_path = repo / manifest['matching_qpy']['path']
        assert hashlib.sha256(qpy_path.read_bytes()).hexdigest() == manifest['matching_qpy']['sha256']
        for name, expected in validation['source_sha256'].items():
            assert hashlib.sha256((repo/name).read_bytes()).hexdigest() == expected, name
            assert hashlib.sha256((root/'source_snapshot'/name).read_bytes()).hexdigest() == expected, name
            checks[name] = expected
        for path in sorted(directory.glob('chi*.json')):
            if path.stem.endswith('_timeout'):
                timeouts.append({'route': folder, **json.loads(path.read_text())})
                continue
            record = json.loads(path.read_text())
            assert record['source_sha256'] == validation['source_sha256']
            assert record['config'] == manifest['config']
            assert len(record['snapshots']) == record['config']['steps']
            for snapshot in record['snapshots']:
                assert 0 < snapshot['cumulative_retained_norm_weight'] <= 1+1e-8
                for site in snapshot['sites']:
                    up, down, double = (site[k] for k in ('n_up', 'n_down', 'double_occupancy'))
                    assert -1e-8 <= up <= 1+1e-8 and -1e-8 <= down <= 1+1e-8
                    assert max(0, up+down-1)-1e-8 <= double <= min(up, down)+1e-8
                    assert abs(site['charge']-up-down) < 1e-10
                    assert abs(site['spin_z']-up+down) < 1e-10
            cases.append({'route': folder, **record})
    cross = []
    for chi in sorted({r['chi'] for r in cases}):
        same = [r for r in cases if r['chi'] == chi]
        if len(same) == 2:
            assert same[0]['config'] == same[1]['config']
            cross.append({'chi': chi, 'differences': differences(same[0]['snapshots'][-1]['sites'], same[1]['snapshots'][-1]['sites'])})
    save(root/'cross_route_comparison.json', cross)
    result = {'artifact_integrity_passed': True, 'completed_cases': len(cases),
              'source_files_verified': len(checks), 'timeouts': timeouts,
              'hardware_accuracy_benchmark_ready': False,
              'reason': 'Completed bond ladders do not satisfy the screening criteria; a controlled 6x6 dt study is still missing.',
              'qpu_jobs_submitted': 0}
    save(root/'audit.json', result)
    lines = ['# Next-step result: baseline not yet ready for a 72-qubit accuracy claim', '',
             'The full t-t-prime-U network is numerically implemented and matches the stored QPY. The classical reference at total time 0.2 is not yet converged under the declared screening criteria.', '',
             '| classical route | chi | seconds | retained norm weight | total charge | mean double occupancy |',
             '|---|---:|---:|---:|---:|---:|']
    for r in sorted(cases, key=lambda r: (r['route'], r['chi'])):
        s = r['snapshots'][-1]
        label = 'direct gates' if r['route'] == folders[0] else 'routing-free MPO'
        lines.append(f"| {label} | {r['chi']} | {r['elapsed_seconds_including_observables']:.1f} | {s['cumulative_retained_norm_weight']:.6f} | {s['totals']['total_charge']:.8f} | {s['totals']['mean_double_occupancy']:.6f} |")
    lines += ['', 'Retained norm weight is not fidelity. Charge near 32 does not certify local accuracy. Timing covers each MPS evolution and its observables, not all validation/import/startup costs; it is not an end-to-end advantage comparison.', '',
              '## What passed', '',
              '- Direct MPS vs exact Qiskit statevectors on 2x2/2x3: maximum tested state distance 3.45e-14.',
              '- Routing-free MPO vs the exact network on 2x2/2x3: maximum tested state distance 1.07e-14.',
              '- Three explicit JW hopping MPO matrices match the reference gate matrices; all 16 engine/oracle checks passed.',
              '- On the independent 2x3 Hamiltonian at fixed total time 0.2, halving dt reduces the state error by factors 4.049 and 4.012. Errors at dt=0.1/0.05/0.025 are 0.0134463/0.00332084/0.000827677. This is not a 6x6 convergence result.',
              f'- Artifact audit: {len(cases)} completed cases, {len(checks)} source snapshots, and all tested local probability bounds passed.', '',
              '## What remains open', '',
              '- Direct-gate chi 32 -> 64 differences: charge RMSE 0.004612, spin RMSE 0.024368, double-occupancy RMSE 0.009706; each exceeds the 0.001 target.',
              '- Routing-free chi 16 -> 32 differences: charge RMSE 0.003385, spin RMSE 0.016261, double-occupancy RMSE 0.006331; also above target. No higher-chi result is implied by a partial run.']
    for timeout in timeouts:
        lines.append(f"- Local limit reached for {timeout['route']}: {timeout['error']}. Partial progress is retained, not used as a completed reference.")
    lines += ['', 'The physics verification gate therefore stops promotion to a quantitative 72-qubit hardware benchmark. The 6x6 dt study is deferred because truncation error would currently contaminate it.',
              'Next options are a larger or symmetry-aware classical convergence calculation, or an exact-reference smaller-lattice hardware-validation pilot. Neither hardware submission nor extra QPU spend has occurred. Failure of this bounded MPS study is not evidence of quantum advantage.',
              'Future hardware settings remain in the previous sealed plans: 512 shots per noise factor and a five-second execution cap. The inherited shots=20000 field in the classical input is unused.', '',
              '## Reproducible check', '', '```text',
              'python audit_cuprate_2d_fswap_baseline.py --root results_cuprate_2d/fermionic_baseline_2026-09-05',
              json.dumps({k:v for k,v in result.items() if k != 'timeouts'}), '```', '',
              'Canonical MPS/MPO contraction API: https://quimb.readthedocs.io/en/main/autoapi/quimb/tensor/tn1d/core/index.html', '']
    (root/'NEXT_STEP_REPORT.md').write_text('\n'.join(lines), encoding='utf-8')
    save(root/'artifact_sha256.json', [{'path': str(p.relative_to(root)),
          'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(root.rglob('*'))
          if p.is_file() and p.name != 'artifact_sha256.json'])
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    audit(parser.parse_args().root)
