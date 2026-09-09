import unittest
import numpy as np
from lmpf_2d.single_twirl import OUTCOMES, subset_indices, counts4, moment_table, estimate_batch, physical, pair_probabilities
from lmpf_2d.hardware_inputs import moment_samples
from lmpf_2d.verify_single_twirl import inverse_means


class SingleTwirlTests(unittest.TestCase):
    def test_moment_table_matches_existing_readout_order(self):
        errors = np.array([[[.03,.08],[.07,.02]],[[.01,.02],[.09,.12]]])
        for mask in ([0,0],[1,0],[0,1],[1,1]):
            actual = moment_table(errors,mask)
            for i in range(2):
                np.testing.assert_allclose(actual[i],moment_samples(OUTCOMES,mask,errors[i]),atol=1e-12)

    def test_fixed_subset_is_disjoint_complete_and_reproducible(self):
        shared, extra = subset_indices()
        self.assertEqual((len(shared),len(extra)),(43,21))
        np.testing.assert_array_equal(np.sort(np.r_[shared,extra]),np.arange(64))
        np.testing.assert_array_equal(shared,subset_indices()[0])
        bits = OUTCOMES[np.arange(64)%4]
        np.testing.assert_array_equal(counts4(bits[shared])+counts4(bits[extra]),counts4(bits))

    def test_physical_transform_and_no_clipping(self):
        for i,bits in enumerate(OUTCOMES):
            z = 1-2*bits
            pauli = np.r_[z,z.prod()]
            np.testing.assert_array_equal(physical(pauli),[bits.sum(),bits[0]-bits[1],bits.prod()])
            expected = np.eye(4)[i]
            np.testing.assert_array_equal(pair_probabilities(pauli),expected)
        self.assertLess(pair_probabilities([0,0,3]).min(),0)

    def test_budget_strata_and_fixed_calibration_broadcast(self):
        counts = np.array([np.diag([43,21,7,14])]*2)
        weights = np.tile([1.,0,0],(3,1))
        values = estimate_batch(counts,np.zeros((1,2,2)),np.zeros((4,2),int),weights)
        np.testing.assert_array_equal(values[:,3],[[1,1,1],[1,1,1]])
        np.testing.assert_array_equal(values[:,4],values[:,1])
        self.assertGreater(np.max(abs(values[:,2])),1.)
        with self.assertRaises(ValueError):
            estimate_batch(counts+1,np.zeros((1,2,2)),np.zeros((4,2),int),weights)

    def test_independent_assignment_inverse_agrees(self):
        rng = np.random.default_rng(412)
        counts = np.stack([rng.multinomial(n,[.1,.3,.2,.4],size=7) for n in (43,21,7,14)],axis=1)
        errors = rng.uniform(.01,.12,size=(7,2,2))
        masks = np.array([[1,0],[1,0],[0,1],[1,1]])
        weights = np.array([[2.1,-.1,-1],[1.8,.2,-1],[2.6,-.2,-1.4]])
        np.testing.assert_allclose(estimate_batch(counts,errors,masks,weights),inverse_means(counts,errors,masks,weights),atol=1e-12)


if __name__ == '__main__':
    unittest.main(verbosity=2)
