"""Local tests only: exact quantum simulation and synthetic-noise plumbing."""
import copy
import tempfile
import unittest
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit
from qiskit.primitives import StatevectorSampler
from qiskit.quantum_info import Operator

from cuprate_2d_hubbard_pipeline import Cuprate2DConfig
from cuprate_2d_tflo import (parameterized_network, compile_template, bind, skeleton,
    explicit_twirl, embed_measurement, flo_reference, decode_bitstrings,
    pauli_samples, physical_observables, sector_mask, fit_tflo, apply_tflo,
    archive_sampler_results, analyze)
from cuprate_2d_fermionic_mapping import build_network
from cuprate_2d_fermionic_pilot import simulator_state
from validate_cuprate_2d_fermionic_dynamics import phase_distance
from prepare_cuprate_2d_tflo import state_paulis


class TFLOTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = Cuprate2DConfig(lx=2,ly=2,holes=0,steps=2,dt=.1)
        cls.template = compile_template(parameterized_network(cls.cfg))

    def test_structure_preserved_at_zero_U_and_zero_time(self):
        signature = skeleton(self.template)
        for u in (0.,8.):
            for t in (0.,.2,.5):
                self.assertEqual(skeleton(bind(self.template,self.cfg,t,u)),signature)
        self.assertGreater(self.template.count_ops()['cz'],0)

    def test_full_operator_equivalence_not_only_initial_state(self):
        cfg = Cuprate2DConfig(lx=2,ly=2,holes=0,steps=1,dt=.1)
        template = compile_template(parameterized_network(cfg))
        for u in (0.,8.):
            from dataclasses import replace
            old = Operator(build_network(replace(cfg,u_over_t=u))).data.ravel()
            new = Operator(bind(template,cfg,.1,u)).data.ravel()
            self.assertLess(phase_distance(old,new),2e-9)

    def test_flo_matches_many_body_with_diagonal_hopping(self):
        for t in (0.,.2,.5):
            ref, covariance = flo_reference(self.cfg,t)
            state = simulator_state(bind(self.template,self.cfg,t,0.))
            np.testing.assert_allclose(ref,state_paulis(state,self.cfg.qubits),atol=1e-10)
            np.testing.assert_allclose(covariance@covariance,covariance,atol=1e-10)

    def test_twirl_operator_identity_for_all_CZ_paulis(self):
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.cz(0,1)
        qc.rx(.37,1)
        original = Operator(qc).data.ravel()
        for seed in range(64):
            twisted, mask = explicit_twirl(qc,seed)
            for q in np.flatnonzero(mask):
                twisted.x(int(q))
            self.assertLess(phase_distance(Operator(twisted).data.ravel(),original),1e-12)

    def test_bit_order_mask_and_separate_spin_sectors(self):
        bits = decode_bitstrings(['1001'],4,[1,0,0,0])
        np.testing.assert_array_equal(bits,[[0,0,0,1]])
        candidates = np.array([[1,0,0,1],[1,0,1,0],[0,0,0,1]],dtype=np.uint8)
        np.testing.assert_array_equal(sector_mask(candidates,1,1),[True,False,False])
        np.testing.assert_array_equal(sector_mask(candidates,1,1,1),[True,False,True])
        np.testing.assert_array_equal(physical_observables(pauli_samples(candidates[:1])),
                                      [[[1,1,0],[1,-1,0]]])

    def test_invalid_bitstrings_rejected(self):
        for invalid in ([],['10x1'],['101']):
            with self.assertRaises(ValueError):
                decode_bitstrings(invalid,4,[0,0,0,0])
        with self.assertRaises(ValueError):
            decode_bitstrings(['1010'],4,[0,0,0,2])

    def test_sampler_adapter_raw_archive_round_trip(self):
        # Nontrivial physical layout: c0 <- physical q3, c1 <- physical q1.
        logical = QuantumCircuit(2)
        logical.x(0)
        physical = embed_measurement(logical,[3,1],4)
        result = StatevectorSampler(seed=7).run([physical],shots=64).result()
        record = {'setting_id':'test','twirl_id':0,'shots':64,
                  'readout_mask_little_endian':[1,0]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'raw.json'
            archive = archive_sampler_results(path,result,[record],job_id='LOCAL_TEST_ONLY',width=2)
            decoded = decode_bitstrings(archive['records'][0]['bitstrings'],2,[1,0])
            np.testing.assert_array_equal(decoded,np.zeros((64,2),dtype=np.uint8))
            with self.assertRaises(FileExistsError):
                archive_sampler_results(path,result,[record],job_id='LOCAL_TEST_ONLY',width=2)
            with self.assertRaises(ValueError):
                archive_sampler_results(Path(directory)/'bad.json',result,[{**record,'shots':65}],
                                        job_id='LOCAL_TEST_ONLY',width=2)

    def test_known_affine_transfer_and_rank_deficient_regularization(self):
        times = np.array([0.,.1,.2,.3,.4,.5])
        exact = np.column_stack([np.cos(3*times),np.sin(2*times)])
        noisy = (exact-.07*times[:,None]-.03)/1.6
        model = fit_tflo(noisy,exact,times,ridge=1e-10)
        target = np.array([.4,-.3])
        predicted = apply_tflo(model,(target-.07*.25-.03)/1.6,.25)
        np.testing.assert_allclose(predicted,target,atol=1e-6)
        flat = fit_tflo(np.ones((6,2)),np.ones((6,2)),times)
        self.assertTrue(all(d['rank'] < 3 for d in flat['diagnostics']))
        self.assertTrue(np.isfinite(flat['coefficients']).all())

    def test_synthetic_pipeline_no_interacting_reference_leakage(self):
        rng = np.random.default_rng(88)
        settings, raw = [], {}
        all_states = np.arange(2**self.cfg.qubits,dtype=np.uint32)
        for i,t in enumerate([0.,.1,.2,.3,.4,.5,.25]):
            u = 8. if i == 6 else 0.
            state = simulator_state(bind(self.template,self.cfg,t,u))
            reference = state_paulis(state,self.cfg.qubits)
            sid = str(i)
            settings.append({'id':sid,'time':t,'u_over_t':u,
                             'role':'interacting_holdout' if u else 'train',
                             'reference':reference.tolist()})
            raw[sid] = {}
            for twirl in range(4):
                sampled = rng.choice(all_states,size=64,p=np.abs(state)**2/np.sum(np.abs(state)**2))
                bits = ((sampled[:,None] >> np.arange(self.cfg.qubits)) & 1).astype(np.uint8)
                # Synthetic READOUT flips only: explicitly NOT a Phoenix noise model.
                bits ^= (rng.random(bits.shape)<(.01+.002*twirl)).astype(np.uint8)
                raw[sid][twirl] = bits
        report = analyze(settings,raw,2,2,bootstrap=30,seed=6)
        changed = copy.deepcopy(settings)
        changed[-1]['reference'] = [0.]*12
        alternative = analyze(changed,raw,2,2,bootstrap=30,seed=6)
        self.assertEqual(report['model'],alternative['model'])
        self.assertEqual(report['settings'][-1]['tflo']['observables'],
                         alternative['settings'][-1]['tflo']['observables'])
        self.assertEqual(report['bootstrap_failures'],0)
        self.assertTrue(all(0<r['retained_fraction']<=1 for r in report['settings']))
        unsafe = copy.deepcopy(settings)
        unsafe[-1]['role'] = 'train'
        with self.assertRaises(ValueError):
            analyze(unsafe,raw,2,2,bootstrap=2)

    def test_empty_sector_rejected_not_silently_replaced(self):
        settings = [{'id':str(i),'time':i/10,'u_over_t':0.,'role':'train',
                     'reference':[1.]*6} for i in range(4)]
        raw = {s['id']:{j:np.zeros((64,4),dtype=np.uint8) for j in range(2)} for s in settings}
        with self.assertRaises(ValueError):
            analyze(settings,raw,1,1,bootstrap=2)


if __name__ == '__main__':
    from threadpoolctl import threadpool_limits
    with threadpool_limits(limits=1):
        unittest.main(verbosity=2)
