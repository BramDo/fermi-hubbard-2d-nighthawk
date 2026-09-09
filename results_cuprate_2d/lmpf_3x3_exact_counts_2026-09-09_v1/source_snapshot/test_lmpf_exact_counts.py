"""Analytic, symmetry, probability and independent SciPy checks."""
import math,unittest
import numpy as np
from scipy.stats import multinomial,binom
from lmpf_2d.exact_counts import (count_vectors,probabilities,joint_probabilities,
    measured_probabilities,multinomial_logmass,deviance,exact_test)

class ExactCountTests(unittest.TestCase):
    def test_count_vector_numbers_and_uniqueness(self):
        for n,expected in ((7,120),(14,680),(64,47905)):
            rows=count_vectors(n)
            self.assertEqual(len(rows),expected)
            self.assertEqual(len({tuple(x) for x in rows}),expected)
            np.testing.assert_array_equal(rows.sum(1),n)
            self.assertTrue(np.all(rows>=0))

    def test_categorical_uniform_all_tied(self):
        rec,_=exact_test([0,1,0,0],[.25]*4)
        self.assertAlmostEqual(rec['statistic'],2*math.log(4),places=12)
        self.assertAlmostEqual(rec['p_value'],1,places=12)

    def test_uniform_two_identical(self):
        rec,_=exact_test([2,0,0,0],[.25]*4)
        self.assertAlmostEqual(rec['p_value'],.25,places=12)

    def test_fair_seven_binary_six_plus(self):
        rec,_=exact_test([6,1],[.5,.5])
        self.assertAlmostEqual(rec['p_value'],.125,places=12)
        self.assertAlmostEqual(rec['p_value'],2*binom.sf(5,7,.5),places=12)

    def test_deterministic_and_impossible(self):
        rec,_=exact_test([2,0,0,0],[1,0,0,0])
        self.assertAlmostEqual(rec['p_value'],1)
        rec,_=exact_test([1,1,0,0],[1,0,0,0])
        self.assertTrue(math.isinf(rec['statistic']))
        self.assertEqual(rec['p_value'],0)

    def test_label_permutation(self):
        c=np.array([2,1,3,1]);p=np.array([.1,.2,.3,.4]);idx=[2,0,3,1]
        a,_=exact_test(c,p);b,_=exact_test(c[idx],p[idx])
        self.assertAlmostEqual(a['statistic'],b['statistic'],places=12)
        self.assertAlmostEqual(a['p_value'],b['p_value'],places=12)

    def test_scipy_mass_and_exact_moments(self):
        p=np.array([.1,.2,.3,.4]);r=count_vectors(14)
        np.testing.assert_allclose(np.exp(multinomial_logmass(r,p)),multinomial.pmf(r,14,p),atol=1e-14,rtol=1e-12)
        result,_=exact_test([1,3,4,6],p)
        self.assertLess(result['mean_max_error'],1e-10)
        self.assertLess(result['covariance_max_error'],1e-10)

    def test_readout_identity_and_mask(self):
        p=joint_probabilities([.2,-.1,.3])
        np.testing.assert_array_equal(measured_probabilities([.2,-.1,.3],[0,0],np.zeros((2,2))),p)
        np.testing.assert_array_equal(measured_probabilities([.2,-.1,.3],[1,0],np.zeros((2,2))),p[[1,0,3,2]])

    def test_asymmetric_readout_known_case(self):
        got=measured_probabilities([1,1,1],[1,0],[[.1,.2],[.3,.4]])
        np.testing.assert_allclose(got,[.24,.56,.06,.14],atol=1e-15)

    def test_invalid_inputs_rejected_without_clipping(self):
        for p in ([-.01,.31,.3,.4],[.1,.2,.3,.5],[math.nan,.2,.3,.5]):
            with self.assertRaises(ValueError):probabilities(p)
        for n in (0,-1,65,1.5,True):
            with self.assertRaises(ValueError):count_vectors(n)
        for c in ([[1.5,.5]],[[1,-1]],[[1,0],[1,1]]):
            with self.assertRaises(ValueError):deviance(c,[.5,.5])
        with self.assertRaises(ValueError):joint_probabilities([1,1,-1])
        with self.assertRaises(ValueError):measured_probabilities([0,0,0],[2,0],np.zeros((2,2)))

if __name__=='__main__':unittest.main()
