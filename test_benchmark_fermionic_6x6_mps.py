from dataclasses import replace
import unittest
import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import XXPlusYYGate
from qiskit.quantum_info import Operator,Statevector
import benchmark_fermionic_6x6_mps as b
from cuprate_2d_tflo import parameterized_network,bind,pauli_samples

class BenchmarkTests(unittest.TestCase):
    def test_fused_matrix_against_qiskit(self):
        for c in [0.,-1.,.25]:
            for u in [0.,8.]:
                qc=QuantumCircuit(2); qc.append(XXPlusYYGate(np.pi+c*.2),[0,1])
                qc.p(np.pi/2,0); qc.p(np.pi/2,1); qc.cp(-u*.2/2,0,1)
                np.testing.assert_allclose(b.fused_gate(c,u,.2),Operator(qc).data,atol=1e-14)

    def test_unitary(self):
        for c in [0.,-1.,.25]:
            for u in [0.,8.]:
                g=b.fused_gate(c,u,.2)
                np.testing.assert_allclose(g.conj().T@g,np.eye(4),atol=1e-14)

    def test_fermionic_sign_and_involution(self):
        f=b.fused_gate(0.,0.,.2)
        expected=np.array([[1,0,0,0],[0,0,1,0],[0,1,0,0],[0,0,0,-1]])
        np.testing.assert_allclose(f,expected,atol=1e-14)
        np.testing.assert_allclose(f@f,np.eye(4),atol=1e-14)

    def test_exact2x2_full_state_and_observables(self):
        cfg=b.cfg_for(2)
        qc=bind(parameterized_network(cfg),cfg,.4,8.)
        exact=Statevector(qc).data
        psi,res=b.evolve(cfg,16,cutoff=0,verify_norm=True)
        # Quimb first physical index is MSB; Qiskit q0 is LSB.
        dense=np.asarray(psi.to_dense()).reshape([2]*8).transpose(list(reversed(range(8)))).ravel()
        phase=np.vdot(exact,dense); aligned=dense*np.exp(-1j*np.angle(phase))
        np.testing.assert_allclose(aligned,exact,atol=2e-12)
        indices=np.arange(256,dtype=np.uint16)
        bits=((indices[:,None]>>np.arange(8))&1).astype(int)
        moments=np.abs(exact)**2@pauli_samples(bits)
        np.testing.assert_allclose(res['moments'],moments,atol=2e-12)
        self.assertAlmostEqual(res['number_expectation'],4,10)
        self.assertAlmostEqual(res['log_retained_norm'],0,10)

    def test_zeroU_polynomial_FLO_reference(self):
        cfg=replace(b.cfg_for(2),u_over_t=0.)
        _,res=b.evolve(cfg,16,cutoff=0)
        exact,_=b.flo_reference(cfg,.4)
        np.testing.assert_allclose(res['moments'],exact,atol=2e-12)

    def test_sizes_target_and_update_count(self):
        cfg=b.cfg_for(6)
        self.assertEqual(cfg.electrons,32); self.assertEqual(cfg.qubits,72)
        self.assertEqual(cfg.total_time,.4)
        self.assertEqual(sum(len(x) for x in b.fused_layers(cfg)),10224)
        self.assertEqual(len(b.fused_layers(cfg)),288)

    def test_mu_rejected(self):
        with self.assertRaises(ValueError): b.fused_layers(replace(b.cfg_for(2),chemical_potential=.1))

    def test_deadline_before_work(self):
        with self.assertRaises(TimeoutError): b.evolve(b.cfg_for(2),16,deadline=0)

if __name__=='__main__': unittest.main()
