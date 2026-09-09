import unittest
import numpy as np
from qiskit import QuantumCircuit
from lmpf_2d.operators import compile_steps,fuse_steps,evolve_dense,dense_tn,product_operator_tn
from lmpf_2d.canonical_chain import evolve_canonical
from lmpf_2d.chain_contract import chain_overlap,chain_expectation_zero,chain_arrays
from lmpf_2d.tn_storage import bounded_contract

class ChainContractTests(unittest.TestCase):
    def test_against_dense_and_unsimplified_tn(self):
        qc=QuantumCircuit(4)
        for a,b in ((0,1),(1,2),(2,3),(1,2),(0,1)):
            qc.ry(.32,a);qc.cx(a,b);qc.rxx(.23,a,b);qc.rz(.11,b)
        steps=fuse_steps(compile_steps(qc,lambda *_:.009))
        left=evolve_canonical(4,{0:'Z',2:'Y'},steps,0.,16)
        right=evolve_canonical(4,{0:'Z',2:'Y'},steps,1.,4)
        dl=dense_tn(left);dr=dense_tn(right)
        np.testing.assert_allclose(dl,evolve_dense(4,{0:'Z',2:'Y'},steps,0.),atol=1e-10)
        expected=float(np.vdot(dl,dr).real)
        self.assertAlmostEqual(chain_overlap(left,right)[0],expected,places=11)
        self.assertAlmostEqual(bounded_contract(left.H & right)[0],expected,places=11)
        functional=np.array(1.)
        for _ in range(4):functional=np.multiply.outer(functional,[1.,0.,0.,1.])
        self.assertAlmostEqual(chain_expectation_zero(right),float(np.sum(dr*functional)),places=11)
        left.equalize_norms_(value=2.)
        self.assertAlmostEqual(chain_overlap(left,right)[0],expected,places=11)
        with self.assertRaises(ValueError):chain_overlap(left,right,max_elements=0)
    def test_rejects_loop_and_preserves_mixed_bonds(self):
        loop=product_operator_tn(4,[(0,1),(1,2),(2,3),(3,0)],{0:'Z'})
        with self.assertRaises(ValueError):chain_arrays(loop)
        a=product_operator_tn(4,[(0,1),(1,2),(2,3)],{0:'Z'})
        b=product_operator_tn(4,[(0,1),(1,2),(2,3)],{1:'Z'})
        self.assertEqual(chain_overlap(a,b)[0],0.)
        self.assertEqual(chain_overlap(a,a)[0],1.)

if __name__=='__main__':unittest.main(verbosity=2)
