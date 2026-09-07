"""Offline PA edge encoding for the spinful Hubbard model; no provider API.

Conventions and scope are frozen in PA_ANCILLA_PROTOCOL.md.
This is a correctness-first PA implementation, not the paper's XYZ compiler.
"""
from dataclasses import dataclass
from functools import lru_cache
import numpy as np
import networkx as nx
from qiskit import QuantumCircuit
from qiskit.synthesis import synth_circuit_from_stabilizers
from cuprate_2d_fermionic_mapping import pair_model
from cuprate_2d_shallow_network import network_events
from cuprate_2d_hubbard_pipeline import initial_site_rows, SPINS, validate_config


@dataclass(frozen=True)
class P:
    x: int = 0
    z: int = 0
    phase: complex = 1

    def __mul__(self, other):
        if not isinstance(other, P):
            return P(self.x,self.z,self.phase*other)
        x,z=self.x^other.x,self.z^other.z
        power=(self.x&self.z).bit_count()+(other.x&other.z).bit_count()-(x&z).bit_count()
        phase=self.phase*other.phase*(1j**(power%4))*(-1)**((self.z&other.x).bit_count()%2)
        return P(x,z,phase)

    __rmul__=__mul__

    def commutes(self,other):
        return ((self.x&other.z).bit_count()+(self.z&other.x).bit_count())%2==0

    @property
    def support(self):
        mask=self.x|self.z
        return tuple(q for q in range(mask.bit_length()) if mask>>q&1)

    def label(self,n):
        letters=['I','X','Z','Y']
        return ''.join(letters[((self.x>>q)&1)+2*((self.z>>q)&1)] for q in reversed(range(n)))

    def signed_label(self,n):
        if self.phase not in (1,-1): raise ValueError('Not a signed Hermitian Pauli')
        return ('-' if self.phase==-1 else '')+self.label(n)

    def apply(self,array):
        array=np.asarray(array); dim=len(array)
        indices=np.arange(dim,dtype=np.int64)
        parity=np.zeros(dim,dtype=np.int8)
        for q in range(self.z.bit_length()):
            if self.z>>q&1: parity^=((indices>>q)&1).astype(np.int8)
        factor=self.phase*1j**((self.x&self.z).bit_count()%4)*(1-2*parity)
        out=np.empty_like(array,dtype=complex)
        out[indices^self.x]=factor.reshape((-1,)+(1,)*(array.ndim-1))*array
        return out


def letters(items):
    x=z=0
    for q,letter in items:
        if letter in 'XY': x|=1<<q
        if letter in 'ZY': z|=1<<q
    return P(x,z)


