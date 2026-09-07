import unittest
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator,Statevector,random_statevector
from cuprate_2d_hubbard_pipeline import Cuprate2DConfig
from cuprate_2d_fermionic_mapping import build_network
from cuprate_2d_fermionic_dynamics import add_fermionic_hopping
from cuprate_2d_shallow_network import restore_order,network_events
import cuprate_2d_shallow_frontier as f

class FrontierTests(unittest.TestCase):
    def test_disjoint_even_fermionic_hops_commute(self):
        a=QuantumCircuit(4); b=QuantumCircuit(4)
        add_fermionic_hopping(a,0,2,-1,.31)
        add_fermionic_hopping(b,1,3,.25,.27)
        x,y=Operator(a).data,Operator(b).data
        np.testing.assert_allclose(x@y,y@x,atol=1e-13)
    def test_full_2x2_unitaries_all_policies(self):
        cfg=Cuprate2DConfig(lx=2,ly=2,holes=0,steps=2,dt=.2,u_over_t=8,t_prime_over_t=-.25,chemical_potential=.17)
        reference=Operator(build_network(cfg,prepare=False)).data
        for policy in ('distance','critical','asap'):
            qc,ledger=f.build_frontier(cfg,policy=policy,prepare=False,restore=True)
            np.testing.assert_allclose(Operator(qc).data,reference,atol=3e-12,rtol=0)
            ids=[e['original_event_id'] for e in ledger]; events=network_events(cfg)
            self.assertEqual(f.mode_trace(events,ids,8),f.mode_trace(events,range(len(events)),8))
    def test_random_2x3_state_and_final_fermionic_permutation(self):
        cfg=Cuprate2DConfig(lx=2,ly=3,holes=2,steps=2,dt=.2,u_over_t=8,t_prime_over_t=-.25)
        state=random_statevector(2**12,seed=623)
        reference=state.evolve(build_network(cfg,prepare=False))
        qc,_=f.build_frontier(cfg,prepare=False,restore=False)
        restore_order(qc,qc.metadata['mode_order_final'])
        np.testing.assert_allclose(state.evolve(qc).data,reference.data,atol=3e-12,rtol=0)
    def test_probability_readout_relabel(self):
        cfg=Cuprate2DConfig(lx=2,ly=2,holes=0,steps=2,dt=.2)
        reference=Statevector.from_instruction(build_network(cfg)).probabilities()
        qc,_=f.build_frontier(cfg,restore=False)
        actual=Statevector.from_instruction(qc).probabilities()
        slot=qc.metadata['slot_for_mode']; mapped=np.empty_like(actual)
        for native in range(len(actual)):
            logical=sum(((native>>slot[q])&1)<<q for q in range(8))
            mapped[logical]=actual[native]
        np.testing.assert_allclose(mapped,reference,atol=1e-12)
    def test_invalid_policy(self):
        with self.assertRaises(ValueError):
            f.build_frontier(Cuprate2DConfig(),policy='not-a-policy')

if __name__=='__main__': unittest.main()

