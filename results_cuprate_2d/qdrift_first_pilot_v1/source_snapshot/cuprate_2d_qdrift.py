"""Explicit-N qDRIFT for Pauli or number-conserving Hubbard groups.

No provider APIs; no new dependency. See QDRIFT_PILOT_PROTOCOL.md.
"""
from dataclasses import dataclass
import numpy as np
from qiskit import QuantumCircuit
from cuprate_2d_bonsai import Bonsai
from cuprate_2d_pa_mapping import P
from cuprate_2d_fermionic_mapping import pair_model


@dataclass
class Ensemble:
    operators: list
    weights: np.ndarray
    identity: float
    arm: str

    @property
    def lam(self): return float(sum(self.weights))


def make_ensemble(mapping,cfg,arm):
    hops,onsite=pair_model(cfg)
    weighted=[]
    for (p,q),c in hops.items():
        if c: weighted.append((abs(c),tuple(np.sign(c)*a for a in mapping.hopping(p,q))))
    for (p,q),c in onsite.items():
        if c: weighted.append((abs(c),tuple(np.sign(c)*a for a in mapping.onsite(p,q))))
    if cfg.chemical_potential:
        # -mu*n = (-mu/2) I+(mu/2) V, included exactly in either expansion.
        for mode in range(mapping.n):
            c=-cfg.chemical_potential
            weighted.append((abs(c),(P(phase=.5*np.sign(c)),
                -.5*np.sign(c)*mapping.vertex(mode))))
    if arm=='grouped':
        return Ensemble([op for _,op in weighted],np.array([w for w,_ in weighted]),0.,arm)
    if arm!='pauli': raise ValueError('Unknown qDRIFT arm')
    merged={}
    for weight,op in weighted:
        for p in op:
            key=p.x,p.z
            merged[key]=merged.get(key,0)+weight*p.phase
    identity=float(np.real(merged.pop((0,0),0)))
    ops=[]; weights=[]
    for (x,z),value in sorted(merged.items()):
        if abs(value)<1e-13: continue
        if abs(value.imag)>1e-13: raise AssertionError('Non-real Hamiltonian coefficient')
        ops.append((P(x,z,np.sign(value.real)),)); weights.append(abs(value.real))
    return Ensemble(ops,np.array(weights),identity,arm)


def sample_indices(ensemble,N,seed):
    if N<=0 or int(N)!=N or ensemble.lam<=0: raise ValueError('Positive N and nonzero Hamiltonian required')
    return np.random.default_rng(seed).choice(len(ensemble.weights),size=N,p=ensemble.weights/ensemble.lam)


def circuit(mapping,ensemble,T,N,seed,bits):
    if T<0: raise ValueError('Nonnegative time required')
    qc=mapping.preparation(bits); qc.global_phase-=ensemble.identity*T
    draws=sample_indices(ensemble,N,seed); tau=ensemble.lam*T/N
    for index in draws:
        for pauli in ensemble.operators[int(index)]: mapping.rotate(qc,pauli,tau)
    qc.metadata={'family':'qDRIFT_'+ensemble.arm,'N_random_steps':N,'seed':seed,
        'lambda':ensemble.lam,'T':T,'tau':tau,'different_from_old_finite_circuit':True,
        'grouped_number_conserving':ensemble.arm=='grouped','hardware_authorized':False}
    return qc,draws


def sparse_action_tables(ensemble,n):
    """Each chosen A is a signed Pauli, hopping or number projector: A^3=A."""
    dim=1<<n; basis=np.arange(dim,dtype=np.int64)
    permutations=[]; amplitudes=[]
    for terms in ensemble.operators:
        # Small-system independent matrix assembly; require monomial or zero columns.
        matrix=sum(p.apply(np.eye(dim)) for p in terms)
        mask=np.abs(matrix)>1e-12
        if np.any(mask.sum(axis=0)>1): raise AssertionError('Group is not monomial')
        rows=np.argmax(mask,axis=0)
        values=matrix[rows,basis]
        if not np.allclose(np.abs(values[np.abs(values)>1e-12]),1,atol=1e-12):
            raise AssertionError('Expected spectrum0,+/-1')
        # Output-row action: A psi[row]=amplitude[row]*psi[permutation[row]].
        perm=np.arange(dim)
        amp=np.zeros(dim,complex)
        for col,row in enumerate(rows):
            if mask[row,col]: perm[row]=col; amp[row]=values[col]
        permutations.append(perm); amplitudes.append(amp)
    return np.array(permutations),np.array(amplitudes)


def trajectories(ensemble,n,T,N,seed,initial,replicates=256,tables=None):
    if tables is None: tables=sparse_action_tables(ensemble,n)
    perms,values=tables
    draws=np.random.default_rng(seed).choice(len(ensemble.weights),size=(N,replicates),
                                            p=ensemble.weights/ensemble.lam)
    tau=ensemble.lam*T/N; c,s=np.cos(tau),np.sin(tau)
    psi=np.tile(initial,(replicates,1)).astype(complex)
    row=np.arange(replicates)[:,None]
    for indices in draws:
        amp=values[indices]
        acted=amp*psi[row,perms[indices]]
        psi=(1+(c-1)*np.abs(amp)**2)*psi-1j*s*acted
    psi*=np.exp(-1j*ensemble.identity*T)
    error=float(np.max(np.abs(np.sum(np.abs(psi)**2,axis=1)-1)))
    if error>2e-10: raise AssertionError('qDRIFT trajectory normalization failed')
    return psi


def occupation_hamiltonian(cfg):
    """Independent dense occupation-basis reference, no Bonsai Pauli algebra."""
    n=cfg.qubits; dim=1<<n; H=np.zeros((dim,dim),complex)
    hops,onsite=pair_model(cfg)
    for bits in range(dim):
        H[bits,bits]=sum(c*((bits>>p)&1)*((bits>>q)&1) for (p,q),c in onsite.items())
        H[bits,bits]-=cfg.chemical_potential*bits.bit_count()
        for (p,q),c in hops.items():
            lo,hi=sorted((p,q))
            if ((bits>>p)^(bits>>q))&1:
                parity=(bits&(((1<<hi)-1)^((1<<(lo+1))-1))).bit_count()%2
                H[bits^(1<<p)^(1<<q),bits]+=c*(-1)**parity
    return H


def observables(mapping):
    """Rows indexed by encoded bits; columns charge, spin, doublons, N, leakage."""
    number=[]; charge=[]; spin=[]; double=[]
    for bits in range(1<<mapping.n):
        occ=mapping.decode([(bits>>q)&1 for q in range(mapping.n)])
        charge.append([occ[2*s]+occ[2*s+1] for s in range(mapping.n//2)])
        spin.append([occ[2*s]-occ[2*s+1] for s in range(mapping.n//2)])
        double.append([occ[2*s]*occ[2*s+1] for s in range(mapping.n//2)])
        number.append(sum(occ))
    return {'charge':np.array(charge),'spin':np.array(spin),'doublon':np.array(double),
            'number':np.array(number)}
