import unittest
import numpy as np
from qiskit.quantum_info import Statevector
from cuprate_2d_hubbard_pipeline import Cuprate2DConfig
from cuprate_2d_tflo import parameterized_network,bind
from cuprate_spin_correlation_probe import mps_moments,dense_z_moments,spin_from_z,flo_spin_moments,mixture,compare,invariant_checks

class Tests(unittest.TestCase):
    def test_random_mps_against_dense(self):
        rng=np.random.default_rng(20260906)
        arrays=[rng.normal(size=s)+1j*rng.normal(size=s) for s in ((1,2,2),(2,3,2),(3,2,2),(2,1,2))]
        dense=np.einsum('abp,bcq,cdr,des->pqrs',*arrays,optimize=True).reshape(-1)
        a=mps_moments(arrays); b=dense_z_moments(dense,little_endian=False)
        for x,y in zip(a,b): np.testing.assert_allclose(x,y,atol=1e-12,rtol=1e-12)
        invariant_checks(spin_from_z(a[1],a[2]))
    def test_product_state_zero_connected(self):
        arrays=[np.eye(2)[bit].reshape(1,1,2).astype(complex) for bit in (1,0,0,1)]
        _,s,p=mps_moments(arrays); row=spin_from_z(s,p)
        np.testing.assert_allclose(row[0],[1.,-1.],atol=1e-14)
        np.testing.assert_allclose(row[2],0.,atol=1e-14)
    def test_mixture_includes_classical_covariance(self):
        rows=[]
        for mean in (np.array([1.,-1.]),np.array([-1.,1.])):
            rows.append((mean,np.outer(mean,mean),np.zeros((2,2)),np.stack((np.ones(2),mean,np.zeros(2)),axis=-1)))
        row=mixture(rows)
        np.testing.assert_allclose(row[2],[[1.,-1.],[-1.,1.]],atol=1e-14)
        invariant_checks(row)
    def test_flo_wick_matches_full_quantum(self):
        cfg=Cuprate2DConfig(lx=2,ly=2,holes=0,steps=2)
        template=parameterized_network(cfg)
        for T in (0.,.2,.4):
            state=Statevector.from_instruction(bind(template,cfg,T,0.)).data
            _,z,zz=dense_z_moments(state)
            direct=spin_from_z(z,zz); flo=flo_spin_moments(cfg,T)
            for x,y in zip(direct,flo): np.testing.assert_allclose(x,y,atol=1e-12,rtol=0)
    def test_shells_do_not_cancel_signed_errors(self):
        a=np.zeros((4,4)); a[0,1]=.1; a[1,0]=.1; a[0,2]=-.1; a[2,0]=-.1
        c=compare(a,np.zeros_like(a),2,2)['distance_1']
        self.assertEqual(c['pairs'],4)
        self.assertAlmostEqual(c['mean_signed'],0.)
        self.assertGreater(c['rms'],0.)
    def test_safety_limits(self):
        with self.assertRaises(ValueError): spin_from_z(np.zeros(3),np.eye(3))
        with self.assertRaises(ValueError): dense_z_moments(np.ones(3))
        with self.assertRaises(TimeoutError): mps_moments([np.ones((1,1,2))]*2,deadline=0)

if __name__=='__main__': unittest.main()
