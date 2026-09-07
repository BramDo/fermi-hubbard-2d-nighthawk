import unittest
import numpy as np
from scipy.linalg import expm
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator, Statevector
from cuprate_2d_pa_mapping import PA, P, occupations
from cuprate_2d_pa_pair_synthesis import paired_hop, evolution
from cuprate_2d_hubbard_pipeline import Cuprate2DConfig


class TestPairedPA(unittest.TestCase):
    def test_individual_pairs_against_matrix_exponential(self):
        mapping=PA(6,6)
        cfg=Cuprate2DConfig(lx=6,ly=6,holes=4,steps=2,dt=.2)
        terms=[t for t in mapping.model_terms(cfg) if t['kind']=='hop']
        chosen=terms[::11]
        # Ensure the largest support is explicitly tested.
        chosen.append(max(terms,key=lambda t:len(mapping.hopping(t['p'],t['q'])[0].support)))
        for term in chosen:
            p,q=term['p'],term['q']
            pair=mapping.hopping(p,q); support=list(pair[0].support)
            inv={q:k for k,q in enumerate(support)}
            circuit=QuantumCircuit(mapping.n)
            paired_hop(circuit,mapping,p,q,.123)
            small=QuantumCircuit(len(support))
            for instruction in circuit.data:
                wires=[inv[circuit.find_bit(q).index] for q in instruction.qubits]
                small.append(instruction.operation,wires)
            matrices=[]
            for pauli in pair:
                x=sum(1<<k for q,k in inv.items() if pauli.x>>q&1)
                z=sum(1<<k for q,k in inv.items() if pauli.z>>q&1)
                matrices.append(P(x,z,pauli.phase).apply(np.eye(1<<len(support))))
            np.testing.assert_allclose(Operator(small).data,
                expm(-.123j*sum(matrices)),atol=3e-12)

    def test_complete_evolution_against_previous_synthesis(self):
        mapping=PA(2,2)
        cfg=Cuprate2DConfig(lx=2,ly=2,holes=0,steps=2,dt=.2,chemical_potential=.17)
        rng=np.random.default_rng(762)
        state=rng.normal(size=4096)+1j*rng.normal(size=4096); state/=np.linalg.norm(state)
        for ordering in ('network','layered'):
            expected=Statevector(state).evolve(mapping.evolution(cfg,ordering)).data
            actual=Statevector(state).evolve(evolution(mapping,cfg,ordering)).data
            np.testing.assert_allclose(actual,expected,atol=2e-11)


if __name__=='__main__': unittest.main(verbosity=2)
