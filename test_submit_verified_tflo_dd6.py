import contextlib,hashlib,io,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch,Mock
import submit_verified_tflo_dd6 as s


class SubmitTests(unittest.TestCase):
    def exercise(self,mode):
        with tempfile.TemporaryDirectory() as tmp,contextlib.ExitStack() as stack:
            root=Path(tmp); r=s.r
            stack.enter_context(patch.object(r,'RUN',root))
            stack.enter_context(patch.object(r,'LOCK',root/'attempt.json'))
            plan={'cap_seconds':15,'authorized_one_new_job':True,'automatic_retry':False,
                'tag':'SYNTHETIC_TEST_ONLY','layout72':list(range(72)),'timing_fingerprint':'fp'}
            r.save(root/'plan.json',plan)
            previous={'options':{'max_execution_time':15},'timing_fingerprint':'fp',
                'instance_sha256':hashlib.sha256(b'unit-test').hexdigest(),
                'timing_by_pub':[{'index':i,'shots':512,'duration_seconds':1. if mode=='budget' else .00012} for i in range(76)]}
            r.save(root/'live_preflight.json',previous)
            class Target(dict): operation_names=['delay']
            target=Target(reset={(q,):NS(duration=4e-7) for q in range(120)})
            props=NS(faulty_qubits=lambda:[],faulty_gates=lambda:['synthetic_fault'] if mode=='fault' else [],last_update_date='test')
            backend=NS(num_qubits=120,target=target,status=lambda:NS(operational=True,pending_jobs=0),
                properties=lambda:props,default_rep_delay=1e-6,rep_delay_range=(1e-6,1e-3))
            service=NS(backend=lambda name:backend,active_account=lambda:{'instance':'unit-test'},
                usage=lambda:{'usage_remaining_seconds':14} if mode=='quota' else {})
            calls=[]
            class FakeJob:
                def job_id(self): return 'SYNTHETIC_NO_PROVIDER'
            def send(pubs): calls.append(len(pubs)); return FakeJob()
            sampler=NS(mode=None,options=NS(max_execution_time=15),run=send)
            stack.enter_context(patch.object(s,'QiskitRuntimeService',return_value=service))
            stack.enter_context(patch.object(s,'SamplerV2',return_value=sampler))
            stack.enter_context(patch.object(s,'cached_pubs',return_value=[NS(shots=512)]*76))
            stack.enter_context(patch.object(r,'verify',return_value=None))
            stack.enter_context(patch.object(s.m,'fingerprint',return_value=('changed' if mode=='timing' else 'fp',{})))
            stack.enter_context(patch.object(r,'options',return_value={'max_execution_time':16 if mode=='options' else 15}))
            stack.enter_context(patch.object(r.safe,'disable_retries',return_value={'test_only':True}))
            stack.enter_context(patch.object(r,'verify_cap',return_value={'verified':True,'test_only':True}))
            with contextlib.redirect_stdout(io.StringIO()):
                if mode=='success':
                    s.submit(True)
                    self.assertEqual(calls,[76]); self.assertTrue(r.LOCK.exists())
                    self.assertEqual(r.read(root/'job_receipt.json')['cap_seconds'],15)
                    with self.assertRaises(ValueError): s.submit(True)
                    self.assertEqual(calls,[76])
                else:
                    with self.assertRaises(ValueError): s.submit(True)
                    self.assertFalse(r.LOCK.exists()); self.assertEqual(calls,[])

    def test_success_once(self): self.exercise('success')
    def test_changed_timing_stops(self): self.exercise('timing')
    def test_fault_stops(self): self.exercise('fault')
    def test_insufficient_quota_stops(self): self.exercise('quota')
    def test_budget_excess_stops(self): self.exercise('budget')
    def test_options_change_stops(self): self.exercise('options')

    def test_missing_confirmation(self):
        with patch.object(s.r,'verify') as verify:
            with self.assertRaises(PermissionError): s.submit(False)
            verify.assert_not_called()

    def test_failed_preflight_not_reused(self):
        with self.assertRaises(ValueError): s.cached_pubs({}, {'status':'FAIL','budget':{'pass':False}})


if __name__=='__main__': unittest.main(verbosity=2)
