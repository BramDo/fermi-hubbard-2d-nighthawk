"""Equal-budget, shared-shot, measurement and readout regression tests."""
import io
import unittest
import numpy as np
from qiskit import QuantumCircuit, qpy
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, ReadoutError
import aer_cuprate_cz_zne_bitshots as b
import analyze_aer_cuprate_cz_zne_bitshots as a

class BudgetTests(unittest.TestCase):
    def test_each_arm_has512(self):
        self.assertEqual(8*b.COUNTS[0],512)
        self.assertEqual(8*sum(b.ALLOCATION),512)
        self.assertEqual(8*sum(b.COUNTS),728)
    def test_cost_is_not_equal(self):
        self.assertEqual(sum(n*f for n,f in zip(b.ALLOCATION,[1,2,3]))*8*1008,878976)
        self.assertEqual(878976/516096,1.703125)
    def test_allocation_minimizes_fixed_equalvariance_proxy(self):
        w=np.array([4/3,1/3,-2/3])
        selected=float(np.sum(w*w/np.array(b.ALLOCATION)))
        minimum=min(float(np.sum(w*w/np.array([i,j,64-i-j])))
                    for i in range(1,63) for j in range(1,64-i))
        self.assertAlmostEqual(selected,minimum,places=14)
    def test_all_new_seeds_unique(self):
        seeds=[b.seed_for(g,t)+s for g in range(3) for t in range(8) for s in range(b.COUNTS[g])]
        self.assertEqual(len(set(seeds)),728)
        self.assertTrue(all(0<=s<2**32 for s in seeds))
    def test_new_seeds_outside_prior_ranges(self):
        older=set()
        for base,n,stride in [(2026090590,64,1),(2026090700,16,1),(2026090800,16,1),
            (2026091000,16,1),(2026091100,16,1),(2026091300,16,1),(2026091400,16,1),
            (2026100000,16,1000),(2026200000,16,1000),(2026400000,16,1000),
            (2026500000,16,1000),(2026600000,16,1000),(2026800000,4096,10000)]:
            older.update(base+stride*t+s for t in range(8) for s in range(n))
        fresh={b.seed_for(g,t)+s for g in range(3) for t in range(8) for s in range(b.COUNTS[g])}
        self.assertFalse(older&fresh)
    def test_invalid_seed_coordinates(self):
        for g,t in [(-1,0),(3,0),(0,8)]:
            with self.assertRaises(ValueError):
                b.seed_for(g,t)

class MeasurementTests(unittest.TestCase):
    def test_endianness_and_mask(self):
        bits=b.decode_bitstrings(['10','01'],2,[1,0])
        np.testing.assert_array_equal(bits,[[1,1],[0,0]])
        np.testing.assert_array_equal(b.pauli_samples(bits),[[-1,-1,1],[1,1,1]])
    def test_qpy_measured_folding_executable(self):
        q=QuantumCircuit(2)
        q.x(0)
        q.rz(.27,1)
        q.cz(0,1)
        q.cz(0,1)
        q.measure_all()
        f,_=b.z.fold_cz(q,3,123)
        buf=io.BytesIO()
        qpy.dump(f,buf)
        buf.seek(0)
        loaded=qpy.load(buf)[0]
        b.check_measured(loaded)
        result=AerSimulator(max_parallel_threads=1).run(loaded,shots=8,memory=True,seed_simulator=1).result()
        self.assertEqual(result.get_memory(),['01']*8)
        self.assertEqual(b.binary_memory(result.to_dict(),2),['01']*8)
    def test_nonidentity_measurement_rejected(self):
        q=QuantumCircuit(2,2)
        q.measure(0,1)
        q.measure(1,0)
        with self.assertRaises(ValueError):
            b.check_measured(q)
    def test_nonterminal_measurement_rejected(self):
        q=QuantumCircuit(2,2)
        q.measure(0,0)
        q.x(1)
        q.measure(1,1)
        with self.assertRaises(ValueError):
            b.check_measured(q)
    def test_missing_measurement_rejected(self):
        with self.assertRaises(ValueError):
            b.check_measured(QuantumCircuit(2))
    def test_deterministic_readout_applied_once(self):
        q=QuantumCircuit(1,1)
        q.x(0)
        q.measure(0,0)
        noise=NoiseModel()
        noise.add_readout_error(ReadoutError([[0,1],[1,0]]),[0])
        result=AerSimulator(noise_model=noise,max_parallel_threads=1).run(q,shots=8,memory=True,seed_simulator=2).result()
        self.assertEqual(result.get_memory(),['0']*8)
        np.testing.assert_array_equal(b.decode_bitstrings(result.get_memory(),1,[0]),np.zeros((8,1)))
    def test_asymmetric_readout_frequencies(self):
        noise=NoiseModel()
        noise.add_readout_error(ReadoutError([[.8,.2],[.35,.65]]),[0])
        for state,expected in [(0,.2),(1,.65)]:
            q=QuantumCircuit(1,1)
            if state:
                q.x(0)
            q.measure(0,0)
            result=AerSimulator(noise_model=noise,max_parallel_threads=1).run(
                q,shots=4096,memory=True,seed_simulator=2027500000+10000*state).result()
            observed=np.mean([int(s,2) for s in result.get_memory()])
            self.assertLess(abs(observed-expected),.035)
    def test_hex_memory_width_and_counts(self):
        raw={'results':[{'data':{'memory':['0x0','0x3','0x3'],'counts':{'0x0':1,'0x3':2}}}]}
        memory=b.binary_memory(raw,2)
        self.assertEqual(memory,['00','11','11'])
        b.check_saved_counts(raw,memory,2)
        with self.assertRaises(AssertionError):
            b.check_saved_counts(raw,['00']*3,2)
        with self.assertRaises(ValueError):
            b.binary_memory(raw,1)

