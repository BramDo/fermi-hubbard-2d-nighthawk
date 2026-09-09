"""Arm counts, functional normalization and independent inverse checks."""
import unittest
import numpy as np
import quimb.tensor as qtn
from lmpf_2d.twirl1_noise_check import merge_strata,arm_means,outside_marginal
from lmpf_2d.chain_contract import chain_expectation_zero
from lmpf_2d.tn_storage import expectation_zero
from lmpf_2d.verify_single_twirl import inverse_means

class TestTwirl1NoiseCheck(unittest.TestCase):
    def inputs(self):
        counts=np.array([[[2,16,6,19],[1,2,7,11],[0,3,2,2],[5,2,4,3]]])
        e=np.array([[[.01,.07],[.03,.04]]])
        m=np.array([[0,1],[0,1],[1,0],[1,1]])
        return counts,e,m

    def test_full64_7_14_arms_and_independent_inverse(self):
        c,e,m=self.inputs();full=merge_strata(c)
        np.testing.assert_array_equal(full.sum(2),[[64,7,14]])
        got=arm_means(full,e,m[[0,2,3]])
        baseline=inverse_means(c,e,m,np.eye(3))[:,1]
        np.testing.assert_allclose(got[:,0],baseline,atol=1e-14)
        for a in (1,2):
            selected=inverse_means(c,e,m,np.tile(np.eye(3)[a],(3,1)))[:,3]
            np.testing.assert_allclose(got[:,a],selected,atol=1e-14)

    def test_unchanged_functional_scale_not_unit_norm_rescaling(self):
        tn=qtn.MPS_product_state([np.array([0.,0.,0.,.5]),np.array([1.,0.,0.,0.])])
        tn.exponent=.2
        self.assertAlmostEqual(chain_expectation_zero(tn),.5*10**.2,places=13)
        self.assertAlmostEqual(chain_expectation_zero(tn),expectation_zero(tn),places=13)
        x=qtn.MPS_product_state([np.array([0.,1.,0.,0.])]*2)
        self.assertAlmostEqual(chain_expectation_zero(x),0.,places=13)

    def test_invalid_exposure_or_readout_rejected(self):
        c,e,m=self.inputs();bad=c.copy();bad[0,0,0]+=1
        with self.assertRaises(ValueError):merge_strata(bad)
        full=merge_strata(c);full[0,1,0]+=1
        with self.assertRaises(ValueError):arm_means(full,e,m[[0,2,3]])
        with self.assertRaises(ValueError):arm_means(merge_strata(c),np.full((1,2,2),.49),m[[0,2,3]])

    def test_marginal_flag_keeps_boundary_inside(self):
        intervals=np.array([[-1.,-.2],[1.,.2]])
        np.testing.assert_array_equal(outside_marginal(intervals,[1.,.3]),[False,True])
        with self.assertRaises(ValueError):outside_marginal(intervals,[0.,0.,0.])

if __name__=='__main__':unittest.main()
