"""Independent occupation-basis, full-Hilbert-space Bonsai checks."""
import unittest
import numpy as np
import networkx as nx
from qiskit import QuantumCircuit,transpile
from qiskit.quantum_info import Operator,Statevector
from qiskit.transpiler import CouplingMap
from cuprate_2d_bonsai import Bonsai,anneal
from cuprate_2d_pa_mapping import P,letters,occupations
from cuprate_2d_hubbard_pipeline import Cuprate2DConfig
from cuprate_2d_fermionic_mapping import build_network,pair_model


def grid(rows,columns):
    g=nx.grid_2d_graph(rows,columns)
    return nx.relabel_nodes(g,{(r,c):r*columns+c for r,c in g})


def fock_isometry(mapping):
    indices=[]; phases=[]
    for bits in range(1<<mapping.n):
        physical=0; phase=1
        for mode in range(mapping.n):
            if bits>>mode&1:
                p=mapping.gamma(mode)
                scalar=p.phase*1j**((p.x&p.z).bit_count()%4)*(-1)**((p.z&physical).bit_count()%2)
                jw=(-1)**((bits&((1<<mode)-1)).bit_count()%2)
                phase*=scalar/jw; physical^=p.x
        assert mapping.decode([(physical>>q)&1 for q in range(mapping.n)])==[(bits>>q)&1 for q in range(mapping.n)]
        indices.append(physical); phases.append(phase)
    assert len(set(indices))==1<<mapping.n
    return np.array(indices),np.array(phases,dtype=complex)


def jw_hop(n,p,q):
    result=np.zeros((1<<n,1<<n),complex)
    lo,hi=sorted((p,q)); between=((1<<hi)-1)^((1<<(lo+1))-1)
    for bits in range(1<<n):
        if ((bits>>p)^(bits>>q))&1:
            result[bits^(1<<p)^(1<<q),bits]=(-1)**((bits&between).bit_count()%2)
    return result


