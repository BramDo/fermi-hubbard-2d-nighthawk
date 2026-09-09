"""Fail-closed structural reuse and independent determinant tests."""
import unittest
import numpy as np
from qiskit import QuantumCircuit
from lmpf_2d.twirl_reuse_check import signatures,per_wire_parts,compare,normalized_logdet
from lmpf_2d.verify_twirl_reuse import dense_logdet

class TestTwirlReuse(unittest.TestCase):
    def test_terminal_suffix_does_not_modify_core(self):
        a=QuantumCircuit(3);a.sx(0);a.cz(0,1);a.rz(.3,2)
        b=a.copy();b.x(0);b.x(1)
        self.assertTrue(compare(signatures(a),signatures(b),3)['internal_per_wire_equal'])
        self.assertFalse(compare(signatures(a),signatures(b),3)['exact_instruction_sequence_equal'])

    def test_disjoint_order_and_cz_qarg_order(self):
        a=QuantumCircuit(3);a.x(0);a.sx(2);a.cz(0,1)
        b=QuantumCircuit(3);b.sx(2);b.x(0);b.cz(1,0)
        self.assertTrue(compare(signatures(a),signatures(b),3)['internal_per_wire_equal'])

    def test_internal_gate_change_rejected(self):
        a=QuantumCircuit(2);a.x(0);a.cz(0,1)
        b=QuantumCircuit(2);b.sx(0);b.cz(0,1)
        self.assertEqual(compare(signatures(a),signatures(b),2)['internal_mismatch_wires'],[0])

    def test_dense_noncommuting_channel_and_unmask(self):
        q=QuantumCircuit(3);q.sx(0);q.cz(1,0);q.rz(.8,1);q.cz(1,2);q.x(2)
        rate=lambda name,qs: .021*(1+sum(qs)) if name!='rz' else 0.
        expected=normalized_logdet(signatures(q),rate)[0]
        for scale in (0.,.3,1.):
            for mask in (None,[1,1,0]):
                self.assertAlmostEqual(dense_logdet(q,rate,scale,mask),scale*expected,places=12)

    def test_equal_determinants_not_channel_equivalence(self):
        a=QuantumCircuit(1);a.x(0)
        b=QuantumCircuit(1);b.sx(0)
        rate=lambda name,qs:.01
        self.assertEqual(normalized_logdet(signatures(a),rate)[0],
                         normalized_logdet(signatures(b),rate)[0])
        self.assertNotEqual(signatures(a),signatures(b))

    def test_noise_and_unitary_limits(self):
        a=QuantumCircuit(2);a.x(0);a.cz(1,0)
        rows=signatures(a)
        self.assertEqual(normalized_logdet(rows,lambda name,qs:.4,0)[0],0.)
        self.assertEqual(normalized_logdet(rows,lambda name,qs:0.)[0],0.)
        for bad in (-1.,float('inf'),float('nan')):
            with self.assertRaises(ValueError):normalized_logdet(rows,lambda name,qs:bad)
            with self.assertRaises(ValueError):normalized_logdet(rows,lambda name,qs:.1,bad)

    def test_reject_measurement(self):
        a=QuantumCircuit(2);a.measure_all()
        with self.assertRaises(ValueError):signatures(a)

if __name__=='__main__':unittest.main()
