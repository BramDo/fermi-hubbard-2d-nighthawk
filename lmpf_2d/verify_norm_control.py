"""Independent KKT/constant-term audit of the saved exact-norm follow-up."""
from pathlib import Path
import argparse, json, sys, time
import numpy as np
from threadpoolctl import threadpool_limits
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lmpf_2d.model import digest


def read(path):
    return json.loads(path.read_text())


def ratio(delta, target):
    num, den = np.sqrt(np.sum(delta*delta)), np.sqrt(np.sum(target*target))
    return float(num/den) if den else (0. if num == 0 else float('inf'))


def verify(folder):
    dest = folder/'verification'
    dest.mkdir(exist_ok=False)
    started = time.monotonic()
    plan, result = read(folder/'plan.json'), read(folder/'results.json')
    if plan['ridge'] != 1/56 or plan['matrix_tolerance'] != .01 or plan['coefficient_l1_tolerance'] != .05:
        raise ValueError('Changed follow-up criteria')
    if not plan['defined_after_prior_diagnosis'] or plan['independent_data_validation']:
        raise ValueError('Incorrect evidence independence claim')
    for name, expected in read(folder/'sha256.json').items():
        if digest(folder/name) != expected:
            raise ValueError('Changed saved evidence: ' + name)
    for name, expected in plan['source_sha256'].items():
        if digest(ROOT/name) != expected or digest(folder/'source_snapshot'/Path(name).name) != expected:
            raise ValueError('Changed numerical source: ' + name)
    fits, max_kkt, max_shift, max_weight = 0, 0., 0., 0.
    passed = []
    for record in result['records']:
        source = folder/'inputs'/f"{record['operator']}_record.json"
        if digest(source) != record['source_sha256'] or digest(ROOT/record['source_record']) != record['source_sha256']:
            raise ValueError('Input provenance mismatch')
        original = read(source)
        low, high = map(str, record['comparison_levels'])
        for chi in (low, high):
            level = record['levels'][chi]
            raw, fixed = np.array(level['raw_gram']), np.array(level['exact_norm_gram'])
            np.testing.assert_array_equal(raw, original['chi_results'][chi]['overlaps_exact'])
            expected = raw.copy()
            expected[0,0] = 1.
            np.testing.assert_array_equal(fixed, expected)
            if not np.isfinite(fixed).all() or np.linalg.eigvalsh(raw).min() < -1e-8 or np.linalg.eigvalsh(fixed).min() < -1e-8:
                raise ValueError('Invalid Gram')
            for kind, ridge in (('unregularized',0.), ('ridge',1/56)):
                before, after = level['fits'][kind]['before'], level['fits'][kind]['exact_norm']
                old_c, new_c = np.array(before['coefficients']), np.array(after['coefficients'])
                max_weight = max(max_weight, float(np.max(abs(old_c-new_c))))
                np.testing.assert_array_equal(old_c, new_c)
                np.testing.assert_allclose(old_c, original['chi_results'][chi]['fits']['exact'][kind]['coefficients'], atol=1e-10, rtol=0)
                g, b = fixed[1:,1:], fixed[1:,0]
                k = len(b)
                # Direct equality-constrained KKT solve, independent of the null-space solver.
                matrix = np.zeros((k+1,k+1))
                matrix[:k,:k] = g + ridge*np.eye(k)
                matrix[:k,k] = 1
                matrix[k,:k] = 1
                direct = np.linalg.solve(matrix, np.r_[b,1.])[:k]
                max_kkt = max(max_kkt, float(np.max(abs(direct-new_c))))
                np.testing.assert_allclose(direct, new_c, atol=1e-8, rtol=0)
                for gram, fit in ((raw,before), (fixed,after)):
                    residual = gram[0,0] - 2*b@new_c + new_c@g@new_c
                    np.testing.assert_allclose(residual, fit['projection_residual'], atol=1e-11, rtol=0)
                shift_error = abs((after['projection_residual']-before['projection_residual']) - (1-raw[0,0]))
                max_shift = max(max_shift, shift_error)
                if shift_error > 1e-11 or abs(new_c.sum()-1) > 1e-9:
                    raise ValueError('Residual shift or normalization failed')
                fits += 1
        a, b = np.array(record['levels'][low]['raw_gram']), np.array(record['levels'][high]['raw_gram'])
        fixed_a, fixed_b = a.copy(), b.copy()
        fixed_a[0,0] = fixed_b[0,0] = 1.
        ca = np.array(record['levels'][low]['fits']['ridge']['before']['coefficients'])
        cb = np.array(record['levels'][high]['fits']['ridge']['before']['coefficients'])
        values = {'raw_full_gram_relative_change': ratio(b-a,b),
                  'exact_norm_full_gram_relative_change': ratio(fixed_b-fixed_a,fixed_b),
                  'G_relative_change': ratio(b[1:,1:]-a[1:,1:],b[1:,1:]),
                  'b_relative_change': ratio(b[1:,0]-a[1:,0],b[1:,0]),
                  'ridge_coefficient_l1_change': float(np.sum(abs(cb-ca)))}
        for key, value in values.items():
            np.testing.assert_allclose(value, record['stability'][key], atol=1e-12)
        raw_pass = values['raw_full_gram_relative_change'] <= .01 and values['ridge_coefficient_l1_change'] <= .05
        new_pass = all(values[key] <= .01 for key in ('exact_norm_full_gram_relative_change','G_relative_change','b_relative_change')) and values['ridge_coefficient_l1_change'] <= .05
        if raw_pass != record['raw_archived_stability']['passes_local_flags'] or raw_pass != record['stability']['raw_flags_pass']:
            raise ValueError('Historical classification was changed')
        if new_pass != record['stability']['followup_flags_pass']:
            raise ValueError('Incorrect follow-up classification')
        passed.append(new_pass)
    if all(passed) != result['all_followup_local_flags_pass']:
        raise ValueError('Incorrect overall classification')
    report = {'status': 'EXACT_NORM_SAVED_EVIDENCE_VERIFIED', 'fits_checked': fits,
              'maximum_direct_KKT_coefficient_error': max_kkt,
              'maximum_before_after_weight_change': max_weight,
              'maximum_residual_shift_error': max_shift,
              'historical_raw_flags_preserved': True,
              'followup_flags_pass': all(passed), 'new_qpu_seconds': 0,
              'independent_hardware_validation': False, 'seconds': time.monotonic()-started,
              'verifier_source_sha256': digest(Path(__file__))}
    with (dest/'verification.json').open('x') as handle:
        json.dump(report, handle, indent=2)
        handle.write('\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    with threadpool_limits(limits=1):
        verify(parser.parse_args().folder)
