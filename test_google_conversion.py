"""Bounded conversion tests; no quantum or dynamics jobs."""
import io, pickle, unittest
import numpy as np
from convert_google_hubbard import moments, direct_probabilities, physical_row
from google_hdf_safe import ArrayUnpickler

class ConversionTests(unittest.TestCase):
    def test_fock_states(self):
        got=moments([1,1,-1,-1],[1,-1,1,-1],[1,-1,-1,1])
        np.testing.assert_array_equal(got,[[0,0,0],[1,-1,0],[1,1,0],[2,0,1]])

    def test_mixed_states(self):
        p=np.random.default_rng(173).dirichlet(np.ones(4),size=100)
        zu=p @ np.array([1,1,-1,-1]); zd=p @ np.array([1,-1,1,-1]); zz=p @ np.array([1,-1,-1,1])
        expected=np.column_stack((p[:,1]+p[:,2]+2*p[:,3],p[:,2]-p[:,1],p[:,3]))
        np.testing.assert_allclose(moments(zu,zd,zz),expected,atol=3e-16)
        p2,got=direct_probabilities(zu,zd,zz)
        np.testing.assert_allclose(p2,p,atol=3e-16)
        np.testing.assert_allclose(got,expected,atol=3e-16)

    def test_spin_not_doubled(self):
        self.assertEqual(moments(-1,1,-1)[1],1)

    def test_no_clipping(self):
        self.assertLess(direct_probabilities(np.array([1.4]),np.array([1.4]),np.array([1.]))[0].min(),0)

    def test_shapes(self):
        with self.assertRaises(ValueError): moments([1,2],[1],[1])

    def test_restricted_unpickler(self):
        with self.assertRaises(pickle.UnpicklingError): ArrayUnpickler(io.BytesIO(b'cposix\nsystem\n.')).load()
        expected=np.array([('up',),(0,1)],dtype=object)
        np.testing.assert_array_equal(ArrayUnpickler(io.BytesIO(pickle.dumps(expected,protocol=4))).load(),expected)

    def fixture(self):
        d={k:[] for k in ['ev_time','method','initial_state','system_dims','onsite_term','n_layers','mag_field','obs_type','site_coords','spins','obs_val','obs_err']}
        for x in range(5):
            for y in range(5):
                for kind,coords,spins in [('Z',((x,y),),('up',)),('Z',((x,y),),('down',)),('ZZ',((x,y),(x,y)),('up','down'))]:
                    values=[.4,'raw','holon_stripe','5x5',8,3,'0',kind,coords,spins,1.,0.]
                    for k,v in zip(d,values): d[k].append(v)
        return d

    def test_complete_profile(self):
        d=self.fixture(); row=physical_row(d,5,.4)
        self.assertEqual(row['N'],0)
        self.assertEqual(row['onsite_ZZ_rows'],25)
        self.assertIsNone(physical_row(d,5,.401))

    def test_missing_duplicate_and_bounds(self):
        for mode in ('missing','duplicate','bounds'):
            d=self.fixture()
            if mode=='missing': d={k:v[:-1] for k,v in d.items()}
            elif mode=='duplicate': d={k:v+[v[0]] for k,v in d.items()}
            else: d['site_coords'][0]=((8,8),)
            with self.assertRaises(ValueError): physical_row(d,5,.4)

if __name__=='__main__': unittest.main()
