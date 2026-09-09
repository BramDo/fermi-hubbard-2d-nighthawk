"""Offline gates: frozen allocation, exactly-once dispatch, secrets, quota and raw mapping."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import copy,json,unittest
from qiskit import QuantumCircuit
from qiskit.primitives.containers import BitArray,DataBin,SamplerPubResult
from lmpf_2d import floor_hardware as h
class FloorHardwareTests(unittest.TestCase):
    def draft(self):return h.safe.read(h.CANDIDATE/'hardware_candidate.json')
    def intent(self):return {'authorized_one_new_job':True,'cap_seconds':5,'total_shots':3072,'tag':'offline-test','plan_sha256':'test-hash'}
    def test_exact_twenty_pub_allocation(self):
        d=self.draft();h.validate_draft(d)
        self.assertEqual(len(d['records']),20);self.assertEqual(sum(r['shots'] for r in d['records']),3072)
        for role,total in (('calibration',512),('shared_factor1',512),('baseline_only_factor1',1024),('factor2',512),('factor3',512)):
            self.assertEqual(sum(r['shots'] for r in d['records'] if r['role']==role),total)
    def test_changed_draft_and_order_rejected(self):
        for key,value in (('backend','ibm_other'),('proposed_max_execution_time_seconds',6),('penalty_denominator',128),('automatic_retry',True)):
            d=self.draft();d[key]=value
            with self.assertRaises(ValueError):h.validate_draft(d)
        d=self.draft();d['records'][2],d['records'][3]=d['records'][3],d['records'][2]
        with self.assertRaises(ValueError):h.validate_draft(d)
    def test_physics_signature_ignores_only_metadata(self):
        c=QuantumCircuit(2,2);c.x(0);c.cz(0,1);c.measure([0,1],[0,1]);a=h.circuit_signature(c)
        c.metadata={'label':'new'};self.assertEqual(a,h.circuit_signature(c))
        c.x(1);self.assertNotEqual(a,h.circuit_signature(c))
    def test_wrong_authority_does_not_consume_attempt(self):
        with TemporaryDirectory() as d:
            p=Path(d);intent=self.intent();intent['cap_seconds']=6
            with self.assertRaises(ValueError):h.dispatch_once(p/'lock',p/'receipt',intent,lambda:None)
            self.assertFalse((p/'lock').exists())
    def test_exactly_one_send_and_receipt(self):
        with TemporaryDirectory() as d:
            p=Path(d);calls=[]
            def send():calls.append(1);return SimpleNamespace(job_id=lambda:'offline-fake-job')
            h.dispatch_once(p/'lock',p/'receipt',self.intent(),send)
            with self.assertRaises(FileExistsError):h.dispatch_once(p/'lock',p/'receipt',self.intent(),send)
            self.assertEqual(len(calls),1);self.assertEqual(json.loads((p/'receipt').read_text())['shots'],3072)
    def test_uncertain_send_keeps_lock_and_redacts(self):
        with TemporaryDirectory() as d:
            p=Path(d);calls=[]
            def send():calls.append(1);raise RuntimeError('synthetic-secret-not-for-log')
            with self.assertRaises(RuntimeError):h.dispatch_once(p/'lock',p/'receipt',self.intent(),send)
            self.assertTrue((p/'lock').exists());self.assertFalse((p/'receipt').exists())
            self.assertNotIn('synthetic-secret', (p/'dispatch_uncertain.json').read_text())
            with self.assertRaises(FileExistsError):h.dispatch_once(p/'lock',p/'receipt',self.intent(),send)
            self.assertEqual(len(calls),1)
    def test_quota_unknown_is_not_unlimited_and_low_is_rejected(self):
        self.assertFalse(h.quota_summary({'usage_consumed_seconds':10})['remaining_reported'])
        self.assertEqual(h.quota_summary({'usage_limit_seconds':20,'usage_consumed_seconds':12})['usage_remaining_seconds'],8)
        with self.assertRaises(ValueError):h.quota_summary({'usage_remaining_seconds':4})
        with self.assertRaises(ValueError):h.quota_summary({'usage_consumed_seconds':float('nan')})
    def test_sampler_options_hold_cap_and_disable_extra_mitigation(self):
        options=h.options('offline')
        self.assertEqual(options['max_execution_time'],5);self.assertEqual(options['execution']['rep_delay'],1e-6)
        self.assertFalse(options['twirling']['enable_gates']);self.assertFalse(options['twirling']['enable_measure'])
        self.assertFalse(options['dynamical_decoupling']['enable'])
    def test_retries_disabled_for_all_runtime_clients(self):
        def client():return SimpleNamespace(_session=SimpleNamespace(adapters={'https':SimpleNamespace(max_retries=None)}))
        a,b=client(),client();service=SimpleNamespace(_active_api_client=a,_api_clients={'a':a,'b':b})
        report=h.safe.disable_retries(service,SimpleNamespace(_api_client=a),SimpleNamespace(_service=service))
        self.assertEqual(report['runtime_sessions_with_retries_disabled'],2)
        for c in (a,b):self.assertEqual(c._session.adapters['https'].max_retries.total,0)
    def test_raw_archive_keeps_unique_block_ids_and_all_bits(self):
        records=[{'setting_id':'block0_shared','twirl_id':1,'shots':2,'readout_mask_little_endian':[0]*18},
                 {'setting_id':'block1_shared','twirl_id':1,'shots':2,'readout_mask_little_endian':[0]*18}]
        result=[SamplerPubResult(DataBin(meas=BitArray.from_samples(['0'*18,'1'+'0'*17])),metadata={}) for _ in records]
        with TemporaryDirectory() as d:
            got=h.archive_sampler_results(Path(d)/'raw.json',result,records,job_id='offline',width=18)
            self.assertEqual(len(got['records']),2);self.assertEqual(got['records'][0]['bitstrings'][1],'1'+'0'*17)
            with self.assertRaises(ValueError):h.archive_sampler_results(Path(d)/'bad.json',result,[records[0]]*2,job_id='offline',width=18)
if __name__=='__main__':unittest.main()
