import unittest
import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
from qiskit.quantum_info import Operator,Statevector
from compact_symbolic_tflo import compact_constants,cancel_diagonal_cz_pairs,optimize,verify_constant_cleanup
from compile_tflo_dd6_blocks import compile_blocks
from cuprate_2d_tflo import parameterized_network,bind,skeleton,explicit_twirl
from cuprate_2d_hubbard_pipeline import Cuprate2DConfig

class Tests(unittest.TestCase):
    def test_constant_full_operator_and_symbolic_anchors(self):
        p=Parameter('p'); c=QuantumCircuit(2)
        c.x(0); c.sx(0); c.rz(.2,0); c.sx(0); c.rz(p,0); c.cz(0,1)
        c.rz(.3,1); c.rz(.4,1); c.x(1); c.x(1); c.global_phase=.7+p/5
        d,_=compact_constants(c)
        for value in (0.,.31,-.7):
            np.testing.assert_allclose(Operator(c.assign_parameters({p:value})).data,Operator(d.assign_parameters({p:value})).data,atol=1e-11,rtol=0)
    def test_CZ_cancels_only_through_diagonal_endpoints(self):
        p=Parameter('p'); c=QuantumCircuit(3)
        c.cz(0,1); c.rz(p,0); c.cz(1,2); c.x(2); c.cz(0,1)
        d,check=cancel_diagonal_cz_pairs(c)
        self.assertEqual(check['CZ_removed'],2)
        np.testing.assert_allclose(Operator(c.assign_parameters({p:.4})).data,Operator(d.assign_parameters({p:.4})).data,atol=1e-12)
        bad=QuantumCircuit(2); bad.cz(0,1); bad.sx(0); bad.cz(0,1)
        _,check=cancel_diagonal_cz_pairs(bad); self.assertEqual(check['CZ_removed'],0)
    def test_wrong_anchor_and_gate_rejected(self):
        p=Parameter('p'); c=QuantumCircuit(2); c.rz(p,0); c.cz(0,1)
        d=c.copy(); d.x(0)
        with self.assertRaises(AssertionError): verify_constant_cleanup(c,d)
        d=QuantumCircuit(2); d.rz(2*p,0); d.cz(0,1)
        with self.assertRaises(AssertionError): verify_constant_cleanup(c,d)
    def test_measurement_mapping_preserved(self):
        c=QuantumCircuit(2,2); c.x(0); c.x(0); c.measure(0,1); c.measure(1,0)
        d,_=compact_constants(c)
        self.assertEqual([(d.find_bit(i.qubits[0]).index,d.find_bit(i.clbits[0]).index) for i in d.data if i.operation.name=='measure'],[(0,1),(1,0)])
    def test_full_small_network_family(self):
        cfg=Cuprate2DConfig(lx=2,ly=2,holes=0,steps=2,dt=.2)
        original=parameterized_network(cfg); native,_=compile_blocks(original)
        reduced,_=optimize(native)
        rng=np.random.default_rng(20260907); vector=rng.normal(size=256)+1j*rng.normal(size=256); vector/=np.linalg.norm(vector)
        shape=skeleton(reduced)
        for T,U in ((0.,0.),(.04,0.),(.2,0.),(.4,8.),(.37,3.1),(.48,0.)):
            a=bind(original,cfg,T,U); b=bind(reduced,cfg,T,U)
            np.testing.assert_allclose(Statevector(vector).evolve(a).data,Statevector(vector).evolve(b).data,atol=1e-10,rtol=0)
            self.assertEqual(skeleton(b),shape)
        # Dense full operator check, not only one initial/random state.
        np.testing.assert_allclose(Operator(bind(original,cfg,.4,8.)).data,Operator(bind(reduced,cfg,.4,8.)).data,atol=1e-10,rtol=0)
    def test_twirl_cleanup_preserves_family(self):
        p=Parameter('p'); c=QuantumCircuit(2); c.sx(0); c.rz(p,0); c.cz(0,1); c.sx(1)
        t,mask=explicit_twirl(c,42); d,_=compact_constants(t)
        self.assertEqual(d.metadata['readout_mask_little_endian'],mask.tolist())
        for value in (0.,.4):
            np.testing.assert_allclose(Operator(t.assign_parameters({p:value})).data,Operator(d.assign_parameters({p:value})).data,atol=1e-11,rtol=0)

if __name__=='__main__': unittest.main()
