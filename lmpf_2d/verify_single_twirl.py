"""Audit central hardware estimates with an independent assignment inverse."""
from pathlib import Path
import argparse, json, sys, time
import numpy as np
from threadpoolctl import threadpool_limits
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lmpf_2d.model import digest


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def inverse_means(counts, errors, masks, weights):
    n = len(counts)
    errors = np.broadcast_to(errors, (n,2,2))
    bits = np.array([[i%2, i//2] for i in range(4)])
    assignment = np.ones((n,4,4))
    for true in range(4):
        for measured in range(4):
            for q in range(2):
                probability_one = errors[:,0,q] if bits[true,q] == 0 else 1-errors[:,1,q]
                assignment[:,true,measured] *= probability_one if bits[measured,q] else 1-probability_one
    probabilities = counts / np.array([43,21,7,14])[None,:,None]
    corrected = np.linalg.solve(assignment.transpose(0,2,1), probabilities.transpose(0,2,1))
    groups, features = [], []
    for group in range(4):
        z = 1-2*(bits ^ np.asarray(masks[group], dtype=int))
        feature = np.column_stack([z,z[:,0]*z[:,1]])
        features.append(feature)
        groups.append(corrected[:,:,group]@feature)
    base = (43*groups[0]+21*groups[1])/64
    raw = ((counts[:,0]+counts[:,1])/64)@features[0]
    zne = (4*groups[0]+groups[2]-2*groups[3])/3
    lmpf, full = np.zeros_like(base), np.zeros_like(base)
    for observable in range(3):
        for arm, group in enumerate((0,2,3)):
            lmpf[:,observable] += weights[observable,arm]*groups[group][:,observable]
            full[:,observable] += weights[observable,arm]*(base[:,observable] if arm == 0 else groups[group][:,observable])
    return np.stack([raw,base,zne,lmpf,full], axis=1)


def occupation_values(paulis):
    z, d, zz = np.moveaxis(np.asarray(paulis), -1, 0)
    p10, p01, p11 = (1-z+d-zz)/4, (1+z-d-zz)/4, (1-z-d+zz)/4
    return np.stack([p10+p01+2*p11,p10-p01,p11], axis=-1)


def central_bits(record):
    return np.array([[(int(s,2)>>8)&1,(int(s,2)>>9)&1] for s in record['bitstrings']])


def verify(folder):
    dest = folder/'verification'
    dest.mkdir(exist_ok=False)
    started = time.monotonic()
    plan, summary = read(folder/'plan.json'), read(folder/'summary.json')
    inputs, frozen = read(folder/'selected_inputs.json'), read(folder/'frozen_weights.json')
    if plan['twirl'] != 0 or plan['observables'] != [8,9,22] or frozen['reference_used_to_fit_or_select']:
        raise ValueError('Changed scope or coefficient selection')
    for name, expected in read(folder/'sha256.json').items():
        if digest(folder/name) != expected:
            raise ValueError('Changed result file: '+name)
    for name, expected in plan['source_sha256'].items():
        if digest(ROOT/name) != expected or digest(folder/'source_snapshot'/Path(name).name) != expected:
            raise ValueError('Changed source: '+name)
    for name, expected in plan['input_sha256'].items():
        if digest(ROOT/name) != expected:
            raise ValueError('Changed hardware source: '+name)
    archive = ROOT/'results_cuprate_2d/hardware_readout_cz_folding_3x3_2026-09-06'
    raw, hardware_plan = read(archive/'raw_bitstrings.json'), read(archive/'plan.json')
    if raw['job_id'] != plan['job_id'] or hardware_plan['backend'] != plan['backend']:
        raise ValueError('Wrong job/backend')
    for record in inputs['target_records']+inputs['calibration_records']:
        original = next(r for r in raw['records'] if (r['setting_id'],r['twirl_id']) == (record['setting_id'],record['twirl_id']))
        if record != original:
            raise ValueError('Selected record differs from original')
    norm_path = (ROOT/frozen['source']/'results.json').resolve()
    if not norm_path.is_relative_to(ROOT) or digest(norm_path) != frozen['source_sha256']:
        raise ValueError('Changed frozen-weight source')
    norm = read(norm_path)
    weights = np.array(frozen['weights'])
    expected_weights = [r['levels'][str(r['comparison_levels'][1])]['fits']['ridge']['exact_norm']['coefficients'] for r in norm['records']]
    np.testing.assert_array_equal(weights, expected_weights)
    order = np.random.default_rng(plan['subset_seed']).permutation(64)
    np.testing.assert_array_equal(order[:43], frozen['shared_factor1_indices'])
    np.testing.assert_array_equal(order[43:], frozen['extra_factor1_indices'])
    target_bits = [central_bits(r) for r in inputs['target_records']]
    groups = [target_bits[0][order[:43]],target_bits[0][order[43:]],target_bits[1],target_bits[2]]
    patterns = np.array([[i%2,i//2] for i in range(4)])
    counts = np.array([[np.all(g == pattern,axis=1).sum() for pattern in patterns] for g in groups])
    np.testing.assert_array_equal(counts, inputs['stratum_counts'])
    masks = np.array([[r['readout_mask_little_endian'][8],r['readout_mask_little_endian'][9]] for r in inputs['target_records']])
    masks = masks[[0,0,1,2]]
    np.testing.assert_array_equal(masks, inputs['stratum_masks'])
    cal0, cal1 = [central_bits(r) for r in inputs['calibration_records']]
    cal_counts = np.array([cal0.sum(0),(1-cal1).sum(0)])
    np.testing.assert_array_equal(cal_counts, inputs['calibration_error_counts'])
    errors = (cal_counts+.5)/65
    np.testing.assert_array_equal(errors, inputs['calibration_errors_posterior_mean'])
    if [len(g) for g in groups] != [43,21,7,14] or len(cal0)+len(cal1) != 128:
        raise ValueError('Wrong shot accounting')
    if plan['primary_total_shots'] != 192 or plan['all85_total_shots'] != 213 or plan['selected_union_shots'] != 213:
        raise ValueError('Wrong budget claim')
    n = plan['replicates']
    rng = np.random.default_rng(plan['bootstrap_seed'])
    expected_errors = rng.beta(cal_counts+.5,64-cal_counts+.5,size=(n,2,2))
    expected_counts = np.stack([rng.multinomial(size, counts[j]/size, size=n) for j,size in enumerate((43,21,7,14))],axis=1)
    with np.load(folder/'bootstrap.npz',allow_pickle=False) as saved:
        np.testing.assert_array_equal(saved['calibration_errors'], expected_errors)
        np.testing.assert_array_equal(saved['sampled_counts'], expected_counts)
        pauli = inverse_means(expected_counts,expected_errors,masks,weights)
        boot = occupation_values(pauli)
        fixed = occupation_values(inverse_means(expected_counts,errors[None,:,:],masks,weights))
        max_boot = float(np.max(abs(pauli-saved['pauli'])))
        max_physical = float(np.max(abs(boot-saved['physical'])))
        max_fixed = float(np.max(abs(fixed-saved['physical_fixed_calibration'])))
        np.testing.assert_allclose(pauli,saved['pauli'],atol=1e-10,rtol=0)
        np.testing.assert_allclose(boot,saved['physical'],atol=1e-10,rtol=0)
        np.testing.assert_allclose(fixed,saved['physical_fixed_calibration'],atol=1e-10,rtol=0)
    point_pauli = inverse_means(counts[None,:,:],errors[None,:,:],masks,weights)[0]
    point = occupation_values(point_pauli)
    reference = np.array(hardware_plan['target']['reference'])[[8,9,22]]
    target = occupation_values(reference)
    np.testing.assert_allclose(target,summary['reference_physical'],atol=1e-12)
    max_point, max_interval = 0., 0.
    for j,name in enumerate(plan['methods']):
        rec = summary['methods'][name]
        max_point = max(max_point,float(np.max(abs(point[j]-rec['physical']))))
        np.testing.assert_allclose(point_pauli[j],rec['paulis'],atol=1e-10)
        np.testing.assert_allclose(point[j],rec['physical'],atol=1e-10)
        np.testing.assert_allclose(abs(point[j]-target),rec['absolute_errors'],atol=1e-10)
        np.testing.assert_allclose(boot[:,j].std(0,ddof=1),rec['bootstrap_sd'],atol=1e-10)
        np.testing.assert_allclose(fixed[:,j].std(0,ddof=1),rec['fixed_calibration_bootstrap_sd'],atol=1e-10)
        interval = np.quantile(boot[:,j],[.025,.975],axis=0)
        max_interval = max(max_interval,float(np.max(abs(interval-rec['percentile_interval']))))
        np.testing.assert_allclose(interval,rec['percentile_interval'],atol=1e-10)
        z,d,zz = point_pauli[j]
        pairs = np.array([1+z+d+zz,1-z+d-zz,1+z-d-zz,1-z-d+zz])/4
        np.testing.assert_allclose(pairs,rec['pair_probabilities_00_10_01_11'],atol=1e-10)
        if rec['clipped'] or abs(pairs.min()-rec['minimum_pair_probability']) > 1e-10:
            raise ValueError('Probability clipping or reporting mismatch')
    for base in ('readout64','zne_matched'):
        i = plan['methods'].index(base)
        rec = summary['comparisons'][base]
        np.testing.assert_allclose(abs(point[i]-target)-abs(point[3]-target),rec['absolute_error_improvement'],atol=1e-10)
        interval = np.quantile(abs(boot[:,i]-target)-abs(boot[:,3]-target),[.025,.975],axis=0)
        fixed_interval = np.quantile(abs(fixed[:,i]-target)-abs(fixed[:,3]-target),[.025,.975],axis=0)
        np.testing.assert_allclose(interval,rec['paired_percentile_interval'],atol=1e-10)
        np.testing.assert_allclose(fixed_interval,rec['fixed_calibration_paired_interval'],atol=1e-10)
    report = {'status':'SINGLE_TWIRL_ASSIGNMENT_INVERSE_AUDIT_PASSED',
        'methods_checked':len(plan['methods']),'bootstrap_replicates_checked':n,
        'maximum_point_physical_error':max_point,'maximum_bootstrap_pauli_error':max_boot,
        'maximum_bootstrap_physical_error':max_physical,'maximum_fixed_calibration_error':max_fixed,
        'maximum_percentile_interval_error':max_interval,'matched_budget_verified':True,
        'coefficient_and_subset_provenance_verified':True,'paired_intervals_verified':True,
        'new_qpu_seconds':0,'hardware_accuracy_validated':False,
        'seconds':time.monotonic()-started,'verifier_source_sha256':digest(Path(__file__))}
    with (dest/'verification.json').open('x') as handle:
        json.dump(report,handle,indent=2)
        handle.write('\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder',type=Path)
    with threadpool_limits(limits=1):
        verify(parser.parse_args().folder)
