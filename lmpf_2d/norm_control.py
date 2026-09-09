"""Exact F00 only: immutable follow-up to the central-operator diagnostics."""
from pathlib import Path
import argparse, io, json, shutil, sys, time, unittest
import numpy as np
from qiskit import qpy
from qiskit.quantum_info import Operator
from threadpoolctl import threadpool_limits
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lmpf_2d.archive_3x3 import ARCHIVE, active_circuit
from lmpf_2d.model import digest
from lmpf_2d.fit import fit_coefficients

CASES = [('Z_up', 8, 'lmpf_3x3_chi128_2026-09-08_v1', 64, 128),
         ('Z_down', 9, 'lmpf_3x3_chi128_2026-09-08_v1', 64, 128),
         ('ZZ', 22, 'lmpf_3x3_zz_chi256_2026-09-09_v1', 128, 256)]


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path, value):
    with path.open('x') as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write('\n')


def with_exact_pauli_norm(matrix):
    f = np.asarray(matrix)
    fit_coefficients(f, ridge=1/56)  # Reject an invalid original before correction.
    f = np.asarray(f.real, dtype=float)
    if f[0,0] < 0 or f[0,0] > 1 + 1e-10:
        raise ValueError('Incompatible canonical Pauli norm')
    corrected = f.copy()
    corrected[0,0] = 1.
    return corrected


def relative_delta(low, high):
    numerator = float(np.linalg.norm(np.asarray(high)-low))
    denominator = float(np.linalg.norm(high))
    if denominator == 0:
        return 0. if numerator == 0 else float('inf')
    return numerator / denominator


def evaluate_pair(low, high):
    a, b = np.asarray(low), np.asarray(high)
    fixed_a, fixed_b = with_exact_pauli_norm(a), with_exact_pauli_norm(b)
    a, b = a.real.astype(float), b.real.astype(float)
    ca = fit_coefficients(a, ridge=1/56).coefficients
    cb = fit_coefficients(b, ridge=1/56).coefficients
    result = {
        'raw_full_gram_relative_change': relative_delta(a, b),
        'exact_norm_full_gram_relative_change': relative_delta(fixed_a, fixed_b),
        'G_relative_change': relative_delta(a[1:,1:], b[1:,1:]),
        'b_relative_change': relative_delta(a[1:,0], b[1:,0]),
        'ridge_coefficient_l1_change': float(np.linalg.norm(np.array(cb)-ca, ord=1))}
    result['raw_flags_pass'] = bool(result['raw_full_gram_relative_change'] <= .01 and result['ridge_coefficient_l1_change'] <= .05)
    result['followup_flags_pass'] = bool(all(result[key] <= .01 for key in
        ('exact_norm_full_gram_relative_change', 'G_relative_change', 'b_relative_change')) and result['ridge_coefficient_l1_change'] <= .05)
    return result


def symbolic_identity():
    import sympy as sp
    z = sp.diag(1, -1)
    r = sp.Matrix([[sp.Rational(3,5), -sp.Rational(4,5)],
                   [sp.Rational(4,5), sp.Rational(3,5)]])
    v = sp.Matrix([[1, sp.I], [sp.I, 1]]) / sp.sqrt(2)
    u, o = sp.kronecker_product(r, v), sp.kronecker_product(z, z)
    a = sp.simplify(u.H * o * u)
    assert sp.simplify(u.H*u) == sp.eye(4)
    assert o*o == sp.eye(4)
    value = sp.simplify(sp.trace(a.H*a)/4)
    assert value == 1
    return {'dimension': 4, 'exact_normalized_trace': str(value),
            'complex_unitary_verified': True, 'sympy_version': sp.__version__,
            'scope': 'Exact finite example; the dimension-independent trace proof is in PLAN_EXACT_NORM.md.'}


def check_native_gates():
    plan = read(ARCHIVE/'plan.json')
    inputs, cache = [], {}
    count, error = 0, 0.
    for factor in (1,2,3):
        index = next(i for i,r in enumerate(plan['records']) if r.get('factor') == factor and r['twirl_id'] == 0)
        path = ARCHIVE/'provider_inputs'/f'circuit_{index:03d}.qpy'
        if digest(path) != digest(ARCHIVE/'bound_inputs'/path.name):
            raise ValueError('Native provider/bound inputs differ')
        with path.open('rb') as handle:
            qc = active_circuit(qpy.load(handle)[0], plan['layout'])
        for item in qc.data:
            operation = item.operation
            if operation.name == 'barrier':
                continue
            key = (operation.name, tuple(float(x) for x in operation.params))
            if key not in cache:
                matrix = Operator(operation).data
                if matrix.shape[0] > 4:
                    raise ValueError('Only native one/two-qubit gates expected')
                cache[key] = float(np.max(abs(matrix.conj().T@matrix - np.eye(matrix.shape[0]))))
            count += 1
            error = max(error, cache[key])
        inputs.append({'factor': factor, 'record_index': index, 'qpy_sha256': digest(path)})
    if error > 1e-12:
        raise ValueError('Native ideal gate is not numerically unitary')
    return {'inputs': inputs, 'native_gates_checked': count,
            'unique_gate_matrices': len(cache), 'maximum_unitarity_error': error,
            'scope': 'Ideal archived gate matrices only, not physical noisy QPU channels.'}


