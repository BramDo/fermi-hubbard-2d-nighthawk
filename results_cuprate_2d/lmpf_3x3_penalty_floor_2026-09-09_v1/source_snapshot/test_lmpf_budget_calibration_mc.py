"""Finite calibration mixture, independently checked on a two-outcome example."""
import unittest
import numpy as np
from lmpf_2d.budget_calibration_mc import mixture
from lmpf_2d.verify_balanced_budget import oracle
class CalibrationMixtureTests(unittest.TestCase):
    def test_discrete_total_covariance(self):
        e=np.array([[[.01,.03],[.02,.04]],[[.06,.02],[.01,.07]]])
        e=np.repeat(e,2,axis=0)
        m=np.array([[0,1],[1,0],[1,1]]);g=np.tile(np.eye(4),(3,1,1))
        q=np.array([[.1,.2,.3,.4],[.2,.3,.1,.4],[.3,.1,.4,.2]])
        got=mixture(64,e,m,g,g,q);expected=[oracle(64,x,m,g,q) for x in e]
        means=np.array([x[0] for x in expected]);shot=np.mean([x[1] for x in expected],axis=0)
        np.testing.assert_allclose(got['means'],means,atol=1e-12)
        np.testing.assert_allclose(got['total_covariance'],shot+np.cov(means,rowvar=False,ddof=1),atol=1e-12)
    def test_constant_calibration_reduces_to_conditional(self):
        e=np.tile([[[.01,.03],[.02,.04]]],(4,1,1));m=np.zeros((3,2),dtype=int)
        g=np.tile(np.eye(4),(3,1,1));q=np.full((3,4),.25)
        got=mixture(64,e,m,g,g,q);want=oracle(64,e[0],m,g,q)[1]
        np.testing.assert_allclose(got['calibration_mean_covariance'],0,atol=1e-15)
        np.testing.assert_allclose(got['total_covariance'],want,atol=1e-12)
if __name__=='__main__':unittest.main()
