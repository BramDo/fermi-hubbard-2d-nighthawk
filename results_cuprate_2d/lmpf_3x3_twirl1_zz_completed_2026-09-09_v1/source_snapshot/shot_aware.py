"""One target-blind, shot-aware variance penalty on the existing central pilot."""
from pathlib import Path
import argparse, io, json, shutil, sys, time, unittest
import numpy as np
from scipy.linalg import null_space
from threadpoolctl import threadpool_limits
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from lmpf_2d.model import digest
from lmpf_2d.fit import fit_coefficients
from lmpf_2d.single_twirl import moment_table, physical, pair_probabilities

PARENT = ROOT/'results_cuprate_2d/lmpf_3x3_central_hardware_2026-09-09_v1'
NORM = ROOT/'results_cuprate_2d/lmpf_3x3_exact_norm_2026-09-09_v1'
SHOTS = np.array([43,7,14])


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path,value):
    with path.open('x') as handle:
        json.dump(value,handle,indent=2,allow_nan=False)
        handle.write('\n')


def variance_penalties(errors,masks,shots=SHOTS):
    shots = np.asarray(shots)
    if shots.shape != (3,) or not np.isfinite(shots).all() or np.any(shots<=0) or not np.all(shots==np.floor(shots)):
        raise ValueError('Three positive shot counts required')
    bounds = []
    for group in (0,2,3):
        table = moment_table(np.asarray(errors),masks[group])
        bounds.append(np.ptp(table,axis=1)**2/4)
    # replicate, observable, arm; all possible outcomes, not target frequencies.
    return np.stack(bounds,axis=2)/shots[None,None,:]


def solve_weights(grams,penalties):
    grams, penalties = np.asarray(grams), np.asarray(penalties)
    if grams.ndim != 3 or grams.shape[1:] != (4,4):
        raise ValueError('Expected operator x four-arm Gram matrices')
    if penalties.ndim != 3 or penalties.shape[0] == 0 or penalties.shape[1:] != (len(grams),3):
        raise ValueError('Expected replicate x operator x arm penalties')
    if np.iscomplexobj(penalties) and np.any(penalties.imag != 0):
        raise ValueError('Penalties must be real')
    penalties = penalties.real.astype(float)
    if not np.isfinite(penalties).all() or np.any(penalties<=0):
        raise ValueError('Finite positive penalties required')
    for gram in grams:
        fit_coefficients(gram)  # Validate the unpenalized original first.
    grams = grams.real.astype(float)
    a = np.broadcast_to(grams[None,:,1:,1:],(*penalties.shape[:2],3,3)).copy()
    index = np.arange(3)
    a[...,index,index] += penalties
    z, c0 = null_space(np.ones((1,3))), np.ones(3)/3
    reduced = z.T @ a @ z
    rhs = (grams[None,:,1:,0]-a@c0)@z
    x = np.linalg.solve(reduced,rhs[...,None])[...,0]
    result = c0 + x@z.T
    if not np.isfinite(result).all() or np.max(abs(result.sum(-1)-1))>1e-9:
        raise ValueError('Invalid fitted weights')
    return result


def objective_parts(gram,penalty,weights):
    c, f = np.asarray(weights), np.asarray(gram)
    projection = float(f[0,0]-2*f[1:,0]@c+c@f[1:,1:]@c)
    variance = float(np.sum(penalty*c*c))
    return {'projection_loss':projection,'conditional_sampling_variance_bound':variance,
            'surrogate_objective':projection+variance,'coefficient_l1':float(abs(c).sum())}


def apply_weights(counts,errors,masks,weights):
    counts = np.asarray(counts)
    if counts.ndim != 3 or counts.shape[1:] != (4,4):
        raise ValueError('Unexpected bootstrap count shape')
    if not np.all(counts.sum(2)==[43,21,7,14]):
        raise ValueError('Changed matched shot budget')
    errors = np.broadcast_to(errors,(len(counts),2,2))
    weights = np.broadcast_to(weights,(len(counts),3,3))
    arms = []
    for group,shots in zip((0,2,3),SHOTS):
        arms.append(np.einsum('rp,rpo->ro',counts[:,group]/shots,moment_table(errors,masks[group])))
    return np.einsum('roa,rao->ro',weights,np.stack(arms,axis=1))


