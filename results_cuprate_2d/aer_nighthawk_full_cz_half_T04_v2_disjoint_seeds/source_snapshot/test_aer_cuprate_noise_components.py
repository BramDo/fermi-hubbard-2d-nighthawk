"""Channel decomposition, mask/readout orientation and trajectory estimator tests."""
import unittest

import numpy as np
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error
from qiskit_ibm_runtime.models import BackendProperties

import aer_cuprate_noise_components as c


class ComponentModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.properties = BackendProperties.from_dict(c.a.read(c.BASELINE/'restricted_backend_properties.json'))
        cls.models, cls.rows = c.split_model(cls.properties)

    def test_every_full_channel_reconstructed(self):
        self.assertGreaterEqual(len(self.rows), 62)
        self.assertLess(max(x['reconstructed_max_superop_difference'] for x in self.rows), 1e-12)

    def test_ablated_models_have_no_readout(self):
        for model in self.models.values():
            self.assertFalse(model.is_ideal())
            self.assertTrue(all(e['type'] == 'qerror' for e in model.to_dict()['errors']))

    def test_no_double_counting_of_relaxation_floor(self):
        rows = {(r['gate'], tuple(r['local_qubits'])): r for r in self.rows}
        for q in [3, 13, 15]:
            for name in ['x', 'sx']:
                self.assertLess(rows[name, (q,)]['residual_p'], 1e-12)

    def test_virtual_rz_is_not_noisy(self):
        self.assertFalse(any(row['gate'] == 'rz' for row in self.rows))


class ReadoutMomentTests(unittest.TestCase):
    def test_readout_identity(self):
        x = np.array([.3, -.4, .15])
        for mask in [[0, 0], [1, 1]]:
            np.testing.assert_allclose(c.apply_readout(x, mask, np.tile(np.eye(2), (2, 1, 1))), x)

    def test_asymmetric_readout_and_all_masks_against_enumeration(self):
        probabilities = [.13, .23, .31, .33]
        matrices = np.array([[[.91, .09], [.17, .83]], [[.96, .04], [.23, .77]]])
        p = np.zeros(3)
        for x, prob in enumerate(probabilities):
            z = [1-2*((x >> q) & 1) for q in range(2)]
            p += prob*np.array([z[0], z[1], z[0]*z[1]])
        for m in range(4):
            mask = np.array([(m >> q) & 1 for q in range(2)], dtype=np.uint8)
            expected = np.zeros(3)
            for x, prob in enumerate(probabilities):
                for y in range(4):
                    weight = prob
                    for q in range(2):
                        weight *= matrices[q, ((x >> q) & 1)^int(mask[q]), (y >> q) & 1]
                    z = [1-2*(((y >> q) & 1)^int(mask[q])) for q in range(2)]
                    expected += weight*np.array([z[0], z[1], z[0]*z[1]])
            np.testing.assert_allclose(c.apply_readout(p, mask, matrices), expected, atol=1e-14)

    def test_unmask_is_involution_and_zz_sign_is_product(self):
        x = np.array([.3, -.4, .15])
        for mask in [[0, 1], [1, 0], [1, 1]]:
            np.testing.assert_allclose(c.unmask_paulis(c.unmask_paulis(x, mask), mask), x)
        np.testing.assert_allclose(c.unmask_paulis(x, [1, 1]), [-.3, .4, .15])

    def test_invalid_dimensions_rejected(self):
        with self.assertRaises(ValueError):
            c.apply_readout(np.zeros(4), [0, 0], np.tile(np.eye(2), (2, 1, 1)))


class ExpectationEstimatorTests(unittest.TestCase):
    def test_noiseless_bell_moments(self):
        q = QuantumCircuit(2, 2)
        q.h(0)
        q.cx(0, 1)
        q.measure([0, 1], [0, 1])
        saved = c.expectation_circuit(q)
        simulator = AerSimulator(method='statevector', max_parallel_threads=1)
        result = simulator.run(saved, shots=1).result()
        np.testing.assert_allclose(c.extract_expectations(result, 2, 1), [[0, 0, 1]], atol=1e-14)
        self.assertNotIn('measure', saved.count_ops())

    def test_noisy_pershot_values_retained_without_measurement(self):
        q = QuantumCircuit(2, 2)
        q.x(0)
        q.measure([0, 1], [0, 1])
        noise = NoiseModel()
        noise.add_quantum_error(depolarizing_error(.2, 1), 'x', [0])
        simulator = AerSimulator(method='statevector', noise_model=noise,
                                 enable_truncation=False, max_parallel_threads=2, max_parallel_shots=2)
        result = simulator.run(c.expectation_circuit(q), shots=16, seed_simulator=613).result()
        values = c.extract_expectations(result, 2, 16)
        np.testing.assert_allclose(np.abs(values), np.ones((16, 3)), atol=1e-14)
        np.testing.assert_allclose(values[:, 0], values[:, 2], atol=1e-14)
        np.testing.assert_allclose(values[:, 1], 1, atol=1e-14)


if __name__ == '__main__':
    unittest.main()
