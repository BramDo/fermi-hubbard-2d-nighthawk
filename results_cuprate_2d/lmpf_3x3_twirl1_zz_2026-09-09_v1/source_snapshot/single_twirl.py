"""Fixed central L-MPF weights on matching archived twirl0 hardware only."""
from pathlib import Path
import argparse, io, json, shutil, sys, time, unittest
import numpy as np
from threadpoolctl import threadpool_limits
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lmpf_2d.archive_3x3 import ARCHIVE
from lmpf_2d.hardware_inputs import decode
from lmpf_2d.model import digest
from lmpf_2d.fit import linear_zne_weights

NORM = ROOT/'results_cuprate_2d/lmpf_3x3_exact_norm_2026-09-09_v1'
METHODS = ['raw64', 'readout64', 'zne_matched', 'lmpf_matched', 'lmpf_all85']
SIZES = np.array([43,21,7,14])
REPLICATES, SUBSET_SEED, BOOT_SEED = 10000, 2026090917, 2026090918
OUTCOMES = np.array([[i & 1, (i >> 1) & 1] for i in range(4)])
TRANSFORM = np.array([[-.5,-.5,0],[-.5,.5,0],[-.25,-.25,.25]])
OFFSET = np.array([1.,0.,.25])


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path, value):
    with path.open('x') as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write('\n')


def subset_indices():
    order = np.random.default_rng(SUBSET_SEED).permutation(64)
    return order[:43], order[43:]


def counts4(bits):
    bits = np.asarray(bits)
    if bits.ndim != 2 or bits.shape[1] != 2 or not np.isin(bits, [0,1]).all():
        raise ValueError('Expected two binary central bits per shot')
    return np.bincount((bits[:,0]+2*bits[:,1]).astype(int), minlength=4)


def moment_table(errors, mask):
    errors = np.asarray(errors)
    a = 1-errors[:,0,:]-errors[:,1,:]
    b = errors[:,1,:]-errors[:,0,:]
    if np.min(a) <= .1:
        raise ValueError('Ill-conditioned readout draw; no silent redraw')
    z = ((1-2*OUTCOMES[None,:,:])-b[:,None,:])/a[:,None,:]
    z *= 1-2*np.asarray(mask)[None,None,:]
    return np.concatenate([z, (z[:,:,0]*z[:,:,1])[:,:,None]], axis=2)


def estimate_batch(counts, errors, masks, weights):
    counts = np.asarray(counts)
    if counts.ndim != 3 or counts.shape[1:] != (4,4):
        raise ValueError('Expected replicates x four strata x four outcomes')
    if not np.all(counts.sum(axis=2) == SIZES):
        raise ValueError('Incorrect stratum shot budget')
    errors = np.broadcast_to(np.asarray(errors), (len(counts),2,2))
    probs = counts/SIZES[None,:,None]
    moments = [np.einsum('rp,rpo->ro', probs[:,j], moment_table(errors,masks[j])) for j in range(4)]
    baseline = (43*moments[0]+21*moments[1])/64
    raw_table = moment_table(np.zeros((1,2,2)), masks[0])[0]
    raw = ((counts[:,0]+counts[:,1])/64)@raw_table
    matched = np.stack([moments[0],moments[2],moments[3]], axis=1)
    all_shots = np.stack([baseline,moments[2],moments[3]], axis=1)
    zne = np.einsum('a,rao->ro', linear_zne_weights([1,2,3]), matched)
    lmpf = np.einsum('oa,rao->ro', weights, matched)
    full = np.einsum('oa,rao->ro', weights, all_shots)
    return np.stack([raw,baseline,zne,lmpf,full], axis=1)


def physical(paulis):
    return np.asarray(paulis)@TRANSFORM.T+OFFSET


def pair_probabilities(paulis):
    z, d, zz = np.asarray(paulis)
    return np.array([1+z+d+zz,1-z+d-zz,1+z-d-zz,1-z-d+zz])/4