def run(out):
    if out.exists():
        raise FileExistsError('Preserve prior norm-control output')
    out.mkdir(parents=True)
    (out/'source_snapshot').mkdir()
    (out/'inputs').mkdir()
    started = time.monotonic()
    names = ['norm_control.py', 'verify_norm_control.py', 'fit.py', 'archive_3x3.py',
             'model.py', 'operators.py', 'hardware_inputs.py', 'PLAN_EXACT_NORM.md']
    sources = [ROOT/'lmpf_2d'/name for name in names] + [ROOT/'test_lmpf_norm_control.py']
    for path in sources:
        shutil.copyfile(path, out/'source_snapshot'/path.name)
    test_names = ('test_lmpf_2d', 'test_lmpf_hardware_inputs', 'test_lmpf_product',
                  'test_lmpf_tn_storage', 'test_lmpf_canonical_chain', 'test_lmpf_chain_contract',
                  'test_lmpf_zz_refine', 'test_lmpf_norm_control')
    suite = unittest.TestSuite()
    for name in test_names:
        suite.addTests(unittest.defaultTestLoader.loadTestsFromName(name))
    stream = io.StringIO()
    tests = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    (out/'tests.txt').write_text(stream.getvalue())
    if not tests.wasSuccessful():
        raise RuntimeError('Regression tests failed')
    gate_check = check_native_gates()
    plan = {'schema': 'exact-ideal-pauli-norm-followup-v1', 'cases': CASES,
            'job_id': 'daem7r642tqs73autong', 'backend': 'ibm_phoenix', 'twirl': 0,
            'ridge': 1/56, 'matrix_tolerance': .01, 'coefficient_l1_tolerance': .05,
            'defined_after_prior_diagnosis': True, 'independent_data_validation': False,
            'new_qpu_seconds': 0, 'tn_propagation_performed': False,
            'source_sha256': {str(p.relative_to(ROOT)): digest(p) for p in sources},
            'native_gate_check': gate_check}
    write(out/'plan.json', plan)
    records = []
    for label, obs, parent_name, low, high in CASES:
        parent = ROOT/'results_cuprate_2d'/parent_name
        old_plan = read(parent/'plan.json')
        if old_plan['job_id'] != plan['job_id'] or old_plan['backend'] != plan['backend'] or old_plan['twirl'] != 0:
            raise ValueError('Changed native job or twirl')
        if old_plan['inputs'] != gate_check['inputs']:
            raise ValueError('Native inputs differ from the parent')
        path = parent/f'observable_{obs:02d}.json'
        if digest(path) != read(parent/'sha256.json')[path.name]:
            raise ValueError('Changed archived operator record')
        old = read(path)
        target = out/'inputs'/f'{label}_record.json'
        shutil.copyfile(path, target)
        item = {'operator': label, 'observable': obs, 'comparison_levels': [low,high],
                'source_record': str(path.relative_to(ROOT)), 'source_sha256': digest(path),
                'parent_manifest_sha256': digest(parent/'sha256.json'),
                'raw_archived_stability': old['stability'], 'levels': {}}
        for chi in (low, high):
            original = old['chi_results'][str(chi)]
            f = np.array(original['overlaps_exact'])
            fixed = with_exact_pauli_norm(f)
            fits = {}
            for kind, ridge in (('unregularized',0.), ('ridge',1/56)):
                before = fit_coefficients(f, ridge=ridge).to_dict()
                after = fit_coefficients(fixed, ridge=ridge).to_dict()
                np.testing.assert_allclose(before['coefficients'], original['fits']['exact'][kind]['coefficients'], atol=1e-10, rtol=0)
                if before['coefficients'] != after['coefficients']:
                    raise ValueError('Changing F00 changed the weights')
                np.testing.assert_allclose(after['projection_residual']-before['projection_residual'], 1-f[0,0], atol=1e-12)
                fits[kind] = {'before': before, 'exact_norm': after}
            item['levels'][str(chi)] = {'raw_gram': f.tolist(), 'exact_norm_gram': fixed.tolist(),
                'fits': fits, 'ideal_tn_expectation_unchanged': original['ideal_tn_expectation'],
                'exact_circuit_expectation_reference': old['exact_ideal_reference']}
        item['stability'] = evaluate_pair(item['levels'][str(low)]['raw_gram'], item['levels'][str(high)]['raw_gram'])
        if item['stability']['raw_flags_pass'] != old['stability']['passes_local_flags']:
            raise ValueError('Changed historical raw classification')
        records.append(item)
    result = {'status': 'EXACT_NORM_FOLLOWUP_FINISHED', 'records': records,
              'symbolic_identity': symbolic_identity(), 'tests_passed': tests.testsRun,
              'all_followup_local_flags_pass': all(r['stability']['followup_flags_pass'] for r in records),
              'all_coefficients_unchanged': True, 'new_hardware_estimates': False,
              'full_profile_or_8_twirl_validation': False, 'noise_model_validated': False,
              'six_by_six_started': False, 'new_qpu_seconds': 0, 'seconds': time.monotonic()-started}
    write(out/'results.json', result)
    write(out/'sha256.json', {str(p.relative_to(out)): digest(p) for p in out.rglob('*') if p.is_file()})
    print(json.dumps({k:v for k,v in result.items() if k != 'records'}, indent=2))
    print(json.dumps([{ 'operator': r['operator'], **r['stability']} for r in records], indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output exists; choose a new directory')
    try:
        with threadpool_limits(limits=1):
            run(args.output)
    except Exception as error:
        if args.output.exists():
            write(args.output/'failure.json', {'type': type(error).__name__, 'reason': str(error)})
        raise
