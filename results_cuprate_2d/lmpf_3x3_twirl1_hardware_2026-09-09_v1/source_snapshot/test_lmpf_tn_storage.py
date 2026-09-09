import tempfile,unittest
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit
from lmpf_2d.operators import compile_steps,evolve_tn,dense_tn,overlap_network,evolve_dense
from lmpf_2d.tn_storage import save_tn,load_tn,bounded_contract,expectation_zero

class TNStorageTests(unittest.TestCase):
    def test_stability_accepts_valid_and_rejects_missing(self):
        from lmpf_2d.higher_bond import stability_flags
        valid={'failure':None,'overlaps_exact':np.eye(4),'fits':{'exact':{'ridge':{'coefficients':[1.,0.,0.]}}}}
        self.assertTrue(stability_flags(valid,valid)['passes_local_flags'])
        self.assertFalse(stability_flags(valid,{})['passes_local_flags'])
        rejected={'failure':None,'fits':{'exact':{'rejected':True}}}
        self.assertFalse(stability_flags(valid,rejected)['passes_local_flags'])
        changed={'failure':None,'overlaps_exact':np.eye(4),'fits':{'exact':{'ridge':{'coefficients':[1.1,0.,-.1]}}}}
        self.assertFalse(stability_flags(valid,changed)['passes_local_flags'])
    def test_round_trip_entangled_and_exponent(self):
        qc=QuantumCircuit(4);qc.ry(.33,0);qc.rxx(.47,0,1);qc.cx(1,2);qc.rzz(.26,2,3)
        steps=compile_steps(qc,lambda *_:.004)
        tn,_=evolve_tn(4,[(0,1),(1,2),(2,3)],{2:'Z'},steps,1.,chi=4)
        expected=evolve_dense(4,{2:'Z'},steps,1.)
        np.testing.assert_allclose(dense_tn(tn),expected,atol=1e-10)
        tn.equalize_norms_(value=2.)
        with tempfile.TemporaryDirectory(prefix='lmpf_tn_test_') as directory:
            prefix=Path(directory)/'state';save_tn(prefix,tn);loaded=load_tn(prefix)
            np.testing.assert_allclose(dense_tn(loaded),expected,atol=1e-10)
            self.assertAlmostEqual(bounded_contract(overlap_network(loaded,loaded))[0],float(np.sum(expected**2)),places=10)
            self.assertAlmostEqual(expectation_zero(loaded),float(sum(expected[ix] for ix in np.ndindex((4,)*4) if all(k in (0,3) for k in ix))),places=10)
            with self.assertRaises(FileExistsError):save_tn(prefix,loaded)
            with self.assertRaises(ValueError):bounded_contract(overlap_network(loaded,loaded),max_elements=0)

if __name__=='__main__':unittest.main(verbosity=2)
