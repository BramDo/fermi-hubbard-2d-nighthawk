"""Exact small-circuit, seed, and estimator regressions for CZ ZNE."""
import unittest
import io
import numpy as np
from qiskit import QuantumCircuit, qpy
from qiskit.quantum_info import Operator, Pauli
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, ReadoutError, depolarizing_error, amplitude_damping_error
import aer_cuprate_cz_zne as z
import analyze_aer_cuprate_cz_zne as an

def fixture():
    q=QuantumCircuit(3,1)
    q.global_phase=.17
    q.h(0)
    for k in range(4):
        q.cz(0,1)
        q.rz(.13*k,1)
        q.cz(1,2)
        q.sx(2)
    return q

class FoldingTests(unittest.TestCase):
    def test_qpy_measured_source_recreates_executable_saves(self):
        measured=QuantumCircuit(2)
        measured.x(0)
        measured.cz(0,1)
        measured.cz(0,1)
        measured.measure_all()
        buffer=io.BytesIO()
        qpy.dump(measured,buffer)
        buffer.seek(0)
        base=z.prepare_base(qpy.load(buffer)[0])
        f,_=z.fold_cz(base,3,123)
        result=AerSimulator(method='statevector',max_parallel_threads=1).run(f,shots=1).result()
        self.assertTrue(result.success)
        np.testing.assert_allclose(z.c.extract_expectations(result,2,1),[[-1,1,-1]],atol=1e-14)
    def test_prepare_base_rejects_missing_measurements(self):
        with self.assertRaises(ValueError):
            z.prepare_base(QuantumCircuit(2))
    def test_ideal_unitary_factors_1_2_3(self):
        q=fixture()
        for factor in (1,2,3):
            f,_=z.fold_cz(q,factor,123)
            np.testing.assert_allclose(Operator(f).data,Operator(q).data,atol=1e-12,rtol=0)
    def test_each_ordered_support_doubles(self):
        f,audit=z.fold_cz(fixture(),2,321)
        self.assertEqual(f.count_ops()['cz'],16)
        self.assertTrue(all(r['folded']==2*r['original'] for r in audit['per_support']))
    def test_factor3_adds_exactly_two_per_original_cz(self):
        q=fixture()
        f,audit=z.fold_cz(q,3,321)
        self.assertEqual(len(audit['selected_original_indices']),8)
        self.assertEqual(len(f.data)-len(q.data),16)
    def test_original_object_unchanged(self):
        q=fixture()
        before=z.instruction_rows(q)
        z.fold_cz(q,2,111)
        self.assertEqual(before,z.instruction_rows(q))
    def test_same_placement_seed_reproducible(self):
        first,a=z.fold_cz(fixture(),2,123)
        second,b=z.fold_cz(fixture(),2,123)
        self.assertEqual(a,b)
        self.assertEqual(z.instruction_rows(first),z.instruction_rows(second))
    def test_single_qubit_counts_and_classical_register_preserved(self):
        q=fixture()
        f,_=z.fold_cz(q,3,123)
        for gate in ['h','rz','sx']:
            self.assertEqual(q.count_ops()[gate],f.count_ops()[gate])
        self.assertEqual(q.num_clbits,f.num_clbits)
    def test_odd_support_factor2_rejected(self):
        q=QuantumCircuit(2)
        q.cz(0,1)
        with self.assertRaises(ValueError):
            z.fold_cz(q,2,123)
    def test_invalid_factor_rejected(self):
        with self.assertRaises(ValueError):
            z.fold_cz(fixture(),1.5,123)
    def test_missing_cz_rejected(self):
        with self.assertRaises(ValueError):
            z.fold_cz(QuantumCircuit(2),1,123)
    def test_noise_effect_matches_exact_depolarization_with_fusion(self):
        q=QuantumCircuit(2)
        q.h(0)
        q.h(1)
        q.cz(0,1)
        q.cz(0,1)
        q.save_expectation_value(Pauli('XX'),[0,1],label='xx')
        noise=NoiseModel()
        noise.add_quantum_error(depolarizing_error(.1,2),'cz',[0,1])
        sim=AerSimulator(method='density_matrix',noise_model=noise,max_parallel_threads=1,
                         fusion_threshold=1,fusion_enable=True)
        results=[]
        for factor in (1,2,3):
            f,_=z.fold_cz(q,factor,123)
            result=sim.run(f,shots=1).result()
            value=float(result.data()['xx'])
            self.assertAlmostEqual(value,.9**(2*factor),places=12)
            results.append(value)
        self.assertGreater(results[0],results[1])
        self.assertGreater(results[1],results[2])
    def test_kraus_statevector_folded_matches_exact_mean(self):
        q=QuantumCircuit(2)
        q.x(0)
        q.x(1)
        q.cz(0,1)
        q.cz(0,1)
        q.save_expectation_value(Pauli('Z'),[0],label='z',pershot=True)
        f,_=z.fold_cz(q,3,123)
        noise=NoiseModel()
        error=amplitude_damping_error(.1)
        noise.add_quantum_error(error.tensor(error),'cz',[0,1])
        sim=AerSimulator(method='statevector',noise_model=noise,max_parallel_threads=2,
                         max_parallel_shots=2,fusion_threshold=1)
        result=sim.run(f,shots=4096,seed_simulator=2026800000).result()
        self.assertLess(abs(float(np.mean(result.data()['z']))-(1-2*.9**6)),.04)
        self.assertEqual(result.results[0].metadata['noise'],'kraus')
        self.assertTrue(result.results[0].metadata['fusion']['applied'])
    def test_czoff_keeps_non_cz_and_readout(self):
        noise=NoiseModel(basis_gates=['cz','x'])
        noise.add_quantum_error(depolarizing_error(.12,2),'cz',[0,1])
        noise.add_quantum_error(depolarizing_error(.07,1),'x',[0])
        noise.add_readout_error(ReadoutError([[.97,.03],[.04,.96]]),[0])
        out,audit=z.without_cz_noise(noise)
        self.assertEqual(set(z.h.qerrors(out)),{('x',(0,))})
        self.assertTrue(audit['readout_identical'])