class PA:
    def __init__(self,lx,ly):
        if min(lx,ly)<1: raise ValueError('Positive lattice dimensions required')
        self.lx,self.ly=lx,ly
        self.modes=2*lx*ly; self.n=3*lx*ly
        self.data={}; self.anc=[]; self.graph=nx.Graph()
        self.graph.add_nodes_from(range(self.modes))
        self.edges={}
        for y in range(ly):
            for x in range(lx):
                site=y*lx+x
                for slot in (0,1):
                    mode=2*site+(slot^(x%2))
                    self.data[mode]=3*site+slot
                self.anc.append(3*site+2)
        inverse={v:k for k,v in self.data.items()}
        def add(q,r,operator):
            p,s=inverse[q],inverse[r]
            self.edges[p,s]=operator; self.edges[s,p]=-1*operator
            self.graph.add_edge(p,s)
        for y in range(ly):
            for x in range(lx):
                base=3*(y*lx+x); t='X' if x%2==0 else 'Y'; opposite='Y' if t=='X' else 'X'
                add(base,base+1,letters([(base,t),(base+1,opposite)]))
                if x+1<lx:
                    add(base+1,base+3,letters([(base+1,t),(base+2,'Z'),(base+3,t)]))
                if y+1<ly:
                    below=base+3*lx
                    add(base+1,below+1,letters([(base+1,t),(base+2,'Y'),(below+2,'X'),(below+1,t)]))
        self.cycles=nx.cycle_basis(self.graph)
        self.stabilizers=[]
        for cycle in self.cycles:
            product=P()
            for a,b in zip(cycle,cycle[1:]+cycle[:1]): product=product*self.edges[a,b]
            self.stabilizers.append((1j**(len(cycle)%4))*product)

    def vertex(self,mode):
        return letters([(self.data[mode],'Z')])

    @lru_cache(maxsize=None)
    def edge(self,p,q):
        if p==q: raise ValueError('An edge needs distinct modes')
        if (p,q) in self.edges: return self.edges[p,q]
        path=nx.shortest_path(self.graph,p,q)
        result=self.edges[path[0],path[1]]
        for a,b in zip(path[1:],path[2:]): result=1j*result*self.edges[a,b]
        return result

    def hopping(self,p,q):
        e=self.edge(p,q)
        return (0.5j*self.vertex(q)*e, -0.5j*self.vertex(p)*e)

    def audit(self):
        edges=[(p,q,self.edges[p,q]) for p,q in self.graph.edges]
        checked=0
        for i,(p,q,e) in enumerate(edges):
            assert e*e==P()
            for r in range(self.modes):
                assert e.commutes(self.vertex(r))==(r not in (p,q))
                checked+=1
            for r,s,f in edges[i+1:]:
                assert e.commutes(f)==(len({p,q}&{r,s})!=1)
                checked+=1
        for s in self.stabilizers:
            assert s*s==P()
            assert all(s.commutes(e) for _,_,e in edges)
            assert all(s.commutes(self.vertex(m)) for m in range(self.modes))
            assert all(s.commutes(t) for t in self.stabilizers)
        expected=self.graph.number_of_edges()-self.modes+1
        assert len(self.stabilizers)==expected==(self.lx-1)*(self.ly-1)
        # Rank in the binary symplectic representation, independently of cycle count.
        basis={}
        for s in self.stabilizers:
            row=s.x|(s.z<<self.n)
            while row:
                bit=row.bit_length()-1
                if bit in basis: row^=basis[bit]
                else: basis[bit]=row; break
        assert len(basis)==expected
        return {'modes':self.modes,'qubits':self.n,'ancillas':len(self.anc),
                'edge_algebra_checks':checked,'loop_rank':expected,
                'unfixed_boundary_auxiliary_degrees':len(self.anc)-expected}

    def preparation(self,bits):
        if len(bits)!=self.modes or any(b not in (0,1) for b in bits):
            raise ValueError('One occupation bit per mode required')
        reduced=[]
        ancindex={q:i for i,q in enumerate(self.anc)}
        for stabilizer in self.stabilizers:
            phase=stabilizer.phase
            for mode,q in self.data.items():
                assert not(stabilizer.x>>q&1)
                if stabilizer.z>>q&1 and bits[mode]: phase=-phase
            x=sum(1<<i for q,i in ancindex.items() if stabilizer.x>>q&1)
            z=sum(1<<i for q,i in ancindex.items() if stabilizer.z>>q&1)
            reduced.append(P(x,z,phase).signed_label(len(self.anc)))
        qc=QuantumCircuit(self.n)
        for mode,q in self.data.items():
            if bits[mode]: qc.x(q)
        if reduced:
            aux=synth_circuit_from_stabilizers(reduced,allow_underconstrained=True)
            qc.compose(aux,self.anc,inplace=True)
        qc.metadata={'PA_ancilla_preparation':True,'loops':len(reduced),
                     'boundary_gauge':'deterministic underconstrained Clifford completion'}
        return qc

    def model_terms(self,cfg):
        hops,onsite=pair_model(cfg)
        terms=[{'kind':'hop','p':p,'q':q,'c':c} for (p,q),c in hops.items() if c]
        terms += [{'kind':'onsite','p':p,'q':q,'c':c} for (p,q),c in onsite.items() if c]
        return terms

    def term_support(self,term):
        if term['kind']=='onsite': return {self.data[term['p']],self.data[term['q']]}
        return set(self.hopping(term['p'],term['q'])[0].support)

    def events(self,cfg,ordering):
        if ordering=='network':
            result=[]
            for event in network_events(cfg):
                p,q=event['modes']
                if event['hopping_angle']:
                    result.append({'kind':'hop','p':p,'q':q,'angle':event['hopping_angle']/2})
                if event['onsite_angle']:
                    result.append({'kind':'onsite','p':p,'q':q,'angle':-event['onsite_angle']})
            return result
        if ordering!='layered': raise ValueError('Unknown PA ordering')
        terms=self.model_terms(cfg); groups=[]; occupied=[]
        for term in sorted(terms,key=lambda t:(-len(self.term_support(t)),t['p'],t['q'])):
            support=self.term_support(term)
            group=next((k for k,used in enumerate(occupied) if not(support&used)),len(groups))
            if group==len(groups): groups.append([]); occupied.append(set())
            groups[group].append(term); occupied[group]|=support
        half=[{'kind':t['kind'],'p':t['p'],'q':t['q'],'angle':t['c']*cfg.dt/2}
              for group in groups for t in group]
        return (half+list(reversed(half)))*cfg.steps

    def evolution(self,cfg,ordering='layered'):
        validate_config(cfg)
        if (cfg.lx,cfg.ly)!=(self.lx,self.ly): raise ValueError('Configuration mismatch')
        qc=QuantumCircuit(self.n)
        for event in self.events(cfg,ordering):
            p,q,angle=event['p'],event['q'],event['angle']
            if event['kind']=='onsite': qc.cp(-angle,self.data[p],self.data[q])
            else:
                for pauli in self.hopping(p,q): rotate(qc,pauli,angle)
        # Uniform mu*N commutes with every term.
        if cfg.chemical_potential:
            for q in self.data.values(): qc.p(cfg.chemical_potential*cfg.total_time,q)
        qc.metadata={'family':'PA_correctness_first','ordering':ordering,
                     'same_old_finite_circuit':ordering=='network',
                     'steps':cfg.steps,'dt':cfg.dt,'time':cfg.total_time,
                     'paper_XYZ_schedule_reproduced':False}
        return qc


def rotate(qc,pauli,angle):
    if abs(pauli.phase.imag)>1e-12: raise ValueError('Non-Hermitian rotation')
    support=list(pauli.support)
    if not support: qc.global_phase-=angle*pauli.phase.real; return
    for q in support:
        if pauli.x>>q&1:
            if pauli.z>>q&1: qc.sdg(q)
            qc.h(q)
    for a,b in zip(support,support[1:]): qc.cx(a,b)
    qc.rz(2*angle*pauli.phase.real,support[-1])
    for a,b in reversed(list(zip(support,support[1:]))): qc.cx(a,b)
    for q in reversed(support):
        if pauli.x>>q&1:
            qc.h(q)
            if pauli.z>>q&1: qc.s(q)


def occupations(cfg):
    bits=[0]*cfg.qubits
    for row in initial_site_rows(cfg):
        for spin_index,spin in enumerate(SPINS):
            bits[2*int(row['site'])+spin_index]=int(row[f'n_{spin}_initial'])
    return bits
