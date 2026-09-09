"""Independent checks for archived-data preparation, no hardware connection."""
import itertools,unittest
import numpy as np
from lmpf_2d.hardware_inputs import moment_samples,decode
from lmpf_2d.model import features
from lmpf_2d.fit import fit_coefficients,richardson_weights

class HardwareInputTests(unittest.TestCase):
    def test_twirl_and_asymmetric_readout_order(self):
        bits=np.array(list(itertools.product([0,1],repeat=2)))[:,::-1]
        errors=np.array([[.03,.06],[.08,.02]])
        assignment=np.kron([[.94,.06],[.02,.98]],[[.97,.03],[.08,.92]])
        for mask in itertools.product([0,1],repeat=2):
            twirled=bits^np.array(mask)
            truth_index=twirled[:,0]+2*twirled[:,1]
            corrected=moment_samples(bits,mask,errors)
            np.testing.assert_allclose(assignment[truth_index]@corrected,features(bits,[0,1]),atol=1e-12)
    def test_invalid_strings_rejected(self):
        for strings in [['0x1'],['010'],['01x1'],[]]:
            with self.assertRaises(ValueError):decode(strings,4)
    def test_bit_endianness(self):
        np.testing.assert_array_equal(decode(['1001','0110'],4),[[1,0,0,1],[0,1,1,0]])
    def test_projection_objective_not_worse_than_richardson(self):
        rng=np.random.default_rng(20260908);w=richardson_weights([1,2,3])
        for _ in range(30):
            v=rng.normal(size=(4,20));f=v@v.T;fit=fit_coefficients(f)
            zne=float(f[0,0]-2*f[0,1:]@w+w@f[1:,1:]@w)
            self.assertLessEqual(fit.projection_residual,zne+1e-9)

if __name__=='__main__':unittest.main(verbosity=2)