def run(out):
    if out.exists():
        raise FileExistsError('Preserve prior hardware comparison')
    out.mkdir(parents=True)
    (out/'source_snapshot').mkdir()
    started = time.monotonic()
    names = ['single_twirl.py','verify_single_twirl.py','hardware_inputs.py','fit.py',
             'model.py','archive_3x3.py','PLAN_SINGLE_TWIRL.md']
    sources = [ROOT/'lmpf_2d'/name for name in names]+[ROOT/'test_lmpf_single_twirl.py']
    for path in sources:
        shutil.copyfile(path, out/'source_snapshot'/path.name)
    stream = io.StringIO()
    suite = unittest.TestSuite()
    for name in ('test_lmpf_2d','test_lmpf_hardware_inputs','test_lmpf_product',
                 'test_lmpf_tn_storage','test_lmpf_canonical_chain','test_lmpf_chain_contract',
                 'test_lmpf_zz_refine','test_lmpf_norm_control','test_lmpf_single_twirl'):
        suite.addTests(unittest.defaultTestLoader.loadTestsFromName(name))
    tests = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    (out/'tests.txt').write_text(stream.getvalue())
    if not tests.wasSuccessful():
        raise RuntimeError('Tests failed')
    norm, norm_plan, norm_manifest = read(NORM/'results.json'), read(NORM/'plan.json'), read(NORM/'sha256.json')
    for name in ('results.json','plan.json'):
        if digest(NORM/name) != norm_manifest[name]:
            raise ValueError('Changed frozen coefficients')
    if not norm['all_followup_local_flags_pass'] or norm_plan['twirl'] != 0:
        raise ValueError('Central coefficient prerequisite not met')
    weights = np.array([r['levels'][str(r['comparison_levels'][1])]['fits']['ridge']['exact_norm']['coefficients'] for r in norm['records']])
    if [r['observable'] for r in norm['records']] != [8,9,22] or weights.shape != (3,3):
        raise ValueError('Unexpected coefficient ordering')
    if np.max(abs(weights.sum(1)-1)) > 1e-9:
        raise ValueError('Invalid coefficient normalization')
    shared, extra = subset_indices()
    write(out/'frozen_weights.json', {'source': str(NORM.relative_to(ROOT)),
        'source_sha256': digest(NORM/'results.json'), 'observables': [8,9,22],
        'weights': weights.tolist(), 'ridge': 1/56, 'twirl': 0,
        'shared_factor1_indices': shared.tolist(), 'extra_factor1_indices': extra.tolist(),
        'subset_seed': SUBSET_SEED, 'reference_used_to_fit_or_select': False})
    original, raw, receipt = [read(ARCHIVE/name) for name in ('plan.json','raw_bitstrings.json','job_receipt.json')]
    if raw['job_id'] != receipt['job_id'] or receipt['job_id'] != norm_plan['job_id']:
        raise ValueError('Hardware/coefficient job mismatch')
    if receipt['backend'] != original['backend'] or original['backend'] != norm_plan['backend'] or raw['width'] != 18:
        raise ValueError('Hardware backend or width mismatch')
    if receipt['plan_sha256'] != digest(ARCHIVE/'plan.json'):
        raise ValueError('Changed hardware plan')
    keyed = {(r['setting_id'],r['twirl_id']): r for r in raw['records']}
    if len(keyed) != len(raw['records']):
        raise ValueError('Duplicate hardware record key')
    selected, central, arm_masks = [], [], []
    for factor, expected_shots in ((1,64),(2,7),(3,14)):
        key = (f'U8_T04_factor{factor}',0)
        r = keyed[key]
        index = next(i for i,p in enumerate(original['records']) if (p['setting_id'],p['twirl_id']) == key)
        p = original['records'][index]
        for field in ('factor','shots','readout_mask_little_endian','source_qpy'):
            if r[field] != p[field]:
                raise ValueError('Record/plan field mismatch: '+field)
        if len(r['bitstrings']) != expected_shots:
            raise ValueError('Unexpected target shot count')
        native = next(x for x in norm_plan['native_gate_check']['inputs'] if x['factor'] == factor)
        qpy = ARCHIVE/'provider_inputs'/f'circuit_{index:03d}.qpy'
        if digest(qpy) != native['qpy_sha256'] or digest(qpy) != digest(ARCHIVE/'bound_inputs'/qpy.name):
            raise ValueError('Native circuit/weight mismatch')
        mask = np.array(r['readout_mask_little_endian'])
        if len(mask) != 18 or not np.isin(mask,[0,1]).all():
            raise ValueError('Invalid readout mask')
        selected.append(r)
        central.append(decode(r['bitstrings'],18)[:,[8,9]])
        arm_masks.append(mask[[8,9]])
    calibration = [keyed[(f'readout_all{i}',0)] for i in (0,1)]
    for i,r in enumerate(calibration):
        if str(r['state']) != str(i) or len(r['bitstrings']) != 64 or any(r['readout_mask_little_endian']):
            raise ValueError('Unexpected calibration convention')
    cal_bits = [decode(r['bitstrings'],18)[:,[8,9]] for r in calibration]
    cal_counts = np.array([cal_bits[0].sum(0),(1-cal_bits[1]).sum(0)])
    errors = (cal_counts+.5)/65
    data = [central[0][shared],central[0][extra],central[1],central[2]]
    observed = np.array([counts4(bits) for bits in data])
    masks = np.array([arm_masks[0],arm_masks[0],arm_masks[1],arm_masks[2]])
    write(out/'selected_inputs.json', {'job_id':raw['job_id'],'width':18,
        'target_records':selected,'calibration_records':calibration,
        'central_modes':[8,9], 'stratum_counts':observed.tolist(),'stratum_masks':masks.tolist(),
        'calibration_error_counts':cal_counts.tolist(),'calibration_errors_posterior_mean':errors.tolist()})
    runplan = {'schema':'central-single-twirl-hardware-v1','job_id':raw['job_id'],
        'backend':original['backend'],'twirl':0,'observables':[8,9,22],
        'methods':METHODS,'replicates':REPLICATES,'bootstrap_seed':BOOT_SEED,
        'subset_seed':SUBSET_SEED,'stratum_sizes':SIZES.tolist(),
        'primary_target_shots':{'readout64':[64,0,0],'zne_matched':[43,7,14],'lmpf_matched':[43,7,14]},
        'shared_calibration_shots':128,'primary_total_shots':192,'all85_total_shots':213,
        'raw64_calibration_shots_used':0,'selected_union_shots':213,
        'new_qpu_seconds':0,'hardware_mitigation_validated':False,'go_for_6x6':False,
        'source_sha256':{str(p.relative_to(ROOT)):digest(p) for p in sources},
        'input_sha256':{str((ARCHIVE/name).relative_to(ROOT)):digest(ARCHIVE/name) for name in ('plan.json','raw_bitstrings.json','job_receipt.json')}}
    write(out/'plan.json',runplan)
    # All coefficients and the subset are frozen before any accuracy scoring.
    reference = np.array(original['target']['reference'])[[8,9,22]]
    np.testing.assert_allclose(reference,[r['levels'][str(r['comparison_levels'][1])]['exact_circuit_expectation_reference'] for r in norm['records']],atol=1e-12)
    point_pauli = estimate_batch(observed[None,:,:],errors[None,:,:],masks,weights)[0]
    point = physical(point_pauli)
    rng = np.random.default_rng(BOOT_SEED)
    draws = rng.beta(cal_counts+.5,64-cal_counts+.5,size=(REPLICATES,2,2))
    sampled = np.stack([rng.multinomial(int(n), observed[j]/n, size=REPLICATES) for j,n in enumerate(SIZES)],axis=1)
    boot_pauli = estimate_batch(sampled,draws,masks,weights)
    boot = physical(boot_pauli)
    fixed_boot = physical(estimate_batch(sampled,errors[None,:,:],masks,weights))
    np.savez_compressed(out/'bootstrap.npz',calibration_errors=draws,
        sampled_counts=sampled.astype(np.int16),pauli=boot_pauli,physical=boot,
        physical_fixed_calibration=fixed_boot)
    target = physical(reference)
    method_results = {}
    for index,name in enumerate(METHODS):
        probabilities = pair_probabilities(point_pauli[index])
        method_results[name] = {'paulis':point_pauli[index].tolist(),'physical':point[index].tolist(),
            'absolute_errors':abs(point[index]-target).tolist(),
            'bootstrap_sd':boot[:,index].std(0,ddof=1).tolist(),
            'fixed_calibration_bootstrap_sd':fixed_boot[:,index].std(0,ddof=1).tolist(),
            'percentile_interval':np.quantile(boot[:,index],[.025,.975],axis=0).tolist(),
            'pair_probabilities_00_10_01_11':probabilities.tolist(),
            'minimum_pair_probability':float(probabilities.min()),'clipped':False}
    comparisons = {}
    for base in ('readout64','zne_matched'):
        i = METHODS.index(base)
        delta = abs(boot[:,i]-target)-abs(boot[:,3]-target)
        fixed_delta = abs(fixed_boot[:,i]-target)-abs(fixed_boot[:,3]-target)
        comparisons[base] = {'absolute_error_improvement':(abs(point[i]-target)-abs(point[3]-target)).tolist(),
            'paired_percentile_interval':np.quantile(delta,[.025,.975],axis=0).tolist(),
            'fixed_calibration_paired_interval':np.quantile(fixed_delta,[.025,.975],axis=0).tolist()}
    summary = {'status':'CENTRAL_TWIRL0_EXPLORATORY_HARDWARE_COMPARISON',
        'physical_order':['central_charge','central_spin','central_doublon'],
        'reference_paulis':reference.tolist(),'reference_physical':target.tolist(),
        'methods':method_results,'comparisons':comparisons,'tests_passed':tests.testsRun,
        'seconds':time.monotonic()-started,'new_qpu_seconds':0,
        'hardware_mitigation_validated':False,'full_profile_or_eight_twirl_validation':False,
        'go_for_6x6':False,'noise_model_validated':False,'coefficients_refitted':False,
        'uncertainty_scope':'Paired stratified empirical bootstrap plus shared independent-assignment Jeffreys calibration draws; not coverage-certified, especially with 7 shots. No TN/model/drift/correlated-readout coverage.'}
    write(out/'summary.json',summary)
    write(out/'sha256.json',{str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file()})
    print(json.dumps(summary,indent=2))


if __name__ == '__main__':
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
