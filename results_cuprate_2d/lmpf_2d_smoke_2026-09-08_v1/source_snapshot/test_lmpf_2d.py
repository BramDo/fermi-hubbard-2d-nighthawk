"""Independent dense-channel checks and small-loop TN tests; no cloud calls."""
import itertools,unittest
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import DensityMatrix,Pauli,Statevector
from qiskit_aer.noise import depolarizing_error
from threadpoolctl import threadpool_limits
from lmpf_2d.fit import fit_coefficients,richardson_weights,linear_zne_weights,estimate
from lmpf_2d.operators import (compile_steps,evolve_dense,evolve_tn,dense_tn,
    overlap,initial_functional,expectation_tn,product_operator_tn)

def circuit():
    qc=QuantumCircuit(4)
    qc.h(0);qc.ry(.31,1);qc.rx(.17,2);qc.cx(0,1);qc.cz(1,3)
    qc.ry(.43,3);qc.cx(3,2);qc.cz(2,0);qc.rx(.23,1)
    return qc

def operator_matrix(vec):
    n=vec.ndim;out=np.zeros((2**n,2**n),complex)
    for index in itertools.product(range(4),repeat=n):
        if abs(vec[index])>1e-15:
            label=''.join('IXYZ'[i] for i in reversed(index))
            out+=vec[index]*Pauli(label).to_matrix()
    return out

class SolverTests(unittest.TestCase):
    def test_projection_not_value_fit(self):
        v=np.array([[1.,0],[.8,0],[.6,0],[.4,0]])
        fit=fit_coefficients(v@v.T)
        self.assertAlmostEqual(sum(fit.coefficients),1)
        self.assertAlmostEqual(np.asarray(fit.coefficients)@v[1:,0],1)
        self.assertLess(abs(fit.projection_residual),1e-10)
    def test_noiseless_minimum_norm(self):
        fit=fit_coefficients(np.ones((4,4)))
        np.testing.assert_allclose(fit.coefficients,[1/3]*3)
    def test_calibration_constraint(self):
        fit=fit_coefficients(np.eye(4),coefficient_sum=1.7)
        self.assertAlmostEqual(sum(fit.coefficients),1.7)
    def test_reject_bad_gram(self):
        with self.assertRaises(ValueError):fit_coefficients(np.array([[1,2,0],[2,1,0],[0,0,1]]))
    def test_zne_weights(self):
        np.testing.assert_allclose(richardson_weights([1,2,3]),[3,-3,1])
        np.testing.assert_allclose(linear_zne_weights([1,2,3]),[4/3,1/3,-2/3])
    def test_covariance(self):
        self.assertAlmostEqual(estimate([2,-1],[.2,.3],np.diag([.01,.04]))['shot_standard_error'],np.sqrt(.08))

class ChannelTests(unittest.TestCase):
    def test_dense_adjoint_matches_density_channel(self):
        qc=circuit();rate=lambda name,qs:.017*len(qs);steps=compile_steps(qc,rate)
        rng=np.random.default_rng(81);psi=rng.normal(size=16)+1j*rng.normal(size=16);psi/=np.linalg.norm(psi)
        rho0=DensityMatrix(psi);rho=rho0
        gamma=2.1
        for item,step in zip(qc.data,steps):
            rho=rho.evolve(item.operation,qargs=list(step.qubits))
            rho=rho.evolve(depolarizing_error(1-np.exp(-gamma*step.lindblad_decay_rate),len(step.qubits)),qargs=list(step.qubits))
        target=Pauli('ZIZI').to_matrix()
        expected=np.trace(rho.data@target).real
        adj=operator_matrix(evolve_dense(4,{1:'Z',3:'Z'},steps,gamma))
        self.assertLess(abs(np.trace(rho0.data@adj).real-expected),1e-11)
    def test_dense_unitary_and_bit_order(self):
        qc=QuantumCircuit(3);qc.h(2);qc.cx(2,0);qc.ry(.3,1);qc.cx(0,1)
        vec=evolve_dense(3,{1:'Z'},compile_steps(qc,lambda name,qs:0),0)
        for bits in itertools.product([0,1],repeat=3):
            sv=Statevector.from_label(''.join(map(str,reversed(bits)))).evolve(qc)
            value=np.sum(vec*initial_functional(bits))
            self.assertAlmostEqual(value,sv.expectation_value(Pauli('IZI')).real,places=11)

class TensorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.edges=[(0,1),(1,3),(3,2),(2,0)]
        cls.steps=compile_steps(circuit(),lambda name,qs:.01*len(qs))
    def test_product_operator(self):
        tn=product_operator_tn(4,self.edges,{1:'Z'})
        expected=np.zeros((4,)*4);expected[0,3,0,0]=1
        np.testing.assert_allclose(dense_tn(tn),expected)
    def test_full_bond_tn_matches_dense(self):
        tn,_=evolve_tn(4,self.edges,{1:'Z'},self.steps,1,chi=16)
        expected=evolve_dense(4,{1:'Z'},self.steps,1)
        np.testing.assert_allclose(dense_tn(tn),expected,atol=2e-8)
        self.assertAlmostEqual(expectation_tn(tn,[1,0,1,0]),np.sum(expected*initial_functional([1,0,1,0])),places=8)
    def test_loop_correction_matches_complete_small_loop(self):
        a,_=evolve_tn(4,self.edges,{1:'Z'},self.steps,1,chi=4)
        b,_=evolve_tn(4,self.edges,{1:'Z'},self.steps,2,chi=4)
        exact,_=overlap(a,b,exact=True)
        corrected,info=overlap(a,b,loop_size=4)
        self.assertLess(abs(exact-corrected),2e-8)
    def test_nonlocal_gate_rejected(self):
        with self.assertRaises(ValueError):evolve_tn(4,[(0,1),(1,2)],{0:'Z'},self.steps,1,chi=2)

if __name__=='__main__':
    with threadpool_limits(limits=1):unittest.main(verbosity=2)
