import unittest
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator,Statevector,SparsePauliOp
from qiskit.circuit.library import PauliEvolutionGate
from qiskit.synthesis import QDrift
from cuprate_2d_bonsai import Bonsai
from cuprate_2d_pa_mapping import P,letters,occupations
from cuprate_2d_hubbard_pipeline import Cuprate2DConfig
from cuprate_2d_qdrift import (
    Ensemble,make_ensemble,sample_indices,circuit,trajectories,
    occupation_hamiltonian,observables)
from test_cuprate_2d_bonsai import grid,fock_isometry


class TestQDrift(unittest.TestCase):
    def test_exact_N_sampler_matches_installed_Qiskit(self):
        mapping=Bonsai(grid(1,2))
        ensemble=Ensemble([(letters([(0,'X'),(1,'Y')]),),(-1*letters([(0,'Z')]),)],
                          np.array([1.,.5]),0.,'pauli')
        op=SparsePauliOp.from_list([(p[0].label(2),w*p[0].phase)
                                    for p,w in zip(ensemble.operators,ensemble.weights)])
        T=1.; N=int(np.ceil(2*ensemble.lam**2*T**2)); seed=91
        reference=QDrift(reps=1,seed=seed).synthesize(PauliEvolutionGate(op,time=T))
        ours,_=circuit(mapping,ensemble,T,N,seed,[0,0])
        np.testing.assert_allclose(Operator(ours).data,Operator(reference).data,atol=2e-12)
        self.assertEqual(N,5)

    def test_complete_Hamiltonians_and_norms(self):
        cfg=Cuprate2DConfig(lx=2,ly=2,holes=1,steps=2,dt=.2,chemical_potential=.17)
        mapping=Bonsai(grid(2,4),'xyz')
        indices,phases=fock_isometry(mapping); W=np.zeros((256,256),complex)
        W[indices,np.arange(256)]=phases
        exact=occupation_hamiltonian(cfg)
        for arm in ('pauli','grouped'):
            ensemble=make_ensemble(mapping,cfg,arm)
            total=ensemble.identity*np.eye(256,dtype=complex)
            for weight,terms in zip(ensemble.weights,ensemble.operators):
                group=sum(p.apply(np.eye(256)) for p in terms)
                np.testing.assert_allclose(group@group@group,group,atol=2e-12)
                total+=weight*group
            np.testing.assert_allclose(total@W,W@exact,atol=2e-12)
        cfg6=Cuprate2DConfig(lx=6,ly=6,holes=4,steps=2,dt=.2)
        m6=Bonsai(grid(8,9),'xyz')
        pauli=make_ensemble(m6,cfg6,'pauli'); grouped=make_ensemble(m6,cfg6,'grouped')
        self.assertAlmostEqual(pauli.lam,361)
        self.assertAlmostEqual(pauli.identity,72)
        self.assertAlmostEqual(grouped.lam,433)

    def test_vectorized_trajectories_match_circuit(self):
        cfg=Cuprate2DConfig(lx=2,ly=2,holes=1,steps=2,dt=.2)
        mapping=Bonsai(grid(2,4),'xyz'); bits=occupations(cfg)
        initial=Statevector.from_instruction(mapping.preparation(bits)).data
        for arm in ('pauli','grouped'):
            ensemble=make_ensemble(mapping,cfg,arm)
            sample,_=circuit(mapping,ensemble,.4,32,seed=15,bits=bits)
            actual=trajectories(ensemble,8,.4,32,15,initial,replicates=1)[0]
            np.testing.assert_allclose(actual,Statevector.from_instruction(sample).data,atol=3e-12)

    def test_grouped_conserves_particle_number(self):
        cfg=Cuprate2DConfig(lx=2,ly=2,holes=1,steps=2,dt=.2)
        mapping=Bonsai(grid(2,4),'xyz'); bits=occupations(cfg)
        initial=Statevector.from_instruction(mapping.preparation(bits)).data
        ensemble=make_ensemble(mapping,cfg,'grouped')
        psi=trajectories(ensemble,8,.4,32,188,initial,replicates=16)
        n=observables(mapping)['number']
        leakage=np.sum(np.abs(psi[:,n!=3])**2)
        self.assertLess(leakage,1e-22)

    def test_individual_Paulis_can_leak_number(self):
        XX=letters([(0,'X'),(1,'X')]); YY=letters([(0,'Y'),(1,'Y')])
        split=Ensemble([(XX,),(YY,)],np.array([.5,.5]),0.,'pauli')
        grouped=Ensemble([(.5*XX,.5*YY)],np.array([1.]),0.,'grouped')
        initial=np.array([1.,0.,0.,0.],complex)
        noisy=trajectories(split,2,.3,1,9,initial,replicates=8)
        preserved=trajectories(grouped,2,.3,1,9,initial,replicates=8)
        np.testing.assert_allclose(np.abs(noisy[:,3])**2,np.sin(.3)**2,atol=1e-13)
        np.testing.assert_allclose(preserved,np.tile(initial,(8,1)),atol=1e-13)

    def test_time_and_sampling_guards(self):
        e=Ensemble([(P(z=1),)],np.array([1.]),0.,'pauli')
        with self.assertRaises(ValueError): sample_indices(e,0,9)
        with self.assertRaises(ValueError): sample_indices(e,2.5,9)
        self.assertEqual(len(sample_indices(e,12,9)),12)


if __name__=='__main__': unittest.main(verbosity=2)
