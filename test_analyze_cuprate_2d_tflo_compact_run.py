"""Synthetic same-sector data; no new hardware samples or provider calls."""
import copy
import unittest

import numpy as np

import analyze_cuprate_2d_tflo_compact_run as compact


class CompactAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.settings = compact.read(compact.PLAN / 'manifest.json')['settings']
        bits = np.zeros((64, 18), dtype=np.uint8)
        bits[:, [0, 2, 4, 6, 1, 3, 5, 7]] = 1
        cls.raw = {s['id']: {t: bits.copy() for t in range(8)} for s in cls.settings}

    def test_fit_ignores_all_holdout_references(self):
        baseline = compact.evaluate_once(self.settings, self.raw)
        settings = copy.deepcopy(self.settings)
        for setting in settings:
            if setting['role'] != 'train':
                del setting['reference']
        actual = compact.evaluate_once(settings, self.raw)
        np.testing.assert_allclose(actual[0], baseline[0], atol=0, rtol=0)
        self.assertEqual(actual[2], baseline[2])

    def test_interacting_training_rejected(self):
        settings = copy.deepcopy(self.settings)
        settings[0]['u_over_t'] = 8
        with self.assertRaises(ValueError):
            compact.evaluate_once(settings, self.raw)

    def test_bad_sector_stops_without_relaxation(self):
        raw = copy.deepcopy(self.raw)
        for bits in raw[self.settings[-1]['id']].values():
            bits[:] = 0
        with self.assertRaises(compact.RetentionFailure):
            compact.evaluate_once(self.settings, raw)

    def test_central_results_match_existing_evaluator(self):
        values, counts, _ = compact.evaluate_once(self.settings, self.raw)
        original = compact.analyze(self.settings, self.raw, 4, 4, tolerance=1, bootstrap=2)
        self.assertEqual(counts, [512] * 10)
        for i, row in enumerate(original['settings']):
            for j, method in enumerate(compact.METHODS):
                np.testing.assert_allclose(row[method]['observables'], compact.physical_observables(values[j, i]), atol=1e-12)

    def test_zero_crossing_and_insufficient_bootstrap_do_not_pass(self):
        gains = {'raw_minus_tflo': {'low': .1, 'high': .2},
                 'classical_minus_tflo': {'low': -.01, 'high': .01}}
        result = compact.inference_gate(gains, 400, 400)
        self.assertTrue(result['TFLO_better_than_raw'])
        self.assertFalse(result['TFLO_better_than_classical_FLO_only'])
        gains['classical_minus_tflo']['low'] = .001
        result = compact.inference_gate(gains, 379, 400)
        self.assertFalse(result['TFLO_better_than_raw'])
        self.assertFalse(result['TFLO_better_than_classical_FLO_only'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
