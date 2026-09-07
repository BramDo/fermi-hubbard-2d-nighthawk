"""Deterministic arithmetic and stored-vector resampling tests; no circuit execution."""
from fractions import Fraction
import unittest
import numpy as np
import analyze_aer_equal_cz_budget as a

class BudgetTests(unittest.TestCase):
    def test_exact_64_allocation_and_proxy(self):
        counts,score,n=a.allocation(64)
        self.assertEqual(counts,(30,5,8))
        self.assertEqual(score,Fraction(37,30))
        self.assertGreater(n,1)
        self.assertEqual(sum(c*f for c,f in zip(counts,(1,2,3))),64)
    def test_exact_half_budget_allocation(self):
        counts,score,_=a.allocation(32)
        self.assertEqual(counts,(14,3,4))
        self.assertEqual(sum(c*f for c,f in zip(counts,(1,2,3))),32)
    def test_invalid_budgets(self):
        for budget in (0,5,6.5):
            with self.assertRaises(ValueError):
                a.allocation(budget)
    def test_allocation_fits_parent_and_exact_costs(self):
        self.assertTrue(all(n<=m for n,m in zip(a.ALLOCATION,(64,9,18))))
        self.assertEqual(8*sum(a.ALLOCATION),344)
        self.assertEqual(8*64*1008,516096)
        self.assertEqual(8*sum(n*f for n,f in zip(a.ALLOCATION,(1,2,3)))*1008,516096)
        self.assertEqual(8*(64+5+8),616)
        self.assertEqual(728-616,112)
    def test_weights_affine_and_linear_moment(self):
        np.testing.assert_allclose(a.WEIGHTS.sum(axis=1),1,atol=1e-14)
        self.assertAlmostEqual(float(a.WEIGHTS[1]@np.array([1,1,2,3])),0)
        self.assertAlmostEqual(float(a.WEIGHTS[2]@np.array([1,1,4,9])),0)

class SelectionTests(unittest.TestCase):
    def fixture(self):
        return [np.broadcast_to(np.arange(n)[None,:,None],(8,n,27)).copy()
                for n in (64,9,18)]
    def test_fixed_prefixes_and_raw_suffix(self):
        groups=self.fixture()
        strata=a.split_groups(groups)
        self.assertEqual([x.shape for x in strata],[(8,30,27),(8,34,27),(8,5,27),(8,8,27)])
        self.assertEqual(strata[0][0,-1,0],29)
        self.assertEqual(strata[1][0,0,0],30)
        self.assertEqual(strata[1][0,-1,0],63)
        self.assertEqual(strata[2][0,-1,0],4)
        self.assertEqual(strata[3][0,-1,0],7)
    def test_raw_uses_all64_zne_only30(self):
        groups=[np.ones((8,64,27)),np.zeros((8,9,27)),np.zeros((8,18,27))]
        groups[0][:,30:]=-1
        strata=a.split_groups(groups)
        values=a.arm_means(np.stack([x.mean(axis=(0,1)) for x in strata]))
        np.testing.assert_allclose(values[0],-4/64,atol=1e-14)
        np.testing.assert_allclose(values[1],4/3,atol=1e-14)
    def test_wrong_parent_shapes_rejected(self):
        with self.assertRaises(ValueError):
            a.split_groups([np.zeros((8,64,27))]*3)
    def test_old_bootstrap_strata_rejected(self):
        with self.assertRaises(ValueError):
            a.bootstrap([np.zeros((8,n,27)) for n in (37,27,9,18)],2,1)

class InferenceTests(unittest.TestCase):
    def test_shared_prefix_preserves_both_arm_covariance(self):
        strata=[np.zeros((8,n,27)) for n in a.SIZES]
        strata[0][:,:,0]=np.arange(30)[None,:]/100
        draws=a.arm_means(a.bootstrap(strata,32,1))
        np.testing.assert_allclose(draws[:,1,0],draws[:,0,0]*(4/3)/(30/64),atol=1e-14)
        self.assertGreater(float(np.cov(draws[:,0,0],draws[:,1,0])[0,1]),0)
    def test_bootstrap_repeatable(self):
        rng=np.random.default_rng(1)
        strata=[rng.normal(size=(8,n,27)) for n in a.SIZES]
        np.testing.assert_array_equal(a.bootstrap(strata,10,3),a.bootstrap(strata,10,3))
    def test_linear_intercept_exact(self):
        target=np.linspace(-.3,.3,27)
        source=np.stack([target+.02,target+.02,target+.04,target+.06])
        np.testing.assert_allclose(a.arm_means(source)[1],target,atol=1e-14)
    def test_quadratic_secondary_intercept(self):
        source=np.stack([np.full(27,.1+.02*x+.005*x*x) for x in (1,1,2,3)])
        np.testing.assert_allclose(a.arm_means(source)[2],.1,atol=1e-14)
    def test_negative_gain_not_clipped(self):
        m=np.array([[.2,.3,.4,.5],[.3,.4,.5,.4],[0,0,0,0]])
        np.testing.assert_allclose(a.benefits(m),[-.1]*4,atol=1e-14)
    def test_physical_units_and_spin_convention(self):
        up_occupied=np.array([-1.,1.]*9+[-1.]*9)
        expected=np.tile([1.,1.,0.],(9,1))
        np.testing.assert_array_equal(a.physical(up_occupied),expected)
        np.testing.assert_allclose(a.metrics(up_occupied,up_occupied),[0,0,0,1],atol=1e-14)
        np.testing.assert_allclose(a.metrics(np.zeros(27),up_occupied),[0,1,.25,0],atol=1e-14)
    def test_zero_reference_spin_rejected(self):
        with self.assertRaises(ValueError):
            a.metrics(np.ones(27),np.ones(27))
    def test_ranges_reported_without_clipping(self):
        p=np.zeros(27)
        p[0]=2.
        check=a.ranges(p)
        self.assertGreater(check['negative_two_mode_probabilities'],0)
        self.assertEqual(check['paulis_outside_range'],1)
        self.assertEqual(p[0],2.)
    def test_half_budget_raw_weights(self):
        source=np.stack([np.ones(27),np.zeros(27),np.zeros(27),np.zeros(27)])
        np.testing.assert_allclose(a.arm_means(source,(14,18))[0],14/32)
    def test_wrong_inference_shapes_rejected(self):
        with self.assertRaises(ValueError):
            a.arm_means(np.zeros((3,27)))
        with self.assertRaises(ValueError):
            a.benefits(np.zeros((2,4)))
        with self.assertRaises(ValueError):
            a.physical(np.zeros(18))

if __name__=='__main__':
    unittest.main()
