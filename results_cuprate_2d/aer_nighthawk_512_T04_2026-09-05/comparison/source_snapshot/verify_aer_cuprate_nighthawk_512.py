"""Independent bit-based observable audit and final immutable completion record."""
import argparse
import shutil
from pathlib import Path

import numpy as np

import aer_cuprate_nighthawk_smoke as a
from analyze_aer_cuprate_nighthawk_512 import verify_hashes


def independent_observables(records, synthetic=False):
    decoded = []
    for entry in records:
        meta = entry['record'] if synthetic else entry
        mask = meta['readout_mask_little_endian']
        for s in entry['bitstrings']:
            value = int(s, 2)
            decoded.append([((value >> q) & 1) ^ mask[q] for q in range(18)])
    n = np.asarray(decoded, dtype=float)
    up, down = n[:, ::2], n[:, 1::2]
    keep = (np.abs(up.sum(axis=1)-4)+np.abs(down.sum(axis=1)-4)) <= 1
    sample_observables = np.stack([up+down, up-down, up*down], axis=-1)
    return np.stack([sample_observables.mean(axis=0), sample_observables[keep].mean(axis=0)]), int(keep.sum())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    root = args.output.resolve()
    if (root/'COMPLETION.json').exists():
        parser.error('Final audit already exists; never overwrite')
    checks = {}
    checks['run_hash_count'] = verify_hashes(root, 'run_archive_sha256.json')
    checks['analysis_hash_count'] = verify_hashes(root/'comparison', 'sha256.json')
    comparison = a.read(root/'comparison/results.json')
    for name, expected in comparison['analysis_source_sha256'].items():
        if a.digest(a.ROOT/name) != expected:
            raise AssertionError('Analysis source changed')
    actual = []
    for synthetic in [True, False]:
        records = ([a.read(root/'blocks'/f'twirl_{t}'/'record.json') for t in range(8)]
                   if synthetic else a.read(root/'hardware_matched_records.json')['records'])
        values, retained = independent_observables(records, synthetic)
        actual.append(values)
        index = 0 if synthetic else 1
        if retained != comparison['counts'][index][1]:
            raise AssertionError('Independent retention mismatch')
    diff = float(np.max(np.abs(np.asarray(actual)-comparison['physical_means'])))
    if diff > 1e-12:
        raise AssertionError('Independent physical observable disagreement')
    checks['independent_physical_max_error'] = diff
    preflight = a.read(root/'preflight.json')
    if len(preflight['checks']) != 8 or any(c['max_pauli_error'] > 1e-9
            or c['native_counts']['cz'] != 1008 for c in preflight['checks']):
        raise AssertionError('Missing or failed full-circuit verification')
    checks['noise_off_max_pauli_error'] = max(c['max_pauli_error'] for c in preflight['checks'])
    draws = np.load(root/'comparison/bootstrap_draws.npz')
    for key, label in [('fixed', 'fixed_twirls'), ('hierarchical', 'resampled_twirl_sensitivity')]:
        if draws[key].shape != (2000, 2, 2, 27) or not np.isfinite(draws[key]).all():
            raise AssertionError('Incomplete or nonfinite bootstrap archive')
        delta = np.asarray(comparison['aer_minus_hardware_paulis'])[0]
        errors = draws[key][:, 0, 0]-draws[key][:, 1, 0]-delta
        radius = float(np.quantile(np.max(np.abs(errors), axis=1), .95))
        saved = comparison['uncertainty'][label]['raw_simultaneous_pauli_band']
        if abs(radius-saved['radius']) > 1e-14:
            raise AssertionError('Simultaneous band does not reproduce')
        if np.flatnonzero(np.abs(delta) > radius).tolist() != saved['coordinates_excluding_zero']:
            raise AssertionError('Mismatch in jointly resolved differences')
    checks['bootstrap_band_reproduction'] = True
    if a.read(root/'run_summary.json')['qpu_seconds'] != 0:
        raise AssertionError('Nonzero QPU usage in a local-only test')
    checks['zero_new_QPU_seconds'] = True
    shutil.copyfile(Path(__file__), root/'comparison/source_snapshot'/Path(__file__).name)
    a.write(root/'COMPLETION.json', {
        'status': 'COMPLETE_SIMULATION_ANALYSIS_AND_INDEPENDENT_AUDIT',
        'scope': 'Only U8 T0.4; eight matched twirls, 512 shots per data set.',
        'historical_run_summary_analysis_pending_is_superseded': True,
        'unit_tests': a.read(root/'comparison/verification.json')['unit_tests'],
        'checks': checks, 'new_QPU_seconds': 0})
    a.write(root/'final_archive_sha256.json', {str(p.relative_to(root)): a.digest(p)
        for p in root.rglob('*') if p.is_file()})
    print(checks)


if __name__ == '__main__':
    main()