class SharedInferenceTests(unittest.TestCase):
    def test_factor1_zne_does_not_use_all512(self):
        raw=np.ones((8,64,27))
        raw[:,37:]=-1
        strata=a.split_strata([raw,np.zeros((8,9,27)),np.zeros((8,18,27))])
        means=np.stack([x.mean(axis=(0,1)) for x in strata])
        answer=a.method_means(means)
        np.testing.assert_allclose(answer[0],10/64,atol=1e-14)
        np.testing.assert_allclose(answer[1],4/3,atol=1e-14)
    def test_same_shared_draw_used_by_both_arms(self):
        strata=[np.zeros((8,n,27)) for n in a.SIZES]
        strata[0][:,:,0]=np.arange(37)[None,:]/100
        source=a.bootstrap(strata,repetitions=32,seed=1)
        arms=a.method_means(source)
        np.testing.assert_allclose(arms[:,1,0],arms[:,0,0]*(4/3)/(37/64),atol=1e-14)
        self.assertGreater(float(np.cov(arms[:,0,0],arms[:,1,0])[0,1]),0)
    def test_bootstrap_reproducible(self):
        rng=np.random.default_rng(1)
        strata=[rng.normal(size=(8,n,27)) for n in a.SIZES]
        np.testing.assert_array_equal(a.bootstrap(strata,8,2),a.bootstrap(strata,8,2))
    def test_linear_intercept_exact(self):
        target=np.linspace(-.3,.3,27)
        source=np.stack([target+.02,target+.02,target+.04,target+.06])
        np.testing.assert_allclose(a.method_means(source)[1],target,atol=1e-14)
    def test_quadratic_secondary_exact(self):
        values=[.1+.02*x+.005*x*x for x in (1,1,2,3)]
        source=np.array([np.full(27,v) for v in values])
        np.testing.assert_allclose(a.method_means(source)[2],.1,atol=1e-14)
    def test_gain_sign_and_negative_not_clipped(self):
        metrics=np.array([[.2,.3,.4,.5],[.3,.4,.5,.4],[0,0,0,0]])
        np.testing.assert_allclose(a.benefits(metrics),[-.1]*4,atol=1e-14)
    def test_invalid_shapes_rejected(self):
        with self.assertRaises(ValueError):
            a.split_strata([np.zeros((8,64,27))]*3)
        with self.assertRaises(ValueError):
            a.bootstrap([np.zeros((8,16,27))]*4,1,1)
        with self.assertRaises(ValueError):
            a.method_means(np.zeros((3,27)))
        with self.assertRaises(ValueError):
            a.benefits(np.zeros((2,4)))
    def test_half_arm_counts_and_raw_weights(self):
        self.assertEqual(8*(18+14),256)
        self.assertEqual(8*(18+5+9),256)
        source=np.stack([np.ones(27),np.zeros(27),np.zeros(27),np.zeros(27)])
        np.testing.assert_allclose(a.method_means(source,raw_counts=(18,14))[0],18/32)

if __name__=='__main__':
    unittest.main()
