import unittest
import numpy as np
from qiskit import QuantumCircuit
from lmpf_2d.canonical_chain import evolve_canonical
from lmpf_2d.operators import compile_steps,fuse_steps,evolve_dense,dense_tn
from lmpf_2d.product import evolve_products,dense_product

class CanonicalTests(unittest.TestCase):
    def test_full_bond_and_product_limit(self):
        qc=QuantumCircuit(4)
        for a,b in ((0,1),(1,2),(2,3),(1,2),(0,1)):
            qc.ry(.28,a);qc.rxx(.31,a,b);qc.rz(.53,b)
        steps=fuse_steps(compile_steps(qc,lambda *_:.017));support={0:'Z',2:'X'}
        for scale in (0.,1.):
            full=evolve_canonical(4,support,steps,scale,16)
            np.testing.assert_allclose(dense_tn(full),evolve_dense(4,support,steps,scale),atol=1e-10)
            product=evolve_canonical(4,support,steps,scale,1)
            expected=evolve_products(4,[support],steps,scale)
            np.testing.assert_allclose(dense_tn(product),dense_product(expected,0),atol=1e-10)
    def test_nonlocal_rejected(self):
        qc=QuantumCircuit(3);qc.cx(0,2)
        with self.assertRaises(ValueError):evolve_canonical(3,{0:'Z'},compile_steps(qc,lambda *_:0),0.,2)

if __name__=='__main__':unittest.main(verbosity=2)
