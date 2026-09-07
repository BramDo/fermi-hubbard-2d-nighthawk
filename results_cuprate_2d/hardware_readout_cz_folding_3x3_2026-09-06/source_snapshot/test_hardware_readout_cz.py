import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
import numpy as np
from qiskit import QuantumCircuit,QuantumRegister,ClassicalRegister,qpy
import run_hardware_readout_cz_once as h
import analyze_hardware_readout_cz as a

class HardwareTests(unittest.TestCase):
    def parent(self): return {'records':[{'readout_mask_little_endian':[t%2]*18} for t in range(8)]}
    def intent(self): return {'authorized_one_new_job':True,'cap_seconds':5,'tag':'test-only','plan_sha256':'frozen-test'}

    def test_records_counts(self):
        rows=h.records(self.parent())
        self.assertEqual(sum(x['shots'] for x in rows),808); self.assertEqual(len(rows),26)
        self.assertEqual(rows[:2],[{'setting_id':f'readout_all{s}','twirl_id':0,'role':'calibration','state':s,'shots':64,'readout_mask_little_endian':[0]*18} for s in range(2)])
        self.assertEqual(rows,h.records(self.parent()))

    def test_bad_allocation_rejected(self):
        rows=h.records(self.parent()); rows[4]['shots']+=1
        with self.assertRaises(ValueError): h.validate_records(rows)

    def test_duplicate_rejected(self):
        rows=h.records(self.parent()); rows[3]=rows[2]
        with self.assertRaises(ValueError): h.validate_records(rows)

    def test_embed_nontrivial_layout_and_register(self):
        qc=QuantumCircuit(QuantumRegister(18,'q'),ClassicalRegister(18,'meas'))
        qc.x(3); qc.rz(.51,5); qc.cz(5,7); qc.measure(range(18),range(18)); qc.global_phase=.2
        layout=[112,113,114,115,116,117,118,119,109,108,107,106,105,104,103,102,101,111]
        out=h.embed(qc,layout)
        self.assertEqual(out.num_qubits,120); self.assertEqual(out.cregs[0].name,'meas')
        self.assertEqual(out.count_ops(),qc.count_ops())
        stream=io.BytesIO(); qpy.dump(out,stream); stream.seek(0)
        self.assertEqual(qpy.load(stream)[0],out)

    def test_bad_layout_rejected(self):
        qc=QuantumCircuit(18,18); qc.measure(range(18),range(18))
        with self.assertRaises(ValueError): h.embed(qc,[0]*18)
        with self.assertRaises(ValueError): h.embed(qc,list(range(18)),width=17)

    def test_unsupported_instruction_rejected(self):
        qc=QuantumCircuit(18,18); qc.h(0); qc.measure(range(18),range(18))
        with self.assertRaises(ValueError): h.embed(qc,list(range(18)))

    def test_literal_confirmation_before_work(self):
        with self.assertRaises(PermissionError): h.prepare(False)
        with self.assertRaises(PermissionError): h.submit(False)

    def test_options_hard_cap_no_builtin_mitigation(self):
        backend=Mock(default_rep_delay=1e-6)
        options=h.options_for(backend,'test-only')
        self.assertEqual(options['max_execution_time'],5)
        self.assertFalse(options['twirling']['enable_gates']); self.assertFalse(options['twirling']['enable_measure'])
        self.assertFalse(options['dynamical_decoupling']['enable'])
        self.assertEqual(options['execution']['rep_delay'],1e-6)

    def test_single_send_and_lock_precedes_post(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); calls=[]
            def send():
                self.assertTrue((root/'lock.json').exists()); calls.append(1)
                return Mock(job_id=lambda:'fake-test-job')
            with contextlib.redirect_stdout(io.StringIO()):
                h.dispatch_once(root/'lock.json',root/'receipt.json',self.intent(),send)
            with self.assertRaises(FileExistsError):
                h.dispatch_once(root/'lock.json',root/'receipt.json',self.intent(),send)
            self.assertEqual(calls,[1])

    def test_ambiguous_send_never_retried(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); calls=[]
            def send(): calls.append(1); raise RuntimeError('simulated transport failure')
            with self.assertRaises(RuntimeError): h.dispatch_once(root/'lock.json',root/'receipt.json',self.intent(),send)
            with self.assertRaises(FileExistsError): h.dispatch_once(root/'lock.json',root/'receipt.json',self.intent(),send)
            self.assertEqual(calls,[1]); self.assertFalse(json.loads((root/'dispatch_uncertain.json').read_text())['resubmit_allowed'])

    def test_wrong_cap_never_calls_send(self):
        callback=Mock(); intent={**self.intent(),'cap_seconds':6}
        with self.assertRaises(ValueError): h.dispatch_once('unused-test-lock','unused-receipt',intent,callback)
        callback.assert_not_called()

    def test_missing_authority_never_calls_send(self):
        callback=Mock(); intent={**self.intent(),'authorized_one_new_job':False}
        with self.assertRaises(ValueError): h.dispatch_once('unused-test-lock','unused-receipt',intent,callback)
        callback.assert_not_called()

    def test_prediction_weights_identity_readout(self):
        rng=np.random.default_rng(23); means=rng.uniform(-1,1,(5,8,27))
        p=a.predictions(means,np.zeros((8,18)),np.zeros((2,18)))
        expected=(27*means[0]+21*means[1]+16*means[2]).mean(axis=0)/64
        np.testing.assert_allclose(p[0],expected,atol=1e-14)
        np.testing.assert_allclose(p[2],p[3],atol=1e-14)
        design=np.c_[np.ones(3),[1,2,3]]
        intercept=np.linalg.lstsq(design,means[[0,3,4]].mean(axis=1),rcond=None)[0][0]
        np.testing.assert_allclose(intercept,p[2],atol=1e-14)

    def test_arm_and_union_costs(self):
        self.assertEqual((64+7+14)*8+128,808)
        self.assertEqual((27+7+14)*8+128,512)
        self.assertEqual((512+56*2+112*3)*1008,967680)
        self.assertEqual((216+56*2+112*3)*1008,669312)

    def test_calibration_shared_inverse(self):
        data=np.zeros((5,8,27)); errors=np.ones((2,18))*.05
        p=a.predictions(data,np.zeros((8,18)),errors)
        np.testing.assert_allclose(p,0,atol=1e-14)

    def test_wrong_shape_refused(self):
        with self.assertRaises(ValueError): a.predictions(np.zeros((4,8,27)),np.zeros((8,18)),np.zeros((2,18)))

if __name__=='__main__': unittest.main()
