"""Bounded, resumable offline 8x64-shot Aer pilot; no provider calls."""
import argparse
import json
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from qiskit import qpy
from qiskit_aer import AerSimulator
from qiskit_ibm_runtime.models import BackendProperties

import aer_cuprate_nighthawk_smoke as a
from analyze_cuprate_2d_tflo import load_archive

SETTING = 'interacting_holdout_U8_T0.4'
PROTOCOL = a.ROOT / 'AER_NIGHTHAWK_512_PROTOCOL.md'
SMOKE = a.RESULTS / 'aer_nighthawk_smoke_2026-09-05'


def validate_noise(circuit, physical, snapshot, noise):
    edges = {tuple(e) for e in snapshot['coupling_edges']}
    for i in physical.data:
        if i.operation.name == 'cz':
            qs = tuple(physical.find_bit(q).index for q in i.qubits)
            if qs not in edges and qs[::-1] not in edges:
                raise ValueError('CZ outside calibrated graph')
    encoded = noise.to_dict()
    covered = {(name, tuple(qs)) for e in encoded['errors'] if e['type'] == 'qerror'
               for name in e['operations'] for qs in e['gate_qubits']}
    required = {(i.operation.name, tuple(circuit.find_bit(q).index for q in i.qubits))
                for i in circuit.data if i.operation.name in {'x', 'sx', 'cz'}}
    if required - covered:
        raise ValueError('Missing native gate noise')
    readouts = {q for e in encoded['errors'] if e['type'] == 'roerror'
                for qs in e['gate_qubits'] for q in qs}
    if readouts != set(range(18)):
        raise ValueError('Missing readout channels')
    return len(required)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    out = args.output.resolve()
    plan, raw, _, nup, ndn = load_archive(a.PLAN, a.RUN / 'raw_bitstrings.json')
    if (nup, ndn) != (4, 4):
        raise ValueError('Wrong sector')
    primary = a.read(a.RUN / 'primary_analysis/results.json')
    if primary['raw_sha256'] != a.digest(a.RUN / 'raw_bitstrings.json'):
        raise ValueError('Hardware archive differs from verified primary input')
    old_provenance = a.read(SMOKE / 'provenance.json')
    for name, expected in old_provenance['input_sha256'].items():
        if a.digest(a.ROOT / name) != expected:
            raise ValueError(f'Smoke input/source changed: {name}')
    selected = [(i, r) for i, r in enumerate(plan['records']) if r['setting_id'] == SETTING]
    selected.sort(key=lambda ir: ir[1]['twirl_id'])
    if [r['twirl_id'] for _, r in selected] != list(range(8)) or any(r['shots'] != 64 for _, r in selected):
        raise ValueError('Expected exactly eight 64-shot twirls')
    layout = plan['initial_layout']
    reference = next(s for s in plan['settings'] if s['id'] == SETTING)
    props = a.read(a.CAL / 'backend_properties.json')
    snapshot = a.read(a.CAL / 'backend_snapshot.json')
    if props['backend_name'] != 'ibm_phoenix' or layout != old_provenance['physical_layout']:
        raise ValueError('Changed device/layout')
    reduced, mirrors = a.restrict_properties(props, layout)
    noise = a.build_noise(BackendProperties.from_dict(reduced))
    source_names = [Path(__file__).name, 'aer_cuprate_nighthawk_smoke.py',
                    'analyze_cuprate_2d_tflo.py', 'cuprate_2d_tflo.py',
                    'AER_NIGHTHAWK_512_PROTOCOL.md', 'AER_NIGHTHAWK_PROTOCOL.md']
    inputs = [a.ROOT / n for n in source_names] + [a.PLAN / 'manifest.json',
              a.RUN / 'raw_bitstrings.json', a.CAL / 'backend_properties.json',
              a.CAL / 'backend_snapshot.json']
    paths = {r['twirl_id']: a.RUN/'provider_inputs'/f'circuit_{i:03d}.qpy' for i, r in selected}
    inputs += list(paths.values())
    hashes = {str(p.relative_to(a.ROOT)): a.digest(p) for p in inputs}
    if out.exists():
        if not args.resume:
            parser.error('Output exists; use --resume only for this exact frozen run')
        if (out / 'run_summary.json').exists():
            parser.error('Run already complete; no resampling')
        if a.read(out / 'plan.json')['input_sha256'] != hashes:
            raise ValueError('Resume input/source mismatch')
    else:
        if args.resume:
            parser.error('Cannot resume a missing run')
        out.mkdir(parents=True)
        (out / 'blocks').mkdir()
        (out / 'circuits').mkdir()
        (out / 'source_snapshot').mkdir()
        for name in source_names:
            shutil.copyfile(a.ROOT / name, out / 'source_snapshot' / name)
        a.write(out / 'plan.json', {
            'schema': 'aer-matched512-plan-v1', 'synthetic_not_hardware': True,
            'setting': reference, 'config': plan['config'], 'layout': layout,
            'shots_per_twirl': 64, 'twirls': 8, 'total_shots': 512,
            'records': [r for _, r in selected], 'seed_base': 2026090590,
            'bootstrap_repetitions': 2000, 'bootstrap_seed': 2026090601,
            'source_job': raw['job_id'], 'qpu_seconds': 0,
            'calibration_updated': props['last_update_date'],
            'calibration_captured_unix': snapshot['captured_unix'],
            'mirrored_symmetric_cz_pairs': mirrors,
            'limitations': old_provenance['limitations'][:4],
            'method': 'statevector', 'precision': 'double', 'max_parallel_threads': 2,
            'affinity_cpus': len(os.sched_getaffinity(0)), 'qiskit': a.qiskit.__version__,
            'aer': a.qiskit_aer.__version__, 'created_utc': datetime.now(timezone.utc).isoformat(),
            'input_sha256': hashes})
        a.write(out / 'hardware_matched_records.json', {
            'job_id': raw['job_id'], 'records': [r for r in raw['records'] if r['setting_id'] == SETTING]})
        a.write(out / 'restricted_backend_properties.json', reduced)
        a.write(out / 'noise_model.json', noise.to_dict(serializable=True))
    checks = []
    circuits = {}
    for _, r in selected:
        tid = r['twirl_id']
        with paths[tid].open('rb') as handle:
            physical = qpy.load(handle)[0]
        if physical.num_qubits != 120 or physical.parameters:
            raise ValueError('Unexpected provider circuit')
        local = a.remap_measured(physical, layout)
        covered = validate_noise(local, physical, snapshot, noise)
        ideal, norm, outside = a.exact_paulis(local, r['readout_mask_little_endian'])
        error = float(np.max(np.abs(ideal-reference['reference'])))
        if error > 1e-9 or abs(norm-1) > 1e-9 or outside > 1e-9:
            raise ValueError(f'Noise-off check failed for twirl {tid}')
        checks.append({'twirl_id': tid, 'max_pauli_error': error, 'norm': norm,
                       'outside_4_4_sector': outside, 'noise_keys_covered': covered,
                       'native_counts': dict(local.count_ops()), 'depth': local.depth()})
        circuits[tid] = local
        path = out / 'circuits' / f'twirl_{tid}.qpy'
        if not path.exists():
            with path.open('wb') as handle:
                qpy.dump(local, handle)
    if not (out / 'preflight.json').exists():
        a.write(out / 'preflight.json', {'status': 'PASS', 'checks': checks})
    print(json.dumps({'stage': 'all_eight_noise_off_checks_passed',
                      'max_error': max(c['max_pauli_error'] for c in checks)}), flush=True)
    simulator = AerSimulator(method='statevector', precision='double', noise_model=noise,
                             max_parallel_threads=2, max_parallel_shots=2, enable_truncation=False)
    start = time.perf_counter()
    for _, r in selected:
        tid = r['twirl_id']
        folder = out / 'blocks' / f'twirl_{tid}'
        if (folder / 'sha256.json').exists():
            for name, expected in a.read(folder / 'sha256.json').items():
                if a.digest(folder / name) != expected:
                    raise ValueError('Completed block hash mismatch')
            old = a.read(folder / 'record.json')
            if old['record'] != r or old['seed_simulator'] != 2026090590 + tid:
                raise ValueError('Completed block metadata mismatch')
            continue
        if folder.exists():
            raise ValueError('Partial block preserved; inspect before retry, do not overwrite')
        # A folder is created only after a successful completed simulation.
        block_start = time.perf_counter()
        result = simulator.run(circuits[tid], shots=64, memory=True,
                               seed_simulator=2026090590+tid).result()
        elapsed = time.perf_counter()-block_start
        if not result.success:
            raise RuntimeError(result.status)
        memory = result.get_memory(0)
        metadata = result.results[0].metadata
        if len(memory) != 64 or metadata['num_qubits'] != 18 or metadata['measure_sampling']:
            raise ValueError('Wrong trajectory/shot metadata')
        bits = a.decode_bitstrings(memory, 18, r['readout_mask_little_endian'])
        folder.mkdir()
        a.write(folder / 'record.json', {'schema': 'synthetic-aer-block-v1', 'record': r,
                'seed_simulator': 2026090590+tid, 'bitstrings': memory,
                'decoded_little_endian_bits': bits.tolist(), 'run_wall_seconds': elapsed})
        a.write(folder / 'aer_result.json', result.to_dict())
        a.write(folder / 'sha256.json', {p.name: a.digest(p) for p in folder.iterdir() if p.is_file()})
        print(json.dumps({'completed_twirls': tid+1, 'shots_completed': (tid+1)*64,
                          'last_block_wall_seconds': elapsed}), flush=True)
    records = [a.read(out/'blocks'/f'twirl_{t}'/'record.json') for t in range(8)]
    summary = {'status': 'COMPLETE_512_SYNTHETIC_SHOTS', 'shots': 512, 'twirls': 8,
               'setting_id': SETTING, 'qpu_seconds': 0,
               'sum_aer_run_wall_seconds': sum(r['run_wall_seconds'] for r in records),
               'this_execution_loop_wall_seconds': time.perf_counter()-start,
               'analysis_pending': True}
    a.write(out / 'run_summary.json', summary)
    a.write(out / 'run_archive_sha256.json', {str(p.relative_to(out)): a.digest(p)
                for p in out.rglob('*') if p.is_file()})
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    main()
