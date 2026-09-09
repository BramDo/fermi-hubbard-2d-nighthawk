"""Spin-down-specific checks: distinguish calibration columns even when equal in data."""
import unittest
import numpy as np
from lmpf_2d.twirl1_zdown import zdown_penalty,OBSERVABLE,CENTRAL_MODE_INDEX,SUPPORT
from lmpf_2d.twirl1_zup import zup_penalty

class TestTwirl1Zdown(unittest.TestCase):
    def test_correct_observable_and_second_calibration_mode(self):
        self.assertEqual((OBSERVABLE,CENTRAL_MODE_INDEX,SUPPORT),(9,1,{9:'Z'}))
        e=np.array([[.01,.07],[.03,.04]])
        actual=zdown_penalty(e,np.zeros((4,2),int))[0,0]
        expected=1/(1-e[:,1].sum())**2/np.array([43,7,14])
        np.testing.assert_allclose(actual,expected,atol=1e-15)
        self.assertGreater(np.max(abs(actual-zup_penalty(e,np.zeros((4,2),int))[0,0])),.001)

    def test_first_mode_changes_cannot_change_zdown_penalty(self):
        e=np.array([[.01,.07],[.03,.04]])
        m=np.zeros((4,2),int);original=zdown_penalty(e,m)
        changed=e.copy();changed[:,0]=[.08,.06]
        np.testing.assert_array_equal(zdown_penalty(changed,m),original)
        changed=e.copy();changed[0,1]=.15
        self.assertGreater(float(np.max(abs(zdown_penalty(changed,m)-original))),.01)

    def test_column_swap_and_mask_range_invariance(self):
        e=np.array([[.01,.07],[.03,.04]])
        original=zdown_penalty(e,np.zeros((4,2),int))
        for m in (np.ones((4,2),int),np.array([[0,1],[0,1],[1,0],[1,1]])):
            np.testing.assert_allclose(zdown_penalty(e,m),original,atol=1e-15)
            np.testing.assert_allclose(zup_penalty(e[:,::-1],m[:,::-1]),original,atol=1e-15)

    def test_invalid_readout_and_masks_rejected(self):
        for e in (np.full((2,2),.49),np.zeros((1,2)),np.full((2,2),np.nan)):
            with self.assertRaises(ValueError):zdown_penalty(e,np.zeros((4,2),int))
        for m in (np.ones((4,2))*2,np.zeros((3,2))):
            with self.assertRaises(ValueError):zdown_penalty(np.zeros((2,2)),m)

if __name__=='__main__':unittest.main()