class TestBonsai(unittest.TestCase):
    def test_ternary_tree_algebra(self):
        for g in [nx.path_graph(1),nx.path_graph(8),grid(2,4),grid(8,9)]:
            for labeling in ['z_priority','xyz']: Bonsai(g,labeling).audit()

    def test_full_majorana_and_hubbard_intertwining(self):
        mapping=Bonsai(grid(2,4))
        mapping.set_assignment([5,0,2,1,3,4,7,6])
        indices,phases=fock_isometry(mapping); n=mapping.n; dim=1<<n
        W=np.zeros((dim,dim),complex); W[indices,np.arange(dim)]=phases
        np.testing.assert_allclose(W.conj().T@W,np.eye(dim),atol=1e-14)
        cfg=Cuprate2DConfig(lx=2,ly=2,holes=0,steps=2,dt=.2)
        for mode in range(n):
            for odd in (0,1):
                exact=np.zeros((dim,dim),complex)
                for bits in range(dim):
                    sign=(-1)**((bits&((1<<mode)-1)).bit_count()%2)
                    if odd: sign*=1j*(-1)**((bits>>mode)&1)
                    exact[bits^(1<<mode),bits]=sign
                np.testing.assert_allclose(mapping.gamma(mode,odd).apply(W),W@exact,atol=1e-14)
        hops,onsite=pair_model(cfg)
        for p,q in hops:
            np.testing.assert_allclose(sum(a.apply(W) for a in mapping.hopping(p,q)),
                                       W@jw_hop(n,p,q),atol=1e-14)
        for p,q in onsite:
            diag=np.array([((b>>p)&1)*((b>>q)&1) for b in range(dim)])
            np.testing.assert_allclose(sum(a.apply(W) for a in mapping.onsite(p,q)),
                                       W*diag,atol=1e-14)

    def test_sparse_parity_rotation_restores_steiner_data(self):
        mapping=Bonsai(nx.path_graph(5)); rng=np.random.default_rng(907)
        for _ in range(24):
            items=[(q,rng.choice(list('IXYZ'))) for q in range(5)]
            pauli=letters(items); qc=QuantumCircuit(5)
            mapping.rotate(qc,pauli,.137)
            expected=np.cos(.137)*np.eye(32)-1j*np.sin(.137)*pauli.apply(np.eye(32))
            np.testing.assert_allclose(Operator(qc).data,expected,atol=3e-12)
            for inst in qc.data:
                if inst.operation.name=='cx':
                    wires=[qc.find_bit(q).index for q in inst.qubits]
                    self.assertTrue(mapping.graph.has_edge(*wires))
        qc=QuantumCircuit(5); mapping.rotate(qc,P(phase=.25),.4)
        np.testing.assert_allclose(Operator(qc).data,np.exp(-.1j)*np.eye(32),atol=1e-14)

    def test_same_finite_circuit_2x2_and_2x3(self):
        rng=np.random.default_rng(73)
        for lx,ly in [(2,2),(2,3)]:
            cfg=Cuprate2DConfig(lx=lx,ly=ly,holes=0,steps=2,dt=.2,chemical_potential=.17)
            mapping=Bonsai(grid(ly,2*lx))
            permutation=rng.permutation(mapping.n).tolist(); mapping.set_assignment(permutation)
            indices,phases=fock_isometry(mapping)
            vector=rng.normal(size=1<<mapping.n)+1j*rng.normal(size=1<<mapping.n)
            vector/=np.linalg.norm(vector)
            encoded=np.empty_like(vector); encoded[indices]=phases*vector
            actual=Statevector(encoded).evolve(mapping.evolution(cfg)).data
            expected=Statevector(vector).evolve(build_network(cfg,prepare=False)).data
            np.testing.assert_allclose(actual[indices]/phases,expected,atol=3e-11)

    def test_native_compile_and_bit_decoding(self):
        cfg=Cuprate2DConfig(lx=2,ly=2,holes=0,steps=2,dt=.2)
        mapping=Bonsai(grid(2,4)); mapping.set_assignment([5,0,2,1,3,4,7,6])
        bits=occupations(cfg)
        circuit=mapping.preparation(bits).compose(mapping.evolution(cfg))
        cm=CouplingMap([list(e) for a,b in mapping.graph.edges for e in [(a,b),(b,a)]])
        native=transpile(circuit,basis_gates=['rz','sx','x','cz'],coupling_map=cm,
            initial_layout=list(range(8)),routing_method='none',optimization_level=3,
            approximation_degree=1,seed_transpiler=9)
        self.assertEqual(native.layout.final_index_layout(),list(range(8)))
        np.testing.assert_allclose(Statevector.from_instruction(native).data,
                                   Statevector.from_instruction(circuit).data,atol=3e-11)
        for bits in range(256):
            vector=[(bits>>q)&1 for q in range(8)]
            self.assertEqual(mapping.decode(mapping.encode(vector)),vector)
        # Physical occupancy is not identical to a raw measured bit in this mapping.
        self.assertTrue(any(v.z.bit_count()>1 for v in mapping.vertices))

    def test_number_and_doublon_from_decoded_samples(self):
        cfg=Cuprate2DConfig(lx=2,ly=2,holes=0,steps=2,dt=.2)
        mapping=Bonsai(grid(2,4))
        probabilities=Statevector.from_instruction(
            mapping.preparation(occupations(cfg)).compose(mapping.evolution(cfg))).probabilities()
        numbers=[]; doublons=[]
        for bits in range(256):
            occupations_=mapping.decode([(bits>>q)&1 for q in range(8)])
            numbers.append(sum(occupations_))
            doublons.append(sum(occupations_[2*s]*occupations_[2*s+1] for s in range(4))/4)
        reference=Statevector.from_instruction(build_network(cfg)).probabilities()
        rawdouble=[sum(((b>>(2*s))&1)*((b>>(2*s+1))&1) for s in range(4))/4 for b in range(256)]
        self.assertAlmostEqual(float(probabilities@numbers),4.,places=11)
        self.assertAlmostEqual(float(probabilities@doublons),float(reference@rawdouble),places=11)

    def test_pair_annealing_preserves_mapping(self):
        cfg=Cuprate2DConfig(lx=2,ly=2,holes=0,steps=2,dt=.2)
        mapping=Bonsai(grid(2,4)); result=anneal(mapping,cfg,seed=19,proposals=500)
        self.assertLessEqual(result['best_proxy'],result['initial_proxy']+1e-10)
        mapping.audit(); fock_isometry(mapping)


if __name__=='__main__': unittest.main(verbosity=2)
