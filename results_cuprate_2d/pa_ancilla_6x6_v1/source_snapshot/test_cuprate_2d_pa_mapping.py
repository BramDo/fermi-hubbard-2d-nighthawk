"""Independent occupation-basis tests for PA; no IBM calls."""
import unittest
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector, Operator, Pauli
from cuprate_2d_hubbard_pipeline import Cuprate2DConfig
from cuprate_2d_fermionic_dynamics import add_fermionic_hopping
from cuprate_2d_pa_mapping import P, PA, letters, rotate, occupations


def even_isometry(mapping,parity=0):
    """Build a full fixed-parity isometry using an independent JW sign rule."""
    basis=[b for b in range(1<<mapping.modes) if b.bit_count()%2==parity]
    initial=parity
    vacuum=Statevector.from_instruction(mapping.preparation(
        [(initial>>q)&1 for q in range(mapping.modes)])).data
    columns=[]
    for bits in basis:
        state=vacuum.copy(); previous=initial
        for q in range(1,mapping.modes):
            if bits>>q&1:
                # -i gamma_0 gamma_q: apply gamma_q first, then gamma_0.
                jwphase=-1j*(-1)**((previous&((1<<q)-1)).bit_count())
                state=mapping.edge(0,q).apply(state)/jwphase
                previous^=(1<<q)|1
        assert previous==bits
        columns.append(state)
    return basis,np.column_stack(columns)


def mapped_hop(operator,p,q,mapping):
    return sum(term.apply(operator) for term in mapping.hopping(p,q))


def independent_hop_image(basis,W,p,q):
    index={b:i for i,b in enumerate(basis)}
    expected=np.zeros_like(W)
    low,high=sorted((p,q)); between=((1<<high)-1)^((1<<(low+1))-1)
    for col,bits in enumerate(basis):
        if ((bits>>p)^(bits>>q))&1:
            sign=(-1)**((bits&between).bit_count())
            expected[:,col]=sign*W[:,index[bits^(1<<p)^(1<<q)]]
    return expected


def jw_same_events(mapping,cfg,ordering):
    circuit=QuantumCircuit(cfg.qubits)
    for event in mapping.events(cfg,ordering):
        p,q=event['p'],event['q']
        if event['kind']=='hop':
            add_fermionic_hopping(circuit,p,q,1.0,event['angle'])
        else: circuit.cp(-event['angle'],p,q)
    for q in range(cfg.qubits):
        if cfg.chemical_potential: circuit.p(cfg.chemical_potential*cfg.total_time,q)
    return circuit


class TestPA(unittest.TestCase):
    def test_integer_pauli_against_qiskit(self):
        import itertools
        for a,b in itertools.product('IXYZ',repeat=2):
            pa=letters([(0,a)]); pb=letters([(0,b)])
            actual=(pa*pb).apply(np.eye(2))
            expected=Pauli(a).to_matrix()@Pauli(b).to_matrix()
            np.testing.assert_allclose(actual,expected,atol=1e-14)
        rng=np.random.default_rng(815)
        for _ in range(16):
            strings=[''.join(rng.choice(list('IXYZ'),size=4)) for j in range(2)]
            pa,pb=[letters(list(enumerate(reversed(s)))) for s in strings]
            np.testing.assert_allclose((pa*pb).apply(np.eye(16)),
                Pauli(strings[0]).to_matrix()@Pauli(strings[1]).to_matrix(),atol=1e-14)

    def test_edge_algebra_and_loops(self):
        for size in [(1,1),(2,2),(2,3),(6,6)]:
            PA(*size).audit()

    def test_state_preparation(self):
        mapping=PA(2,2)
        for bits in [[0]*8,[1]*8,[1,0,0,1,1,0,0,1]]:
            state=Statevector.from_instruction(mapping.preparation(bits)).data
            for stabilizer in mapping.stabilizers:
                np.testing.assert_allclose(stabilizer.apply(state),state,atol=2e-12)
            for m,bit in enumerate(bits):
                np.testing.assert_allclose(mapping.vertex(m).apply(state),(-1)**bit*state,atol=2e-12)

    def test_all_hubbard_terms_both_parity_sectors(self):
        mapping=PA(2,2)
        cfg=Cuprate2DConfig(lx=2,ly=2,holes=0,steps=2,dt=.2,u_over_t=8,t_prime_over_t=-.25)
        for parity in (0,1):
            basis,W=even_isometry(mapping,parity)
            np.testing.assert_allclose(W.conj().T@W,np.eye(len(basis)),atol=2e-12)
            for term in mapping.model_terms(cfg):
                p,q=term['p'],term['q']
                if term['kind']=='hop':
                    actual=mapped_hop(W,p,q,mapping)
                    expected=independent_hop_image(basis,W,p,q)
                else:
                    actual=(W-mapping.vertex(p).apply(W)-mapping.vertex(q).apply(W)
                            +(mapping.vertex(p)*mapping.vertex(q)).apply(W))/4
                    values=np.array([((b>>p)&1)*((b>>q)&1) for b in basis])
                    expected=W*values[None,:]
                np.testing.assert_allclose(actual,expected,atol=3e-12)

    def test_full_circuit_arbitrary_even_state_and_mu(self):
        mapping=PA(2,2); basis,W=even_isometry(mapping)
        cfg=Cuprate2DConfig(lx=2,ly=2,holes=0,steps=2,dt=.2,
                           chemical_potential=.17,u_over_t=8,t_prime_over_t=-.25)
        rng=np.random.default_rng(918)
        vector=rng.normal(size=len(basis))+1j*rng.normal(size=len(basis))
        vector/=np.linalg.norm(vector)
        logical=np.zeros(256,complex); logical[basis]=vector
        for ordering in ('network','layered'):
            final=Statevector(W@vector).evolve(mapping.evolution(cfg,ordering)).data
            reference=Statevector(logical).evolve(jw_same_events(mapping,cfg,ordering)).data
            np.testing.assert_allclose(final,W@reference[basis],atol=2e-11)
            for stabilizer in mapping.stabilizers:
                np.testing.assert_allclose(stabilizer.apply(final),final,atol=2e-11)
            self.assertAlmostEqual(float(np.vdot(final,final).real),1.0,places=11)

    def test_network_target_is_original(self):
        from cuprate_2d_fermionic_mapping import build_network
        cfg=Cuprate2DConfig(lx=2,ly=2,holes=0,steps=2,dt=.2)
        mapping=PA(2,2)
        np.testing.assert_allclose(Operator(jw_same_events(mapping,cfg,'network')).data,
                                   Operator(build_network(cfg,prepare=False)).data,atol=3e-12)

    def test_rotation_zero_and_inverse(self):
        qc=QuantumCircuit(3); p=letters([(0,'Y'),(1,'Z'),(2,'X')])
        rotate(qc,p,.173); rotate(qc,p,-.173)
        np.testing.assert_allclose(Operator(qc).data,np.eye(8),atol=2e-12)

    def test_model_coverage(self):
        cfg=Cuprate2DConfig(lx=6,ly=6,holes=4,steps=2,dt=.2)
        mapping=PA(6,6)
        from collections import Counter
        first=Counter((e['kind'],e['p'],e['q'],e['angle']) for e in mapping.events(cfg,'network'))
        second=Counter((e['kind'],e['p'],e['q'],e['angle']) for e in mapping.events(cfg,'layered'))
        self.assertEqual(first,second)
        self.assertEqual(sum(occupations(cfg)),32)
        self.assertEqual(len(mapping.model_terms(cfg)),256)


if __name__=='__main__': unittest.main(verbosity=2)
