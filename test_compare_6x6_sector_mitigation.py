import unittest
import numpy as np
from compare_6x6_sector_mitigation import strict_success,site_samples,projected,WEIGHTS
from cuprate_2d_tflo import decode_bitstrings


class SectorTests(unittest.TestCase):
    def test_mask_and_endianness(self):
        np.testing.assert_array_equal(decode_bitstrings(['1001'],4,[1,1,0,0]),[[0,1,0,1]])

    def test_hand_computed_site_features(self):
        np.testing.assert_array_equal(site_samples([[1,0,1,1]]),[[[1,1,0],[2,0,1]]])

    def test_spin_sectors_not_just_total_number(self):
        np.testing.assert_array_equal(strict_success(np.array([[1,1,0,0],[1,0,1,0]]),1,1),[True,False])

    def test_reject_invalid_bits(self):
        with self.assertRaises(ValueError): strict_success([[0,2]],0,0)

    def test_empty_sector(self):
        with self.assertRaises(ValueError): projected(np.zeros(3),np.ones((3,2,3)),WEIGHTS)

    def test_zero_noise_identity(self):
        expected=np.array([[1.,1.,0.],[1.,-1.,0.]])
        result=projected(np.ones(3),np.repeat(expected[None],3,axis=0),WEIGHTS)
        np.testing.assert_allclose(result,expected,atol=1e-14)

    def test_linear_numerator_and_denominator(self):
        f=np.arange(1,4)
        expected=np.array([[1.,.4,.1],[1.,-.4,.1]])
        numerator=expected[None]+f[:,None,None]*np.array([[.1,.2,.05],[.1,-.2,.05]])
        success=1-.1*f
        np.testing.assert_allclose(projected(success,numerator,WEIGHTS),expected,atol=1e-14)
        self.assertAlmostEqual(float(WEIGHTS.sum()),1.)
        self.assertAlmostEqual(float(WEIGHTS@f),0.)

    def test_normalize_after_extrapolation(self):
        success=np.array([.2,.3,.4])
        num=np.array([2.,3.,5.])[:,None,None]
        correct=projected(success,num,WEIGHTS)
        self.assertFalse(np.allclose(correct,np.tensordot(WEIGHTS,num/success[:,None,None],axes=(0,0))))


if __name__=='__main__': unittest.main(verbosity=2)
