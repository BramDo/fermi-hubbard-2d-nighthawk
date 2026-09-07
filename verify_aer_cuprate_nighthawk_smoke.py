"""Archive offline smoke-test verification without modifying its frozen outputs."""
import argparse
import io
import shutil
import unittest
from pathlib import Path

import aer_cuprate_nighthawk_smoke as smoke


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    out = args.output.resolve()
    if (out / 'verification.json').exists():
        parser.error('Verification already archived; do not overwrite it')
    checks = {}
    for name, expected in smoke.read(out / 'sha256.json').items():
        checks[f'output_sha256:{name}'] = smoke.digest(out / name) == expected
    provenance = smoke.read(out / 'provenance.json')
    for name, expected in provenance['input_sha256'].items():
        checks[f'input_sha256:{name}'] = smoke.digest(smoke.ROOT / name) == expected
    result = smoke.read(out / 'aer_result.json')
    summary = smoke.read(out / 'summary.json')
    samples = smoke.read(out / 'synthetic_memory.json')
    metadata = result['results'][0]['metadata']
    checks['success'] = result['success'] is True
    checks['18_qubit_statevector'] = metadata['num_qubits'] == 18 and metadata['method'] == 'statevector'
    checks['noisy_trajectories_not_ideal_measurement_sampling'] = metadata['measure_sampling'] is False
    memory_from_hex = [format(int(s, 16), '018b') for s in result['results'][0]['data']['memory']]
    checks['raw_memory_matches_aer_result'] = memory_from_hex == samples['memory']
    checks['exact_shot_count'] = len(samples['memory']) == provenance['shots'] == summary['noisy_shots']
    checks['zero_qpu_usage'] = summary['qpu_seconds'] == 0 == provenance['qpu_seconds']
    checks['all_checks_pass'] = all(checks.values())
    if not checks['all_checks_pass']:
        raise AssertionError(checks)
    log = io.StringIO()
    suite = unittest.defaultTestLoader.loadTestsFromName('test_aer_cuprate_nighthawk_smoke')
    tests = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    if not tests.wasSuccessful():
        raise AssertionError(log.getvalue())
    snapshot = out / 'source_snapshot'
    snapshot.mkdir()
    for name in ['aer_cuprate_nighthawk_smoke.py', 'test_aer_cuprate_nighthawk_smoke.py',
                 'verify_aer_cuprate_nighthawk_smoke.py', 'AER_NIGHTHAWK_PROTOCOL.md',
                 'cuprate_2d_tflo.py']:
        shutil.copyfile(smoke.ROOT / name, snapshot / name)
    (out / 'unit_tests.txt').write_text(log.getvalue(), encoding='utf-8')
    smoke.write(out / 'verification.json', {'checks': checks, 'unit_tests': tests.testsRun,
                                           'failures': len(tests.failures), 'errors': len(tests.errors)})
    smoke.write(out / 'verified_archive_sha256.json',
                {str(p.relative_to(out)): smoke.digest(p) for p in out.rglob('*') if p.is_file()})
    print(f'PASS: {sum(checks.values())} integrity/execution checks; {tests.testsRun} unit tests')


if __name__ == '__main__':
    main()
