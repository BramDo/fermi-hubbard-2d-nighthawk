import tempfile,unittest
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import Delay,Measure,Reset,Parameter
from qiskit.circuit.library import XGate,SXGate,RZGate,CZGate
from qiskit.quantum_info import Operator
from qiskit.transpiler import Target,InstructionProperties
import cuprate_2d_tflo_dd6 as m
import run_tflo_dd6_once as r


def target3():
    t=Target(num_qubits=3,dt=4e-9,pulse_alignment=1,acquire_alignment=1,granularity=1,min_length=2)
    for gate,duration in [(XGate(),40e-9),(SXGate(),40e-9),(RZGate(Parameter('a')),0.),
                          (Measure(),1.94e-6),(Reset(),400e-9)]:
        t.add_instruction(gate,{(q,):InstructionProperties(duration=duration,error=.001) for q in range(3)})
    t.add_instruction(CZGate(),{(a,b):InstructionProperties(duration=320e-9,error=.001)
        for a in range(3) for b in range(3) if a!=b})
    t.add_instruction(Delay(Parameter('duration')),{(q,):None for q in range(3)})
    return t


def unitary_only(c):
    out=QuantumCircuit(c.num_qubits); out.global_phase=c.global_phase
    for inst in c.data:
        if inst.operation.name not in ('delay','measure','barrier'):
            out.append(inst.operation,[c.find_bit(q).index for q in inst.qubits])
    return Operator(out)


