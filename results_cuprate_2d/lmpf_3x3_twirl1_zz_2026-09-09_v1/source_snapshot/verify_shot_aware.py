"""Independent assignment-range and KKT audit of the shot-aware pilot."""
from pathlib import Path
import argparse, json, sys, time
import numpy as np
from threadpoolctl import threadpool_limits
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from lmpf_2d.model import digest
from lmpf_2d.verify_single_twirl import inverse_means, occupation_values


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def inverse_penalties(errors,masks):
    errors = np.asarray(errors)
    r = len(errors)
    bits = np.array([[i%2,i//2] for i in range(4)])
    assignment = np.ones((r,4,4))
    for true in range(4):
        for measured in range(4):
            for q in range(2):
                prob = errors[:,0,q] if bits[true,q] == 0 else 1-errors[:,1,q]
                assignment[:,true,measured] *= prob if bits[measured,q] else 1-prob
    values = []
    for group,n in zip((0,2,3),(43,7,14)):
        z = 1-2*(bits ^ np.asarray(masks[group],int))
        features = np.column_stack([z,z[:,0]*z[:,1]])
        scores = np.linalg.solve(assignment,np.broadcast_to(features,(r,4,3)))
        values.append((np.max(scores,axis=1)-np.min(scores,axis=1))**2/(4*n))
    return np.stack(values,axis=2)


def direct_weights(grams,penalties):
    grams, penalties = np.asarray(grams), np.asarray(penalties)
    r,o = penalties.shape[:2]
    matrix = np.zeros((r,o,4,4))
    matrix[:,:,:3,:3] = grams[None,:,1:,1:]
    idx = np.arange(3)
    matrix[:,:,idx,idx] += penalties
    matrix[:,:,:3,3] = 1
    matrix[:,:,3,:3] = 1
    rhs = np.ones((r,o,4))
    rhs[:,:,:3] = grams[None,:,1:,0]
    return np.linalg.solve(matrix,rhs[...,None])[...,:3,0]


def independent_paulis(counts,errors,masks,weights):
    weights = np.broadcast_to(weights,(len(counts),3,3))
    result = np.zeros((len(counts),3))
    for arm in range(3):
        select = np.tile(np.eye(3)[arm],(3,1))
        # The previous independent inverse evaluates the selected matched arm.
        moments = inverse_means(counts,errors,masks,select)[:,3]
        result += weights[:,:,arm]*moments
    return result


def verify(folder):
    dest = folder/'verification'
    dest.mkdir(exist_ok=False)
    started = time.monotonic()
    plan, frozen, summary = [read(folder/name) for name in ('plan.json','frozen_rule_and_weights.json','summary.json')]
    if plan['target_shots'] != [43,7,14] or plan['primary_total_shots'] != 192 or plan['twirl'] != 0:
        raise ValueError('Changed budget/twirl')
    if frozen['eta'] != 1 or frozen['old_scalar_ridge_added'] or frozen['target_means_or_reference_used']:
        raise ValueError('Changed penalty or target tuning')
    if not frozen['calibration_dependence_propagated_in_primary_bootstrap']:
        raise ValueError('Calibration dependence omitted')
    for name, expected in read(folder/'sha256.json').items():
        if digest(folder/name) != expected:
            raise ValueError('Changed saved result: '+name)
    for name, expected in plan['source_sha256'].items():
        if digest(ROOT/name) != expected or digest(folder/'source_snapshot'/Path(name).name) != expected:
            raise ValueError('Changed numerical source: '+name)
    for name, expected in plan['input_sha256'].items():
        if digest(ROOT/name) != expected:
            raise ValueError('Changed input: '+name)
        copied = folder/'inputs'/('norm_results.json' if 'exact_norm_' in name else 'parent_'+Path(name).name)
        if digest(copied) != expected:
            raise ValueError('Changed input copy: '+name)
    inputs = read(folder/'inputs/parent_selected_inputs.json')
    parent_plan, parent_summary = read(folder/'inputs/parent_plan.json'), read(folder/'inputs/parent_summary.json')
    norm = read(folder/'inputs/norm_results.json')
    masks = np.array(inputs['stratum_masks'])
    cal_counts = np.array(inputs['calibration_error_counts'])
    errors = (cal_counts+.5)/65
    np.testing.assert_array_equal(errors,frozen['calibration_errors'])
    grams = np.array([r['levels'][str(r['comparison_levels'][1])]['exact_norm_gram'] for r in norm['records']])
    low = np.array([r['levels'][str(r['comparison_levels'][0])]['exact_norm_gram'] for r in norm['records']])
    np.testing.assert_array_equal(grams,frozen['grams'])
    np.testing.assert_array_equal(low,frozen['low_grams'])
    penalties = inverse_penalties(errors[None,:,:],masks)
    np.testing.assert_allclose(penalties[0],frozen['penalties'],atol=1e-12,rtol=0)
    weights = direct_weights(grams,penalties)[0]
    low_weights = direct_weights(low,penalties)[0]
    weight_error = float(np.max(abs(weights-frozen['new_weights'])))
    np.testing.assert_allclose(weights,frozen['new_weights'],atol=1e-10,rtol=0)
    np.testing.assert_allclose(low_weights,frozen['low_chi_new_weights'],atol=1e-10,rtol=0)
    changes = np.sum(abs(weights-low_weights),axis=1)
    np.testing.assert_allclose(changes,frozen['chi_coefficient_l1_changes'],atol=1e-10,rtol=0)
    if np.any(changes>.05):
        raise ValueError('Coefficient stability failed')
    old_weights = np.array(read(folder/'inputs/parent_frozen_weights.json')['weights'])
    np.testing.assert_array_equal(old_weights,frozen['old_weights'])
    objective_error = 0.
    for i in range(3):
        for name,c in (('old_fixed_ridge',old_weights[i]),('shot_aware',weights[i])):
            f = grams[i]
            projection = f[0,0]-2*f[0,1:]@c+c@f[1:,1:]@c
            variance = np.dot(c*c,penalties[0,i])
            expected = [projection,variance,projection+variance,np.sum(abs(c))]
            rec = frozen['objectives'][i][name]
            actual = [rec[k] for k in ('projection_loss','conditional_sampling_variance_bound','surrogate_objective','coefficient_l1')]
            objective_error = max(objective_error,float(np.max(abs(np.array(expected)-actual))))
            np.testing.assert_allclose(expected,actual,atol=1e-10,rtol=0)
        if frozen['objectives'][i]['shot_aware']['surrogate_objective'] > frozen['objectives'][i]['old_fixed_ridge']['surrogate_objective']+1e-10:
            raise ValueError('Surrogate objective did not improve')
    with np.load(folder/'inputs/parent_bootstrap.npz',allow_pickle=False) as original:
        counts,draws = original['sampled_counts'],original['calibration_errors']
        old_boot,old_fixed_cal = original['physical'],original['physical_fixed_calibration']
    observed = np.array(inputs['stratum_counts'])
    rng = np.random.default_rng(parent_plan['bootstrap_seed'])
    n = plan['replicates']
    np.testing.assert_array_equal(draws,rng.beta(cal_counts+.5,64-cal_counts+.5,size=(n,2,2)))
    expected_counts = np.stack([rng.multinomial(size,observed[j]/size,size=n) for j,size in enumerate((43,21,7,14))],axis=1)
    np.testing.assert_array_equal(counts,expected_counts)
    p_draws = inverse_penalties(draws,masks)
    w_draws = direct_weights(grams,p_draws)
    paulis = independent_paulis(counts,draws,masks,w_draws)
    boot = occupation_values(paulis)
    frozen_boot = occupation_values(independent_paulis(counts,draws,masks,weights))
    fixed_boot = occupation_values(independent_paulis(counts,errors[None,:,:],masks,weights))
    with np.load(folder/'shot_aware_bootstrap.npz',allow_pickle=False) as saved:
        errors_to_report = {}
        for key,expected in (('penalties',p_draws),('weights',w_draws),('pauli',paulis),
                             ('physical',boot),('physical_frozen_weights',frozen_boot),
                             ('physical_fixed_calibration',fixed_boot)):
            error = float(np.max(abs(expected-saved[key])))
            errors_to_report['maximum_'+key+'_error'] = error
            np.testing.assert_allclose(expected,saved[key],atol=1e-10,rtol=0)
    point_pauli = independent_paulis(observed[None,:,:],errors[None,:,:],masks,weights)[0]
    point = occupation_values(point_pauli)
    rec = summary['methods']['lmpf_shot_aware']
    target = np.array(parent_summary['reference_physical'])
    np.testing.assert_allclose(point_pauli,rec['paulis'],atol=1e-10,rtol=0)
    np.testing.assert_allclose(point,rec['physical'],atol=1e-10,rtol=0)
    np.testing.assert_allclose(abs(point-target),rec['absolute_errors'],atol=1e-10,rtol=0)
    for key,data in (('bootstrap_sd',boot),('frozen_weight_bootstrap_sd',frozen_boot),('fixed_calibration_bootstrap_sd',fixed_boot)):
        np.testing.assert_allclose(data.std(0,ddof=1),rec[key],atol=1e-10,rtol=0)
    np.testing.assert_allclose(np.quantile(boot,[.025,.975],axis=0),rec['percentile_interval'],atol=1e-10,rtol=0)
    z,d,zz = point_pauli
    pairs = np.array([1+z+d+zz,1-z+d-zz,1+z-d-zz,1-z-d+zz])/4
    np.testing.assert_allclose(pairs,rec['pair_probabilities_00_10_01_11'],atol=1e-10,rtol=0)
    if rec['clipped'] or abs(pairs.min()-rec['minimum_pair_probability'])>1e-10:
        raise ValueError('Probability reporting mismatch')
    for name in ('readout64','zne_matched','lmpf_matched'):
        if summary['methods'][name] != parent_summary['methods'][name]:
            raise ValueError('Historical baseline changed')
        j = parent_plan['methods'].index(name)
        base_point = np.array(parent_summary['methods'][name]['physical'])
        comparison = summary['comparisons'][name]
        np.testing.assert_allclose(abs(base_point-target)-abs(point-target),comparison['absolute_error_improvement'],atol=1e-10,rtol=0)
        interval = np.quantile(abs(old_boot[:,j]-target)-abs(boot-target),[.025,.975],axis=0)
        fixed_interval = np.quantile(abs(old_fixed_cal[:,j]-target)-abs(fixed_boot-target),[.025,.975],axis=0)
        np.testing.assert_allclose(interval,comparison['paired_percentile_interval'],atol=1e-10,rtol=0)
        np.testing.assert_allclose(fixed_interval,comparison['fixed_calibration_paired_interval'],atol=1e-10,rtol=0)
    report = {'status':'SHOT_AWARE_ASSIGNMENT_KKT_AUDIT_PASSED','operators_checked':3,
        'bootstrap_replicates_checked':n,'maximum_point_weight_error':weight_error,
        'maximum_objective_error':objective_error,**errors_to_report,
        'calibration_dependent_weights_verified':True,'paired_intervals_verified':True,
        'historical_baselines_unchanged':True,'new_qpu_seconds':0,
        'hardware_accuracy_validated':False,'seconds':time.monotonic()-started,
        'verifier_source_sha256':digest(Path(__file__))}
    with (dest/'verification.json').open('x') as handle:
        json.dump(report,handle,indent=2)
        handle.write('\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder',type=Path)
    with threadpool_limits(limits=1):
        verify(parser.parse_args().folder)
