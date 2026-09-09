import unittest
import numpy as np
from qiskit import QuantumCircuit
from lmpf_2d.product import evolve_products,overlaps,gram_mixtures,expectations,dense_product
from lmpf_2d.operators import compile_steps,fuse_steps,evolve_dense,evolve_tn,dense_tn

class ProductTests(unittest.TestCase):
    def test_identity(self):
        p=evolve_products(18,[{0:'Z'},{2:'Z',3:'Z'}],[])
        np.testing.assert_allclose(overlaps(p,p),[1,1]);np.testing.assert_allclose(expectations(p,[0]*18),[1,1])
    def test_clifford_no_truncation(self):
        qc=QuantumCircuit(4);qc.h(0);qc.cx(0,1);qc.s(2);qc.swap(1,2);qc.cz(2,3)
        steps=compile_steps(qc,lambda *_:.003)
        supports=[{0:'Z'},{1:'Y',3:'X'},{0:'X',2:'Z'}]
        for scale in (0.,1.,3.):
            p=evolve_products(4,supports,steps,scale)
            for i,support in enumerate(supports):np.testing.assert_allclose(dense_product(p,i),evolve_dense(4,support,steps,scale),atol=1e-12)
            self.assertLess(p.truncation_bound.max(),1e-12)
    def test_quimb_chi_one(self):
        qc=QuantumCircuit(4)
        for a,b in [(0,1),(1,3),(3,2),(2,0)]:
            qc.ry(.213,a);qc.rx(.387,b);qc.cx(a,b);qc.rz(.092,a)
        steps=fuse_steps(compile_steps(qc,lambda *_:.002));edges=[(0,1),(1,3),(3,2),(2,0)]
        supports=[{0:'Z'},{0:'Z',1:'Z'}]
        for scale in (0.,1.):
            p=evolve_products(4,supports,steps,scale)
            for i,support in enumerate(supports):
                tn,info=evolve_tn(4,edges,support,steps,scale,chi=1)
                np.testing.assert_allclose(dense_product(p,i),dense_tn(tn),atol=1e-10)
                self.assertEqual(info['bp_nonconverged_updates'],0)
    def test_bound_and_mixture(self):
        qc=QuantumCircuit(3);qc.ry(.43,0);qc.rxx(.34,0,1);qc.ry(.77,1);qc.rzz(.64,1,2)
        steps=compile_steps(qc,lambda *_:.01);supports=[{0:'Z'},{1:'X'}]
        a=evolve_products(3,supports,steps,0);b=evolve_products(3,supports,steps,1)
        for i,support in enumerate(supports):
            error=np.linalg.norm(dense_product(b,i)-evolve_dense(3,support,steps,1))
            self.assertLessEqual(error,b.truncation_bound[i]+1e-10)
        f=gram_mixtures([[a],[a,b],[b]])
        for i in range(2):
            va=dense_product(a,i).ravel();vb=dense_product(b,i).ravel();vs=np.array([va,(va+vb)/2,vb])
            np.testing.assert_allclose(f[i],vs@vs.T,atol=1e-12)

if __name__=='__main__':unittest.main(verbosity=2)
