"""Independent NumPy contractions of the saved chi64 MPS and archive checks."""
import hashlib
import json
import os
from pathlib import Path
for _key in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS']:
    os.environ[_key] = '1'
import numpy as np

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'results_cuprate_2d/classical_full_6x6_mps_T04_chi64_v1'
BASE = ROOT / 'results_cuprate_2d/classical_full_6x6_mps_T04_v1'
Z = np.array([1., -1.])


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def left_step(environment, array, diagonal=None):
    if diagonal is None:
        return np.einsum('ab,arp,bsp->rs', environment, array, array.conj(), optimize=True)
    return np.einsum('ab,arp,bsp,p->rs', environment, array, array.conj(), diagonal, optimize=True)


def moments(arrays):
    """No Quimb/Qiskit observable or physical conversion function is imported."""
    length = len(arrays)
    left = [np.ones((1, 1), dtype=complex)]
    for array in arrays:
        left.append(left_step(left[-1], array))
    norm = left[-1][0, 0]
    if abs(norm.imag) > 1e-10 or norm.real <= 0:
        raise ArithmeticError('Invalid contracted norm')
    right = [None] * (length + 1)
    right[-1] = np.ones((1, 1), dtype=complex)
    for site in reversed(range(length)):
        a = arrays[site]
        right[site] = np.einsum('arp,bsp,rs->ab', a, a.conj(), right[site + 1], optimize=True)
    singles = []
    doubles = []
    for site, a in enumerate(arrays):
        inserted = left_step(left[site], a, Z)
        singles.append(np.sum(inserted * right[site + 1]) / norm)
        if site % 2 == 0:
            inserted = left_step(inserted, arrays[site + 1], Z)
            doubles.append(np.sum(inserted * right[site + 2]) / norm)
    values = np.asarray(singles + doubles)
    if np.max(np.abs(values.imag)) > 1e-10:
        raise ArithmeticError('Complex Hermitian observable')
    values = values.real
    nsite = length // 2
    up, down, pair = values[:length:2], values[1:length:2], values[length:]
    physical = np.column_stack(((2 - up - down) / 2, (down - up) / 2,
                                (1 - up - down + pair) / 4))
    assert physical.shape == (nsite, 3)
    return float(norm.real), values, physical


def self_test():
    rng = np.random.default_rng(12358)
    arrays = [rng.normal(size=shape) + 1j * rng.normal(size=shape)
              for shape in [(1, 2, 2), (2, 3, 2), (3, 2, 2), (2, 1, 2)]]
    dense = np.einsum('abp,bcq,cdr,des->pqrs', *arrays, optimize=True).reshape(-1)
    probabilities = np.abs(dense)**2 / np.vdot(dense, dense).real
    labels = np.arange(16)
    bits = (labels[:, None] >> np.arange(3, -1, -1)) & 1
    signs = 1 - 2 * bits
    expected = probabilities @ np.column_stack([signs, signs[:, ::2] * signs[:, 1::2]])
    norm, values, physical = moments(arrays)
    np.testing.assert_allclose(norm, np.vdot(dense, dense).real, rtol=1e-13)
    np.testing.assert_allclose(values, expected, atol=1e-13)
    expected_physical = np.column_stack([bits[:, ::2] + bits[:, 1::2],
                                        bits[:, ::2] - bits[:, 1::2],
                                        bits[:, ::2] * bits[:, 1::2]])
    expected_physical = (probabilities @ expected_physical).reshape(3, 2).T
    np.testing.assert_allclose(physical, expected_physical, atol=1e-13)


def load_arrays(folder):
    metadata = read(folder / 'mps_metadata.json')
    labels = metadata['tensor_inds']
    arrays = []
    with np.load(folder / 'mps_arrays.npz', allow_pickle=False) as packed:
        for i, inds in enumerate(labels):
            left = [] if i == 0 else list(set(inds) & set(labels[i - 1]))
            right = [] if i + 1 == len(labels) else list(set(inds) & set(labels[i + 1]))
            if len(left) != int(i > 0) or len(right) != int(i + 1 < len(labels)):
                raise ValueError('Expected one open-chain bond between adjacent tensors')
            order = left + right + [f'k{i}']
            if sorted(order) != sorted(inds):
                raise ValueError('Unexpected tensor labels')
            a = packed[f'site_{i}'].transpose([inds.index(label) for label in order])
            dims = dict(zip(order, a.shape))
            a = a.reshape(dims[left[0]] if left else 1,
                          dims[right[0]] if right else 1, 2)
            arrays.append(a)
    return arrays


def run():
    self_test()
    manifest = read(OUT / 'sha256.json')
    for name, expected in manifest.items():
        if digest(OUT / name) != expected:
            raise ValueError('Continuation archive changed: ' + name)
    for name, expected in read(OUT / 'plan.json')['input_sha256'].items():
        if digest(ROOT / name) != expected:
            raise ValueError('Continuation input changed: ' + name)
    for name, expected in read(BASE / 'sha256.json').items():
        if digest(BASE / name) != expected:
            raise ValueError('Original archive changed: ' + name)
    folder = OUT / '6x6_chi64_threads1'
    result = read(folder / 'result.json')
    norm, values, physical = moments(load_arrays(folder))
    np.testing.assert_allclose(norm, 1., atol=1e-11)
    np.testing.assert_allclose(values, result['moments'], atol=1e-11, rtol=0.)
    np.testing.assert_allclose(physical, result['physical_means'], atol=1e-11, rtol=0.)
    summary = read(OUT / 'summary.json')
    for threads in [1, 3]:
        previous = read(BASE / f'6x6_chi32_threads{threads}/result.json')
        delta = physical - np.asarray(previous['physical_means'])
        actual = summary['comparisons'][f'chi64_minus_chi32_threads{threads}']
        np.testing.assert_allclose(np.sqrt(np.mean(delta**2, axis=0)),
                                   actual['rms_charge_spin_doublon'], atol=1e-11, rtol=0.)
        np.testing.assert_allclose(np.max(np.abs(delta), axis=0),
                                   actual['max_abs_charge_spin_doublon'], atol=1e-11, rtol=0.)
    report = {'status': 'PASS', 'verifier_source_sha256': digest(Path(__file__)),
              'continuation_archive_files_checked': len(manifest),
              'original_archive_and_input_hashes_checked': True,
              'independent_random_four_qubit_dense_self_test': 'PASS',
              'independent_72_mode_numpy_mps_contraction': 'PASS',
              'contracted_state_norm': norm,
              'maximum_moment_difference': float(np.max(np.abs(values - result['moments']))),
              'maximum_physical_difference': float(np.max(np.abs(physical - result['physical_means']))),
              'both_chi32_comparison_calculations': 'PASS',
              'certified_higher_chi_convergence': False}
    with (OUT / 'INDEPENDENT_VERIFICATION.json').open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    with (OUT / 'verification_sha256.json').open('x', encoding='utf-8') as stream:
        json.dump({'INDEPENDENT_VERIFICATION.json': digest(OUT / 'INDEPENDENT_VERIFICATION.json'),
                   'sha256.json': digest(OUT / 'sha256.json'),
                   '../../verify_classical_chi64_continuation.py': digest(Path(__file__))}, stream, indent=2)
        stream.write('\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    run()
