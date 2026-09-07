"""Verify exact gate-class partitioning; no fitting or noise-budget reassignment."""
import copy
import unittest

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import SuperOp
from qiskit_aer.noise import NoiseModel, depolarizing_error

import aer_cuprate_gate_split as s


class GatePartitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = s.c.a.read(s.PARENT/'residual_depolarization_only_noise.json')
        cls.models, cls.audit = s.partition_channels(cls.source)
        cls.original = s.channel_map(cls.source)

    def test_cz_model_has_only_two_qubit_cz_noise(self):
        channels = s.channel_map(self.models[s.MODELS[0]].to_dict())
        self.assertTrue(channels)
        self.assertTrue(all(name == 'cz' and len(qs) == 2 for name, qs in channels))

    def test_single_qubit_model_has_only_x_sx_noise(self):
        channels = s.channel_map(self.models[s.MODELS[1]].to_dict())
        self.assertTrue(channels)
        self.assertTrue(all(name in {'x', 'sx'} and len(qs) == 1 for name, qs in channels))

    def test_disjoint_complete_union(self):
        left, right = [s.channel_map(self.models[name].to_dict()) for name in s.MODELS]
        self.assertFalse(set(left) & set(right))
        self.assertEqual(set(left) | set(right), set(self.original))

    def test_original_channels_preserved_including_wire_order(self):
        for model in self.models.values():
            for key, error in s.channel_map(model.to_dict()).items():
                np.testing.assert_allclose(SuperOp(error).data, SuperOp(self.original[key]).data,
                                           atol=1e-14, rtol=0)
        self.assertLess(self.audit['max_channel_difference'], 1e-14)

    def test_no_mutation_of_saved_model(self):
        original = copy.deepcopy(self.source)
        s.partition_channels(self.source)
        self.assertEqual(original, self.source)

    def test_readout_channel_rejected(self):
        with self.assertRaises(ValueError):
            s.channel_map({'errors': [{'type': 'roerror'}]})

    def test_unexpected_gate_rejected(self):
        changed = copy.deepcopy(self.source)
        changed['errors'][0]['operations'] = ['rz']
        with self.assertRaises(ValueError):
            s.channel_map(changed)

    def test_duplicate_channel_rejected(self):
        changed = copy.deepcopy(self.source)
        changed['errors'].append(copy.deepcopy(changed['errors'][0]))
        with self.assertRaises(ValueError):
            s.channel_map(changed)

    def test_wrong_gate_width_rejected(self):
        changed = copy.deepcopy(self.source)
        entry = next(e for e in changed['errors'] if e['operations'] == ['cz'])
        entry['gate_qubits'] = [[0]]
        with self.assertRaises(ValueError):
            s.channel_map(changed)

    def test_simple_model_preserves_distinct_gate_error_strengths(self):
        model = NoiseModel()
        model.add_quantum_error(depolarizing_error(.1, 1), 'x', [0])
        model.add_quantum_error(depolarizing_error(.2, 1), 'sx', [1])
        model.add_quantum_error(depolarizing_error(.3, 2), 'cz', [0, 1])
        pieces, audit = s.partition_channels(model.to_dict())
        self.assertEqual(audit['channels_per_model'], [1, 2])
        self.assertEqual(set(s.channel_map(pieces[s.MODELS[1]].to_dict())), {('x', (0,)), ('sx', (1,))})

    def test_expectation_conversion_keeps_all_ideal_gates(self):
        circuit = QuantumCircuit(2, 2)
        circuit.x(0)
        circuit.sx(1)
        circuit.cz(0, 1)
        circuit.rz(.2, 0)
        circuit.measure([0, 1], [0, 1])
        converted = s.c.expectation_circuit(circuit)
        for gate in s.c.a.NATIVE:
            self.assertEqual(converted.count_ops().get(gate, 0), circuit.count_ops().get(gate, 0))
        self.assertNotIn('measure', converted.count_ops())


if __name__ == '__main__':
    unittest.main()
