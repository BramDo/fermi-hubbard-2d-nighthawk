import io
from dataclasses import replace
import unittest
import numpy as np
from qiskit import QuantumCircuit,qpy
from qiskit.quantum_info import Operator,Statevector
from cuprate_2d_hubbard_pipeline import Cuprate2DConfig
from cuprate_2d_fermionic_mapping import build_network
from cuprate_2d_tflo import compile_template,explicit_twirl
import cuprate_2d_shallow_network as s

class ShallowTests(unittest.TestCase):
    def test_physical_event_counts(self):
        cfg=Cuprate2DConfig(lx=6,ly=6,holes=4,steps=2,dt=.2,u_over_t=8,t_prime_over_t=-.25)
        events=s.network_events(cfg)
        self.assertEqual(len(events),1024)
        self.assertEqual(sum(bool(x['hopping_angle']) for x in events),880)
        self.assertEqual(sum(bool(x['onsite_angle']) for x in events),144)
    def test_small_full_unitary_all_routes(self):
        cfg=Cuprate2DConfig(lx=2,ly=2,holes=0,steps=2,dt=.2,u_over_t=8,t_prime_over_t=-.25,chemical_potential=.17)
        original=Operator(build_network(cfg,prepare=False))
        for strategy in ('left','right','look4','look12'):
            candidate,_=s.build_sparse(cfg,strategy=strategy,prepare=False,restore=True)
            np.testing.assert_allclose(Operator(candidate).data,original.data,atol=2e-12,rtol=0)
    def test_2x3_final_fermionic_permutation(self):
        cfg=Cuprate2DConfig(lx=2,ly=3,holes=2,steps=2,dt=.2,u_over_t=8,t_prime_over_t=-.25)
        initial=Statevector.from_instruction(build_network(cfg))
        candidate,_=s.build_sparse(cfg,restore=False)
        s.restore_order(candidate,candidate.metadata['mode_order_final'])
        np.testing.assert_allclose(Statevector.from_instruction(candidate).data,initial.data,atol=2e-12,rtol=0)
    def test_readout_permutation_and_mask(self):
        q=QuantumCircuit(4); q.x(0)
        out=s.embed_with_logical_readout(q,[8,3,7,1],[2,0,3,1],[1,0,1,0],physical_width=10)
        self.assertEqual(out.metadata['logical_output_layout'],[7,8,1,3])
        self.assertEqual(out.metadata['readout_mask_little_endian'],[1,1,0,0])
        mapping=[(out.find_bit(i.qubits[0]).index,out.find_bit(i.clbits[0]).index) for i in out.data if i.operation.name=='measure']
        self.assertEqual(mapping,[(7,0),(8,1),(1,2),(3,3)])
    def test_bad_permutation(self):
        with self.assertRaises(ValueError):
            s.embed_with_logical_readout(QuantumCircuit(4),[0,1,2,3],[0,0,2,3])
    def test_cleanup_unitary_and_CZ(self):
        cfg=Cuprate2DConfig(lx=2,ly=2,holes=0,steps=2,dt=.2)
        native=compile_template(build_network(cfg))
        twirled,_=explicit_twirl(native,1201)
        compact,check=s.compact_bound(twirled)
        np.testing.assert_allclose(Operator(compact).data,Operator(twirled).data,atol=3e-12,rtol=0)
        self.assertTrue(check['CZ_partial_order_preserved'])
    def test_bad_cleanup_detected(self):
        q=QuantumCircuit(2); q.x(0); q.cz(0,1)
        bad=q.copy(); bad.x(1)
        with self.assertRaises(AssertionError): s.verify_cleanup(q,bad)
    def test_fold_pairs_survive_cleanup(self):
        q=QuantumCircuit(2); q.x(0)
        for _ in range(3): q.cz(0,1)
        out,_=s.compact_bound(q)
        self.assertEqual(out.count_ops()['cz'],3)
        np.testing.assert_allclose(Operator(out).data,Operator(q).data,atol=1e-13)
    def test_qpy_metadata(self):
        q=QuantumCircuit(4); q.x(0)
        out=s.embed_with_logical_readout(q,[8,3,7,1],[2,0,3,1])
        stream=io.BytesIO(); qpy.dump(out,stream); stream.seek(0)
        restored=qpy.load(stream)[0]
        self.assertEqual(restored,out)
        self.assertEqual(restored.metadata,out.metadata)

if __name__=='__main__': unittest.main()
