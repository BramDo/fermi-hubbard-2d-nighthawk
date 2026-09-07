"""Offline tests: wiring, native noise coverage and physical calibration identity."""
import copy
import unittest

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import SuperOp, average_gate_fidelity
from qiskit_aer.noise.device import basic_device_gate_errors, basic_device_readout_errors
from qiskit_ibm_runtime.models import BackendProperties

import aer_cuprate_nighthawk_smoke as smoke


class NoiseMappingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = smoke.read(smoke.CAL / 'backend_properties.json')
        cls.layout = smoke.read(smoke.PLAN / 'manifest.json')['initial_layout']
        cls.reduced, cls.mirrors = smoke.restrict_properties(cls.original, cls.layout)
        cls.props = BackendProperties.from_dict(cls.reduced)

    def test_properties_are_unchanged_and_permuted_exactly(self):
        before = copy.deepcopy(self.original)
        smoke.restrict_properties(self.original, self.layout)
        self.assertEqual(before, self.original)
        for local, physical in enumerate(self.layout):
            self.assertEqual(self.reduced['qubits'][local], self.original['qubits'][physical])

    def test_time_unit_conversion(self):
        archived_t1 = next(p for p in self.original['qubits'][112] if p['name'] == 'T1')
        self.assertEqual(archived_t1['unit'], 'us')
        self.assertAlmostEqual(self.props.t1(0), archived_t1['value'] * 1e-6, places=15)

    def test_asymmetric_readout_matches_physical_not_local_indices(self):
        full = dict((tuple(q), e.probabilities) for q, e in basic_device_readout_errors(
            BackendProperties.from_dict(self.original)))
        local = dict((tuple(q), e.probabilities) for q, e in basic_device_readout_errors(self.props))
        for i, physical in enumerate(self.layout):
            np.testing.assert_allclose(local[(i,)], full[(physical,)], atol=0, rtol=0)

    def test_cz_channel_matches_original_physical_calibration(self):
        full_one = copy.deepcopy(self.original)
        full_one['gates'] = [g for g in full_one['gates']
                             if g['gate'] == 'cz' and g['qubits'] == [112, 113]]
        self.assertEqual(len(full_one['gates']), 1)
        expected = basic_device_gate_errors(BackendProperties.from_dict(full_one))[0][2]
        channels = {(n, tuple(q)): e for n, q, e in basic_device_gate_errors(self.props)}
        np.testing.assert_allclose(SuperOp(channels['cz', (0, 1)]).data,
                                   SuperOp(expected).data, atol=1e-14, rtol=0)
        reported = next(p['value'] for p in full_one['gates'][0]['parameters']
                        if p['name'] == 'gate_error')
        self.assertAlmostEqual(1-average_gate_fidelity(channels['cz', (0, 1)]),
                               reported, places=12)

    def test_symmetric_cz_reverse_present(self):
        channels = {(n, tuple(q)): e for n, q, e in basic_device_gate_errors(self.props)}
        self.assertIn(('cz', (1, 0)), channels)
        # Reverse the channel's wire ordering, including unequal T1/T2 values.
        swap = QuantumCircuit(2)
        swap.swap(0, 1)
        s = SuperOp(swap).data
        np.testing.assert_allclose(SuperOp(channels['cz', (1, 0)]).data,
                                   s @ SuperOp(channels['cz', (0, 1)]).data @ s,
                                   atol=1e-14, rtol=0)

    def test_missing_frequency_supported_without_fabrication(self):
        self.assertTrue(all(not any(v['name'] == 'frequency' for v in q)
                            for q in self.reduced['qubits']))
        model = smoke.build_noise(self.props)
        self.assertFalse(model.is_ideal())
        self.assertEqual(model.noise_qubits, list(range(18)))

    def test_duplicate_layout_rejected(self):
        with self.assertRaises(ValueError):
            smoke.restrict_properties(self.original, [112, 112])


class CircuitMappingTests(unittest.TestCase):
    def test_gate_and_measurement_permutation(self):
        circuit = QuantumCircuit(5, 2)
        circuit.x(4)
        circuit.cz(4, 1)
        circuit.measure(4, 0)
        circuit.measure(1, 1)
        local = smoke.remap_measured(circuit, [4, 1])
        self.assertEqual(local.num_qubits, 2)
        self.assertEqual(local.count_ops(), circuit.count_ops())
        self.assertEqual([local.find_bit(q).index for q in local.data[1].qubits], [0, 1])

    def test_unmapped_wire_rejected(self):
        circuit = QuantumCircuit(5, 2)
        circuit.x(3)
        with self.assertRaises(ValueError):
            smoke.remap_measured(circuit, [4, 1])

    def test_nonterminal_measurement_rejected(self):
        circuit = QuantumCircuit(5, 2)
        circuit.measure(4, 0)
        circuit.x(4)
        with self.assertRaises(ValueError):
            smoke.remap_measured(circuit, [4, 1])

    def test_changed_readout_bit_order_rejected(self):
        circuit = QuantumCircuit(5, 2)
        circuit.measure(4, 1)
        circuit.measure(1, 0)
        with self.assertRaises(ValueError):
            smoke.remap_measured(circuit, [4, 1])


if __name__ == '__main__':
    unittest.main()
