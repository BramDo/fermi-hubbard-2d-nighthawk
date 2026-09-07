"""Read-only input audit of RNG sharing; writes a separate sensitivity artifact."""
from pathlib import Path
import argparse
import shutil
import numpy as np
import aer_cuprate_noise_components as c
import analyze_aer_noise_components as analysis
from cuprate_2d_tflo import pauli_samples

def sensitivity(values, bases):
    k, m = values.shape
    residual = values-values.mean(axis=1, keepdims=True)
    totals = {}
    for t in range(k):
        for shot in range(m):
            seed = int(bases[t])+shot
            totals[seed] = totals.get(seed, 0.)+residual[t, shot]
    correction = m/(m-1)
    naive = np.sqrt(correction*np.sum(residual**2))/(k*m)
    cluster = np.sqrt(correction*np.sum(np.array(list(totals.values()))**2))/(k*m)
    return {'mean': float(values.mean()), 'nominal_trajectories_or_bitshots': k*m,
            'unique_seed_labels': len(totals), 'independent_assumption_se': float(naive),
            'shared_seed_cluster_sensitivity_se': float(cluster),
            'se_ratio': float(cluster/naive)}

def run(destination):
    if destination.exists():
        raise ValueError('Refuse overwrite')
    # Identity check: without shared labels both variance expressions coincide.
    fixture = np.arange(24.).reshape(3,8)**1.1
    identity = sensitivity(fixture, [100,1000,2000])
    assert abs(identity['se_ratio']-1) < 1e-14
    v1 = c.a.RESULTS/'aer_nighthawk_full_cz_half_T04_v1'
    v2 = c.a.RESULTS/'aer_nighthawk_full_cz_half_T04_v2_disjoint_seeds'
    exact = np.asarray(c.a.read(v1/'plan.json')['setting']['reference'])
    inputs = [v1/'plan.json']
    old = []
    for t in range(8):
        path = c.BASELINE/'blocks'/f'twirl_{t}'/'record.json'
        old.append(c.a.read(path))
        inputs.append(path)
    bits = np.array([r['decoded_little_endian_bits'] for r in old])
    paulis = pauli_samples(bits.reshape(-1,18)).reshape(8,64,27)
    cases = [('old_512_full', paulis, [r['seed_simulator'] for r in old])]
    for folder, label in [(v1,'v1_overlapping'),(v2,'v2_disjoint')]:
        for model in range(2):
            entries = []
            for t in range(8):
                path = folder/'blocks'/f'{model}_{t}'/'record.json'
                entries.append(c.a.read(path))
                inputs.append(path)
            cases.append((f'{label}_model{model}',
                np.array([r['with_readout_paulis'] for r in entries]), [r['seed'] for r in entries]))
    rows = {name: sensitivity(analysis.metrics(values,exact)[...,3], bases)
            for name,values,bases in cases}
    for model in range(2):
        row = rows[f'v2_disjoint_model{model}']
        assert row['unique_seed_labels'] == 128
        assert abs(row['se_ratio']-1) < 1e-14
    # These are independent run families, so sum their diagnostic variances.
    contrast_gap = rows['v1_overlapping_model0']['mean']-rows['old_512_full']['mean']
    gap_se = np.hypot(rows['v1_overlapping_model0']['shared_seed_cluster_sensitivity_se'],
                      rows['old_512_full']['shared_seed_cluster_sensitivity_se'])
    output = {'status': 'SEED_CLUSTER_SENSITIVITY_ONLY', 'metric': 'linear spin contrast projection',
              'rows': rows, 'unique_seed_identity_test': identity,
              'historical_v1_minus_old512': {'contrast_gap': float(contrast_gap),
                  'diagnostic_se': float(gap_se), 'gap_over_diagnostic_se': float(contrast_gap/gap_se)},
              'formula': 'sum over seed labels of squared sums of twirl-centered residuals, times m/(m-1)/(k*m)^2',
              'not_a_validated_replacement_ci': True,
              'caveats': ['Small and unbalanced seed clusters; this is a sandwich sensitivity estimate, not a convergence certificate.',
                  'Different twirls consume common RNG streams differently; labels do not imply identical trajectories.',
                  'Shot zero uses Aer init_rng; preprocessing can affect its stream position.',
                  'Unique seed labels are not an estimate of effective independent sample size.',
                  'Do not assert this fully explains the historical control mismatch.',
                  'Hardware samples unaffected; previous Aer-dependent significance claims require reanalysis or independent rerun.'],
              'source_sha256': c.a.digest(Path(__file__)),
              'input_sha256': {str(p.relative_to(c.a.ROOT)): c.a.digest(p) for p in inputs},
              'new_qpu_seconds': 0}
    destination.mkdir(parents=True)
    shutil.copyfile(Path(__file__), destination/'source.py')
    c.a.write(destination/'results.json', output)
    c.a.write(destination/'sha256.json', {p.name: c.a.digest(p) for p in destination.iterdir() if p.is_file()})
    print(rows)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.output)
