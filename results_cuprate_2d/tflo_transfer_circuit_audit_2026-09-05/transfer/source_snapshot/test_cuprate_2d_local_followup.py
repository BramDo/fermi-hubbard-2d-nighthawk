import copy
import unittest

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

from cuprate_2d_hubbard_pipeline import Cuprate2DConfig
from cuprate_2d_tflo import parameterized_network, bind, pauli_samples
from cuprate_2d_fermionic_mapping import prepare_state
from cuprate_2d_fermionic_dynamics import add_fermionic_hopping
from cuprate_2d_local_followup import (fit_models, predict, means, ordered_terms,
    sparse_template, half_gate, phase_distance)


class FollowupTests(unittest.TestCase):
    def calibration(self):
        settings, raw = [], {}
        for i, time in enumerate([0., .1, .2, .3, .4, .5, .15, .35]):
            bits = np.zeros((64, 18), dtype=np.uint8)
            for spin in (0, 1):
                for k in range(4):
                    bits[:, 2*((k+i)%9)+spin] = 1
            sid = str(i)
            raw[sid] = {t: bits.copy() for t in range(8)}
            settings.append({'id': sid, 'time': time, 'u_over_t': 0,
                'role': 'train' if i < 6 else 'flo_holdout',
                'reference': pauli_samples(bits).mean(axis=0).tolist()})
        return settings, raw

    def test_identity_noise_recovered(self):
        settings, raw = self.calibration()
        models = fit_models(settings, raw)
        x, _ = means(settings, raw)
        for name in ('linear_linear', 'affine_no_time'):
            np.testing.assert_allclose(predict(models[name], x, [s['time'] for s in settings]), x, atol=1e-11)

    def test_holdout_references_do_not_train(self):
        settings, raw = self.calibration()
        models = fit_models(settings, raw)
        for setting in settings:
            if setting['role'] != 'train':
                setting['reference'] = None
        self.assertEqual(models, fit_models(settings, raw))

    def test_target_data_rejected(self):
        settings, raw = self.calibration()
        settings[0]['u_over_t'] = 8
        with self.assertRaises(ValueError):
            fit_models(settings, raw)

    def test_time_only_does_not_use_quantum_values(self):
        settings, raw = self.calibration()
        model = fit_models(settings, raw)['time_only']
        x, _ = means(settings, raw)
        times = [s['time'] for s in settings]
        np.testing.assert_array_equal(predict(model, x, times), predict(model, x*100+99, times))

    def test_retention_guard(self):
        settings, raw = self.calibration()
        for block in raw['0'].values():
            block[:] = 0
        with self.assertRaises(ValueError):
            fit_models(settings, raw)

    def test_full_2x2_operator_and_parity_reference(self):
        cfg = Cuprate2DConfig(lx=2, ly=2, holes=0, steps=1, chemical_potential=.13)
        old = parameterized_network(cfg)
        for time, u in ((0., 8.), (.2, 0.), (.23, 8.)):
            expected = Operator(bind(old, cfg, time, u)).data
            for strategy in ('left', 'right', 'look4', 'look12'):
                candidate = sparse_template(cfg, strategy)
                self.assertTrue(all(len(i.qubits) != 2 or abs(candidate.find_bit(i.qubits[0]).index-candidate.find_bit(i.qubits[1]).index) == 1 for i in candidate.data))
                actual = Operator(bind(candidate, cfg, time, u)).data
                self.assertLess(np.max(np.abs(actual-expected)), 1e-11)
        # Independent JW parity-string implementation of the same term order.
        time, u = .23, 8.
        direct = QuantumCircuit(cfg.qubits)
        prepare_state(direct, cfg)
        terms = ordered_terms(cfg)
        for term in terms + list(reversed(terms)):
            if term['kind'] == 'hop':
                add_fermionic_hopping(direct, term['p'], term['q'], term['coefficient'], time/2)
            else:
                direct.cp(-u*cfg.hopping_t*time/2, term['p'], term['q'])
        for q in range(cfg.qubits):
            direct.p(cfg.chemical_potential*time, q)
        np.testing.assert_allclose(Operator(direct).data, Operator(bind(old, cfg, time, u)).data, atol=1e-11)

    def test_unprepared_zero_time_identity(self):
        cfg = Cuprate2DConfig(lx=2, ly=2, holes=0, steps=2)
        qc = bind(sparse_template(cfg, prepare=False), cfg, 0., 8.)
        np.testing.assert_allclose(Operator(qc).data, np.eye(256), atol=1e-11)


if __name__ == '__main__':
    unittest.main(verbosity=2)
