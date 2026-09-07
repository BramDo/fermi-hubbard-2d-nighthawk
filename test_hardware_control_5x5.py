import copy
from pathlib import Path
import tempfile
import unittest
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
from cuprate_2d_hubbard_pipeline import Cuprate2DConfig
from cuprate_2d_fermionic_mapping import build_network
from cuprate_2d_tflo import (compile_template,parameterized_network,bind,skeleton,
    flo_reference,initial_occupations,physical_observables)
from cuprate_2d_hardware_controls import (configurations,preparation,records,
    validate_records,corrected_paulis,quota_summary,budget_summary)


class TestControls(unittest.TestCase):
    def test_configurations_and_preparations(self):
        for cfg,N in zip(configurations(),(22,32)):
            occ=initial_occupations(cfg)
            self.assertEqual(int(occ.sum()),N)
            self.assertEqual(int(occ[::2].sum()),N//2)
            for flip in (0,1):
                mask=np.full(cfg.qubits,flip,dtype=int)
                circuit=preparation(cfg,mask)
                actual=np.zeros(cfg.qubits,dtype=int)
                for inst in circuit.data:
                    self.assertEqual(inst.operation.name,'x')
                    actual[circuit.find_bit(inst.qubits[0]).index]^=1
                np.testing.assert_array_equal(actual^mask,occ)

    def test_allocation_and_scope_guards(self):
        rows=records(list(range(72)),np.zeros((4,50),dtype=int))
        self.assertEqual(len(rows),12); self.assertEqual(sum(r['shots'] for r in rows),6144)
        bad=copy.deepcopy(rows)
        next(r for r in bad if r['role']=='dynamics')['U']=8
        with self.assertRaises(ValueError): validate_records(bad)
        bad=copy.deepcopy(rows); bad[0]['shots']=1024
        with self.assertRaises(ValueError): validate_records(bad)

    def test_FLO_against_exact_statevector(self):
        cfg=Cuprate2DConfig(lx=2,ly=2,holes=1,steps=2,dt=.2,u_over_t=0.)
        for T in (0.,.1,.4):
            from dataclasses import replace
            circuit=(preparation(cfg,np.zeros(cfg.qubits,dtype=int)) if T==0
                     else build_network(replace(cfg,dt=T/2)))
            state=Statevector.from_instruction(circuit).data
            prob=np.abs(state)**2
            bits=((np.arange(256)[:,None]>>np.arange(8))&1)
            z=1-2*bits
            exact=np.concatenate([prob@z,prob@(z[:,::2]*z[:,1::2])])
            actual,cov=flo_reference(cfg,T)
            np.testing.assert_allclose(actual,exact,atol=3e-12,rtol=0)
            self.assertLess(float(np.max(np.abs(cov@cov-cov))),1e-12)

    def test_fixed_native_skeleton_and_state(self):
        cfg=Cuprate2DConfig(lx=2,ly=2,holes=1,steps=2,dt=.2)
        template=compile_template(parameterized_network(cfg))
        zero=bind(template,cfg,.4,0.); interacting=bind(template,cfg,.4,8.)
        self.assertEqual(skeleton(zero),skeleton(interacting))
        from dataclasses import replace
        for U,circuit in [(0.,zero),(8.,interacting)]:
            expected=Statevector.from_instruction(build_network(replace(cfg,u_over_t=U))).data
            actual=Statevector.from_instruction(circuit).data
            np.testing.assert_allclose(actual,expected,atol=5e-11,rtol=0)

    def test_readout_inverse_with_correlations_and_masks(self):
        ideal=np.array([.11,.23,.19,.47])
        errors=np.array([[.02,.04],[.03,.06]])
        for mask in ([0,0],[0,1],[1,0],[1,1]):
            permutation=np.arange(4)^(2*mask[0]+mask[1])
            matrices=[np.array([[1-errors[0,q],errors[1,q]],[errors[0,q],1-errors[1,q]]]) for q in range(2)]
            native=np.kron(*matrices)@ideal[permutation]
            decoded=native[permutation]
            z0=np.array([1,1,-1,-1]); z1=np.array([1,-1,1,-1])
            measured=np.array([decoded@z0,decoded@z1,decoded@(z0*z1)])
            expected=np.array([ideal@z0,ideal@z1,ideal@(z0*z1)])
            np.testing.assert_allclose(corrected_paulis(measured,mask,errors),expected,atol=1e-13)
            batch=corrected_paulis(np.tile(measured,(3,1)),mask,np.tile(errors,(3,1,1)))
            np.testing.assert_allclose(batch,np.tile(expected,(3,1)),atol=1e-13)

    def test_quota_and_budget(self):
        self.assertTrue(budget_summary(.2)['pass'])
        self.assertFalse(budget_summary(.8)['pass'])
        self.assertFalse(quota_summary({'usage_consumed_seconds':38})['remaining_quota_reported'])
        with self.assertRaises(ValueError): quota_summary({'usage_remaining_seconds':4.9})
        with self.assertRaises(ValueError): budget_summary(float('nan'))

    def test_exactly_once_success_and_confirmation(self):
        from run_hardware_control_5x5_once import dispatch_once
        class Job:
            def job_id(self): return 'offline-test'
        intent=dict(cap_seconds=5,authorized_one_new_job=True,automatic_retry=False,tag='local',plan_sha256='test')
        count=[]
        with tempfile.TemporaryDirectory() as directory:
            lock=Path(directory)/'attempt.json'; receipt=Path(directory)/'receipt.json'
            def send(): count.append(1); return Job()
            with self.assertRaises(PermissionError): dispatch_once(lock,receipt,intent,send)
            self.assertFalse(lock.exists()); self.assertEqual(count,[])
            import contextlib,io
            with contextlib.redirect_stdout(io.StringIO()):
                dispatch_once(lock,receipt,intent,send,confirmed=True)
            with self.assertRaises(FileExistsError): dispatch_once(lock,receipt,intent,send,confirmed=True)
            self.assertEqual(count,[1]); self.assertTrue(lock.exists())

    def test_ambiguous_submission_does_not_retry(self):
        from run_hardware_control_5x5_once import dispatch_once
        intent=dict(cap_seconds=5,authorized_one_new_job=True,automatic_retry=False,tag='local',plan_sha256='test')
        calls=[]
        with tempfile.TemporaryDirectory() as directory:
            lock=Path(directory)/'attempt.json'; receipt=Path(directory)/'receipt.json'
            def fail(): calls.append(1); raise TimeoutError()
            with self.assertRaises(TimeoutError): dispatch_once(lock,receipt,intent,fail,confirmed=True)
            with self.assertRaises(FileExistsError): dispatch_once(lock,receipt,intent,fail,confirmed=True)
            self.assertEqual(calls,[1]); self.assertTrue(lock.exists())


if __name__=='__main__': unittest.main(verbosity=2)
