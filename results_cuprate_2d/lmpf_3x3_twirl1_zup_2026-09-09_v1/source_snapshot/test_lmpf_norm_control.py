import unittest
import numpy as np
from lmpf_2d.norm_control import with_exact_pauli_norm, evaluate_pair, symbolic_identity
from lmpf_2d.fit import fit_coefficients, estimate


class ExactNormTests(unittest.TestCase):
    def test_exact_symbolic_complex_unitary_identity(self):
        self.assertEqual(symbolic_identity()['exact_normalized_trace'], '1')

    def test_only_constant_changes_and_estimate_is_unchanged(self):
        vectors = np.array([[.8,0,0,0], [.3,.2,0,0], [.2,0,.15,0], [.1,0,0,.1]])
        original = vectors @ vectors.T
        before_copy = original.copy()
        fixed = with_exact_pauli_norm(original)
        np.testing.assert_array_equal(original, before_copy)
        np.testing.assert_array_equal(fixed[1:,:], original[1:,:])
        np.testing.assert_array_equal(fixed[0,1:], original[0,1:])
        self.assertEqual(fixed[0,0], 1.)
        for ridge in (0., 1/56):
            a, b = fit_coefficients(original, ridge=ridge), fit_coefficients(fixed, ridge=ridge)
            self.assertEqual(a.coefficients, b.coefficients)
            self.assertAlmostEqual(b.projection_residual-a.projection_residual, 1-original[0,0], places=12)
            means, cov = [.25,-.3,.75], np.diag([.01,.04,.02])
            self.assertEqual(estimate(a.coefficients, means, cov), estimate(b.coefficients, means, cov))

    def test_reject_invalid_original_instead_of_hiding_it(self):
        bad = np.diag([.5,1.,1.,1.])
        bad[0,1] = bad[1,0] = 1.
        with self.assertRaises(ValueError):
            with_exact_pauli_norm(bad)
        with self.assertRaises(ValueError):
            with_exact_pauli_norm(np.diag([1.2,1.,1.,1.]))
        bad = np.eye(4).astype(complex)
        bad[0,1] = .1j
        with self.assertRaises(ValueError):
            with_exact_pauli_norm(bad)

    def test_separate_blocks_prevent_known_norm_dilution(self):
        a = np.diag([1.,1e-4,1e-4,1e-4])
        b = np.diag([1.,1.2e-4,1e-4,1e-4])
        result = evaluate_pair(a, b)
        self.assertLess(result['exact_norm_full_gram_relative_change'], .01)
        self.assertGreater(result['G_relative_change'], .01)
        self.assertFalse(result['followup_flags_pass'])
        self.assertEqual(result['b_relative_change'], 0.)


if __name__ == '__main__':
    unittest.main(verbosity=2)
