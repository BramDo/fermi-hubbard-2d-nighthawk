"""Local algebra and calibration-only selection tests; no QPU API calls."""
import copy
import io
import unittest

import numpy as np
from qiskit import qpy
from qiskit.quantum_info import Operator
from threadpoolctl import threadpool_limits

from cuprate_2d_hubbard_pipeline import Cuprate2DConfig
from cuprate_2d_tflo import parameterized_network,compile_template,explicit_twirl,bind,skeleton,pauli_samples
from cuprate_2d_tflo_refinement import (cleanup_one_qubit,cz_trace,select_u0,
    refit_locked_u0,evaluate_target,resample_paired)
from validate_cuprate_2d_fermionic_dynamics import phase_distance


class RefinementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=Cuprate2DConfig(lx=2,ly=2,holes=0,steps=1,dt=.1)
        cls.old=explicit_twirl(compile_template(parameterized_network(cls.cfg)),31)[0]
        cls.new=cleanup_one_qubit(cls.old)

    def test_full_operator_equivalence(self):
        for t,u in [(0.,0.),(.2,8.)]:
            a=Operator(bind(self.old,self.cfg,t,u)).data.ravel()
            b=Operator(bind(self.new,self.cfg,t,u)).data.ravel()
            self.assertLess(phase_distance(a,b),2e-9)

    def test_fixed_structure_and_CZ_trace(self):
        self.assertEqual(cz_trace(self.old),cz_trace(self.new))
        signature=skeleton(self.new)
        for t,u in [(0.,0.),(.3,0.),(.2,8.),(.4,8.)]:
            self.assertEqual(skeleton(bind(self.new,self.cfg,t,u)),signature)
        before=self.old.count_ops()
        after=self.new.count_ops()
        self.assertLess(after.get('x',0)+after.get('sx',0),before.get('x',0)+before.get('sx',0))

    def test_qpy_roundtrip_and_bound_rejection(self):
        buffer=io.BytesIO()
        qpy.dump(self.new,buffer)
        buffer.seek(0)
        self.assertEqual(qpy.load(buffer)[0],self.new)
        with self.assertRaises(ValueError):
            cleanup_one_qubit(bind(self.old,self.cfg,.2,0.))

    def fixture(self):
        rng=np.random.default_rng(12)
        raw={str(i):{j:rng.integers(0,2,(64,4),dtype=np.uint8) for j in range(8)} for i in range(8)}
        settings=[{'id':str(i),'u_over_t':0.,'role':'train' if i<6 else 'flo_holdout',
                   'time':i/10,'reference':pauli_samples(np.concatenate(list(raw[str(i)].values()))).mean(axis=0).tolist()} for i in range(8)]
        protocol={'candidate_tolerances':[0,1,2,3,4,18],'minimum_retained_per_U0_setting':32,'ridge':.001}
        return settings,raw,protocol

    def test_raw_baseline_not_forced_to_use_TFLO(self):
        settings,raw,protocol=self.fixture()
        winner,table=select_u0(settings,raw,1,1,protocol)
        self.assertEqual(winner['id'],'raw')
        self.assertEqual(winner['score'],0.)
        self.assertEqual(len(table),7)

    def test_U8_cannot_enter_selection_or_refitting(self):
        settings,raw,protocol=self.fixture()
        winner,_=select_u0(settings,raw,1,1,protocol)
        bad=copy.deepcopy(settings)
        bad[0]['u_over_t']=8.
        with self.assertRaises(ValueError):
            select_u0(bad,raw,1,1,protocol)
        with self.assertRaises(ValueError):
            refit_locked_u0(winner,bad,raw,1,1,protocol)
        extra={**raw,'interacting':raw['0']}
        with self.assertRaises(ValueError):
            select_u0(settings,extra,1,1,protocol)

    def test_target_prediction_does_not_read_reference(self):
        settings,raw,protocol=self.fixture()
        winner,_=select_u0(settings,raw,1,1,protocol)
        target=[{'id':'target','u_over_t':8.,'time':.2,'reference':[0.]*6}]
        a=evaluate_target(winner,target,{'target':raw['0']},1,1)
        target[0]['reference']=['deliberately invalid reference']
        b=evaluate_target(winner,target,{'target':raw['0']},1,1)
        np.testing.assert_array_equal(a['corrected'],b['corrected'])

    def test_paired_twirl_resampling(self):
        raw={'a':{i:np.full((5,4),i,dtype=np.uint8) for i in range(4)},
             'b':{i:np.full((5,4),i,dtype=np.uint8) for i in range(4)}}
        sampled=resample_paired(raw,np.random.default_rng(88))
        for i in range(4):
            np.testing.assert_array_equal(sampled['a'][i],sampled['b'][i])


if __name__=='__main__':
    with threadpool_limits(limits=1):
        unittest.main(verbosity=2)
