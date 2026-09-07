import itertools
import unittest
import numpy as np
import aer_readout_tflo_zne as r

class ReadoutTests(unittest.TestCase):
    def test_identity_and_masks(self):
        rng=np.random.default_rng(34)
        bits=rng.integers(0,2,(100,18)); p=r.pauli_samples(bits).mean(axis=0)
        for mask in [np.zeros(18),np.ones(18),np.arange(18)%2]:
            np.testing.assert_allclose(r.correct_moments(p,mask,np.zeros((2,18))),p,atol=1e-14)

    def test_asymmetric_correlated_joint_distribution_all_masks(self):
        # Exact two-bit probability enumeration; independent readout, correlated inputs.
        latent=np.array([.51,.09,.17,.23])
        states=np.array(list(itertools.product([0,1],repeat=2)))
        errors=np.tile([[.07],[.19]],(1,18)); errors[:,1]=[.11,.03]
        for mask2 in itertools.product([0,1],repeat=2):
            out=np.zeros(4)
            for i,x in enumerate(states):
                for j,y in enumerate(states):
                    prob=latent[i]
                    for q in range(2):
                        physical=x[q]^mask2[q]
                        e=errors[physical,q]
                        prob*=1-e if y[q]==physical else e
                    out[j]+=prob
            decoded=states^mask2
            p=np.zeros(27)
            p[:2]=out@(1-2*decoded); p[18]=out@np.prod(1-2*decoded,axis=1)
            mask=np.zeros(18); mask[:2]=mask2
            fixed=r.correct_moments(p,mask,errors)
            np.testing.assert_allclose(fixed[:2],latent@(1-2*states),atol=1e-14)
            self.assertAlmostEqual(fixed[18],latent@np.prod(1-2*states,axis=1),14)
            # Independent linear-system inversion of the full 4x4 assignment matrix.
            matrix=np.empty((4,4))
            for i,x in enumerate(states):
                for j,y in enumerate(states):
                    matrix[j,i]=np.prod([1-errors[x[q]^mask2[q],q] if y[q]==(x[q]^mask2[q]) else errors[x[q]^mask2[q],q] for q in range(2)])
            np.testing.assert_allclose(np.linalg.solve(matrix,out),latent,atol=1e-14)

    def test_singular_refused(self):
        with self.assertRaises(ValueError):
            r.correct_moments(np.zeros(27),np.zeros(18),np.full((2,18),.45))

    def test_zero_calibration_not_false_certainty(self):
        c=np.zeros((2,18)); e=r.calibration_mean(c)
        self.assertTrue(np.all(e>0)); self.assertAlmostEqual(e[0,0],.5/65)

    def test_calibration_endianness(self):
        bits=np.zeros((2,64,18),dtype=int); bits[1]=1
        bits[0,:3,0]=1; bits[1,:5,17]=0
        c=r.calibration_counts(bits)
        self.assertEqual(c[0,0],3); self.assertEqual(c[1,17],5); self.assertEqual(c.sum(),8)

    def test_allocation_and_cost(self):
        options=[(float(np.sum(r.W**2/[n,m,48-n-m])),(n,m,48-n-m)) for n in range(1,47) for m in range(1,48-n)]
        best=min(options)
        self.assertEqual(best[1],r.ZNE_SHOTS)
        self.assertEqual(8*sum(r.ZNE_SHOTS)+128,512)
        self.assertEqual((216+2*56+3*112)*1008,669312)
        self.assertEqual(192+6*32+128,512)

    def test_seed_disjoint(self):
        labels=[r.train_seed(s,t)+k for s in range(6) for t in range(8) for k in range(4)]
        self.assertEqual(len(labels),len(set(labels)))
        for s,t in [(-1,0),(6,0),(0,8)]:
            with self.assertRaises(ValueError): r.train_seed(s,t)

    def test_raw_shared_strata_and_identity_tflo(self):
        rng=np.random.default_rng(99)
        refs=rng.uniform(-.6,.6,(6,27)); times=np.arange(6)/10
        training=np.repeat(refs[:,None,:],8,axis=1)
        strata=rng.uniform(-.5,.5,(6,8,27))
        p,_=r.all_methods(strata,training,np.zeros((8,18)),np.zeros((2,18)),refs,times)
        expected=sum(n*strata[i].mean(axis=0) for i,n in enumerate(r.F1_SIZES))/64
        np.testing.assert_allclose(p[0],expected,atol=1e-14)
        np.testing.assert_allclose(p[2],strata[0].mean(axis=0),atol=1e-12)
        np.testing.assert_allclose(p[2],p[4],atol=1e-14)
        np.testing.assert_allclose(p[3],p[5],atol=1e-14)
        np.testing.assert_array_equal(p[6],refs[4])

if __name__=='__main__': unittest.main()
