"""Deterministic statistical and convention tests; no new simulation needed."""
import unittest

import numpy as np

import analyze_aer_cuprate_nighthawk_512 as an


def occupations():
    bits = np.zeros(18, dtype=np.uint8)
    bits[[0, 4, 8, 12, 3, 7, 11, 15]] = 1
    return bits


def mixture(seed=91):
    rng = np.random.default_rng(seed)
    bits = np.tile(occupations(), (8, 64, 1))
    other = occupations()
    other[0], other[2] = other[2], other[0]
    bits[rng.random((8, 64)) < .5] = other
    return bits


class MatchedStatisticsTests(unittest.TestCase):
    def test_physical_spin_convention(self):
        p = an.pauli_samples(occupations()[None])[0]
        np.testing.assert_array_equal(an.physical_observables(p)[0], [1, 1, 0])
        self.assertEqual(an.physical_observables(p)[:, 0].sum(), 8)

    def test_zero_reference_error(self):
        data = np.tile(occupations(), (8, 64, 1))
        p, f, counts = an.estimates(data)
        exact = an.pauli_samples(occupations()[None])[0]
        m = an.metrics(p, f, exact)
        np.testing.assert_array_equal(m[:, :4], np.zeros((2, 4)))
        np.testing.assert_array_equal(counts, [512, 512])

    def test_ps_is_pooled_not_per_twirl_unweighted(self):
        data = np.tile(occupations(), (8, 64, 1))
        other = occupations()
        other[0], other[2] = other[2], other[0]
        data[1:] = other
        data[0, 2:] = 1  # invalid Nup=Ndown=9
        p, _, counts = an.estimates(data)
        states = an.pauli_samples(np.stack([occupations(), other]))
        expected = (2*states[0]+448*states[1])/450
        np.testing.assert_allclose(p[1], expected, atol=1e-14)
        self.assertEqual(counts[1], 450)
        self.assertGreater(np.max(np.abs(p[1]-(states[0]+7*states[1])/8)), .1)

    def test_minimum_acceptance_enforced(self):
        with self.assertRaises(ValueError):
            an.estimates(np.ones((8, 64, 18), dtype=np.uint8))

    def test_fixed_twirl_variance_not_between_twirl_variance(self):
        data = np.tile(occupations(), (8, 64, 1))
        data[::2, :, 0] = 0
        self.assertGreater(an.pauli_samples(data.reshape(-1, 18)).std(axis=0).max(), .9)
        np.testing.assert_array_equal(an.fixed_twirl_standard_error(data), np.zeros(27))

    def test_fixed_standard_error_formula(self):
        data = mixture()
        samples = an.pauli_samples(data.reshape(-1, 18)).reshape(8, 64, 27)
        manual = np.sqrt(sum(np.var(block, axis=0, ddof=1)/64 for block in samples)/64)
        np.testing.assert_allclose(an.fixed_twirl_standard_error(data), manual, atol=1e-14)

    def test_independent_dataset_resampling(self):
        data = mixture()
        means, f, invalid = an.bootstrap_pair(data, data, repetitions=40, seed=8)
        self.assertEqual(means.shape, (40, 2, 2, 27))
        self.assertEqual(invalid, 0)
        self.assertTrue(np.any(means[:, 0] != means[:, 1]))
        np.testing.assert_array_equal(f, np.ones((40, 2, 2)))

    def test_seed_reproducibility_and_hierarchical_mode(self):
        left = mixture()
        right = mixture(103)
        for hierarchical in [False, True]:
            x = an.bootstrap_pair(left, right, repetitions=20, seed=17, hierarchical=hierarchical)
            y = an.bootstrap_pair(left, right, repetitions=20, seed=17, hierarchical=hierarchical)
            np.testing.assert_array_equal(x[0], y[0])

    def test_bootstrap_covariance_preserves_fixed_charge(self):
        means, _, _ = an.bootstrap_pair(mixture(), mixture(122), repetitions=100, seed=5)
        observables = an.physical_observables(means)
        np.testing.assert_allclose(observables[..., 0].sum(axis=-1), 8, atol=1e-13)
        np.testing.assert_allclose(observables[..., 1].sum(axis=-1), 0, atol=1e-13)

    def test_bootstrap_variance_matches_empirical_resampling_law(self):
        data = mixture()
        means, _, _ = an.bootstrap_pair(data, mixture(133), repetitions=2000, seed=91)
        p = an.pauli_samples(data.reshape(-1, 18)).reshape(8, 64, 27)
        expected = p[:, :, 0].var(axis=1, ddof=0).sum()/(8**2*64)
        observed = means[:, 0, 0, 0].var(ddof=1)
        self.assertLess(abs(observed/expected-1), .1)

    def test_simultaneous_band_does_not_reject_zero_delta_for_positive_rmse(self):
        noise = np.random.default_rng(4).normal(0, .04, (2000, 27))
        band = an.simultaneous_raw_band(np.zeros(27), noise)
        self.assertEqual(band['coordinates_excluding_zero'], [])
        self.assertGreater(band['radius'], 0)
        shifted = np.zeros(27)
        shifted[0] = .5
        band2 = an.simultaneous_raw_band(shifted, noise+shifted)
        self.assertEqual(band2['coordinates_excluding_zero'], [0])

    def test_wrong_sample_shape_rejected(self):
        with self.assertRaises(ValueError):
            an.bootstrap_pair(mixture()[:, :32], mixture())


if __name__ == '__main__':
    unittest.main()
