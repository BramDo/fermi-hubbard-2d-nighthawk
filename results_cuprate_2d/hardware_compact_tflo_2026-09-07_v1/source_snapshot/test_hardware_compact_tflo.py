"""No-provider validation of paired records, budget and exactly-once dispatch."""
import contextlib,copy,hashlib,io,tempfile,time,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
import run_hardware_compact_tflo as r

class Guards(unittest.TestCase):
    def test_records_pairing(self):
        rows=r.records(list(range(72)),[[i%2]*72 for i in range(4)])
        r.validate_records(rows)
        self.assertEqual(sum(x['shots'] for x in rows),38912)
        self.assertTrue(all(not x['dd'] for x in rows))
        self.assertEqual(rows,r.records(list(range(72)),[[i%2]*72 for i in range(4)]))
        for field,value in [('arm','original'),('U',99),('shots',1024),('dd',True),('pair_id',99)]:
            bad=copy.deepcopy(rows)
            if field=='arm': value=bad[3]['arm']
            bad[2][field]=value
            with self.assertRaises(ValueError): r.validate_records(bad)

    def test_confirmation_before_provider(self):
        with patch.object(r,'provider') as provider:
            with self.assertRaises(PermissionError): r.submit(False)
            provider.assert_not_called()

    def test_exactly_once_uncertain(self):
        for fail in (False,True):
            with tempfile.TemporaryDirectory() as tmp,contextlib.redirect_stdout(io.StringIO()):
                root=Path(tmp); intent=dict(cap_seconds=15,authorized_one_new_job=True,automatic_retry=False,tag='TEST',plan_sha256='TEST')
                calls=[]
                def send():
                    calls.append(1)
                    if fail: raise ConnectionError('synthetic')
                    return NS(job_id=lambda:'NO_PROVIDER')
                if fail:
                    with self.assertRaises(ConnectionError): r.dispatch_once(root/'lock.json',root/'receipt.json',intent,send,True)
                else: r.dispatch_once(root/'lock.json',root/'receipt.json',intent,send,True)
                with self.assertRaises((ValueError,FileExistsError)): r.dispatch_once(root/'lock.json',root/'receipt.json',intent,send,True)
                self.assertEqual(calls,[1]); self.assertTrue((root/'lock.json').exists())

    def exercise_dispatch(self,mode):
        with tempfile.TemporaryDirectory() as tmp,contextlib.ExitStack() as stack:
            root=Path(tmp); stack.enter_context(patch.object(r,'RUN',root)); stack.enter_context(patch.object(r,'LOCK',root/'attempt.json'))
            plan=dict(cap_seconds=15,authorized_one_new_job=True,automatic_retry=False,tag='TEST',layout72=list(range(72)),timing_fingerprint='fp',
                runtime=dict(qiskit=r.base.qiskit.__version__,qiskit_ibm_runtime=r.base.qiskit_ibm_runtime.__version__))
            r.save(root/'plan.json',plan)
            previous=dict(status='PASS_NOT_SUBMITTED',budget={'pass':True},checked_unix=time.time()-(1900 if mode=='stale' else 0),
                plan_sha256=r.digest(root/'plan.json'),options={'max_execution_time':15},instance_sha256='instance',timing_fingerprint='fp',
                timing_by_pub=[dict(index=i,shots=512,duration_seconds=1. if mode=='budget' else .0001) for i in range(76)])
            r.save(root/'live_preflight.json',previous)
            b=NS(default_rep_delay=1e-6,rep_delay_range=(1e-6,1e-3),target={'reset':{(q,):NS(duration=4e-7) for q in range(120)}})
            live=dict(instance_sha256='changed' if mode=='instance' else 'instance')
            stack.enter_context(patch.object(r,'frozen',return_value=(plan,[NS(shots=512)]*76)))
            stack.enter_context(patch.object(r,'verify',return_value=None))
            stack.enter_context(patch.object(r,'provider',return_value=(NS(),b,NS(),live)))
            stack.enter_context(patch.object(r.m,'fingerprint',return_value=('changed' if mode=='timing' else 'fp',{})))
            stack.enter_context(patch.object(r,'options',return_value={'max_execution_time':16 if mode=='options' else 15}))
            calls=[]
            def send(pubs): calls.append(len(pubs)); return NS(job_id=lambda:'NO_PROVIDER')
            sampler=NS(mode=None,options=NS(max_execution_time=15),run=send)
            stack.enter_context(patch.object(r,'SamplerV2',return_value=sampler))
            stack.enter_context(patch.object(r.safe,'disable_retries',return_value={'TEST':True}))
            stack.enter_context(patch.object(r,'verify_cap',return_value={'TEST':True}))
            with contextlib.redirect_stdout(io.StringIO()):
                if mode=='success':
                    r.submit(True); self.assertEqual(calls,[76]); self.assertTrue(r.LOCK.exists())
                    with self.assertRaises(ValueError): r.submit(True)
                    self.assertEqual(calls,[76])
                else:
                    with self.assertRaises(ValueError): r.submit(True)
                    self.assertEqual(calls,[]); self.assertFalse(r.LOCK.exists())

    def test_success_once(self): self.exercise_dispatch('success')
    def test_timing_changed(self): self.exercise_dispatch('timing')
    def test_options_changed(self): self.exercise_dispatch('options')
    def test_instance_changed(self): self.exercise_dispatch('instance')
    def test_stale_preflight(self): self.exercise_dispatch('stale')
    def test_budget_exceeded(self): self.exercise_dispatch('budget')

    def test_provider_fault_and_quota(self):
        for mode in ('fault','quota','unknown','success'):
            with contextlib.ExitStack() as stack:
                props=NS(faulty_qubits=lambda:[1] if mode=='fault' else [],faulty_gates=lambda:[],last_update_date='test')
                b=NS(name='ibm_phoenix',num_qubits=120,status=lambda:NS(operational=True,pending_jobs=0),properties=lambda:props)
                s=NS(backend=lambda name:b,usage=lambda:{'usage_remaining_seconds':14} if mode=='quota' else {},
                    active_account=lambda:{'instance':'test'},instances=lambda:[dict(crn='test',plan='open' if mode=='unknown' else 'pay-as-you-go')])
                stack.enter_context(patch.object(r,'QiskitRuntimeService',return_value=s))
                if mode=='success': self.assertTrue(r.provider()[3]['quota']['no_quota_limit_claimed'])
                else:
                    with self.assertRaises(ValueError): r.provider()

if __name__=='__main__': unittest.main(verbosity=2)
