"""Joint-ZZ, two-mode readout and explicit chi256 resource guard checks."""
import unittest
from unittest.mock import patch
import numpy as np
from qiskit import QuantumCircuit
from lmpf_2d.twirl1_zz import zz_penalty,guarded_overlap,OBSERVABLE,SUPPORT,CHI_LEVELS
from lmpf_2d.verify_twirl1_zz import assignment_zz_penalty
from lmpf_2d.archive_3x3 import record_sign
from lmpf_2d.canonical_chain import evolve_canonical
from lmpf_2d.operators import compile_steps,evolve_dense,dense_tn

class TestTwirl1ZZ(unittest.TestCase):
    def test_joint_support_and_mask(self):
        self.assertEqual((OBSERVABLE,SUPPORT,CHI_LEVELS),(22,{8:'Z',9:'Z'},(128,256)))
        for x in (0,1):
            for y in (0,1):
                mask=np.zeros(18,int);mask[8]=x;mask[9]=y
                self.assertEqual(record_sign(mask)[OBSERVABLE],(-1)**(x+y))

    def test_product_penalty_matches_assignment_with_asymmetric_errors(self):
        e=np.array([[.01,.07],[.03,.04]])
        for m in (np.zeros((4,2),int),np.ones((4,2),int),
                  np.array([[0,1],[0,1],[1,0],[1,1]])):
            np.testing.assert_allclose(zz_penalty(e,m)[0,0],
                                       assignment_zz_penalty(e,m),atol=2e-15)
        base=zz_penalty(e,np.zeros((4,2),int))
        for q in (0,1):
            changed=e.copy();changed[0,q]+=.1
            self.assertGreater(float(np.max(abs(zz_penalty(changed,np.zeros((4,2),int))-base))),.01)

    def test_zero_readout_limit_and_invalid_inputs(self):
        np.testing.assert_allclose(zz_penalty(np.zeros((2,2)),np.zeros((4,2),int))[0,0],
                                   1/np.array([43,7,14]),atol=1e-15)
        for e in (np.zeros((1,2)),np.full((2,2),.49),np.full((2,2),np.nan)):
            with self.assertRaises(ValueError):zz_penalty(e,np.zeros((4,2),int))
        with self.assertRaises(ValueError):zz_penalty(np.zeros((2,2)),np.ones((4,2))*2)

    def test_explicit_guard_does_not_modify_historical_default(self):
        with patch('lmpf_2d.twirl1_zz.chain_overlap',return_value=(.5,{})) as call:
            self.assertEqual(guarded_overlap('left','right'),(.5,{}))
            call.assert_called_once_with('left','right',max_elements=2**22,max_flops=3e9)

    def test_joint_noisy_operator_not_product_of_single_operators(self):
        qc=QuantumCircuit(2);qc.cz(0,1)
        steps=compile_steps(qc,lambda name,qs:.2)
        z0=evolve_dense(2,{0:'Z'},steps,1.)[3,0]
        z1=evolve_dense(2,{1:'Z'},steps,1.)[0,3]
        joint=dense_tn(evolve_canonical(2,{0:'Z',1:'Z'},steps,1.,4))
        exact=evolve_dense(2,{0:'Z',1:'Z'},steps,1.)
        np.testing.assert_allclose(joint,exact,atol=1e-14)
        self.assertAlmostEqual(joint[3,3],np.exp(-.2),places=13)
        self.assertGreater(abs(joint[3,3]-z0*z1),.1)
        ideal=dense_tn(evolve_canonical(2,{0:'Z',1:'Z'},steps,0.,4))
        self.assertAlmostEqual(ideal[3,3],1.,places=13)

if __name__=='__main__':unittest.main()