class SeedTests(unittest.TestCase):
    def test_all_sample_seed_labels_disjoint(self):
        seeds=[z.seed_for(g,t)+s for g in range(4) for t in range(8) for s in range(16)]
        self.assertEqual(len(set(seeds)),512)
        self.assertTrue(all(0<=s<2**32 for s in seeds))
    def test_new_seeds_disjoint_from_previous_studies(self):
        old=set()
        for base,count in [(2026090590,64),(2026090700,16),(2026090800,16),
                           (2026091000,16),(2026091100,16),(2026091300,16),(2026091400,16)]:
            old.update(base+t+s for t in range(8) for s in range(count))
        old.update(base+1000*t+s for base in [2026100000,2026200000]
                   for t in range(8) for s in range(16))
        fresh={z.seed_for(g,t)+s for g in (1,2,3) for t in range(8) for s in range(16)}
        self.assertFalse(old&fresh)
    def test_invalid_group_twirl_rejected(self):
        for g,t in [(-1,0),(4,0),(0,8),(0,-1)]:
            with self.assertRaises(ValueError):
                z.seed_for(g,t)

class InferenceTests(unittest.TestCase):
    def test_weight_moments(self):
        x=np.array([1,2,3])
        np.testing.assert_allclose(an.WEIGHTS.sum(axis=1),1,atol=1e-14)
        self.assertAlmostEqual(float(an.WEIGHTS[1,:3]@x),0)
        self.assertAlmostEqual(float(an.WEIGHTS[2,:3]@x),0)
        self.assertAlmostEqual(float(an.WEIGHTS[2,:3]@(x*x)),0)
    def test_linear_model_intercept_exact(self):
        target=np.linspace(-.5,.5,54).reshape(2,27)
        source=np.stack([target+.03*k for k in (1,2,3)]+[target])
        answer=an.method_means(source)
        np.testing.assert_allclose(answer[1],target,atol=1e-14)
        np.testing.assert_allclose(answer[2],target,atol=1e-14)
    def test_quadratic_is_secondary_and_linear_can_be_biased(self):
        source=np.stack([np.full((2,27),.2+.02*k+.01*k*k) for k in (1,2,3)]
                        +[np.full((2,27),.2)])
        out=an.method_means(source)
        np.testing.assert_allclose(out[2],.2,atol=1e-14)
        np.testing.assert_allclose(out[1],.2-.01*10/3,atol=1e-14)
    def test_benefits_primary_readout_signs(self):
        metrics=np.zeros((4,2,4))
        metrics[0,1]=[.3,.5,.4,.4]
        metrics[1,1]=[.2,.2,.3,.8]
        np.testing.assert_allclose(an.benefits(metrics),[.1,.3,.1,.4],atol=1e-14)
    def test_negative_benefit_not_clipped(self):
        metrics=np.zeros((4,2,4))
        metrics[1,1]=[1,1,1,-1]
        np.testing.assert_array_equal(an.benefits(metrics),[-1,-1,-1,-1])
    def test_bootstrap_preserves_shared_raw_and_readout_pair(self):
        data=np.zeros((4,8,16,2,27))
        data[0]=np.arange(16)[None,:,None,None]/100
        samples=an.bootstrap(data,repetitions=32,seed=123)
        methods=an.method_means(samples)
        np.testing.assert_allclose(methods[:,1],methods[:,0]*4/3,atol=1e-14)
        np.testing.assert_array_equal(samples[:,:,0],samples[:,:,1])
    def test_bootstrap_reproducible(self):
        data=np.random.default_rng(1).normal(size=(4,8,16,2,27))
        np.testing.assert_array_equal(an.bootstrap(data,8,123),an.bootstrap(data,8,123))
    def test_wrong_shapes_rejected(self):
        with self.assertRaises(ValueError):
            an.bootstrap(np.zeros((3,8,16,2,27)),2,1)
        with self.assertRaises(ValueError):
            an.method_means(np.zeros((3,2,27)))
        with self.assertRaises(ValueError):
            an.benefits(np.zeros((3,2,4)))
    def test_range_violations_reported_not_clipped(self):
        p=np.zeros(27)
        p[0]=2
        before=p.copy()
        check=an.physical_range(p)
        self.assertGreater(check['negative_two_mode_probabilities'],0)
        self.assertEqual(check['paulis_outside_range'],1)
        np.testing.assert_array_equal(p,before)
    def test_inrange_exact_empty_state_probabilities(self):
        check=an.physical_range(np.ones(27))
        self.assertEqual(check['negative_two_mode_probabilities'],0)
        self.assertEqual(check['paulis_outside_range'],0)

if __name__=='__main__':
    unittest.main()
