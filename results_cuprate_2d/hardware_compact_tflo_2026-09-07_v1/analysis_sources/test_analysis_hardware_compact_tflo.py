import unittest
import numpy as np
from analyze_hardware_compact_tflo import transform,gain

class AnalysisTests(unittest.TestCase):
    def test_target_and_holdouts_do_not_train(self):
        rng=np.random.default_rng(312); p=rng.uniform(-.5,.5,(2,9,2,108)); y=rng.uniform(-1,1,(6,108))
        _,beta,null=transform(p,y); changed=p.copy(); changed[:,6:]+=1.3
        _,beta2,null2=transform(changed,y)
        np.testing.assert_array_equal(beta,beta2); np.testing.assert_array_equal(null,null2)

    def test_paired_gain_sign_and_axes(self):
        ref=np.zeros((36,3)); p=np.stack([np.ones_like(ref)*.2,np.ones_like(ref)*.1])
        b=np.broadcast_to(p,(400,2,36,3)); result=gain(p,b,ref)
        np.testing.assert_allclose(result['original_minus_compact_RMS'],[.1]*3,atol=1e-14)
        np.testing.assert_allclose(result['conditional_95pct_interval'],[[.1]*3]*2,atol=1e-14)

    def test_null_mean_affine_identity(self):
        rng=np.random.default_rng(911); p=rng.uniform(-.5,.5,(2,9,2,108)); y=rng.uniform(-1,1,(6,108))
        _,beta,null=transform(p,y)
        np.testing.assert_allclose(null,y.mean(0)-.001*beta[:,:,1]/6,atol=1e-12)

if __name__=='__main__': unittest.main(verbosity=2)
