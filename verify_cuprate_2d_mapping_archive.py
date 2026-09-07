"""Verify a saved mapping experiment offline; never access IBM or submit jobs."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from qiskit import qpy

from cuprate_2d_hubbard_pipeline import Cuprate2DConfig
from prepare_cuprate_2d_fermionic_sweep import circuit_summary, observables, pauli_records


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify(root):
    manifest = read_json(root / 'artifact_sha256.json')
    require(bool(manifest), 'Empty archive manifest')
    for record in manifest:
        path = (root / record['path']).resolve()
        require(path.is_relative_to(root.resolve()), 'Archive path escapes root')
        require(digest(path) == record['sha256'], f'Archive hash mismatch: {path}')
    validation = read_json(root / 'validation.json')
    require(validation['passed'] and all(c['passed'] for c in validation['checks']),
            'Numerical validation failed')
    for name, expected in validation['source_sha256'].items():
        require(digest(Path(__file__).with_name(name)) == expected,
                f'Validated source has changed: {name}')
    snapshot = read_json(root / 'backend_snapshot.json')
    edges = {tuple(sorted(e)) for e in snapshot['coupling_edges']}
    checked = []
    for steps in (2, 4, 8):
        directory = root / f'steps{steps}'
        plan = read_json(directory / 'plan.json')
        cfg = Cuprate2DConfig(**plan['config'])
        require(not plan['submitted'], 'Archive claims a submitted job')
        path = plan['initial_layout']
        require(len(path) == cfg.qubits == len(set(path)), 'Layout is not injective')
        require(all(tuple(sorted((a, b))) in edges for a, b in zip(path, path[1:])),
                'Physical path uses a non-existent coupling')
        require(plan['final_index_layout'] == path, 'Unexpected routing permutation')
        for label in ('logical', 'isa'):
            target = directory / f'{label}_circuit.qpy'
            require(digest(target) == plan['qpy_sha256'][label], 'Plan QPY hash mismatch')
            with target.open('rb') as stream:
                circuit = qpy.load(stream)[0]
            if label == 'logical':
                require(circuit.num_qubits == cfg.qubits, 'Wrong logical width')
                require(circuit.metadata['mode_order_final'] == list(range(cfg.qubits)),
                        'Fermion mode order is not restored')
                require(circuit.metadata['steps'] == steps, 'Wrong logical step count')
            else:
                require(circuit_summary(circuit) == plan['isa'], 'ISA metrics changed')
                require(circuit.layout.final_index_layout(filter_ancillas=True) == path,
                        'QPY layout differs from plan')
                for instruction in circuit.data:
                    require(instruction.operation.name in ('rz', 'sx', 'x', 'cz'),
                            'Unexpected native gate or measurement')
                    if len(instruction.qubits) == 2:
                        pair = tuple(sorted(circuit.find_bit(q).index for q in instruction.qubits))
                        require(pair in edges, 'Native gate uses a non-existent coupling')
                expected = [{**record, 'paulis': pauli_records(op.apply_layout(circuit.layout))}
                            for record, op in observables(cfg)]
                require(read_json(directory / 'observables.json') == expected,
                        'Observable mapping differs from saved circuit')
                require(len(expected) == plan['observable_count'] == 3 * cfg.sites,
                        'Wrong observable count')
        require(plan['future_zne_settings'] == {'shots_per_noise_factor': 512,
                'noise_factors': [1, 3, 5], 'max_execution_time': 5},
                'Future budget settings changed')
        checked.append({'steps': steps, 'logical_qubits': cfg.qubits,
                        'observables': plan['observable_count'], **plan['isa']})
    return {'passed': True, 'archive_files_verified': len(manifest),
            'source_files_verified': len(validation['source_sha256']),
            'numerical_checks': len(validation['checks']), 'circuits': checked,
            'qpu_jobs_submitted_by_verifier': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--outdir', type=Path, required=True)
    print(json.dumps(verify(parser.parse_args().outdir), indent=2))
