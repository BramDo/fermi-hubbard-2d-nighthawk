import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
import numpy as np
from qiskit import QuantumCircuit,qpy
from qiskit.quantum_info import Operator,Statevector
import run_hardware_6x6_rocz_once as h
import analyze_hardware_6x6_rocz as a

class Hardware6Tests(unittest.TestCase):
    def masks(self): return [[t%2]*72 for t in range(8)]
    def intent(self): return {'authorized_one_new_job':True,'cap_seconds':15,'tag':'test-only','plan_sha256':'test'}
    def test_records_counts(self):
        rows=h.records(self.masks())
        self.assertEqual(sum(r['shots'] for r in rows),13312)
        self.assertEqual(rows,h.records(self.masks()))
        for f in (1,2,3): self.assertEqual(sum(r['shots'] for r in rows if r.get('factor')==f),4096)
    def test_bad_allocation(self):
        rows=h.records(self.masks()); rows[3]['shots']+=1
        with self.assertRaises(ValueError): h.validate_records(rows)
    def test_duplicate(self):
        rows=h.records(self.masks()); rows[3]=rows[2]
        with self.assertRaises(ValueError): h.validate_records(rows)
    def test_bad_masks(self):
        rows=h.records(self.masks()); rows[2]['readout_mask_little_endian'][0]=2
        with self.assertRaises(ValueError): h.validate_records(rows)
    def test_confirmation(self):
        with self.assertRaises(PermissionError): h.prepare()
        with self.assertRaises(PermissionError): h.submit()
    def test_cap_options(self):
        op=h.options_for(Mock(default_rep_delay=1e-6),'test')
        self.assertEqual(op['max_execution_time'],15)
        self.assertFalse(op['twirling']['enable_gates']); self.assertFalse(op['twirling']['enable_measure'])
        self.assertFalse(op['dynamical_decoupling']['enable'])
    def test_dispatch_lock_and_single_post(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); calls=[]
            def send():
                self.assertTrue((root/'lock').exists()); calls.append(1)
                return Mock(job_id=lambda:'fake')
            with contextlib.redirect_stdout(io.StringIO()):
                h.dispatch_once(root/'lock',root/'receipt',self.intent(),send)
            with self.assertRaises(FileExistsError): h.dispatch_once(root/'lock',root/'receipt',self.intent(),send)
            self.assertEqual(calls,[1])
            self.assertEqual(h.safe.read(root/'receipt')['shots'],13312)
    def test_ambiguous_no_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); calls=[]
            def send(): calls.append(1); raise RuntimeError('simulated')
            with self.assertRaises(RuntimeError): h.dispatch_once(root/'lock',root/'receipt',self.intent(),send)
            with self.assertRaises(FileExistsError): h.dispatch_once(root/'lock',root/'receipt',self.intent(),send)
            self.assertEqual(calls,[1])
    def test_wrong_cap_or_authority_no_send(self):
        for change in [{'cap_seconds':5},{'cap_seconds':16},{'authorized_one_new_job':False}]:
            send=Mock()
            with self.assertRaises(ValueError): h.dispatch_once('unused-lock','unused-receipt',{**self.intent(),**change},send)
            send.assert_not_called()
    def test_embedding_72_order_and_qpy(self):
        q=QuantumCircuit(72); q.x(3); q.rz(.4,15); q.cz(15,16); q.global_phase=.7
        out=h.embed(q,list(reversed(range(72))))
        self.assertEqual(out.num_qubits,120); self.assertEqual(out.num_clbits,72)
        self.assertEqual(out.cregs[0].name,'meas')
        stream=io.BytesIO(); qpy.dump(out,stream); stream.seek(0)
        self.assertEqual(qpy.load(stream)[0],out)
    def test_bad_embedding(self):
        with self.assertRaises(ValueError): h.embed(QuantumCircuit(72),[0]*72)
        q=QuantumCircuit(72); q.h(2)
        with self.assertRaises(ValueError): h.embed(q,list(range(72)))
    def test_small_full_network_compilation_twirling_folding(self):
        cfg=h.benchmark.cfg_for(2)
        logical=h.build_network(cfg); native=h.compile_template(logical)
        self.assertTrue(Operator(native).equiv(Operator(logical)))
        original=Statevector.from_instruction(logical)
        for seed in range(3):
            twirled,mask=h.explicit_twirl(native,seed)
            for f in (1,2,3):
                folded,_=h.folding.fold_cz(twirled,f,91)
                for q in np.flatnonzero(mask): folded.x(int(q))
                self.assertTrue(Statevector.from_instruction(folded).equiv(original))
    def test_readout_inverse_vs_confusion_matrix(self):
        rng=np.random.default_rng(14)
        errors=rng.uniform(.005,.13,(2,72))
        masks=np.array(self.masks()); observed=np.zeros((3,8,108)); ideal=np.zeros_like(observed)
        for t in range(8):
            for site in range(36):
                p=rng.dirichlet(np.ones(4))
                channels=[]
                for q in (2*site,2*site+1):
                    e0,e1=errors[:,q]; A=np.array([[1-e0,e1],[e0,1-e1]])
                    X=np.array([[0,1],[1,0]]) if masks[t,q] else np.eye(2)
                    channels.append(X@A@X)
                measured=np.kron(channels[0],channels[1])@p
                for v,out in [(p,ideal),(measured,observed)]:
                    out[:,t,2*site]=np.array([1,1,-1,-1])@v
                    out[:,t,2*site+1]=np.array([1,-1,1,-1])@v
                    out[:,t,72+site]=np.array([1,-1,-1,1])@v
        np.testing.assert_allclose(a.correct(observed,masks,errors),ideal,atol=1e-13)
    def test_linear_weights_vs_lstsq(self):
        rng=np.random.default_rng(15); means=rng.uniform(-.6,.6,(3,8,108))
        pred=a.predictions(means,np.zeros((8,72)),np.zeros((2,72)))
        expected=np.linalg.lstsq(np.c_[np.ones(3),[1,2,3]],means.mean(axis=1),rcond=None)[0][0]
        np.testing.assert_allclose(pred[2],expected,atol=1e-14)
        np.testing.assert_allclose(pred[0],pred[1],atol=1e-14)
    def test_unstable_readout_refused(self):
        with self.assertRaises(ValueError): a.correct(np.zeros((3,8,108)),np.zeros((8,72)),np.ones((2,72))*.49)
    def test_zero_and_occupied_pair_bounds(self):
        p=np.ones(108)
        np.testing.assert_allclose(a.pair_probabilities(p)[:,0],1)
        np.testing.assert_allclose(a.physical_observables(p),0)
        p[:72]=-1
        expected=np.tile([2,0,1],(36,1))
        np.testing.assert_allclose(a.physical_observables(p),expected)
    def test_bit_order_72(self):
        s='0'*71+'1'
        b=a.decode_bitstrings([s],72,[0]*72)
        self.assertEqual(b[0,0],1); self.assertEqual(b.sum(),1)

if __name__=='__main__': unittest.main()

