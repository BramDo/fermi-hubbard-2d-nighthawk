"""Fixed-twirl inference for model component screening, not hardware attribution."""
import argparse
import io
import json
import shutil
import unittest
from pathlib import Path

import numpy as np

import aer_cuprate_noise_components as c
from cuprate_2d_tflo import physical_observables

METRICS = ['charge_rmse', 'spin_rmse', 'doublon_rmse', 'spin_contrast_projection']


def metrics(paulis, exact):
    observed, target = physical_observables(paulis), physical_observables(exact)
    rmse = np.sqrt(np.mean((observed-target)**2, axis=-2))
    denominator = np.sum(target[:, 1]**2)
    if denominator <= 1e-14:
        raise ValueError('Undefined spin contrast projection for zero reference spin')
    gain = np.sum(observed[..., :, 1]*target[:, 1], axis=-1)/denominator
    return np.concatenate([rmse, gain[..., None]], axis=-1)


def bootstrap(data, repetitions=2000, seed=2026090901):
    if np.shape(data) != (2, 8, 16, 2, 27):
        raise ValueError('Expected two models x eight twirls x 16 trajectories x two readout variants x 27')
    rng = np.random.default_rng(seed)
    result = np.empty((repetitions, 2, 2, 27))
    for b in range(repetitions):
        for model in range(2):
            selected = rng.integers(0, 16, (8, 16))
            result[b, model] = data[model, np.arange(8)[:, None], selected].mean(axis=(0, 1))
    return result


def ci(values):
    return {'low': np.quantile(values, .025, axis=0).tolist(),
            'high': np.quantile(values, .975, axis=0).tolist()}


