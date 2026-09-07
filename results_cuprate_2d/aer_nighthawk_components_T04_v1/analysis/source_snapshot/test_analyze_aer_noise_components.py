"""Analytical and resampling tests for component-effect inference."""
import unittest

import numpy as np

import analyze_aer_noise_components as an


def trajectory_data():
    rng = np.random.default_rng(531)
    off = rng.uniform(-.2, .2, (2, 8, 16, 27))
    return np.stack([off, .9*off+.01], axis=3)


class ComponentInferenceTests(unittest.TestCase):
    def test_ideal_metrics_and_projection(self):
        exact = np.array([-.8, .8, -.9])
        np.testing.assert_allclose(an.metrics(exact, exact), [0, 0, 0, 1], atol=1e-14)

    def test_projection_is_not_fidelity_and_is_not_clipped(self):
        exact = np.array([-.8, .8, -.9])
        self.assertAlmostEqual(an.metrics(np.array([-.88, .88, -.9]), exact)[3], 1.1)

    def test_undefined_zero_spin_projection_rejected(self):
        with self.assertRaises(ValueError):
            an.metrics(np.zeros(3), np.zeros(3))

    def test_paired_readout_variants_remain_paired(self):
        draws = an.bootstrap(trajectory_data(), repetitions=100)
        self.assertEqual(draws.shape, (100, 2, 2, 27))
        np.testing.assert_allclose(draws[:, :, 1], .9*draws[:, :, 0]+.01, atol=1e-14)

    def test_models_resampled_independently(self):
        data = trajectory_data()
        data[1] = data[0]
        draws = an.bootstrap(data, repetitions=100)
        self.assertTrue(np.any(draws[:, 0] != draws[:, 1]))

    def test_reproducible_bootstrap(self):
        data = trajectory_data()
        np.testing.assert_array_equal(an.bootstrap(data, repetitions=20, seed=7),
                                      an.bootstrap(data, repetitions=20, seed=7))

    def test_fixed_twirls_do_not_create_variance(self):
        data = np.zeros((2, 8, 16, 2, 27))
        data[:, :, :, :, :] = np.arange(8)[None, :, None, None, None]/20
        draws = an.bootstrap(data, repetitions=30)
        np.testing.assert_allclose(draws, .175, atol=1e-14)

    def test_empirical_bootstrap_variance(self):
        data = trajectory_data()
        draws = an.bootstrap(data, repetitions=2000)
        expected = data[0, :, :, 0, 0].var(axis=1, ddof=0).sum()/(16*8**2)
        actual = draws[:, 0, 0, 0].var(ddof=1)
        self.assertLess(abs(actual/expected-1), .15)


if __name__ == '__main__':
    unittest.main()
