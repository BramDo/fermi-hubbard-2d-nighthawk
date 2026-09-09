"""Analytic covariance, KKT, timing and unit checks for offline budgets."""
import unittest
import numpy as np
from qiskit import QuantumCircuit
from lmpf_2d.balanced_budget import (seconds,critical_path,exposure,covariance_from_scores,
    estimator_scores,jacobian)
from lmpf_2d.verify_balanced_budget import oracle,complex_jacobian
class BudgetTests(unittest.TestCase):
    def test_duration_units_and_invalid(self):
        self.assertAlmostEqual(seconds(40,'ns'),40e-9)
        self.assertAlmostEqual(seconds(2,'us'),2e-6)
        with self.assertRaises(ValueError):seconds(-1,'s')
        with self.assertRaises(ValueError):seconds(1,'dt')
    def test_parallel_critical_path(self):
        qc=QuantumCircuit(2,2);qc.x(0);qc.x(1);qc.cz(0,1);qc.measure([0,1],[0,1])
        durations={('x',(0,)):40e-9,('x',(1,)):40e-9,('cz',(0,1)):100e-9,
                   ('measure',(0,)):20e-9,('measure',(1,)):20e-9}
        self.assertAlmostEqual(critical_path(qc,durations),160e-9)
    def test_matched_exposure(self):
        for n in (64,128,256,512):
            sizes,total=exposure(n)
            self.assertEqual(sizes.sum(),5*n);self.assertEqual(total,5*n+512)
        with self.assertRaises(ValueError):exposure(100)
    def test_constant_scores_zero_covariance(self):
        np.testing.assert_allclose(covariance_from_scores(np.ones((1,4,2)),np.array([[.25]*4]),[10]),0,atol=1e-15)
    def test_shared_average_difference_variance(self):
        x=np.array([0.,1.]);scores=np.array([np.column_stack([x,x/3]),np.column_stack([x*0,2*x/3])])
        cov=covariance_from_scores(scores,np.full((2,2),.5),[10,20])
        self.assertAlmostEqual(cov[0,0],.25/10)
        self.assertAlmostEqual(cov[1,1],.25/30)
        self.assertAlmostEqual(cov[0,0]+cov[1,1]-2*cov[0,1],.25*(1/10-1/30))
    def test_fixed_weight_square_root_scaling(self):
        scores=np.array([[[0.,1.],[1.,2.],[2.,0.],[3.,-1.]]]);q=np.array([[.1,.2,.3,.4]])
        a=covariance_from_scores(scores,q,[64]);b=covariance_from_scores(scores,q,[256])
        np.testing.assert_allclose(a,4*b,atol=1e-15)
    def test_kkt_and_independent_calibration_derivative(self):
        e=np.array([[.02,.03],[.01,.04]]);m=np.array([[0,1],[1,0],[1,1]])
        grams=np.tile(np.eye(4),(3,1,1));q=np.array([[.1,.2,.3,.4],[.2,.3,.1,.4],[.3,.1,.4,.2]])
        scores,w,p=estimator_scores(64,e,m,grams);result=oracle(64,e,m,grams,q)
        np.testing.assert_allclose(w,1/3,atol=1e-12)
        np.testing.assert_allclose(w,result[2],atol=1e-12)
        np.testing.assert_allclose(p,result[3],atol=1e-12)
        np.testing.assert_allclose(jacobian(64,e,m,grams,q,1e-5),complex_jacobian(64,e,m,grams,q),atol=1e-8,rtol=0)
if __name__=='__main__':unittest.main()