def run(out):
    if out.exists():
        raise FileExistsError('Preserve previous shot-aware run')
    out.mkdir(parents=True)
    (out/'inputs').mkdir()
    (out/'source_snapshot').mkdir()
    started = time.monotonic()
    names = ['shot_aware.py','verify_shot_aware.py','single_twirl.py','verify_single_twirl.py',
             'fit.py','model.py','hardware_inputs.py','PLAN_SHOT_AWARE.md']
    sources = [ROOT/'lmpf_2d'/name for name in names]+[ROOT/'test_lmpf_shot_aware.py']
    for path in sources:
        shutil.copyfile(path,out/'source_snapshot'/path.name)
    stream, suite = io.StringIO(), unittest.TestSuite()
    for name in ('test_lmpf_2d','test_lmpf_hardware_inputs','test_lmpf_product',
                 'test_lmpf_tn_storage','test_lmpf_canonical_chain','test_lmpf_chain_contract',
                 'test_lmpf_zz_refine','test_lmpf_norm_control','test_lmpf_single_twirl',
                 'test_lmpf_shot_aware'):
        suite.addTests(unittest.defaultTestLoader.loadTestsFromName(name))
    tests = unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    (out/'tests.txt').write_text(stream.getvalue())
    if not tests.wasSuccessful():
        raise RuntimeError('Tests failed')
    input_paths = []
    for name in ('plan.json','summary.json','selected_inputs.json','frozen_weights.json','bootstrap.npz'):
        source = PARENT/name
        if digest(source)!=read(PARENT/'sha256.json')[name]:
            raise ValueError('Changed prior pilot input')
        shutil.copyfile(source,out/'inputs'/('parent_'+name))
        input_paths.append(source)
    if digest(NORM/'results.json')!=read(NORM/'sha256.json')['results.json']:
        raise ValueError('Changed overlap source')
    shutil.copyfile(NORM/'results.json',out/'inputs/norm_results.json')
    input_paths.append(NORM/'results.json')
    old_plan, inputs = read(PARENT/'plan.json'), read(PARENT/'selected_inputs.json')
    old_frozen, norm = read(PARENT/'frozen_weights.json'), read(NORM/'results.json')
    if old_frozen['source_sha256'] != digest(NORM/'results.json'):
        raise ValueError('Previous weights use a different overlap source')
    if old_plan['twirl']!=0 or old_plan['primary_target_shots']['lmpf_matched']!=[43,7,14]:
        raise ValueError('Changed twirl/budget')
    if [r['observable'] for r in norm['records']] != [8,9,22] or not norm['all_followup_local_flags_pass']:
        raise ValueError('Overlap prerequisite missing')
    masks = np.array(inputs['stratum_masks'])
    errors = np.array(inputs['calibration_errors_posterior_mean'])
    grams, low_grams = [], []
    for rec in norm['records']:
        low,high = map(str,rec['comparison_levels'])
        grams.append(rec['levels'][high]['exact_norm_gram'])
        low_grams.append(rec['levels'][low]['exact_norm_gram'])
    grams, low_grams = np.array(grams), np.array(low_grams)
    penalties = variance_penalties(errors[None,:,:],masks)
    weights = solve_weights(grams,penalties)[0]
    low_weights = solve_weights(low_grams,penalties)[0]
    changes = abs(weights-low_weights).sum(1)
    old_weights = np.array(old_frozen['weights'])
    objectives = []
    for i in range(3):
        old = objective_parts(grams[i],penalties[0,i],old_weights[i])
        new = objective_parts(grams[i],penalties[0,i],weights[i])
        if new['surrogate_objective'] > old['surrogate_objective']+1e-10:
            raise ValueError('New optimizer failed its own objective')
        objectives.append({'old_fixed_ridge':old,'shot_aware':new})
    frozen = {'penalty_rule':'(max_outcome_score-min_outcome_score)^2/(4*N)',
        'eta':1.,'old_scalar_ridge_added':False,'target_means_or_reference_used':False,
        'shot_counts':SHOTS.tolist(),'calibration_errors':errors.tolist(),
        'penalties':penalties[0].tolist(),'grams':grams.tolist(),'low_grams':low_grams.tolist(),
        'old_weights':old_weights.tolist(),'new_weights':weights.tolist(),
        'low_chi_new_weights':low_weights.tolist(),'chi_coefficient_l1_changes':changes.tolist(),
        'objectives':objectives,'calibration_dependence_propagated_in_primary_bootstrap':True}
    write(out/'frozen_rule_and_weights.json',frozen)
    if np.any(changes>.05):
        raise ValueError('Shot-aware coefficient stability not met')
    runplan = {'schema':'shot-aware-central-pilot-v1','job_id':old_plan['job_id'],
        'backend':old_plan['backend'],'twirl':0,'observables':[8,9,22],
        'target_shots':[43,7,14],'shared_calibration_shots':128,'primary_total_shots':192,
        'replicates':old_plan['replicates'],'same_subsets_and_bootstrap_draws':True,
        'exploratory_reused_data':True,'new_qpu_seconds':0,
        'source_sha256':{str(p.relative_to(ROOT)):digest(p) for p in sources},
        'input_sha256':{str(p.relative_to(ROOT)):digest(p) for p in input_paths}}
    write(out/'plan.json',runplan)
    # The rule, weights and objective checks are saved before target scoring.
    parent_summary = read(PARENT/'summary.json')
    counts = np.array(inputs['stratum_counts'])
    point_pauli = apply_weights(counts[None,:,:],errors[None,:,:],masks,weights)[0]
    point = physical(point_pauli)
    target = np.array(parent_summary['reference_physical'])
    with np.load(PARENT/'bootstrap.npz',allow_pickle=False) as saved:
        sampled = saved['sampled_counts']
        draws = saved['calibration_errors']
        old_boot = saved['physical']
        old_fixed_cal = saved['physical_fixed_calibration']
    draw_penalties = variance_penalties(draws,masks)
    draw_weights = solve_weights(grams,draw_penalties)
    boot_pauli = apply_weights(sampled,draws,masks,draw_weights)
    boot = physical(boot_pauli)
    frozen_weight_boot = physical(apply_weights(sampled,draws,masks,weights))
    fixed_cal_boot = physical(apply_weights(sampled,errors[None,:,:],masks,weights))
    np.savez_compressed(out/'shot_aware_bootstrap.npz',penalties=draw_penalties,
        weights=draw_weights,pauli=boot_pauli,physical=boot,
        physical_frozen_weights=frozen_weight_boot,physical_fixed_calibration=fixed_cal_boot)
    methods = {name:parent_summary['methods'][name] for name in ('readout64','zne_matched','lmpf_matched')}
    pairs = pair_probabilities(point_pauli)
    methods['lmpf_shot_aware'] = {'paulis':point_pauli.tolist(),'physical':point.tolist(),
        'absolute_errors':abs(point-target).tolist(),'bootstrap_sd':boot.std(0,ddof=1).tolist(),
        'frozen_weight_bootstrap_sd':frozen_weight_boot.std(0,ddof=1).tolist(),
        'fixed_calibration_bootstrap_sd':fixed_cal_boot.std(0,ddof=1).tolist(),
        'percentile_interval':np.quantile(boot,[.025,.975],axis=0).tolist(),
        'pair_probabilities_00_10_01_11':pairs.tolist(),'minimum_pair_probability':float(pairs.min()),
        'clipped':False}
    comparisons = {}
    for name in ('readout64','zne_matched','lmpf_matched'):
        j = old_plan['methods'].index(name)
        old_point = np.array(parent_summary['methods'][name]['physical'])
        delta = abs(old_boot[:,j]-target)-abs(boot-target)
        fixed_delta = abs(old_fixed_cal[:,j]-target)-abs(fixed_cal_boot-target)
        comparisons[name] = {'absolute_error_improvement':(abs(old_point-target)-abs(point-target)).tolist(),
            'paired_percentile_interval':np.quantile(delta,[.025,.975],axis=0).tolist(),
            'fixed_calibration_paired_interval':np.quantile(fixed_delta,[.025,.975],axis=0).tolist()}
    summary = {'status':'SHOT_AWARE_EXPLORATORY_COMPARISON_FINISHED',
        'physical_order':parent_summary['physical_order'],'reference_physical':target.tolist(),
        'methods':methods,'comparisons':comparisons,'tests_passed':tests.testsRun,
        'seconds':time.monotonic()-started,'new_qpu_seconds':0,'go_for_6x6':False,
        'hardware_mitigation_validated':False,'noise_model_validated':False,
        'full_profile_or_eight_twirl_validation':False,'target_or_reference_tuning':False,
        'uncertainty_scope':'Same paired empirical target draws and calibration posterior as prior pilot; new weights vary only with calibration. No guaranteed coverage at 7 shots; model, TN, drift and correlated-readout bias excluded.'}
    write(out/'summary.json',summary)
    write(out/'sha256.json',{str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file()})
    print(json.dumps({'weights':weights.tolist(),'penalties':penalties[0].tolist(),
        'objectives':objectives,'new_method':methods['lmpf_shot_aware'],
        'comparisons':comparisons,'seconds':summary['seconds'],'tests':tests.testsRun},indent=2))


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output exists; choose a new directory')
    try:
        with threadpool_limits(limits=1):
            run(args.output)
    except Exception as error:
        if args.output.exists():
            write(args.output/'failure.json',{'type':type(error).__name__,'reason':str(error),'new_qpu_seconds':0})
        raise
