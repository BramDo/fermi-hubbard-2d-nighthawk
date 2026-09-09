"""Tests for the predeclared fresh floor64 hardware analysis."""
import unittest
import numpy as np
from lmpf_2d.analyze_floor_hardware import combine,fit_pair,estimates
from lmpf_2d.verify_floor_hardware_analysis import inverse_estimates
class FloorAnalysisTests(unittest.TestCase):
    def fixture(self):
        c=np.array([[[128,128,128,128],[256,256,256,256],[100,150,200,62],[60,180,120,152]]])
        e=np.array([[[.01,.02],[.03,.04]]]);m=np.array([[1,1],[1,0],[0,1]])
        a=np.array([[1,0,0,0],[.5,.5,0,0],[.25,0,.5,0],[.1,0,0,.5]])
        g=np.tile(a@a.T,(3,1,1));return c,e,m,g
    def test_independent_inverse_and_kkt(self):
        c,e,m,g=self.fixture();w=fit_pair(e,m,g,g);got=estimates(c,e,m,w);want,kw=inverse_estimates(c,e,m,g,g)
        np.testing.assert_allclose(got,want,atol=1e-12)
        for key in w:np.testing.assert_allclose(w[key],kw[key],atol=1e-12)
    def test_floor_penalty_is_eight_times_original(self):
        c,e,m,g=self.fixture();w=fit_pair(e,m,g,g)
        np.testing.assert_allclose(w['floor_penalties'],8*w['original_penalties'],atol=1e-14)
        np.testing.assert_allclose(w['floor'].sum(-1),1,atol=1e-12)
    def test_sixteen_pub_strata_keep_exposure(self):
        roles=['shared_factor1','factor2','baseline_only_factor1','factor3']*4
        rows=np.array([[128,0,0,0] if r!='baseline_only_factor1' else [256,0,0,0] for r in roles])[None]
        got=combine(rows,roles);np.testing.assert_array_equal(got.sum(2),[[512,1024,512,512]])
    def test_partial_or_wrong_roles_rejected(self):
        roles=['shared_factor1','factor2','baseline_only_factor1','factor3']*4
        with self.assertRaises(ValueError):combine(np.zeros((1,16,4)),roles)
        with self.assertRaises(ValueError):combine(np.zeros((1,16,4)),['unknown']*16)
    def test_calibration_broadcast_preserves_point(self):
        c,e,m,g=self.fixture();w=fit_pair(e,m,g,g)
        one=estimates(c,e,m,w);many=estimates(np.repeat(c,3,axis=0),e,m,w)
        np.testing.assert_allclose(many,np.repeat(one,3,axis=0),atol=1e-12)
if __name__=='__main__':unittest.main()
