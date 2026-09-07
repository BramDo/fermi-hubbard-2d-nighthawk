"""Independent small-model checks, outside all reported timing windows."""
import unittest
import numpy as np
from qiskit.quantum_info import Statevector
from cuprate_2d_hubbard_pipeline import Cuprate2DConfig
from cuprate_2d_tflo import initial_occupations,flo_reference,physical_observables,parameterized_network,bind
from benchmark_classical_mean6 import deny_inputs_and_network

class Tests(unittest.TestCase):
    def test_zero_time(self):
        cfg=Cuprate2DConfig(lx=6,ly=6,holes=4,steps=2)
        paulis,c=flo_reference(cfg,0.)
        bits=initial_occupations(cfg).astype(float); up=bits[::2]; down=bits[1::2]
        np.testing.assert_allclose(physical_observables(paulis),np.stack((up+down,up-down,up*down),axis=-1),atol=1e-14)
        self.assertAlmostEqual(np.trace(c).real,32.)
    def test_full_small_quantum_circuit(self):
        cfg=Cuprate2DConfig(lx=2,ly=2,holes=0,steps=2,t_prime_over_t=-.25)
        template=parameterized_network(cfg)
        for T in (.08,.4,.48):
            paulis,_=flo_reference(cfg,T)
            state=Statevector.from_instruction(bind(template,cfg,T,0.)).data
            probabilities=abs(state)**2
            bits=((np.arange(256)[:,None]>>np.arange(8))&1).astype(float)
            up=bits[:,::2]; down=bits[:,1::2]
            direct=np.stack((probabilities@(up+down),probabilities@(up-down),probabilities@(up*down)),axis=-1)
            np.testing.assert_allclose(physical_observables(paulis),direct,atol=1e-12,rtol=0)
    def test_invalid_time(self):
        cfg=Cuprate2DConfig(lx=2,ly=2,steps=2,holes=0)
        for T in (-1.,float('nan'),float('inf')):
            with self.assertRaises(ValueError): flo_reference(cfg,T)
    def test_linear_conversion_of_mean(self):
        cfg=Cuprate2DConfig(lx=2,ly=2,steps=2,holes=0)
        p=np.array([flo_reference(cfg,T)[0] for T in (.08,.2,.4)])
        np.testing.assert_allclose(physical_observables(p).mean(0),physical_observables(p.mean(0)),atol=1e-14)
    def test_forbidden_inputs(self):
        for path in ('results_cuprate_2d/old/summary.json','/home/example/.qiskit/qiskit-ibm.json','/tmp/.env'):
            with self.assertRaises(PermissionError): deny_inputs_and_network('open',(path,'r',0))
        deny_inputs_and_network('open',('/usr/lib/python3.12/os.py','r',0))
    def test_network_forbidden(self):
        with self.assertRaises(PermissionError): deny_inputs_and_network('socket.connect',())
        with self.assertRaises(PermissionError): deny_inputs_and_network('import',('qiskit_ibm_runtime',))

if __name__=='__main__': unittest.main()
