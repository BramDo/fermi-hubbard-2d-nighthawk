"""Matched estimator budgets, correlations and no-clipping regression tests."""
import unittest
import numpy as np
from lmpf_2d.twirl1_hardware import baseline_batch,combine,METHODS
from lmpf_2d.verify_single_twirl import inverse_means
from lmpf_2d.verify_shot_aware import independent_paulis
from lmpf_2d.single_twirl import pair_probabilities

class TestTwirl1Hardware(unittest.TestCase):
    def inputs(self):
        counts=np.array([[[2,16,6,19],[1,2,7,11],[0,3,2,2],[5,2,4,3]]])
        errors=np.array([[[.01,.07],[.03,.04]]])
        masks=np.array([[0,1],[0,1],[1,0],[1,1]])
        weights=np.array([[1.8,-.1,-.7],[1.6,-.1,-.5],[1.9,-.2,-.7]])
        return counts,errors,masks,weights

    def test_baselines_match_independent_assignment_inverse(self):
        c,e,m,w=self.inputs()
        np.testing.assert_allclose(baseline_batch(c,e,m),inverse_means(c,e,m,w)[:,:3],atol=1e-14)
        self.assertEqual(METHODS,['raw64','readout64','zne_matched','lmpf_shot_aware'])

    def test_calibration_dependent_weights_and_static_equivalence(self):
        c,e,m,w=self.inputs();c=np.repeat(c,2,axis=0);e=np.repeat(e,2,axis=0)
        wb=np.stack([w,w+np.array([[.1,-.1,0],[.1,0,-.1],[0,.1,-.1]])])
        np.testing.assert_allclose(combine(c,e,m,wb)[:,3],independent_paulis(c,e,m,wb),atol=1e-14)
        np.testing.assert_array_equal(combine(c,e,m,w),combine(c,e,m,np.broadcast_to(w,(2,3,3))))

    def test_budget_and_mask_mismatch_rejected(self):
        c,e,m,w=self.inputs()
        bad=c.copy();bad[0,2,0]+=1
        with self.assertRaises(ValueError):combine(bad,e,m,w)
        bad=m.copy();bad[1,0]=1-bad[1,0]
        with self.assertRaises(ValueError):combine(c,e,bad,w)
        with self.assertRaises(ValueError):combine(c,np.full((1,2,2),.49),m,w)

    def test_unphysical_estimates_not_clipped(self):
        c,e,m,w=self.inputs()
        c=np.array([[[43,0,0,0],[21,0,0,0],[0,7,0,0],[0,0,0,14]]])
        m=np.zeros((4,2),int);w=np.tile([3.,0.,-2.],(3,1))
        p=combine(c,np.zeros((1,2,2)),m,w)[0,3]
        self.assertGreater(abs(p).max(),1.)
        self.assertLess(pair_probabilities(p).min(),0.)

if __name__=='__main__':unittest.main()