def verify_files(folder, manifest_name):
    folder = Path(folder).resolve()
    manifest = c.a.read(folder/manifest_name)
    for name, digest in manifest.items():
        path = (folder/name).resolve()
        if not path.is_relative_to(folder) or c.a.digest(path) != digest:
            raise ValueError(f'Changed/unsafe artifact {name}')
    return len(manifest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    root = args.output.resolve()
    destination = root/'analysis'
    if destination.exists():
        parser.error('Refuse to overwrite existing analysis')
    verified_count = verify_files(root, 'run_archive_sha256.json')
    plan = c.a.read(root/'plan.json')
    for name, digest in plan['input_sha256'].items():
        if c.a.digest(c.a.ROOT/name) != digest:
            raise ValueError(f'Input/source changed: {name}')
    records = plan['records']
    matrices = np.asarray(c.a.read(root/'readout_matrices.json'))
    exact = np.asarray(plan['setting']['reference'])
    data = np.empty((2, 8, 16, 2, 27))
    for model in range(2):
        for tid in range(8):
            block = c.a.read(root/'blocks'/f'{model}_{tid}'/'result.json')
            raw = c.a.read(root/'blocks'/f'{model}_{tid}'/'aer_result.json')
            if block['model'] != c.COMPONENTS[model] or block['seed'] != 2026090700+100*model+tid:
                raise ValueError('Block model/seed mismatch')
            if block['twirl_id'] != tid or block['trajectories'] != 16 or not raw['success']:
                raise ValueError('Wrong block metadata')
            labels = [f'z_{q}' for q in range(18)]+[f'zz_{s}' for s in range(9)]
            native = np.array([raw['results'][0]['data'][key] for key in labels]).T
            if native.shape != (16, 27):
                raise ValueError('Raw Aer trajectories missing')
            np.testing.assert_allclose(native, block['native_paulis'], atol=0, rtol=0)
            decoded = c.unmask_paulis(native, records[tid]['readout_mask_little_endian'])
            readout = c.apply_readout(decoded, records[tid]['readout_mask_little_endian'], matrices)
            np.testing.assert_allclose(decoded, block['decoded_paulis'], atol=1e-14, rtol=0)
            np.testing.assert_allclose(readout, block['decoded_with_readout_paulis'], atol=1e-14, rtol=0)
            data[model, tid] = np.stack([decoded, readout], axis=1)
    if not np.isfinite(data).all():
        raise AssertionError('Nonfinite trajectories')
    mean = data.mean(axis=(1, 2))
    draws = bootstrap(data)
    md = metrics(draws, exact)
    point_metrics = metrics(mean, exact)
    readout_only = np.mean(c.a.read(root/'preflight.json')['readout_only_exact_per_twirl'], axis=0)
    old = c.a.read(c.BASELINE/'comparison/results.json')
    old_point = np.asarray(old['pauli_means'])[:, 0]
    old_draws = np.load(c.BASELINE/'comparison/bootstrap_draws.npz')['fixed'][:, :, 0]
    old_metrics = metrics(old_point, exact)
    old_metric_draws = metrics(old_draws, exact)
    resolutions = []
    for n in [8, 16]:
        resolutions.append({'trajectories_per_model': 8*n, 'nested_not_independent': True,
            'metrics': metrics(data[:, :, :n].mean(axis=(1, 2)), exact).tolist()})
    result = {
        'schema': 'aer-component-screen-analysis-v1', 'setting': plan['setting'],
        'model_order': c.COMPONENTS, 'readout_variant_order': ['off', 'on_analytic'],
        'metric_order': METRICS, 'means': mean.tolist(),
        'physical_means': physical_observables(mean).tolist(),
        'metrics': point_metrics.tolist(), 'metric_ci95': ci(md),
        'depolarization_minus_relaxation_metric_ci95': ci(md[:, 0, 0]-md[:, 1, 0]),
        'paired_readout_increment_metric_ci95': ci(md[:, :, 1]-md[:, :, 0]),
        'readout_only_exact_paulis': readout_only.tolist(),
        'readout_only_exact_metrics': metrics(readout_only, exact).tolist(),
        'ideal_metrics': metrics(exact, exact).tolist(),
        'baseline_512_bitstring_context': {'dataset_order': ['full_model_aer', 'hardware'],
            'metrics': old_metrics.tolist(), 'ci95_fixed_twirls': ci(old_metric_draws),
            'different_estimator_and_sample_size': True},
        'resolution': resolutions, 'bootstrap_repetitions': len(draws),
        'bootstrap_projection_interval_resolution': {str(n): ci(md[:n, :, :, 3]) for n in [500, 1000, 2000]},
        'new_qpu_seconds': 0, 'run_times': c.a.read(root/'run_summary.json')['model_run_seconds'],
        'run_manifest_sha256': c.a.digest(root/'run_archive_sha256.json'),
        'source_sha256': {name: c.a.digest(c.a.ROOT/name) for name in [
            'analyze_aer_noise_components.py', 'test_analyze_aer_noise_components.py']},
        'limits': ['128 noise trajectories per component; bounded screening, not convergence certification.',
                   'Pointwise conditional bootstrap; no joint multiple-comparison guarantee.',
                   'Uncertainty excludes unknown hardware/model error and drift.',
                   'No component-additivity claim, no postselection, no mitigation, no advantage claim.']}
    log = io.StringIO()
    suite = unittest.defaultTestLoader.loadTestsFromNames([
        'test_aer_cuprate_noise_components', 'test_analyze_aer_noise_components'])
    tests = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    if not tests.wasSuccessful():
        raise AssertionError(log.getvalue())
    destination.mkdir()
    c.a.write(destination/'results.json', result)
    np.savez_compressed(destination/'bootstrap_draws.npz', means=draws)
    (destination/'unit_tests.txt').write_text(log.getvalue(), encoding='utf-8')
    (destination/'source_snapshot').mkdir()
    for name in result['source_sha256']:
        shutil.copyfile(c.a.ROOT/name, destination/'source_snapshot'/name)
    c.a.write(destination/'verification.json', {'status': 'PASS', 'unit_tests': tests.testsRun,
        'run_hashes_verified': verified_count, 'input_hashes_verified': len(plan['input_sha256']),
        'raw_aer_trajectory_values_verified': int(data.shape[0]*data.shape[1]*data.shape[2]*27)})
    rows = [
        ('Ideaal', result['ideal_metrics'], None),
        ('Alleen uitleesruis (exact model)', result['readout_only_exact_metrics'], None),
        ('Alleen resterende depolarisatie (128 trajecten)', point_metrics[0, 0], 0),
        ('Alleen gate-tijdrelaxatie (128 trajecten)', point_metrics[1, 0], 1),
        ('Depolarisatie + uitleesruis', point_metrics[0, 1], None),
        ('Relaxatie + uitleesruis', point_metrics[1, 1], None),
        ('Volledig Aer-model (eerdere 512 bitshots)', old_metrics[0], None),
        ('Hardware (eerdere 512 bitshots)', old_metrics[1], None)]
    report = ['# Componenten van het Nighthawk-Aer-ruismodel', '',
        'Zelfde U/t=8, T=0.4, 18-qubitcircuit en acht twirls. Geen nieuwe QPU-seconden.',
        'Per component 128 ruistrajecten met rechtstreeks opgeslagen Pauli-verwachtingswaarden.',
        'Dit verwijdert meetshotruis, niet onzekerheid door het aantal ruistrajecten.', '',
        '| Model | RMSE lading | RMSE spin | RMSE doublon | Spincontrast g |',
        '|---|---:|---:|---:|---:|']
    for name, value, _ in rows:
        report.append(f'| {name} | {value[0]:.4f} | {value[1]:.4f} | {value[2]:.4f} | {value[3]:.4f} |')
    report += ['', 'Spincontrast is de projectie op het ideale spinpatroon; ideaal=1. Het is geen fideliteit.',
               'RMSE is tegenover de exacte eindige circuitreferentie; component-RMSEs zijn niet optelbaar.', '',
               '## Onzekerheid van de twee primaire componenten', '']
    for model in range(2):
        low = result['metric_ci95']['low'][model][0]
        high = result['metric_ci95']['high'][model][0]
        report.append(f'- {c.COMPONENTS[model]}: spin-RMSE 95%-interval [{low[1]:.4f}, {high[1]:.4f}]; '
                      f'spincontrast [{low[3]:.4f}, {high[3]:.4f}].')
    report += ['', '2000 bootstrap-herhalingen binnen de vaste acht twirls. Puntgewijs, zonder modelonzekerheid.',
        'De eerdere volledige Aer/hardware-rijen gebruiken 512 gemeten bitstrings: andere steekproefgrootte',
        'en extra meetshotruis. Ze zijn context, geen identieke-precisie vergelijking met deze componenten.',
        'Alleen uitleesruis is exact binnen het aangenomen onafhankelijke uitleesmodel.',
        '', 'Het oorspronkelijke volle ruiskanaal is gecontroleerd gereconstrueerd uit beide gatecomponenten.',
        'Geen parameters zijn op hardware gefit. De uitsplitsing is afhankelijk van de gekozen Aer-noiseaannames.',
        'Geen conclusie dat dezelfde component de echte hardwareafwijking veroorzaakt.',
        'Geen idle-gap-relaxatie, crosstalk, leakage of coherente fouten toegevoegd.',
        '', f'Checks: {tests.testsRun} tests, {verified_count} run-hashes, alle ruwe trajectwaarden gereproduceerd.',
        'Tijden per component (Aer.run + resultaat ophalen): '+json.dumps(result['run_times']), '',
        'API: https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.library.save_expectation_value.html', '']
    (destination/'REPORT.md').write_text('\n'.join(report), encoding='utf-8')
    c.a.write(destination/'sha256.json', {str(p.relative_to(destination)): c.a.digest(p)
        for p in destination.rglob('*') if p.is_file()})
    print(json.dumps({'readout_exact': result['readout_only_exact_metrics'],
        'component_metrics': point_metrics.tolist(), 'metric_ci95': result['metric_ci95'],
        'contrast_ordering_ci95': result['depolarization_minus_relaxation_metric_ci95'],
        'baseline': old_metrics.tolist(), 'tests': tests.testsRun, 'times': result['run_times']}), flush=True)


if __name__ == '__main__':
    main()
