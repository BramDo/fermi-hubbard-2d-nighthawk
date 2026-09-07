"""Offline, checkpointed MPS convergence for the full fermionic swap network.

This validates a classical circuit reference, not hardware or quantum advantage.
Times use hbar/t with hopping_t=1. The recorded spin_z is n_up-n_down (2 S_z).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import time
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np
import quimb
import quimb.tensor as qtn
import qiskit
from qiskit import qpy
from qiskit.quantum_info import Statevector
from scipy.sparse.linalg import expm_multiply
from threadpoolctl import threadpool_limits

from cuprate_2d_hubbard_pipeline import Cuprate2DConfig, initial_site_rows
from cuprate_2d_fermionic_mapping import build_network
from cuprate_2d_qiskit_circuit import load_config
from cuprate_2d_mps_circuit_baseline import site_rows, summarize_site_rows, write_csv
from cuprate_2d_exact_sector_baseline import sector_basis, initial_state_vector, diagonal_site_rows
from validate_cuprate_2d_fermionic_dynamics import independent_hamiltonian, phase_distance

OBSERVABLES = ('charge', 'spin_z', 'double_occupancy')
THRESHOLDS = {'rmse': 0.001, 'maximum_site_difference': 0.005,
              'particle_number_drift': 0.01, 'minimum_retained_norm_weight': 0.99}


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def source_hashes():
    names = [Path(__file__).name, 'cuprate_2d_fermionic_mapping.py',
             'cuprate_2d_fermionic_dynamics.py', 'cuprate_2d_mps_circuit_baseline.py',
             'cuprate_2d_hubbard_pipeline.py', 'cuprate_2d_qiskit_circuit.py',
             'cuprate_2d_exact_sector_baseline.py', 'validate_cuprate_2d_fermionic_dynamics.py']
    return {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
            for name in names}


def differences(a, b):
    a = sorted(a, key=lambda r: r['site'])
    b = sorted(b, key=lambda r: r['site'])
    if [r['site'] for r in a] != [r['site'] for r in b]:
        raise ValueError('Observable site mismatch')
    result = {}
    for key in OBSERVABLES:
        delta = np.array([x[key] - y[key] for x, y in zip(a, b)])
        result[key] = {'rmse': float(np.sqrt(np.mean(delta**2))),
                       'max_abs': float(np.max(np.abs(delta)))}
    return result


def evolve(cfg, chi, *, cutoff=1e-12, max_seconds=300, progress=None):
    """Apply exactly the logical gates with canonical SVD and no hidden renorm.

    P, CP, and XXPlusYY(beta=0) are symmetric under reversing the pair order,
    so their Qiskit matrices can be used directly with quimb's site order.
    Only the end-of-step normalization is explicit; its lost norm is recorded.
    """
    if chi < 1 or cutoff < 0 or max_seconds <= 0:
        raise ValueError('Invalid numerical limits')
    bits = ['0'] * cfg.qubits
    initial = initial_site_rows(cfg)
    expected = {spin: sum(int(r[f'n_{spin}_initial']) for r in initial)
                for spin in ('up', 'down')}
    for row in initial:
        for spin, offset in (('up', 0), ('down', 1)):
            bits[2 * int(row['site']) + offset] = str(int(row[f'n_{spin}_initial']))
    psi = qtn.MPS_computational_state(''.join(bits), dtype='complex128')
    step = build_network(replace(cfg, steps=1), prepare=False)
    gates = []
    for instruction in step.data:
        op = instruction.operation
        where = tuple(step.find_bit(q).index for q in instruction.qubits)
        if op.name not in ('xx_plus_yy', 'cp', 'p'):
            raise ValueError(f'Unexpected network operation: {op.name}')
        if len(where) == 2 and where[1] != where[0] + 1:
            raise ValueError('Network gate is not adjacent and ascending')
        gates.append((np.asarray(op.to_matrix(), dtype=complex), where))
    info = {'cur_orthog': 'calc'}
    started = time.perf_counter()
    snapshots = []
    retained_weight = 1.0
    two_qubit_count = 0
    evolution_seconds = 0.0
    for step_index in range(1, cfg.steps + 1):
        tick = time.perf_counter()
        for matrix, where in gates:
            if time.perf_counter() - started > max_seconds:
                raise TimeoutError(f'Local case exceeded {max_seconds} seconds')
            if len(where) == 1:
                psi.gate_(matrix, where[0], contract=True)
            else:
                psi.gate_with_auto_swap_(matrix, where, info=info, max_bond=chi,
                                         cutoff=cutoff, cutoff_mode='rel', renorm=False)
                two_qubit_count += 1
                if progress is not None and two_qubit_count % 512 == 0:
                    progress({'event': 'progress', 'step': step_index, 'chi': chi,
                              'two_qubit_gates': two_qubit_count,
                              'elapsed_seconds': time.perf_counter() - started})
        evolution_seconds += time.perf_counter() - tick
        norm_before = float(np.real(psi.normalize()))
        retained_weight *= norm_before
        # Normalizing at the last tensor and computing observables move the
        # orthogonality center: never reuse a stale cached center afterwards.
        info.clear()
        current = replace(cfg, steps=step_index)
        rows = site_rows(current, psi, profile=f'network_chi{chi}')
        entropy_bits = float(psi.entropy(cfg.qubits // 2))
        info.clear()
        totals = summarize_site_rows(rows)
        totals.update({f'total_n_{spin}': sum(r[f'n_{spin}'] for r in rows)
                       for spin in ('up', 'down')})
        drift = max(abs(totals[f'total_n_{s}'] - expected[s]) for s in expected)
        snapshot = {'step': step_index, 'time': current.total_time,
                    'norm_squared_before_step_normalization': norm_before,
                    'cumulative_retained_norm_weight': retained_weight,
                    'half_chain_entropy_bits': entropy_bits,
                    'entropy_capacity_bits': math.log2(chi),
                    'max_bond_observed': int(max(psi.bond_sizes())),
                    'max_spin_particle_number_drift': float(drift),
                    'totals': totals, 'sites': rows}
        snapshots.append(snapshot)
        if progress is not None:
            progress({'event': 'step_complete', 'chi': chi,
                      'elapsed_seconds': time.perf_counter() - started, **snapshot})
    return psi, {'config': asdict(cfg), 'chi': chi, 'cutoff': cutoff,
                 'cutoff_mode': 'rel', 'renormalize_during_svd': False,
                 'snapshots': snapshots, 'evolution_seconds': evolution_seconds,
                 'elapsed_seconds_including_observables': time.perf_counter() - started,
                 'normalization_note': 'Retained norm is a truncation diagnostic, not fidelity or a rigorous error bound.',
                 'sector_note': 'Mean N_up/N_down drift is monitored; zero mean drift alone does not prove sector purity.'}


def validate_engine():
    checks = []
    def check(name, value, tolerance):
        result = {'check': name, 'value': float(value), 'threshold': tolerance,
                  'passed': bool(value <= tolerance)}
        checks.append(result)
        print(json.dumps(result), flush=True)
        if not result['passed']:
            raise AssertionError(name)
    for lx, ly, holes in ((2, 2, 2), (2, 3, 2)):
        cfg = Cuprate2DConfig(lx=lx, ly=ly, holes=holes, steps=2, chemical_potential=0.17)
        psi, result = evolve(cfg, 64, cutoff=0.0)
        vector = np.asarray(psi.to_dense()).reshape([2] * cfg.qubits)
        vector = vector.transpose(list(reversed(range(cfg.qubits)))).reshape(-1)
        reference = Statevector.from_instruction(build_network(cfg)).data
        check(f'{lx}x{ly}_MPS_full_state_vs_Qiskit', phase_distance(vector, reference), 1e-10)
        check(f'{lx}x{ly}_untruncated_norm_loss',
              abs(1 - result['snapshots'][-1]['cumulative_retained_norm_weight']), 1e-10)
        check(f'{lx}x{ly}_particle_number_drift',
              result['snapshots'][-1]['max_spin_particle_number_drift'], 1e-10)
    cfg = Cuprate2DConfig(lx=2, ly=3, holes=2, steps=2)
    _, truncated = evolve(cfg, 2, cutoff=0.0)
    loss = 1 - truncated['snapshots'][-1]['cumulative_retained_norm_weight']
    check('low_chi_truncation_is_detected', 0.0 if loss > 1e-4 else 1.0, 0.0)
    # Independent Hamiltonian oracle, fixed-time refinement, no MPS truncation.
    basis, index, _, _ = sector_basis(cfg)
    h = independent_hamiltonian(cfg, basis)
    init = initial_state_vector(cfg, index)
    exact = expm_multiply(-0.2j * h, init)
    exact_rows = diagonal_site_rows(cfg, basis, exact, 2, 0.2, 'exact_H')
    errors = []
    refinements = []
    for steps in (2, 4, 8):
        current = replace(cfg, steps=steps, dt=0.2 / steps)
        vector = Statevector.from_instruction(build_network(current)).data[basis]
        error = phase_distance(vector, exact)
        rows = diagonal_site_rows(current, basis, vector, steps, 0.2, 'network')
        errors.append(error)
        refinements.append({'steps': steps, 'dt': current.dt, 'state_distance': error,
                            'observable_errors': differences(rows, exact_rows)})
    for i in (0, 1):
        check(f'fixed_time_second_order_{i}', abs(errors[i] / errors[i+1] - 4), 0.5)
    return {'passed': True, 'checks': checks, 'exact_H_refinement_2x3': refinements,
            'low_chi_detected_norm_loss': loss}


def summarize(root, records, validation):
    comparisons = []
    for lower, upper in zip(records, records[1:]):
        delta = differences(lower['snapshots'][-1]['sites'], upper['snapshots'][-1]['sites'])
        final = upper['snapshots'][-1]
        passed = (all(v['rmse'] <= THRESHOLDS['rmse'] and
                      v['max_abs'] <= THRESHOLDS['maximum_site_difference'] for v in delta.values())
                  and final['max_spin_particle_number_drift'] <= THRESHOLDS['particle_number_drift']
                  and final['cumulative_retained_norm_weight'] >= THRESHOLDS['minimum_retained_norm_weight'])
        comparisons.append({'chi_low': lower['chi'], 'chi_high': upper['chi'],
                            'differences': delta, 'passes_screening_thresholds': bool(passed)})
    consecutive = len(comparisons) >= 2 and all(r['passes_screening_thresholds'] for r in comparisons[-2:])
    summary = {'validation_passed': validation['passed'], 'thresholds': THRESHOLDS,
               'comparisons': comparisons, 'two_consecutive_refinements_pass': consecutive,
               'case_count': len(records), 'config': records[-1]['config'] if records else None,
               'claim_boundary': 'Finite-chi circuit convergence screening, not an exact 6x6 Hamiltonian reference. Independent dt convergence is also required.',
               'hardware_submission_allowed_by_this_script': False}
    save(root / 'convergence_summary.json', summary)
    lines = ['# Full fermionic network: classical baseline screening', '',
             f"Engine validation: {len(validation['checks'])} checks passed.",
             f'Two consecutive bond refinements pass: {consecutive}.', '',
             '| chi | elapsed s | retained norm weight | N-up | N-down | half-chain entropy (bits) |',
             '|---:|---:|---:|---:|---:|---:|']
    for r in records:
        s = r['snapshots'][-1]
        lines.append(f"| {r['chi']} | {r['elapsed_seconds_including_observables']:.2f} | {s['cumulative_retained_norm_weight']:.8f} | {s['totals']['total_n_up']:.6f} | {s['totals']['total_n_down']:.6f} | {s['half_chain_entropy_bits']:.6f} |")
    lines += ['', '## Observable differences', '',
              '| chi pair | charge RMSE | spin-z RMSE | double-occupancy RMSE | screening passes |',
              '|---|---:|---:|---:|---|']
    for r in comparisons:
        d = r['differences']
        lines.append(f"| {r['chi_low']} -> {r['chi_high']} | {d['charge']['rmse']:.6g} | {d['spin_z']['rmse']:.6g} | {d['double_occupancy']['rmse']:.6g} | {r['passes_screening_thresholds']} |")
    lines += ['', 'Screening thresholds: RMSE <= 0.001 and maximum site difference <= 0.005 for each observable; each mean spin particle number within 0.01, retained norm weight >= 0.99.',
              'A pass is a finite-ladder diagnostic, not a certified error bound. Retained norm weight is not fidelity. Mean particle-number conservation alone is not sector purity.',
              'The initial state, t, t-prime, U and network ordering match the mapped full-fermion circuit. Spin-z denotes n-up minus n-down; physical S-z is half this value.',
              'Time uses hbar/t with hopping_t=1. Statistics/shots do not enter this noiseless calculation.',
              'Do not compare the old shallow hardware data against this reference. No QPU jobs are submitted.',
              'MPS method reference: https://quimb.readthedocs.io/en/main/autoapi/quimb/tensor/tn1d/core/index.html', '']
    (root / 'baseline_report.md').write_text('\n'.join(lines), encoding='utf-8')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--outdir', type=Path, required=True)
    parser.add_argument('--steps', type=int, default=2)
    parser.add_argument('--dt', type=float, default=0.1)
    parser.add_argument('--max-bonds', default='16,32,64')
    parser.add_argument('--case-seconds', type=float, default=300)
    parser.add_argument('--validate-only', action='store_true')
    parser.add_argument('--matching-qpy', type=Path)
    args = parser.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)
    cfg = replace(load_config(args.config), steps=args.steps, dt=args.dt)
    chis = [int(x) for x in args.max_bonds.split(',')]
    if chis != sorted(set(chis)) or not chis or chis[0] < 1:
        raise ValueError('Bond dimensions must be positive, unique and increasing')
    hashes = source_hashes()
    with threadpool_limits(limits=1):
        validation = validate_engine()
        validation['source_sha256'] = hashes
        save(args.outdir / 'engine_validation.json', validation)
        if args.validate_only:
            return
        archive_match = None
        if args.matching_qpy:
            with args.matching_qpy.open('rb') as handle:
                archived = qpy.load(handle)[0]
            if archived != build_network(cfg):
                raise ValueError('Baseline circuit differs from archived QPY')
            archive_match = {'path': str(args.matching_qpy),
                             'sha256': hashlib.sha256(args.matching_qpy.read_bytes()).hexdigest(),
                             'logical_circuit_equal': True}
        save(args.outdir / 'run_manifest.json', {'source_sha256': hashes, 'config': asdict(cfg),
             'matching_qpy': archive_match, 'thresholds': THRESHOLDS, 'max_bonds': chis,
             'case_seconds': args.case_seconds, 'blas_threads': 1, 'submitted': False,
             'versions': {'python': platform.python_version(), 'quimb': quimb.__version__,
                          'qiskit': qiskit.__version__, 'numpy': np.__version__}})
        records = []
        for chi in chis:
            target = args.outdir / f'chi{chi}.json'
            if target.exists():
                record = json.loads(target.read_text())
                if record['source_sha256'] != hashes or record['config'] != asdict(cfg):
                    raise ValueError('Existing case has different sources/config; use a new outdir')
            else:
                print(json.dumps({'event': 'case_start', 'chi': chi, 'config': asdict(cfg)}), flush=True)
                with (args.outdir / f'chi{chi}_progress.jsonl').open('a', encoding='utf-8') as log:
                    def progress(event):
                        log.write(json.dumps(event) + '\n'); log.flush()
                        print(json.dumps({k: v for k, v in event.items() if k != 'sites'}), flush=True)
                    try:
                        _, record = evolve(cfg, chi, max_seconds=args.case_seconds, progress=progress)
                    except TimeoutError as exc:
                        save(args.outdir / f'chi{chi}_timeout.json', {'error': str(exc), 'config': asdict(cfg), 'source_sha256': hashes})
                        summarize(args.outdir, records, validation)
                        return
                record['source_sha256'] = hashes
                save(target, record)
                write_csv(args.outdir / f'chi{chi}_sites.csv', record['snapshots'][-1]['sites'])
            records.append(record)
            summary = summarize(args.outdir, records, validation)
            print(json.dumps({'event': 'case_complete', 'chi': chi, 'summary': summary}), flush=True)


if __name__ == '__main__':
    main()
