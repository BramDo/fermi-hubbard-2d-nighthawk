"""Offline audit of the frozen pilot, actual provider input, and result metrics."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from qiskit import qpy
from qiskit.quantum_info import SparsePauliOp
from qiskit_ibm_runtime.json import RuntimeDecoder

from cuprate_2d_fermionic_pilot import verify_frozen, rows_from_values, save, read
from validate_cuprate_2d_fswap_baseline import differences


def audit(root):
    plan = verify_frozen(root)
    inputs = json.loads((root/'provider_inputs.json').read_text(), cls=RuntimeDecoder)
    assert len(inputs['pubs']) == 1
    pub = inputs['pubs'][0]
    with (root/'isa_circuit.qpy').open('rb') as handle:
        frozen = qpy.load(handle)[0]
    assert pub[0] == frozen, 'Provider circuit differs from frozen circuit'
    records = read(root/'observables.json')
    assert len(pub[1]) == len(records) == 27
    for actual, expected in zip(pub[1], records, strict=True):
        a = SparsePauliOp.from_list(list(actual.items()))
        b = SparsePauliOp.from_list(expected['physical_paulis'])
        assert a.equiv(b), 'Provider observable differs from frozen mapping'
    opts = inputs['options']
    # Runtime.program_run puts max_execution_time (seconds) in the job-level
    # field "cost"; it is deliberately absent from primitive program inputs.
    job_metadata = read(root/'provider_job_metadata.json')
    assert job_metadata['id'] == read(root/'submission_receipt.json')['job_id']
    assert job_metadata['cost'] == plan['options']['max_execution_time'] == 5
    assert opts['default_shots'] == plan['options']['default_shots'] == 512
    assert opts['resilience']['zne']['noise_factors'] == [1, 3, 5]
    assert opts['resilience']['zne']['extrapolator'] == ['linear', 'fallback']
    assert opts['resilience']['zne_mitigation'] and not opts['resilience']['pec_mitigation']
    assert not opts['resilience']['measure_mitigation']
    assert opts['twirling']['num_randomizations'] == 8
    assert opts['twirling']['shots_per_randomization'] == 64
    assert opts['twirling']['enable_gates'] and opts['twirling']['enable_measure']
    for name, expected in plan['validation']['source_sha256'].items():
        assert hashlib.sha256((root/'source_snapshot'/name).read_bytes()).hexdigest() == expected
    results = json.loads((root/'provider_result_complete.json').read_text(), cls=RuntimeDecoder)
    data = results[0].data
    assert results[0].metadata['shots'] == 512
    assert results[0].metadata['num_randomizations'] == 8
    assert results[0].metadata['circuit_metadata']['circuit_family'] == 'fermionic_fswap_network'
    assert np.asarray(data.evs).shape == (27,)
    assert np.asarray(data.evs_noise_factors).shape == (27, 3)
    assert np.all(np.isfinite(np.asarray(data.evs)))
    reference = read(root/'exact_circuit_observables.json')
    regenerated = rows_from_values(np.asarray(data.evs), records, 'zne')
    comparison = read(root/'comparison.json')
    assert differences(regenerated, reference) == comparison['comparison'][0]['vs_exact_circuit']
    errors = {}
    for name in ('stds', 'stds_noise_factors', 'ensemble_stds_noise_factors'):
        if hasattr(data, name):
            values = np.asarray(getattr(data, name), dtype=float)
            assert np.all(np.isfinite(values)) and np.all(values >= 0)
            errors[name] = {'shape': list(values.shape), 'median': float(np.median(values)),
                            'min': float(np.min(values)), 'max': float(np.max(values))}
    metrics = read(root/'provider_metrics.json')
    charged = metrics['usage']['qpu_charge_time_seconds']
    assert charged == comparison['qpu_charge_time_seconds']
    assert 0 <= charged <= job_metadata['cost']
    output = {'passed': True, 'job_id': read(root/'submission_receipt.json')['job_id'],
              'provider_circuit_matches_frozen_QPY': True, 'mapped_observables_verified': 27,
              'provider_shots_per_factor': 512, 'provider_num_randomizations': 8,
              'provider_max_execution_time': job_metadata['cost'], 'qpu_charge_time_seconds': charged,
              'maximum_time_verification': 'Provider job cost field; SDK Runtime.program_run maps max_execution_time in seconds to cost.',
              'physics_checks_passed': len(plan['validation']['checks']),
              'source_snapshots_verified': len(plan['validation']['source_sha256']),
              'comparison_recomputed_from_complete_provider_result': True,
              'reported_uncertainties': errors,
              'hardware_point_estimate_screen_passed': comparison['zne_point_estimate_screen_passed'],
              'interpretation': 'Execution/provenance audit passed; hardware accuracy target failed. These are distinct statements.'}
    save(root/'verification.json', output)
    report = ['# Pilot execution and provenance verification', '',
              'The actual provider circuit equals the frozen QPY, and all 27 physical observables match their planned Pauli mappings.',
              f'The provider confirms 512 shots and eight randomizations. Job-level execution cap: {job_metadata["cost"]} seconds; billed QPU time: {charged} seconds.',
              'The execution cap is independently verified from the provider job metadata. SDK Runtime.program_run maps max_execution_time in seconds to the job-level cost field, outside the primitive input options.',
              'The saved complete result independently reproduces the reported RMSEs. Ten source snapshots match their validation hashes.',
              'All 37 pre-submission physics checks passed. The hardware point-estimate accuracy screen FAILED.',
              '', '## Reported uncertainty diagnostics', '', '```json', json.dumps(errors, indent=2), '```', '',
              'Reported ZNE standard errors are retained, not replaced by 1/sqrt(shots). They can be large and do not cover every systematic extrapolation bias.',
              'The reduction in point-estimate RMSE from factor 1 to ZNE is not claimed statistically significant: both estimates share data and their full cross-observable covariance is unavailable.',
              'The much smaller ideal Trotter errors are separately measured against an independent Hamiltonian; they do not explain the large hardware deviations.',
              'No additional QPU submission was made for this audit.', '']
    (root/'verification.md').write_text('\n'.join(report), encoding='utf-8')
    save(root/'artifact_sha256.json', [{'path': str(p.relative_to(root)),
         'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(root.rglob('*'))
         if p.is_file() and p.name != 'artifact_sha256.json'])
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--outdir', type=Path, required=True)
    audit(parser.parse_args().outdir)
