"""Full-model identity, selective CZ scaling and once-only readout tests."""
import unittest

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import SuperOp
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, ReadoutError, coherent_unitary_error
from qiskit_aer.noise.device import basic_device_gate_errors
from qiskit_ibm_runtime.models import BackendProperties

import aer_cuprate_cz_half as s


class FullModelScalingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.props = BackendProperties.from_dict(s.c.a.read(s.c.BASELINE/'restricted_backend_properties.json'))
        cls.decomposition = s.c.a.read(s.PARENT/'decomposition.json')
        cls.built = {scale: s.scaled_full_model(cls.props, cls.decomposition, scale) for scale in [0., .5, 1.]}

    def test_control_matches_archived_full_model(self):
        audit = s.validate_saved_control(self.built[1.][0], s.c.a.read(s.c.BASELINE/'noise_model.json'))
        self.assertLess(audit['saved_full_quantum_channel_max_error'], 1e-12)
        self.assertEqual(audit['identical_readout_qubits'], 18)

    def test_non_cz_quantum_channels_are_identical(self):
        control, half = s.qerrors(self.built[1.][0]), s.qerrors(self.built[.5][0])
        self.assertEqual(set(control), set(half))
        for key in control:
            if key[0] != 'cz':
                np.testing.assert_allclose(SuperOp(control[key]).data, SuperOp(half[key]).data, atol=0, rtol=0)

    def test_cz_residual_parameter_exactly_halved(self):
        for row in self.built[.5][1]:
            expected = .5*row['original_residual_p'] if row['gate'] == 'cz' else row['original_residual_p']
            self.assertEqual(row['new_residual_p'], expected)

    def test_readout_unchanged_at_all_scales(self):
        control = s.readout_entries(self.built[1.][0])
        for scale in [0., .5]:
            candidate = s.readout_entries(self.built[scale][0])
            self.assertEqual(set(control), set(candidate))
            for q in control:
                np.testing.assert_array_equal(control[q], candidate[q])

    def test_zero_residual_still_retains_cz_relaxation(self):
        zero = s.qerrors(self.built[0.][0])
        relax = {(n, tuple(q)): e for n, q, e in basic_device_gate_errors(self.props,
            gate_error=False, thermal_relaxation=True, temperature=0)}
        for key, error in zero.items():
            if key[0] == 'cz':
                np.testing.assert_allclose(SuperOp(error).data, SuperOp(relax[key]).data, atol=1e-14, rtol=0)
                self.assertFalse(error.ideal())

    def test_half_cz_fidelity_between_full_and_relaxation_floor(self):
        for row in self.built[.5][1]:
            if row['gate'] == 'cz':
                self.assertGreaterEqual(row['new_average_fidelity']+1e-12, row['original_average_fidelity'])
                self.assertLessEqual(row['new_average_fidelity']-1e-12, row['relaxation_average_fidelity'])

    def test_invalid_reduction_scales_rejected(self):
        for scale in [-.1, 1.1, float('nan')]:
            with self.assertRaises(ValueError):
                s.scaled_full_model(self.props, self.decomposition, scale)


class ReadoutAndBenefitTests(unittest.TestCase):
    def test_complex_json_roundtrip_preserves_nonzero_imaginary_part(self):
        error = coherent_unitary_error(np.diag([1, np.exp(.31j)]))
        model = NoiseModel()
        model.add_quantum_error(error, 'x', [0])
        encoded = model.to_dict(serializable=True)
        restored = s.channel_map(s.decode_serialized_noise(encoded))['x', (0,)]
        np.testing.assert_allclose(SuperOp(restored).data, SuperOp(error).data, atol=1e-14, rtol=0)
        # Decoding may not mutate the source's three-dimensional pair encoding.
        instruction = encoded['errors'][0]['instructions'][0][0]
        self.assertEqual(np.asarray(instruction['params'][0]).shape, (2, 2, 2))

    def test_readout_not_applied_to_save_but_applied_to_measured_bits(self):
        qc = QuantumCircuit(2, 2)
        qc.x(0)
        qc.measure([0, 1], [0, 1])
        flip = np.array([[0., 1.], [1., 0.]])
        matrices = np.stack([flip, np.eye(2)])
        noise = NoiseModel()
        noise.add_readout_error(ReadoutError(flip), [0])
        simulator = AerSimulator(method='statevector', noise_model=noise,
                                 enable_truncation=False, max_parallel_threads=1)
        saved = s.c.expectation_circuit(qc)
        result = simulator.run(saved, shots=1).result()
        expectations = s.c.extract_expectations(result, 2, 1)
        np.testing.assert_allclose(expectations, [[-1, 1, -1]], atol=1e-14)
        transformed = s.c.apply_readout(expectations, [0, 0], matrices)
        np.testing.assert_allclose(transformed, [[1, 1, 1]], atol=1e-14)
        self.assertEqual(simulator.run(qc, shots=16, seed_simulator=52).result().get_counts(), {'00': 16})

    def test_benefits_use_readout_on_and_correct_signs(self):
        data = np.array([[[9., 9., 9., 9.], [.2, .3, .4, .5]],
                         [[0., 0., 0., 0.], [.1, .2, .3, .6]]])
        np.testing.assert_allclose(s.benefits(data), [.1, .1, .1, .1], atol=1e-14)

    def test_negative_benefit_not_clipped(self):
        data = np.array([[[0., 0., 0., 0.], [.1, .2, .3, .6]],
                         [[0., 0., 0., 0.], [.2, .3, .4, .5]]])
        np.testing.assert_allclose(s.benefits(data), [-.1, -.1, -.1, -.1], atol=1e-14)

    def test_wrong_benefit_shape_rejected(self):
        with self.assertRaises(ValueError):
            s.benefits(np.zeros((2, 4)))


if __name__ == '__main__':
    unittest.main()
