"""Independent two-site probability enumeration for the component report."""
import argparse
import shutil
from pathlib import Path

import numpy as np

import aer_cuprate_noise_components as c
from analyze_aer_noise_components import verify_files


def physical_by_enumeration(native, mask, matrices):
    native = np.atleast_2d(native)
    width = len(mask)
    result = np.zeros((len(native), width//2, 3))
    for site in range(width//2):
        i, j = 2*site, 2*site+1
        for x in range(4):
            x0, x1 = x & 1, (x >> 1) & 1
            s0, s1 = 1-2*x0, 1-2*x1
            probability = (1+s0*native[:, i]+s1*native[:, j]+s0*s1*native[:, width+site])/4
            if probability.min() < -1e-10:
                raise AssertionError('Negative two-site computational-basis marginal')
            for y in range(4):
                y0, y1 = y & 1, (y >> 1) & 1
                up, down = y0 ^ int(mask[i]), y1 ^ int(mask[j])
                weight = probability*matrices[i, x0, y0]*matrices[j, x1, y1]
                result[:, site] += weight[:, None]*np.array([up+down, up-down, up*down])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    root = args.output.resolve()
    if (root/'COMPLETION.json').exists():
        parser.error('Already independently verified; refuse overwrite')
    checks = {'run_hashes': verify_files(root, 'run_archive_sha256.json'),
              'analysis_hashes': verify_files(root/'analysis', 'sha256.json')}
    plan = c.a.read(root/'plan.json')
    results = c.a.read(root/'analysis/results.json')
    for name, digest in results['source_sha256'].items():
        if c.a.digest(c.a.ROOT/name) != digest:
            raise AssertionError('Analysis code changed')
    matrices = np.array(c.a.read(root/'readout_matrices.json'))
    identity = np.tile(np.eye(2), (18, 1, 1))
    values = np.empty((2, 2, 9, 3))
    for model in range(2):
        for variant, readout in enumerate([identity, matrices]):
            blocks = []
            for tid in range(8):
                data = c.a.read(root/'blocks'/f'{model}_{tid}'/'result.json')
                blocks.append(physical_by_enumeration(np.array(data['native_paulis']),
                    plan['records'][tid]['readout_mask_little_endian'], readout))
            values[model, variant] = np.concatenate(blocks).mean(axis=0)
    difference = float(np.max(np.abs(values-results['physical_means'])))
    if difference > 1e-12:
        raise AssertionError('Independent probability-based observable mismatch')
    checks['independent_max_physical_error'] = difference
    exact = np.asarray(plan['setting']['reference'])
    readout_only = []
    for record in plan['records']:
        mask = record['readout_mask_little_endian']
        sign = np.array([(-1)**int(m) for m in mask])
        native = exact*np.concatenate([sign, sign[::2]*sign[1::2]])
        readout_only.append(physical_by_enumeration(native, mask, matrices)[0])
    target_spin = (exact[1:18:2]-exact[:18:2])/2
    spin = np.mean(readout_only, axis=0)[:, 1]
    ro_rmse = float(np.sqrt(np.mean((spin-target_spin)**2)))
    if abs(ro_rmse-results['readout_only_exact_metrics'][1]) > 1e-12:
        raise AssertionError('Independent readout-only exact RMSE mismatch')
    checks['independent_readout_only_spin_rmse'] = ro_rmse
    for model in range(2):
        for variant in range(2):
            spin = values[model, variant, :, 1]
            metric = results['metrics'][model][variant]
            np.testing.assert_allclose(np.sqrt(np.mean((spin-target_spin)**2)), metric[1], atol=1e-12)
            np.testing.assert_allclose(spin @ target_spin/(target_spin @ target_spin), metric[3], atol=1e-12)
    checks['independent_spin_metrics'] = True
    decomposition = c.a.read(root/'decomposition.json')
    checks['max_channel_reconstruction_error'] = max(r['reconstructed_max_superop_difference'] for r in decomposition)
    if checks['max_channel_reconstruction_error'] > 1e-12:
        raise AssertionError('Full model was not preserved')
    draws = np.load(root/'analysis/bootstrap_draws.npz')['means']
    if draws.shape != (2000, 2, 2, 27) or not np.isfinite(draws).all():
        raise AssertionError('Incomplete/nonfinite bootstrap archive')
    checks['bootstrap_replicates_verified'] = 2000
    shutil.copyfile(Path(__file__), root/'analysis/source_snapshot'/Path(__file__).name)
    c.a.write(root/'COMPLETION.json', {'status': 'COMPLETE_COMPONENT_SCREEN_AND_INDEPENDENT_AUDIT',
        'new_qpu_seconds': 0, 'checks': checks,
        'unit_tests': c.a.read(root/'analysis/verification.json')['unit_tests'],
        'scope': '128 trajectories per gate component; exact independent readout moments; one fixed setting.'})
    c.a.write(root/'final_archive_sha256.json', {str(p.relative_to(root)): c.a.digest(p)
        for p in root.rglob('*') if p.is_file()})
    print(checks)


if __name__ == '__main__':
    main()
