"""Identity, scaling, shared samples and independent floor tests."""
import unittest
import numpy as np
from scipy.linalg import block_diag
from lmpf_2d.penalty_floor import effective_denominator,local_probabilities,joint_forecast
from lmpf_2d.verify_balanced_budget import oracle
class PenaltyFloorTests(unittest.TestCase):
    def fixture(self):
        e=np.array([[[.01,.03],[.02,.04]],[[.06,.02],[.01,.07]]]);e=np.repeat(e,2,axis=0)
        masks=np.array([[0,1],[1,0],[1,1]])
        base=np.array([[1,0,0,0],[.5,.5,0,0],[.25,0,.5,0],[.1,0,0,.5]])
        grams=np.tile(base@base.T,(3,1,1));q=np.array([[.1,.2,.3,.4],[.2,.3,.1,.4],[.3,.1,.4,.2]])
        return e,masks,grams,q
    def test_denominator_policy(self):
        self.assertEqual(effective_denominator(512,64),64)
        self.assertEqual(effective_denominator(64,128),64)
        with self.assertRaises(ValueError):effective_denominator(256,0)
    def test_equal_weights_recover_original_and_zero_difference(self):
        e,m,g,q=self.fixture();reference=[oracle(64,x,m,g,q) for x in e];w=np.array([x[2] for x in reference])
        got=joint_forecast(64,e,m,q,w,w)
        want=np.mean([x[1] for x in reference],axis=0)+np.cov(np.array([x[0] for x in reference]),rowvar=False,ddof=1)
        np.testing.assert_allclose(got['total_covariance'][:12,:12],want,atol=1e-12)
        c=np.zeros((3,15));c[:,9:12]=np.eye(3);c[:,12:15]=-np.eye(3)
        np.testing.assert_allclose(c@got['total_covariance']@c.T,0,atol=1e-12)
    def test_fixed_floor_conditional_scaling(self):
        e,m,g,q=self.fixture();w=np.array([oracle(64,x,m,g,q)[2] for x in e])
        a=joint_forecast(64,e,m,q,w,w);b=joint_forecast(256,e,m,q,w,w)
        np.testing.assert_array_equal(a['means'],b['means'])
        np.testing.assert_allclose(a['conditional_average_covariance'],4*b['conditional_average_covariance'],atol=1e-12)
        np.testing.assert_array_equal(a['calibration_mean_covariance'],b['calibration_mean_covariance'])
    def test_independent_actual_shot_covariance(self):
        e,m,g,q=self.fixture();old=[oracle(256,x,m,g,q) for x in e];floor=[oracle(64,x,m,g,q) for x in e]
        got=joint_forecast(256,e,m,q,np.array([x[2] for x in old]),np.array([x[2] for x in floor]))
        expected=[];means=[]
        fcov=block_diag(*[(np.diag(p)-np.outer(p,p))/n for p,n in zip(q[[0,0,1,2]],(256,512,256,256))])
        for a,b in zip(old,floor):
            transfer=np.vstack([a[4],b[4][9:12]])
            expected.append(transfer@fcov@transfer.T);means.append(np.r_[a[0],b[0][9:12]])
        np.testing.assert_allclose(got['total_covariance'],np.mean(expected,axis=0)+np.cov(means,rowvar=False,ddof=1),atol=1e-12)
    def test_probability_normalization_without_clipping(self):
        values=np.array([[.4,-.2,.02],[.3,-.4,-.01]])
        p=local_probabilities(values)
        np.testing.assert_allclose(p.sum(1),1,atol=1e-15)
        self.assertLess(p[1].min(),0)
        with self.assertRaises(ValueError):local_probabilities([0,0])
    def test_invalid_weight_shape_rejected(self):
        e,m,g,q=self.fixture()
        with self.assertRaises(ValueError):joint_forecast(256,e,m,q,np.zeros((4,3,2)),np.zeros((4,3,3)))
if __name__=='__main__':unittest.main()
