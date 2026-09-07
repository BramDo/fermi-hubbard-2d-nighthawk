"""Fixed-protocol comparison of matched synthetic and hardware shot blocks."""
from __future__ import annotations

import argparse
import io
import json
import shutil
import unittest
from pathlib import Path

import numpy as np

import aer_cuprate_nighthawk_smoke as a
from cuprate_2d_tflo import pauli_samples, physical_observables, sector_mask

METHODS = ['raw', 'postselected_tolerance1']
DATASETS = ['aer', 'hardware']
METRICS = ['pauli_mse_to_exact', 'charge_rmse_to_exact', 'spin_rmse_to_exact',
           'doublon_rmse_to_exact', 'retained_fraction']


def estimates(blocks):
    """All accepted shots pooled, preserving variable per-twirl retention."""
    blocks = np.asarray(blocks)
    if blocks.ndim != 3 or blocks.shape[0] != 8 or blocks.shape[2] != 18:
        raise ValueError('Expected eight shot-by-18 twirl blocks')
    flat = blocks.reshape(-1, 18)
    paulis = pauli_samples(flat)
    keep = sector_mask(flat, 4, 4, tolerance=1)
    if keep.sum() < 32:
        raise ValueError('Below prespecified minimum 32 accepted shots')
    values = np.stack([paulis.mean(axis=0), paulis[keep].mean(axis=0)])
    fractions = np.array([1., keep.mean()])
    counts = np.array([len(flat), keep.sum()], dtype=int)
    return values, fractions, counts


def metrics(paulis, fractions, exact):
    delta_physical = physical_observables(paulis)-physical_observables(exact)
    return np.concatenate([np.mean((paulis-exact)**2, axis=-1)[..., None],
                           np.sqrt(np.mean(delta_physical**2, axis=-2)),
                           np.asarray(fractions)[..., None]], axis=-1)


def fixed_twirl_standard_error(blocks):
    """Conditional variance of the equally weighted fixed eight twirl means."""
    blocks = np.asarray(blocks)
    k, m, width = blocks.shape
    if k != 8 or m < 2 or width != 18:
        raise ValueError('Invalid fixed-twirl sample shape')
    samples = pauli_samples(blocks.reshape(-1, 18)).reshape(k, m, 27)
    return np.sqrt(samples.var(axis=1, ddof=1).sum(axis=0) / (m*k*k))


def bootstrap_pair(aer, hardware, repetitions=2000, seed=2026090601, hierarchical=False):
    """Independent shots in the two data sets; matched twirls only, not shots."""
    if np.shape(aer) != (8, 64, 18) or np.shape(hardware) != (8, 64, 18):
        raise ValueError('Exactly 512 shots per data set required')
    rng = np.random.default_rng(seed)
    means, fractions, invalid = [], [], 0
    for _ in range(repetitions):
        twirls = rng.integers(0, 8, 8) if hierarchical else np.arange(8)
        pair, retained = [], []
        try:
            for data in [aer, hardware]:
                draws = rng.integers(0, 64, (8, 64))
                sample = data[twirls[:, None], draws]
                p, f, _ = estimates(sample)
                pair.append(p)
                retained.append(f)
        except ValueError:
            invalid += 1
            continue
        means.append(pair)
        fractions.append(retained)
    if not means:
        raise ValueError('No valid bootstrap repetitions')
    return np.asarray(means), np.asarray(fractions), invalid


def interval(values):
    return {'low': np.quantile(values, .025, axis=0).tolist(),
            'high': np.quantile(values, .975, axis=0).tolist()}


def simultaneous_raw_band(delta, bootstrap_delta):
    """One prespecified 27-component family; never infer from an RMSE > 0."""
    delta = np.asarray(delta)
    radius = float(np.quantile(np.max(np.abs(bootstrap_delta-delta), axis=-1), .95))
    return {'radius': radius, 'low': (delta-radius).tolist(), 'high': (delta+radius).tolist(),
            'coordinates_excluding_zero': np.flatnonzero(np.abs(delta) > radius).tolist()}


def verify_hashes(folder, filename):
    root = Path(folder).resolve()
    values = a.read(root / filename)
    for name, expected in values.items():
        path = (root / name).resolve()
        if not path.is_relative_to(root) or a.digest(path) != expected:
            raise ValueError(f'Changed or unsafe artifact: {name}')
    return len(values)


