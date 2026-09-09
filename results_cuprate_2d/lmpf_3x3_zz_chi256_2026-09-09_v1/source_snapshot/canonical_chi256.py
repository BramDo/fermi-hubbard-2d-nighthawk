"""Refine only the fixed central ZZ operator at chi256; reuse chi128."""
from pathlib import Path
import argparse, copy, io, json, resource, shutil, sys, time, unittest
import numpy as np
from qiskit import qpy
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lmpf_2d.archive_3x3 import ARCHIVE, active_circuit, record_sign
from lmpf_2d.canonical_refine import read, write
from lmpf_2d.canonical_chain import evolve_canonical
from lmpf_2d.chain_contract import chain_overlap, chain_expectation_zero
from lmpf_2d.model import FrozenSurrogate, digest
from lmpf_2d.operators import compile_steps, fuse_steps
from lmpf_2d.tn_storage import save_tn, load_tn, bounded_contract
from lmpf_2d.fit import fit_coefficients
from lmpf_2d.higher_bond import stability_flags

PARENT = ROOT / 'results_cuprate_2d/lmpf_3x3_chi128_2026-09-08_v1'


def resource_estimate(n=18, chi=256):
    """Analytical upper bounds for physical-dimension-four open-chain tensors."""
    if n < 2 or chi < 1:
        raise ValueError('Invalid chain dimensions')
    bonds = [min(chi, 4**min(i, n-i)) for i in range(n+1)]
    pairs = list(zip(bonds[:-1], bonds[1:]))
    return {
        'n': n, 'chi': chi, 'bond_upper_bounds': bonds,
        'real_float64_state_bytes': sum(4*l*r*8 for l, r in pairs),
        'complex128_state_bytes': sum(4*l*r*16 for l, r in pairs),
        'chain_flops_upper_bound': sum(8*l*r*(l+r) for l, r in pairs),
        'chain_peak_elements': max(4*l*r for l, r in pairs),
        'largest_two_site_matrix_elements': (4*chi)**2,
        'scope': 'Storage and chain-overlap bounds, not an SVD runtime guarantee.'}


def overlap(left, right):
    return chain_overlap(left, right, max_elements=2**22, max_flops=3e9)


