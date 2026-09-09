import unittest
import numpy as np
from lmpf_2d.shot_aware import variance_penalties, solve_weights, objective_parts
from lmpf_2d.single_twirl import moment_table
from lmpf_2d.fit import fit_coefficients
from lmpf_2d.verify_shot_aware import inverse_penalties, direct_weights


class ShotAwareTests(unittest.TestCase):
    def test_pauli_variance_bound_without_readout(self):
        actual = variance_penalties(np.zeros((1,2,2)),np.zeros((4,2),int))
        np.testing.assert_allclose(actual,np.tile(1/np.array([43,7,14]),(1,3,1)),atol=1e-15)

    def test_range_bound_for_arbitrary_outcome_distributions(self):
        errors = np.array([[[.03,.07],[.09,.02]]])
        table = moment_table(errors,[1,0])[0]
        bound = np.ptp(table,axis=0)**2/4
        probs = np.random.default_rng(451).dirichlet(np.ones(4),size=100)
        variances = probs@(table*table)-(probs@table)**2
        self.assertTrue(np.all(variances <= bound+1e-12))
        for i in range(3):
            p = np.zeros(4)
            p[np.argmin(table[:,i])] += .5
            p[np.argmax(table[:,i])] += .5
            self.assertAlmostEqual(p@(table[:,i]**2)-(p@table[:,i])**2,bound[i],places=12)

    def test_inverse_variance_allocation_limit(self):
        f = np.zeros((1,4,4))
        f[0,0,0] = 1.
        penalty = (1/np.array([43,7,14]))[None,None,:]
        result = solve_weights(f,penalty)[0,0]
        np.testing.assert_allclose(result,np.array([43,7,14])/64,atol=1e-12)

    def test_scalar_ridge_limit_and_objective(self):
        v = np.array([[.8,0,0,0],[.3,.2,0,0],[.2,0,.15,0],[.1,0,0,.1]])
        f = v@v.T
        penalty = np.full((1,1,3),1/56)
        result = solve_weights(f[None,:,:],penalty)[0,0]
        np.testing.assert_allclose(result,fit_coefficients(f,ridge=1/56).coefficients,atol=1e-12)
        optimum = objective_parts(f,penalty[0,0],result)['surrogate_objective']
        for c in ([1,0,0],[0,1,0],[0,0,1],[1/3]*3):
            self.assertLessEqual(optimum,objective_parts(f,penalty[0,0],c)['surrogate_objective']+1e-12)

    def test_invalid_penalty_and_original_are_rejected(self):
        f = np.eye(4)[None,:,:]
        for penalty in (np.zeros((1,1,3)),np.full((1,1,3),-1),np.full((1,1,3),np.nan)):
            with self.assertRaises(ValueError):
                solve_weights(f,penalty)
        bad = f.copy()
        bad[0,0,1] = bad[0,1,0] = 2
        with self.assertRaises(ValueError):
            solve_weights(bad,np.full((1,1,3),100.))
        with self.assertRaises(ValueError):
            variance_penalties(np.zeros((1,2,2)),np.zeros((4,2),int),[43,0,14])

    def test_independent_assignment_range_and_KKT(self):
        rng = np.random.default_rng(452)
        errors = rng.uniform(.01,.12,size=(11,2,2))
        masks = np.array([[1,0],[1,0],[0,1],[1,1]])
        p = variance_penalties(errors,masks)
        np.testing.assert_allclose(p,inverse_penalties(errors,masks),atol=1e-12)
        v = rng.normal(size=(3,4,7))
        f = v@v.transpose(0,2,1)
        np.testing.assert_allclose(solve_weights(f,p),direct_weights(f,p),atol=1e-11)


if __name__=='__main__':
    unittest.main(verbosity=2)
