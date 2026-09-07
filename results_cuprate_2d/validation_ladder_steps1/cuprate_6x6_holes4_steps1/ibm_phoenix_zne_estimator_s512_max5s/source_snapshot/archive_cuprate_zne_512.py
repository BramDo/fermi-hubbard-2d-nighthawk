"""Archive and independently compare an already-submitted ZNE job; never submits."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import sys
from pathlib import Path


def read_csv(path):
    with path.open(newline='', encoding='utf-8-sig') as handle:
        return list(csv.DictReader(handle))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    base = repo / 'results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1'
    out = base / 'ibm_phoenix_zne_estimator_s512_max5s'
    receipt = json.loads((out / 'submission_receipt.json').read_text())
    plan = json.loads((out / 'plan.json').read_text())
    assert receipt['method'] == 'zne' and receipt['shots'] == 512
    assert receipt['max_execution_time'] == 5 and receipt['backend'] == 'ibm_phoenix'
    sys.path.insert(0, str(repo))
    import qiskit.qpy as qpy
    from qiskit_ibm_runtime.json import RuntimeEncoder
    from ibm_staged_fermi_hubbard_runner import build_runtime_service
    from cuprate_2d_pec_zne_runner import instruction_sha256

    def save(name, data):
        (out / name).write_text(json.dumps(data, cls=RuntimeEncoder, indent=2) + '\n', encoding='utf-8')

    service = build_runtime_service(receipt['account_name'])
    job = service.job(receipt['job_id'])
    raw_status = job.status()
    status = str(getattr(raw_status, 'name', raw_status))
    if status != 'DONE':
        print(json.dumps({'job_id': receipt['job_id'], 'status': status, 'archived': False}))
        return
    inputs = job.inputs
    save('provider_inputs.json', inputs)
    metrics = job.metrics()
    save('provider_metrics.json', metrics)
    result = job.result()
    save('provider_result_complete.json', {
        'metadata': getattr(result, 'metadata', {}),
        'pubs': [{'metadata': pub.metadata, 'data': {key: getattr(pub.data, key) for key in pub.data.keys()}}
                 for pub in result],
    })
    pubs = inputs.get('pubs', [])
    circuit = getattr(pubs[0], 'circuit', None) if pubs else None
    if circuit is None and pubs:
        circuit = pubs[0][0]
    circuit_hash = None
    if circuit is not None and hasattr(circuit, 'data'):
        with (out / 'submitted_circuit.qpy').open('wb') as handle:
            qpy.dump(circuit, handle)
        circuit_hash = instruction_sha256(circuit)
        assert circuit_hash == plan['instruction_sha256'], 'Provider circuit differs from saved plan'
    source_dir = out / 'source_snapshot'
    source_dir.mkdir(exist_ok=True)
    for source in [repo / 'cuprate_2d_pec_zne_runner.py', repo / 'cuprate_2d_qiskit_circuit.py',
                   repo / 'cuprate_2d_hubbard_pipeline.py', repo / 'compare_cuprate_2d_observables.py',
                   base / 'cuprate_2d_config.json', Path(__file__).resolve()]:
        shutil.copy2(source, source_dir / source.name)

    reference = {int(r['site']): r for r in read_csv(base / 'mps_shallow_t_only_steps1/cuprate_2d_mps_site_observables_chi32.csv')
                 if int(r['step']) == 1}
    assert len(reference) == 36
    comparison = []
    for shots in (128, 512):
        rows = read_csv(base / f'ibm_phoenix_zne_estimator_s{shots}_max5s/site_observables.csv')
        assert len(rows) == 36 and len({int(r['site']) for r in rows}) == 36
        record = {'shots_per_noise_factor': shots, 'sites': len(rows),
                  'total_charge': sum(float(r['charge']) for r in rows),
                  'total_spin_z': sum(float(r['spin_z']) for r in rows)}
        for observable in ('charge', 'spin_z', 'double_occupancy'):
            record[observable + '_rmse'] = math.sqrt(sum(
                (float(r[observable]) - float(reference[int(r['site'])][observable])) ** 2 for r in rows) / len(rows))
        comparison.append(record)
    previous_plan = json.loads((base / 'ibm_phoenix_zne_estimator_s128_max5s/plan.json').read_text())
    old_options = dict(previous_plan['options'])
    new_options = dict(plan['options'])
    old_options.pop('default_shots')
    new_options.pop('default_shots')
    verification = {
        'job_id': receipt['job_id'], 'status': status,
        'provider_input_keys': list(inputs),
        'provider_options': inputs.get('options'),
        'same_circuit_as_128': plan['instruction_sha256'] == previous_plan['instruction_sha256'],
        'provider_circuit_matches_plan': circuit_hash == plan['instruction_sha256'] if circuit_hash else None,
        'same_options_except_shots': old_options == new_options,
        'same_observable_records': plan['observable_records'] == previous_plan['observable_records'],
        'comparison': comparison,
        'qpu_charge_time_seconds': metrics.get('usage', {}).get('qpu_charge_time_seconds'),
    }
    save('repeat_verification.json', verification)
    files = sorted(p for p in out.rglob('*') if p.is_file() and p.name != 'archive_sha256.json')
    save('archive_sha256.json', [{'path': str(p.relative_to(out)), 'bytes': p.stat().st_size,
                                'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in files])
    print(json.dumps(verification, indent=2))


if __name__ == '__main__':
    main()
