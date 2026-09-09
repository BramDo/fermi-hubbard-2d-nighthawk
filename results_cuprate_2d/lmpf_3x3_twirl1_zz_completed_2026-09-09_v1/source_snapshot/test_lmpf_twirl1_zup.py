"""Bounded twirl1 fitting and deadline regression tests."""
import time, unittest
import numpy as np
from lmpf_2d.twirl1_zup import TimedStep,zup_penalty,analyze_gram,compare_levels
from lmpf_2d.verify_shot_aware import direct_weights

class TestTwirl1Zup(unittest.TestCase):
    def gram(self):
        v=np.array([[.9,.1,.2,.1],[.5,.2,.1,.1],[.3,.2,.1,.04],[.2,.1,.05,.1]])
        return v@v.T

    def test_zup_penalty_closed_form_and_mask_invariance(self):
        e=np.array([[.01,.02],[.03,.04]])
        expected=1/(1-e[:,0].sum())**2/np.array([43,7,14])
        for mask in (np.zeros((4,2),int),np.ones((4,2),int)):
            np.testing.assert_allclose(zup_penalty(e,mask)[0,0],expected,atol=1e-15)

    def test_exact_norm_does_not_change_weights_or_G_b(self):
        raw=self.gram();before=raw.copy();p=np.array([[[.03,.2,.1]]])
        result=analyze_gram(raw,p)
        np.testing.assert_array_equal(raw,before)
        f=np.array(result['exact_norm_gram']);self.assertEqual(f[0,0],1.)
        np.testing.assert_array_equal(f[1:,:],raw[1:,:])
        expected=direct_weights(f[None],p)[0,0]
        np.testing.assert_allclose(result['weights'],expected,atol=1e-12)

    def test_invalid_gram_and_readout_rejected(self):
        p=np.ones((1,1,3))
        for raw in (np.diag([1.,1.,1.,-1.]),np.eye(4)*2,np.full((4,4),np.nan)):
            with self.assertRaises(ValueError):analyze_gram(raw,p)
        for error in (np.full((2,2),.49),np.full((2,2),-1.),np.zeros((1,2))):
            with self.assertRaises(ValueError):zup_penalty(error,np.zeros((4,2),int))

    def test_stability_flags_and_missing_level(self):
        p=np.array([[[.03,.2,.1]]]);a=analyze_gram(self.gram(),p)
        self.assertTrue(compare_levels(a,a)['exact_norm_local_flags_pass'])
        changed=self.gram();changed[1:,1:]*=1.5
        b=analyze_gram(changed,p)
        self.assertFalse(compare_levels(a,b)['exact_norm_local_flags_pass'])
        with self.assertRaises(ValueError):compare_levels(None,a)

    def test_deadline_wrapper_preserves_channel(self):
        class Fake:
            qubits=(0,1)
            def channel(self,scale):return np.eye(16)*(scale+1)
        f=Fake();s=TimedStep(f,time.monotonic()+10)
        self.assertEqual(s.qubits,(0,1))
        np.testing.assert_array_equal(s.channel(.5),f.channel(.5))
        with self.assertRaises(TimeoutError):TimedStep(f,time.monotonic()-1).channel(0.)

if __name__=='__main__':unittest.main()