def calibration_context(root):
    """Read-only supplemental context check; never tune the running model."""
    from qiskit import qpy
    from qiskit.quantum_info import average_gate_fidelity
    from qiskit_aer.noise.device import basic_device_gate_errors
    from qiskit_ibm_runtime.models import BackendProperties
    old = BackendProperties.from_dict(a.read(a.CAL/'backend_properties.json'))
    latest_path = a.RESULTS/'tflo_compact_budget_2026-09-05/backend_timing_snapshot.json'
    latest = a.read(latest_path)
    comparison = []
    for item in latest['used_instructions']:
        name, qs = item['name'], item['qubits']
        if name not in a.NATIVE:
            continue
        available = {(g.gate, tuple(g.qubits)) for g in old.gates}
        key = tuple(qs)
        if (name, key) not in available and name == 'cz':
            key = key[::-1]
        comparison.append({'name': name, 'physical_wires': qs,
            'abs_reported_gate_error_change': abs(item['error']-old.gate_error(name, key)),
            'abs_duration_change_seconds': abs(item['duration_seconds']-old.gate_length(name, key))})
    props = BackendProperties.from_dict(a.read(root/'restricted_backend_properties.json'))
    channels = {(name, tuple(qs)): e for name, qs, e in basic_device_gate_errors(props)}
    with (root/'circuits/twirl_0.qpy').open('rb') as handle:
        circuit = qpy.load(handle)[0]
    required = {(i.operation.name, tuple(circuit.find_bit(q).index for q in i.qubits))
                for i in circuit.data if i.operation.name in {'x', 'sx', 'cz'}}
    layout = a.read(root/'plan.json')['layout']
    deviations = []
    for name, qs in sorted(required):
        modeled = float(1-average_gate_fidelity(channels[name, qs]))
        reported = props.gate_error(name, qs)
        if abs(modeled-reported) > 1e-10:
            deviations.append({'gate': name, 'physical_wires': [layout[q] for q in qs],
                                'reported_infidelity': reported, 'modeled_infidelity': modeled})
    return {'supplemental_not_a_model_fit': True, 'timing_snapshot_sha256': a.digest(latest_path),
        'later_snapshot_properties_updated': latest['properties_updated'],
        'native_gate_snapshot_comparison': comparison,
        'required_gate_channels_checked': len(required), 'relaxation_floor_deviations': deviations,
        'physical_T2_clipped_qubits': [layout[q] for q in range(18) if props.t2(q) > 2*props.t1(q)],
        'interpretation': 'Aer relaxation can exceed an independently reported gate error; '
                          'its depolarizing contribution is then zero. No values were fitted or changed. '
                          'The partial later snapshot does not verify T1/T2 drift.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    root = args.output.resolve()
    destination = root / 'comparison'
    if destination.exists():
        parser.error('Comparison exists: never overwrite a completed analysis')
    run_hashes = verify_hashes(root, 'run_archive_sha256.json')
    plan = a.read(root / 'plan.json')
    summary = a.read(root / 'run_summary.json')
    if summary['shots'] != 512 or summary['status'] != 'COMPLETE_512_SYNTHETIC_SHOTS':
        raise ValueError('Incomplete synthetic run')
    for name, expected in plan['input_sha256'].items():
        if a.digest(a.ROOT / name) != expected:
            raise ValueError(f'Original source/input changed: {name}')
    exact = np.asarray(plan['setting']['reference'])
    records = {r['twirl_id']: r for r in plan['records']}
    hw = a.read(root / 'hardware_matched_records.json')
    if hw['job_id'] != plan['source_job'] or len(hw['records']) != 8:
        raise ValueError('Wrong hardware data')
    hardware_records = {r['twirl_id']: r for r in hw['records']}
    if set(records) != set(range(8)) or set(hardware_records) != set(range(8)):
        raise ValueError('Missing/duplicated twirls')
    arrays = [[], []]
    for tid in range(8):
        record = records[tid]
        synth = a.read(root/'blocks'/f'twirl_{tid}'/'record.json')
        result = a.read(root/'blocks'/f'twirl_{tid}'/'aer_result.json')
        hardware = hardware_records[tid]
        if synth['record'] != record or any(hardware.get(k) != v for k, v in record.items()):
            raise ValueError('Synthetic/hardware record mismatch')
        if synth['seed_simulator'] != plan['seed_base']+tid:
            raise ValueError('Unexpected random seed')
        expected_memory = [format(int(s, 16), '018b') for s in result['results'][0]['data']['memory']]
        if expected_memory != synth['bitstrings'] or not result['success']:
            raise ValueError('Synthetic record differs from raw Aer result')
        for ds, source in enumerate([synth, hardware]):
            if len(source['bitstrings']) != 64:
                raise ValueError('Wrong block shot count')
            bits = a.decode_bitstrings(source['bitstrings'], 18, record['readout_mask_little_endian'])
            if ds == 0 and bits.tolist() != synth['decoded_little_endian_bits']:
                raise ValueError('Saved decoded bits mismatch')
            arrays[ds].append(bits)
    aer, hardware = (np.asarray(ds, dtype=np.uint8) for ds in arrays)
    point, fractions, counts = zip(*(estimates(ds) for ds in [aer, hardware]))
    point, fractions, counts = np.asarray(point), np.asarray(fractions), np.asarray(counts)
    primary = a.read(a.RUN / 'primary_analysis/results.json')
    if counts[1, 1] != primary['retained_counts'][plan['setting']['id']]:
        raise ValueError('Hardware postselection fails reproduction of original analysis')
    values = metrics(point, fractions, exact)
    draws, fraction_draws, invalid = bootstrap_pair(aer, hardware)
    hdraws, hfraction_draws, hinvalid = bootstrap_pair(aer, hardware, hierarchical=True)
    delta = point[0]-point[1]
    all_draws = [('fixed_twirls', draws, fraction_draws, invalid),
                 ('resampled_twirl_sensitivity', hdraws, hfraction_draws, hinvalid)]
    uncertainty = {}
    for name, means, fracs, bad in all_draws:
        md = metrics(means, fracs, exact)
        dd = means[:, 0]-means[:, 1]
        physical_dd = physical_observables(means[:, 0])-physical_observables(means[:, 1])
        uncertainty[name] = {
            'valid': len(means), 'invalid': bad,
            'metric_intervals': interval(md),
            'aer_minus_hardware_metric_intervals': interval(md[:, 0]-md[:, 1]),
            'pauli_difference_pointwise_intervals': interval(dd),
            'physical_difference_pointwise_intervals': interval(physical_dd),
            'raw_simultaneous_pauli_band': simultaneous_raw_band(delta[0], dd[:, 0]),
            'bootstrap_radius_resolution_diagnostic': {
                str(n): simultaneous_raw_band(delta[0], dd[:n, 0])['radius']
                for n in [500, 1000, 2000] if n <= len(dd)},
            'pauli_mean_pointwise_intervals': interval(means),
            'physical_mean_pointwise_intervals': interval(physical_observables(means))}
    shot_resolution = []
    for m in [8, 16, 32, 64]:
        row = {'shots': 8*m, 'nested_not_independent': True}
        for label, ds in [('aer', aer), ('hardware', hardware)]:
            sub = ds[:, :m]
            flat = sub.reshape(-1, 18)
            raw_mean = pauli_samples(flat).mean(axis=0)
            row[label] = {'raw_metrics': metrics(raw_mean, 1., exact).tolist(),
                          'tolerance1_count_diagnostic_only': int(sector_mask(flat, 4, 4, 1).sum()),
                          'raw_pauli_standard_error': fixed_twirl_standard_error(sub).tolist()}
        shot_resolution.append(row)
    half_delta = (pauli_samples(aer[:, :32].reshape(-1, 18)).mean(axis=0)
                  - pauli_samples(aer[:, 32:].reshape(-1, 18)).mean(axis=0))
    half_se = np.hypot(fixed_twirl_standard_error(aer[:, :32]),
                       fixed_twirl_standard_error(aer[:, 32:]))
    uncorrected_z = np.divide(half_delta, half_se, out=np.zeros(27), where=half_se > 0)
    per_twirl = []
    for tid in range(8):
        per_twirl.append({'twirl_id': tid, **{label: {
            'strict_retained': int(sector_mask(ds[tid], 4, 4, 0).sum()),
            'tolerance1_retained': int(sector_mask(ds[tid], 4, 4, 1).sum()),
            'raw_paulis': pauli_samples(ds[tid]).mean(axis=0).tolist()}
            for label, ds in [('aer', aer), ('hardware', hardware)]}})
    output = {
        'schema': 'aer-hardware-matched-comparison-v1', 'setting': plan['setting'],
        'dataset_order': DATASETS, 'method_order': METHODS, 'metric_order': METRICS,
        'shots_each': 512, 'counts': counts.tolist(), 'metrics': values.tolist(),
        'pauli_means': point.tolist(), 'physical_means': physical_observables(point).tolist(),
        'exact_physical': physical_observables(exact).tolist(),
        'aer_minus_hardware_paulis': delta.tolist(),
        'aer_hardware_pauli_rmse': np.sqrt(np.mean(delta**2, axis=-1)).tolist(),
        'aer_hardware_physical_rmse': np.sqrt(np.mean((physical_observables(point[0])-
            physical_observables(point[1]))**2, axis=-2)).tolist(),
        'uncertainty': uncertainty, 'per_twirl': per_twirl, 'shot_resolution': shot_resolution,
        'independent_half_diagnostic': {'aer_raw_pauli_difference': half_delta.tolist(),
            'difference_standard_error': half_se.tolist(),
            'max_abs_uncorrected_z_not_a_joint_test': float(np.max(np.abs(uncorrected_z)))},
        'new_qpu_seconds': 0, 'aer_run_wall_seconds': summary['sum_aer_run_wall_seconds'],
        'run_hashes_verified': run_hashes, 'input_hashes_verified': len(plan['input_sha256']),
        'run_archive_manifest_sha256': a.digest(root/'run_archive_sha256.json'),
        'analysis_source_sha256': {name: a.digest(a.ROOT/name) for name in [
            'analyze_aer_cuprate_nighthawk_512.py', 'test_aer_cuprate_nighthawk_512.py']},
        'calibration_context': calibration_context(root),
        'boundary': 'One setting, approximate older calibration; no mitigation or advantage claim.'}
    destination.mkdir()
    a.write(destination / 'results.json', output)
    np.savez_compressed(destination / 'bootstrap_draws.npz', fixed=draws,
                        fractions=fraction_draws, hierarchical=hdraws, hierarchical_fractions=hfraction_draws)
    log = io.StringIO()
    suite = unittest.defaultTestLoader.loadTestsFromNames([
        'test_aer_cuprate_nighthawk_smoke', 'test_aer_cuprate_nighthawk_512'])
    tests = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    (destination/'unit_tests.txt').write_text(log.getvalue(), encoding='utf-8')
    if not tests.wasSuccessful():
        raise AssertionError(log.getvalue())
    (destination/'source_snapshot').mkdir()
    for name in ['analyze_aer_cuprate_nighthawk_512.py', 'test_aer_cuprate_nighthawk_512.py']:
        shutil.copyfile(a.ROOT/name, destination/'source_snapshot'/name)
    a.write(destination/'verification.json', {'status': 'PASS', 'unit_tests': tests.testsRun,
        'run_archive_hashes': run_hashes, 'input_hashes': len(plan['input_sha256']),
        'reproduced_hardware_retained_count': int(counts[1, 1]),
        'bootstrap_failures': [invalid, hinvalid]})
    report = [
        '# Aer versus Nighthawk: matched 512-shot vergelijking', '',
        'Een meetpunt: 3x3, U/t=8, T=0.4, 8 identieke twirls x 64 shots per dataset.',
        'Geen nieuwe QPU-seconden. Geen TFLO, PEC of ZNE toegepast.', '',
        '| Dataset / methode | Behouden | RMSE lading | RMSE spin | RMSE doublon |',
        '|---|---:|---:|---:|---:|']
    for d, label in enumerate(DATASETS):
        for m, method in enumerate(METHODS):
            v = values[d, m]
            report.append(f'| {label} / {method} | {counts[d,m]}/512 | {v[1]:.4f} | {v[2]:.4f} | {v[3]:.4f} |')
    conditional = uncertainty['fixed_twirls']['raw_simultaneous_pauli_band']
    sensitive = uncertainty['resampled_twirl_sensitivity']['raw_simultaneous_pauli_band']
    report += ['', 'RMSE is gemeten tegen de exacte ideale EINDIGE circuitreferentie, niet tegen continue tijd.',
        f'Ruwe Aer-hardware Pauli-RMSE: {output["aer_hardware_pauli_rmse"][0]:.5f}.',
        f'Ruwe verschilcomponenten buiten de gelijktijdige 95%-band: {conditional["coordinates_excluding_zero"]}.',
        f'Bandradius (vaste twirls): {conditional["radius"]:.5f}; 2000 bootstrap-herhalingen.',
        f'Met twirl-resampling als gevoeligheidscheck: {sensitive["coordinates_excluding_zero"]}; radius {sensitive["radius"]:.5f}.',
        'Indices 0..17 zijn Z; 18..26 zijn onsite ZZ. Geen afwijking detecteren bewijst geen modelgelijkheid.',
        '', f'Aer-run plus ophalen van resultaten: {summary["sum_aer_run_wall_seconds"]:.2f} s totaal over acht blokken.',
        'Exclusief imports, modelopbouw, ideale controles, opslag en analyse. Twee CPU-threads.',
        '', 'Beperkingen: oudere dagkalibratie, geen idle-gap-relaxatie, crosstalk, leakage, coherente fouten of drift.',
        'Onzekerheidsbanden betreffen samples en de aangegeven twirlkeuze, niet deze modelonzekerheid.',
        'Shot-resolutie, onafhankelijke halve batches, sitewaarden en alle intervallen staan in results.json.',
        f'Verificatie: {tests.testsRun} tests; {run_hashes} archiefhashes; {len(plan["input_sha256"])} inputhashes.', '']
    (destination/'REPORT.md').write_text('\n'.join(report), encoding='utf-8')
    a.write(destination/'sha256.json', {str(p.relative_to(destination)): a.digest(p)
                                      for p in destination.rglob('*') if p.is_file()})
    print(json.dumps({'counts': counts.tolist(), 'metrics': values.tolist(),
                      'raw_discrepancy': conditional, 'tests': tests.testsRun,
                      'aer_seconds': summary['sum_aer_run_wall_seconds']}))


if __name__ == '__main__':
    main()