class PilotTests(unittest.TestCase):
    def test_allocation(self):
        rows=m.records(list(range(72)),np.zeros((4,72),int))
        m.validate_records(rows)
        self.assertEqual(len(rows),76); self.assertEqual(sum(x['shots'] for x in rows),38912)
        self.assertEqual(len([x for x in rows if x['role']=='train']),48)
        self.assertEqual(len([x for x in rows if x['role']=='holdout']),16)
        self.assertEqual(len([x for x in rows if x['role']=='target']),8)

    def test_no_extra_target(self):
        rows=m.records(list(range(72)),np.zeros((4,72),int)); rows[2]['U']=6
        with self.assertRaises(ValueError): m.validate_records(rows)

    def test_budget(self):
        self.assertTrue(m.budget(6.)['pass'])
        self.assertFalse(m.budget(6.3)['pass'])
        with self.assertRaises(ValueError): m.budget(float('nan'))

    def test_quota_missing_not_unlimited(self):
        self.assertFalse(m.quota({'usage_consumed_seconds':41})['remaining_reported'])
        with self.assertRaises(ValueError): m.quota({'usage_remaining_seconds':14})

    def test_affine_identity(self):
        x=np.arange(18,dtype=float).reshape(6,3)/20
        beta=m.fit_affine(x,x)
        np.testing.assert_allclose(beta,np.tile([1.,0.],(3,1)),atol=1e-12)

    def test_affine_independent_lstsq(self):
        rng=np.random.default_rng(812); x=rng.uniform(-1,1,(6,8)); y=.6*x+.15
        got=m.fit_affine(x,y); expected=[]
        for i in range(8):
            A=np.vstack([np.column_stack([x[:,i],np.ones(6)]),np.sqrt(m.RIDGE)*np.eye(2)])
            yy=np.r_[y[:,i],np.sqrt(m.RIDGE)*np.array([1.,0.])]
            expected.append(np.linalg.lstsq(A,yy,rcond=None)[0])
        np.testing.assert_allclose(got,expected,atol=1e-12)

    def test_invalid_fit(self):
        with self.assertRaises(ValueError): m.fit_affine(np.zeros((3,2)),np.zeros((3,2)))
        with self.assertRaises(ValueError): m.fit_affine(np.zeros((6,2)),np.zeros((6,2)),ridge=0)

    def test_no_time_feature_bypass(self):
        x=np.full((6,2),.1); y=np.arange(12).reshape(6,2)/12
        model=m.fit_affine(x,y)
        a=m.apply_affine(model,x[0]); b=m.apply_affine(model,x[-1])
        np.testing.assert_array_equal(a,b)

    def test_dd_preserves_dense_unitary_and_timing(self):
        target=target3(); qc=QuantumCircuit(3,3)
        qc.sx(0); qc.cz(0,1)
        for _ in range(4): qc.cz(1,2); qc.rz(.31,2)
        qc.cz(0,1); qc.measure(range(3),range(3))
        off,on,info=m.schedule_pair(qc,target,[0,1,2])
        self.assertGreater(info['echo_pairs'],0)
        self.assertTrue(unitary_only(off).equiv(unitary_only(qc)))
        self.assertTrue(unitary_only(on).equiv(unitary_only(qc)))
        self.assertAlmostEqual(float(off.estimate_duration(target)),info['duration_seconds'],places=12)

    def test_parameterized_scheduling_before_bind(self):
        target=target3(); qc=QuantumCircuit(3,3); theta=Parameter('theta')
        qc.sx(0); qc.cz(0,1)
        for _ in range(4): qc.cz(1,2); qc.rz(theta,2)
        qc.cz(0,1); qc.measure(range(3),range(3))
        off,on,_=m.schedule_pair(qc,target,[0,1,2])
        for value in (0.,.8):
            self.assertTrue(unitary_only(off.assign_parameters({theta:value})).equiv(unitary_only(on.assign_parameters({theta:value}))))

    def test_unpaired_echo_rejected(self):
        qc=QuantumCircuit(1); qc.append(XGate(label=m.DD_LABEL),[0])
        with self.assertRaises(ValueError): m.wire_sequences(qc,drop_echo=True)

    def test_block_compiler_full_small_network(self):
        from dataclasses import replace
        from qiskit.quantum_info import Statevector
        from cuprate_2d_hubbard_pipeline import Cuprate2DConfig
        from cuprate_2d_tflo import parameterized_network,bind
        from compile_tflo_dd6_blocks import compile_blocks
        cfg=Cuprate2DConfig(lx=2,ly=2,holes=1,steps=2,dt=.2,t_prime_over_t=-.25,u_over_t=8.)
        logical=parameterized_network(cfg); native,info=compile_blocks(logical)
        self.assertLess(info['dense_cell_unitary_max_abs'],1e-11)
        rng=np.random.default_rng(991)
        for T,U in [(.2,0.),(.4,8.),(.37,3.1)]:
            vector=rng.normal(size=256)+1j*rng.normal(size=256); vector/=np.linalg.norm(vector)
            expected=Statevector(vector).evolve(bind(logical,cfg,T,U)).data
            got=Statevector(vector).evolve(bind(native,cfg,T,U)).data
            np.testing.assert_allclose(got,expected,atol=1e-10)

    def test_analysis_holdouts_and_target_do_not_train(self):
        from analyze_tflo_dd6 import transform
        rng=np.random.default_rng(816)
        points=rng.uniform(-.5,.5,(2,9,2,108))
        exact=.8*points[0,:6,1]+.1
        original,models,_=transform(points,exact)
        changed=points.copy(); changed[:,6:]=rng.uniform(-1,1,changed[:,6:].shape)
        altered,new_models,_=transform(changed,exact)
        np.testing.assert_array_equal(models,new_models)
        self.assertFalse(np.allclose(original[:,8,2],altered[:,8,2]))

    def test_analysis_identity(self):
        from analyze_tflo_dd6 import transform
        rng=np.random.default_rng(817); single=rng.uniform(-1,1,(9,108))
        points=np.broadcast_to(single[:,None,:],(2,9,2,108)).copy()
        predicted,_,_=transform(points,single[:6])
        np.testing.assert_allclose(predicted[:,:,2],points[:,:,1],atol=1e-12)

    def test_single_submission_success_and_lock(self):
        class Job:
            def job_id(self): return 'FAKE_TEST_ONLY'
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder); intent={'cap_seconds':15,'authorized_one_new_job':True,'automatic_retry':False,'tag':'TEST','plan_sha256':'TEST'}
            called=[]
            def send(): called.append(1); return Job()
            with self.assertRaises(PermissionError): r.dispatch_once(p/'lock',p/'receipt',intent,send)
            self.assertFalse((p/'lock').exists())
            r.dispatch_once(p/'lock',p/'receipt',intent,send,True)
            with self.assertRaises(ValueError): r.dispatch_once(p/'lock',p/'receipt',intent,send,True)
            self.assertEqual(len(called),1)

    def test_uncertain_submission_cannot_retry(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder); intent={'cap_seconds':15,'authorized_one_new_job':True,'automatic_retry':False,'tag':'TEST','plan_sha256':'TEST'}
            called=[]
            def send(): called.append(1); raise RuntimeError('FAKE_TEST_ONLY')
            with self.assertRaises(RuntimeError): r.dispatch_once(p/'lock',p/'receipt',intent,send,True)
            self.assertTrue((p/'lock').exists())
            with self.assertRaises(FileExistsError): r.dispatch_once(p/'lock',p/'receipt',intent,send,True)
            self.assertEqual(len(called),1)


if __name__=='__main__': unittest.main(verbosity=2)
