"""Routing-free MPS contraction of the SAME full fermionic swap-network unitary.

The fermionic mode permutations are eliminated algebraically. Every retained
pair evolution has its full Jordan-Wigner string in a bond-4 MPO; no hopping,
U interaction, or product-formula ordering is dropped.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np
import quimb.tensor as qtn
from qiskit import QuantumCircuit, qpy
from qiskit.quantum_info import Statevector, Operator
from threadpoolctl import threadpool_limits

from cuprate_2d_hubbard_pipeline import Cuprate2DConfig, initial_site_rows
from cuprate_2d_qiskit_circuit import load_config
from cuprate_2d_fermionic_mapping import network_schedule, pair_model, build_network
from cuprate_2d_fermionic_dynamics import add_fermionic_hopping
from cuprate_2d_mps_circuit_baseline import site_rows, summarize_site_rows, write_csv
from validate_cuprate_2d_fswap_baseline import save, source_hashes, summarize, validate_engine
from validate_cuprate_2d_fermionic_dynamics import phase_distance

IDENTITY = np.eye(2, dtype=complex)
Z = np.diag([1, -1]).astype(complex)
X = np.array([[0, 1], [1, 0]], dtype=complex)
Y = np.array([[0, -1j], [1j, 0]], dtype=complex)


def hopping_mpo(width, p, q, theta):
    """exp[-i theta/2 (Xp Z... Xq + Yp Z... Yq)], p < q.

    The four strings have coefficients (1+cos(theta))/2,
    (1-cos(theta))/2, -i sin(theta)/2, -i sin(theta)/2.
    The ZZ term has identities, not Zs, between the endpoints.
    """
    if not 0 <= p < q < width:
        raise ValueError('Invalid hopping endpoints')
    endpoints = (IDENTITY, Z, X, Y)
    interior = (IDENTITY, IDENTITY, Z, Z)
    coeffs = ((1 + np.cos(theta))/2, (1 - np.cos(theta))/2,
              -0.5j * np.sin(theta), -0.5j * np.sin(theta))
    arrays = [np.stack([c * op for c, op in zip(coeffs, endpoints)])]
    for _ in range(p + 1, q):
        array = np.zeros((4, 4, 2, 2), dtype=complex)
        for i, op in enumerate(interior):
            array[i, i] = op
        arrays.append(array)
    arrays.append(np.stack(endpoints))
    return qtn.MatrixProductOperator(arrays, sites=range(p, q + 1), L=width)


def pair_actions(cfg):
    hops, onsite = pair_model(cfg)
    layers = network_schedule(cfg.qubits)
    actions = []
    for schedule in (layers, list(reversed(layers))):
        for layer in schedule:
            for _, _, pair in layer:
                p, q = pair
                if hops.get(pair, 0):
                    actions.append(('mpo', hopping_mpo(cfg.qubits, p, q, hops[pair]*cfg.dt/2), tuple(range(p, q+1))))
                if onsite.get(pair, 0):
                    phase = np.diag([1, 1, 1, np.exp(-0.5j*onsite[pair]*cfg.dt)])
                    actions.append(('pair', phase, pair))
    if cfg.chemical_potential:
        phase = np.diag([1, np.exp(1j*cfg.chemical_potential*cfg.dt)])
        actions.extend(('single', phase, (q,)) for q in range(cfg.qubits))
    return actions


def evolve_mpo(cfg, chi, *, cutoff=1e-12, max_seconds=300, progress=None):
    initial = initial_site_rows(cfg)
    bits = ''.join(str(int(row[f'n_{spin}_initial'])) for row in initial for spin in ('up', 'down'))
    psi = qtn.MPS_computational_state(bits, dtype='complex128')
    expected = {spin: sum(int(r[f'n_{spin}_initial']) for r in initial) for spin in ('up', 'down')}
    actions = pair_actions(cfg)
    info = {'cur_orthog': 'calc'}
    started = time.perf_counter()
    evolution_seconds = 0.0
    retained = 1.0
    snapshots = []
    for step_index in range(1, cfg.steps + 1):
        tick = time.perf_counter()
        for i, (kind, op, where) in enumerate(actions):
            if time.perf_counter() - started > max_seconds:
                raise TimeoutError(f'Local MPO case exceeded {max_seconds} seconds')
            if kind == 'mpo':
                psi.gate_with_submpo_(op, where=where, method='direct', info=info,
                                      max_bond=chi, cutoff=cutoff, cutoff_mode='rel', renorm=False)
            elif kind == 'pair':
                psi.gate_with_auto_swap_(op, where, info=info, max_bond=chi,
                                         cutoff=cutoff, cutoff_mode='rel', renorm=False)
            else:
                psi.gate_(op, where[0], contract=True)
            if progress is not None and (i+1) % 64 == 0:
                progress({'event': 'progress', 'route': 'routing_free_mpo', 'chi': chi,
                          'step': step_index, 'actions_in_step': i+1,
                          'elapsed_seconds': time.perf_counter()-started})
        evolution_seconds += time.perf_counter() - tick
        norm_before = float(np.real(psi.normalize()))
        retained *= norm_before
        info.clear()
        current = replace(cfg, steps=step_index)
        sites = site_rows(current, psi, profile=f'network_mpo_chi{chi}')
        entropy = float(psi.entropy(cfg.qubits // 2))
        info.clear()
        totals = summarize_site_rows(sites)
        totals.update({f'total_n_{spin}': sum(r[f'n_{spin}'] for r in sites) for spin in expected})
        snapshot = {'step': step_index, 'time': current.total_time,
                    'norm_squared_before_step_normalization': norm_before,
                    'cumulative_retained_norm_weight': retained,
                    'half_chain_entropy_bits': entropy, 'entropy_capacity_bits': math.log2(chi),
                    'max_bond_observed': int(max(psi.bond_sizes())),
                    'max_spin_particle_number_drift': max(abs(totals[f'total_n_{s}']-expected[s]) for s in expected),
                    'totals': totals, 'sites': sites}
        snapshots.append(snapshot)
        if progress is not None:
            progress({'event': 'step_complete', 'chi': chi,
                      'elapsed_seconds': time.perf_counter()-started, **snapshot})
    return psi, {'config': asdict(cfg), 'chi': chi, 'cutoff': cutoff, 'cutoff_mode': 'rel',
                 'route': 'routing_free_mpo', 'actions_per_step': len(actions),
                 'renormalize_during_svd': False, 'snapshots': snapshots,
                 'evolution_seconds': evolution_seconds,
                 'elapsed_seconds_including_observables': time.perf_counter()-started,
                 'normalization_note': 'Retained norm is a diagnostic, not fidelity or a rigorous error bound.',
                 'sector_note': 'Mean particle numbers alone do not prove sector purity.'}


def validate_mpo():
    result = validate_engine()
    def check(name, value):
        record = {'check': name, 'value': float(value), 'threshold': 1e-10, 'passed': bool(value < 1e-10)}
        result['checks'].append(record)
        print(json.dumps(record), flush=True)
        if not record['passed']:
            raise AssertionError(name)
    for width in (2, 3, 5):
        qc = QuantumCircuit(width)
        add_fermionic_hopping(qc, 0, width-1, -0.7, 0.19)
        matrix = hopping_mpo(width, 0, width-1, -0.7*0.19).to_dense()
        check(f'JW_hopping_MPO_width{width}', np.max(np.abs(matrix-Operator(qc).data)))
    for lx, ly, holes in ((2, 2, 2), (2, 3, 2)):
        cfg = Cuprate2DConfig(lx=lx, ly=ly, holes=holes, steps=2, chemical_potential=0.17)
        psi, record = evolve_mpo(cfg, 64, cutoff=0.0)
        vector = np.asarray(psi.to_dense()).reshape([2]*cfg.qubits)
        vector = vector.transpose(list(reversed(range(cfg.qubits)))).reshape(-1)
        reference = Statevector.from_instruction(build_network(cfg)).data
        check(f'{lx}x{ly}_routing_free_MPO_vs_exact_network', phase_distance(vector, reference))
        check(f'{lx}x{ly}_routing_free_MPO_norm', abs(1-record['snapshots'][-1]['cumulative_retained_norm_weight']))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--outdir', type=Path, required=True)
    parser.add_argument('--steps', type=int, default=2)
    parser.add_argument('--dt', type=float, default=0.1)
    parser.add_argument('--max-bonds', default='16,32,64')
    parser.add_argument('--case-seconds', type=float, default=300)
    parser.add_argument('--matching-qpy', type=Path)
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)
    cfg = replace(load_config(args.config), steps=args.steps, dt=args.dt)
    chis = [int(c) for c in args.max_bonds.split(',')]
    if chis != sorted(set(chis)) or not chis or chis[0] < 1:
        raise ValueError('Bond dimensions must be positive, unique and increasing')
    hashes = source_hashes()
    hashes[Path(__file__).name] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    with threadpool_limits(limits=1):
        validation = validate_mpo()
        validation['source_sha256'] = hashes
        save(args.outdir/'engine_validation.json', validation)
        if args.validate_only:
            return
        matching = None
        if args.matching_qpy:
            with args.matching_qpy.open('rb') as handle:
                archived = qpy.load(handle)[0]
            if archived != build_network(cfg):
                raise ValueError('The reference network differs from the archived circuit')
            matching = {'path': str(args.matching_qpy), 'sha256': hashlib.sha256(args.matching_qpy.read_bytes()).hexdigest(), 'logical_circuit_equal': True}
        save(args.outdir/'run_manifest.json', {'source_sha256': hashes, 'config': asdict(cfg),
             'matching_qpy': matching, 'route': 'routing_free_mpo', 'max_bonds': chis,
             'case_seconds': args.case_seconds, 'blas_threads': 1, 'submitted': False,
             'shots_field_unused': True, 'gate_baseline_manifest_for_versions': '../time0p2_dt0p1/run_manifest.json'})
        records = []
        for chi in chis:
            target = args.outdir/f'chi{chi}.json'
            if target.exists():
                record = json.loads(target.read_text())
                if record['source_sha256'] != hashes or record['config'] != asdict(cfg):
                    raise ValueError('Existing case differs; choose another output directory')
            else:
                print(json.dumps({'event': 'case_start', 'route': 'routing_free_mpo', 'chi': chi}), flush=True)
                with (args.outdir/f'chi{chi}_progress.jsonl').open('a', encoding='utf-8') as log:
                    def progress(event):
                        log.write(json.dumps(event)+'\n'); log.flush()
                        print(json.dumps({k:v for k,v in event.items() if k != 'sites'}), flush=True)
                    try:
                        _, record = evolve_mpo(cfg, chi, max_seconds=args.case_seconds, progress=progress)
                    except TimeoutError as exc:
                        save(args.outdir/f'chi{chi}_timeout.json', {'error': str(exc), 'config': asdict(cfg), 'source_sha256': hashes})
                        summarize(args.outdir, records, validation)
                        return
                record['source_sha256'] = hashes
                save(target, record)
                write_csv(args.outdir/f'chi{chi}_sites.csv', record['snapshots'][-1]['sites'])
            records.append(record)
            summary = summarize(args.outdir, records, validation)
            print(json.dumps({'event': 'case_complete', 'route': 'routing_free_mpo', 'chi': chi, 'summary': summary}), flush=True)


if __name__ == '__main__':
    main()
