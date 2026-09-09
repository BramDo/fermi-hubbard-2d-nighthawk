"""Post-hoc decomposition only; never change fits or acceptance criteria."""
from pathlib import Path
import argparse, json, sys
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lmpf_2d.model import digest


def run(folder):
    path = folder / 'observable_22.json'
    manifest = json.loads((folder / 'sha256.json').read_text())
    if digest(path) != manifest['observable_22.json']:
        raise ValueError('Changed numerical input')
    record = json.loads(path.read_text())
    low = record['chi_results']['128']
    high = record['chi_results']['256']
    a, b = np.array(low['overlaps_exact']), np.array(high['overlaps_exact'])
    change = b - a
    relative = float(np.linalg.norm(change) / np.linalg.norm(b))
    np.testing.assert_allclose(relative, record['stability']['relative_gram_change'], atol=1e-14)
    reference = record['exact_ideal_reference']
    result = {
        'status': 'POST_HOC_COMPONENT_DIAGNOSTIC',
        'input_sha256': digest(path), 'source_sha256': digest(Path(__file__)),
        'relative_gram_change': relative,
        'ideal_norm_term_fraction_of_squared_gram_change': float(change[0,0]**2 / np.sum(change**2)),
        'noisy_G_relative_change': float(np.linalg.norm(change[1:,1:]) / np.linalg.norm(b[1:,1:])),
        'ideal_noisy_b_relative_change': float(np.linalg.norm(change[0,1:]) / np.linalg.norm(b[0,1:])),
        'ideal_norm_squared_128': float(a[0,0]), 'ideal_norm_squared_256': float(b[0,0]),
        'exact_ideal_norm_squared': 1.,
        'norm_identity': 'For O=Z8 Z9 and unitary U, Tr[(U_dagger O U)^2]/2^18=1.',
        'absolute_ideal_expectation_error_128': abs(low['ideal_tn_expectation'] - reference),
        'absolute_ideal_expectation_error_256': abs(high['ideal_tn_expectation'] - reference),
        'predeclared_stability': record['stability'],
        'fits_modified': False, 'acceptance_criteria_modified': False,
        'hardware_weights_applied': False, 'new_qpu_seconds': 0,
        'scope': 'Explains the failed full-Gram flag; not a replacement acceptance test or a convergence certificate.'}
    with (folder / 'component_diagnostics.json').open('x') as handle:
        json.dump(result, handle, indent=2)
        handle.write('\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    run(parser.parse_args().folder)