def run(out):
    if out.exists():
        raise FileExistsError('Preserve previous chi256 run')
    out.mkdir(parents=True)
    (out / 'states').mkdir()
    (out / 'source_snapshot').mkdir()
    start = time.monotonic()
    preflight = resource_estimate()
    available = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:'))) * 1024
    preflight.update(available_memory_bytes=available, disk_free_bytes=shutil.disk_usage(out).free)
    if available < 1536 * 1024**2 or preflight['disk_free_bytes'] < 1024**3:
        raise MemoryError('Insufficient free memory or disk space for the bounded run')
    if preflight['chain_flops_upper_bound'] > 3e9 or preflight['chain_peak_elements'] > 2**22:
        raise ValueError('Preflight contraction resource guard')
    sources = [ROOT / 'lmpf_2d' / name for name in (
        'canonical_chi256.py', 'canonical_chain.py', 'chain_contract.py',
        'canonical_refine.py', 'higher_bond.py', 'operators.py', 'tn_storage.py',
        'fit.py', 'model.py', 'archive_3x3.py', 'product.py',
        'verify_zz_chi256.py', 'portable_archive.py', 'PLAN_CHI256.md')]
    tests_names = ('test_lmpf_2d', 'test_lmpf_hardware_inputs', 'test_lmpf_product',
                   'test_lmpf_tn_storage', 'test_lmpf_canonical_chain',
                   'test_lmpf_chain_contract', 'test_lmpf_zz_refine')
    sources += [ROOT / f'{name}.py' for name in tests_names]
    sources.append(ROOT / 'scripts/restore_archives.py')
    for path in sources:
        shutil.copyfile(path, out / 'source_snapshot' / path.name)
    suite = unittest.TestSuite()
    stream = io.StringIO()
    for name in tests_names:
        suite.addTests(unittest.defaultTestLoader.loadTestsFromName(name))
    tests = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    (out / 'tests.txt').write_text(stream.getvalue())
    if not tests.wasSuccessful():
        raise RuntimeError('Prerequisite tests failed')
    print('TESTS_PASSED', tests.testsRun, flush=True)
    parent = read(PARENT / 'plan.json')
    original = read(ARCHIVE / 'plan.json')
    layout = original['layout']
    profile = FrozenSurrogate(ARCHIVE / 'live_backend_properties.json', layout)
    if profile.metadata()['calibration_sha256'] != parent['noise']['calibration_sha256']:
        raise ValueError('Changed surrogate calibration')
    for path, expected in read(PARENT / 'sha256.json').items():
        if digest(PARENT / path) != expected:
            raise ValueError('Changed parent checkpoint ' + path)
    native = {}
    inputs = []
    for factor in (1, 2, 3):
        index = next(i for i, r in enumerate(original['records'])
                     if r.get('factor') == factor and r['twirl_id'] == 0)
        path = ARCHIVE / 'provider_inputs' / f'circuit_{index:03d}.qpy'
        old = next(r for r in parent['inputs'] if r['factor'] == factor)
        if digest(path) != old['qpy_sha256'] or digest(path) != digest(ARCHIVE / 'bound_inputs' / path.name):
            raise ValueError('Changed native input')
        with path.open('rb') as handle:
            qc = active_circuit(qpy.load(handle)[0], layout)
        steps = fuse_steps(compile_steps(qc, profile.rate))
        if {s.qubits for s in steps if len(s.qubits) == 2} != {(q, q + 1) for q in range(17)}:
            raise ValueError('Not the verified open chain')
        native[factor] = (steps, record_sign(original['records'][index]['readout_mask_little_endian']))
        inputs.append({'factor': factor, 'record_index': index, 'qpy_sha256': digest(path)})
    plan = {
        'schema': 'native-chain-chi256-v1', 'observables': [22],
        'chi': [128, 256], 'comparison_levels': [128, 256],
        'backend': profile.backend, 'job_id': parent['job_id'], 'twirl': 0,
        'inputs': inputs, 'noise': profile.metadata(),
        'native_graph': {'vertices': 18, 'edges': 17, 'cycles': 0},
        'parent': str(PARENT.relative_to(ROOT)),
        'parent_manifest_sha256': digest(PARENT / 'sha256.json'),
        'ridge': 1 / 56, 'budget_seconds': 1500, 'budget_checked_between_states': True,
        'relative_gram_change_tolerance': .01, 'coefficient_l1_change_tolerance': .05,
        'overlap_contraction': 'raw_tn_for_independent_audit',
        'primary_overlap_method': 'explicit_left_to_right_chain_environment',
        'max_contraction_elements': 2**22, 'max_contraction_flops': 3e9, 'resource_preflight': preflight,
        'max_process_peak_rss_bytes': 2**31,
        'hardware_weights_applied': False, 'new_qpu_seconds': 0,
        'source_sha256': {str(p.relative_to(ROOT)): digest(p) for p in sources}}
    write(out / 'plan.json', plan)
    summaries = []
    for obs in plan['observables']:
        previous = read(PARENT / f'observable_{obs:02d}.json')
        reused = copy.deepcopy(previous['chi_results']['128'])
        reused['reused_from_parent'] = True
        reused['source_seconds'] = reused['seconds']
        reused['seconds'] = 0.
        record = {'observable_index': obs,
                  'exact_ideal_reference': previous['exact_ideal_reference'],
                  'chi_results': {'128': reused},
                  'previous_step_stability': previous['stability']}
        for arm in range(4):
            for suffix in ('.json', '.npz'):
                file = f'obs{obs:02d}_chi128_arm{arm}{suffix}'
                shutil.copyfile(PARENT / 'states' / file, out / 'states' / file)
                if digest(PARENT / 'states' / file) != digest(out / 'states' / file):
                    raise ValueError('Changed baseline copy')
        write(out / f'observable_{obs:02d}.json', record)
        support = {obs: 'Z'} if obs < 18 else {2 * (obs - 18): 'Z', 2 * (obs - 18) + 1: 'Z'}
        begin = time.monotonic()
        states = []
        for arm in range(4):
            if time.monotonic() > start + plan['budget_seconds']:
                raise TimeoutError('Chi256 time budget reached')
            if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 > plan['max_process_peak_rss_bytes']:
                raise MemoryError('Recorded process peak RSS exceeds the predeclared limit')
            steps, sign = native[max(arm, 1)]
            state_start = time.monotonic()
            tn = evolve_canonical(18, support, steps, 0. if arm == 0 else 1., 256)
            tensor = tn['I0']
            tensor.modify(data=sign[obs] * tensor.data)
            prefix = out / 'states' / f'obs{obs:02d}_chi256_arm{arm}'
            save_tn(prefix, tn)
            restored = load_tn(prefix)
            if abs(overlap(tn, tn)[0] - overlap(restored, restored)[0]) > 1e-10:
                raise ValueError('Checkpoint norm mismatch')
            states.append(restored)
            print('STATE_DONE', obs, 256, arm, round(time.monotonic() - state_start, 3), flush=True)
        gram = np.zeros((4, 4))
        costs = []
        for i in range(4):
            for j in range(i, 4):
                value, info = overlap(states[i], states[j])
                gram[i, j] = gram[j, i] = value
                costs.append(info)
        independent, independent_cost = bounded_contract(states[0].H & states[1], max_flops=3e9)
        if abs(independent - gram[0, 1]) > 1e-9:
            raise ValueError('Independent raw-TN overlap mismatch')
        record['chi_results']['256'] = {
            'failure': None, 'overlaps_exact': gram,
            'fits': {'exact': {'unregularized': fit_coefficients(gram).to_dict(),
                               'ridge': fit_coefficients(gram, ridge=1 / 56).to_dict()}},
            'ideal_tn_expectation': chain_expectation_zero(states[0]),
            'contraction_costs': costs, 'independent_overlap_error': abs(independent - gram[0, 1]),
            'independent_overlap_cost': independent_cost, 'seconds': time.monotonic() - begin,
            'method': 'canonical MPS with exact open-chain contraction'}
        record['stability'] = stability_flags(reused, record['chi_results']['256'])
        write(out / f'observable_{obs:02d}.json', record)
        summaries.append({'observable': obs, **record['stability']})
        print('OBS_DONE', obs, json.dumps(record['stability']), flush=True)
    summary = {
        'status': 'CANONICAL_CHI256_FINISHED', 'observables': summaries,
        'local_stability_flags_pass': all(x['passes_local_flags'] for x in summaries),
        'full_27_observable_8_twirl_validation': False, 'noise_model_validated': False,
        'six_by_six_started': False, 'hardware_weights_applied': False,
        'new_qpu_seconds': 0, 'tests_passed': tests.testsRun,
        'seconds': time.monotonic() - start,
        'process_peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
    write(out / 'summary.json', summary)
    write(out / 'sha256.json', {str(p.relative_to(out)): digest(p) for p in out.rglob('*') if p.is_file()})
    print('DONE', json.dumps(summary), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output already exists; preserve prior evidence and choose a new directory')
    try:
        with threadpool_limits(limits=1):
            run(args.output)
    except Exception as error:
        if args.output.exists():
            write(args.output / 'failure.json', {'error_type': type(error).__name__,
                  'reason': str(error), 'six_by_six_started': False})
        raise
