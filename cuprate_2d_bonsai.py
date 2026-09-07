"""Product-preserving hardware-tree mapping and SWAP-free parity synthesis.

Conventions and frozen target: BONSAI_LOCAL_PROTOCOL.md.
No provider APIs. Uses the already tested exact integer Pauli representation.
"""
from collections import deque
from functools import lru_cache
import math
import numpy as np
import networkx as nx
from qiskit import QuantumCircuit
from cuprate_2d_pa_mapping import P, letters
from cuprate_2d_shallow_network import network_events
from cuprate_2d_fermionic_mapping import pair_model


def gf2_inverse(rows,n):
    work=[int(row)|(1<<(n+i)) for i,row in enumerate(rows)]
    for col in range(n):
        pivot=next((j for j in range(col,n) if work[j]>>col&1),None)
        if pivot is None: raise ValueError('Singular occupation parity matrix')
        work[col],work[pivot]=work[pivot],work[col]
        for row in range(n):
            if row!=col and work[row]>>col&1: work[row]^=work[col]
    if [row&((1<<n)-1) for row in work]!=[1<<i for i in range(n)]:
        raise AssertionError('GF2 elimination failed')
    return [row>>n for row in work]


def parity_transform(rows,bits):
    value=sum(int(bit)<<i for i,bit in enumerate(bits))
    return [(row&value).bit_count()%2 for row in rows]


class Bonsai:
    def __init__(self,graph,labeling='z_priority'):
        self.graph=nx.Graph(graph)
        self.n=len(graph); self.modes=self.n
        if set(graph)!=set(range(self.n)) or not nx.is_connected(graph):
            raise ValueError('Connected graph with nodes0..n-1 required')
        if max(dict(graph.degree).values())>4:
            raise ValueError('Pilot supports degree<=4 hardware')
        distance=dict(nx.all_pairs_shortest_path_length(graph))
        self.paths=dict(nx.all_pairs_shortest_path(graph))
        root_order=sorted(graph,key=lambda q:(max(distance[q].values()),sum(distance[q].values()),q))
        # A root can have at most3 children. Try central roots without assuming
        # that deleting an arbitrary fourth root edge preserves connectivity.
        for root in root_order:
            seen={root}; children={q:[] for q in graph}; parent={root:None}; order=[root]
            for q in order:
                available=sorted((r for r in graph[q] if r not in seen),
                                 key=lambda r:(-graph.degree[r],r))
                for r in available[:3]:
                    children[q].append(r); parent[r]=q; seen.add(r); order.append(r)
            if len(seen)==self.n: break
        else: raise ValueError('Could not construct a hardware ternary spanning tree')
        self.root=root; self.children=children; self.parent=parent; self.order=order
        self.tree=nx.Graph([(p,q) for q,p in parent.items() if p is not None])
        self.tree.add_nodes_from(graph)
        heights={}
        for q in reversed(order): heights[q]=1+max((heights[r] for r in children[q]),default=0)
        self.links={}
        for q in order:
            descendants=sorted(children[q],key=lambda r:(-heights[r],r))
            labels={'z_priority':['Z','X','Y'],'xyz':['X','Y','Z']}.get(labeling)
            if labels is None: raise ValueError('Unknown tree labeling')
            self.links[q]={label:(descendants[k] if k<len(descendants) else None)
                           for k,label in enumerate(labels)}
        prefixes={root:P()}
        for q in order:
            for label,child in self.links[q].items():
                if child is not None: prefixes[child]=prefixes[q]*letters([(q,label)])
        self.pairs=[]
        for node in range(self.n):
            pair=[]
            for first in 'XY':
                p=prefixes[node]*letters([(node,first)])
                child=self.links[node][first]
                while child is not None:
                    p=p*letters([(child,'Z')]); child=self.links[child]['Z']
                pair.append(p)
            self.pairs.append(tuple(pair))
        self.base_vertices=[-1j*a*b for a,b in self.pairs]
        if any(v.x!=0 or v.phase!=1 for v in self.base_vertices):
            raise AssertionError('Fock-product preservation failed')
        self.assignment=list(range(self.n))
        self.set_assignment(self.assignment)
        self.parity_plan_cache={}
        self.labeling=labeling

    def set_assignment(self,assignment):
        if sorted(assignment)!=list(range(self.n)): raise ValueError('Assignment must be a permutation')
        self.assignment=list(map(int,assignment))
        self.vertices=[self.base_vertices[i] for i in self.assignment]
        self.decode_rows=[v.z for v in self.vertices]
        self.encode_rows=gf2_inverse(self.decode_rows,self.n)

    def gamma(self,mode,odd=0):
        return self.pairs[self.assignment[mode]][odd]

    def vertex(self,mode): return self.vertices[mode]

    def hopping_nodes(self,p,q):
        a,b=self.pairs[p]; c,d=self.pairs[q]
        return (0.5j*a*d,-0.5j*b*c)

    def hopping(self,p,q):
        return self.hopping_nodes(self.assignment[p],self.assignment[q])

    def onsite_nodes(self,p,q):
        a,b=self.base_vertices[p],self.base_vertices[q]
        return (P(phase=.25),-.25*a,-.25*b,.25*a*b)

    def onsite(self,p,q):
        return self.onsite_nodes(self.assignment[p],self.assignment[q])

    def encode(self,bits): return parity_transform(self.encode_rows,bits)
    def decode(self,bits): return parity_transform(self.decode_rows,bits)

    def preparation(self,bits):
        if len(bits)!=self.n or any(bit not in (0,1) for bit in bits):
            raise ValueError('A binary occupation vector is required')
        circuit=QuantumCircuit(self.n)
        for q,bit in enumerate(self.encode(bits)):
            if bit: circuit.x(q)
        return circuit

    def audit(self):
        operators=[p for pair in self.pairs for p in pair]; checks=0
        for i,a in enumerate(operators):
            assert a*a==P()
            for b in operators[i+1:]:
                assert not a.commutes(b); checks+=1
        assert nx.is_tree(self.tree)
        assert all(self.graph.has_edge(a,b) for a,b in self.tree.edges)
        for i in range(self.n):
            bits=[0]*self.n; bits[i]=1
            assert self.decode(self.encode(bits))==bits
        return {'qubits':self.n,'encoding_ancillas':0,'root':self.root,
            'tree_edges':len(self.tree.edges),'tree_height':max(nx.single_source_shortest_path_length(self.tree,self.root).values()),
            'Majorana_anticommutation_checks':checks,
            'occupation_weight_max':max(v.z.bit_count() for v in self.vertices),
            'occupation_weight_mean':float(np.mean([v.z.bit_count() for v in self.vertices])),
            'Fock_preparation':'X only','decoder':'GF2 parity matrix, not direct occupations'}

    def parity_plan(self,support):
        support=tuple(sorted(support))
        if not support: return [],None
        if support in self.parity_plan_cache: return self.parity_plan_cache[support]
        terminals=set(support)
        # Connected supports (all single-Majorana excitations) need no Steiner nodes.
        sub=self.graph.subgraph(terminals)
        if nx.is_connected(sub): tree=nx.minimum_spanning_tree(sub)
        else:
            tree=nx.Graph(); tree.add_node(min(terminals)); remaining=terminals-set(tree)
            while remaining:
                path=min((self.paths[a][b] for a in tree for b in remaining),
                         key=lambda path:(len(path),path))
                tree.add_edges_from(zip(path,path[1:]))
                remaining=terminals-set(tree)
            tree=nx.minimum_spanning_tree(tree)
        choices=[]
        for root in support:
            bfs=list(nx.bfs_tree(tree,root).edges())
            mask=set(support); gates=[]
            for parent,child in reversed(bfs):
                if child not in mask: continue
                if parent not in mask:
                    gates.append((parent,child)); mask.add(parent)
                gates.append((child,parent)); mask.remove(child)
            assert mask=={root}
            clocks={q:0 for q in tree}
            for a,b in gates: clocks[a]=clocks[b]=max(clocks[a],clocks[b])+1
            choices.append((len(gates),max(clocks.values()),root,gates))
        _,_,root,gates=min(choices,key=lambda item:item[:3])
        if not all(self.graph.has_edge(a,b) for a,b in gates): raise AssertionError('Nonlocal parity gate')
        result=(gates,root); self.parity_plan_cache[support]=result
        return result

    def rotation_cost(self,pauli):
        gates,_=self.parity_plan(pauli.support)
        return 2*len(gates)+.10*pauli.x.bit_count()

    def rotate(self,circuit,pauli,angle):
        if abs(pauli.phase.imag)>1e-13: raise ValueError('Non-Hermitian rotation')
        gates,root=self.parity_plan(pauli.support)
        if root is None:
            circuit.global_phase-=angle*pauli.phase.real; return
        for q in pauli.support:
            if pauli.x>>q&1:
                if pauli.z>>q&1: circuit.sdg(q)
                circuit.h(q)
        for a,b in gates: circuit.cx(a,b)
        circuit.rz(2*angle*pauli.phase.real,root)
        for a,b in reversed(gates): circuit.cx(a,b)
        for q in reversed(pauli.support):
            if pauli.x>>q&1:
                circuit.h(q)
                if pauli.z>>q&1: circuit.s(q)

    def evolution(self,cfg):
        if cfg.qubits!=self.n: raise ValueError('Mode count mismatch')
        circuit=QuantumCircuit(self.n)
        for event in network_events(cfg):
            p,q=event['modes']
            if event['hopping_angle']:
                for pauli in self.hopping(p,q):
                    self.rotate(circuit,pauli,event['hopping_angle']/2)
            if event['onsite_angle']:
                for pauli in self.onsite(p,q):
                    self.rotate(circuit,pauli,-event['onsite_angle'])
        if cfg.chemical_potential:
            for mode in range(self.n):
                circuit.global_phase+=cfg.chemical_potential*cfg.total_time/2
                self.rotate(circuit,self.vertex(mode),cfg.chemical_potential*cfg.total_time/2)
        circuit.metadata={'family':'hardware_tree_Bonsai','same_old_finite_circuit':True,
            'encoding_ancillas':0,'steps':cfg.steps,'dt':cfg.dt,'time':cfg.total_time,
            'qDRIFT':False,'decode_rows':[str(row) for row in self.decode_rows]}
        return circuit

    def cost_matrices(self):
        if hasattr(self,'_cost_cache'): return self._cost_cache
        hop=np.zeros((self.n,self.n)); onsite=np.zeros_like(hop)
        for p in range(self.n):
            for q in range(p+1,self.n):
                hop[p,q]=hop[q,p]=sum(self.rotation_cost(r) for r in self.hopping_nodes(p,q))
                onsite[p,q]=onsite[q,p]=sum(self.rotation_cost(r) for r in self.onsite_nodes(p,q))
        self._cost_cache=(hop,onsite)
        return self._cost_cache


def anneal(mapping,cfg,seed=9,proposals=15000):
    """Optimize PAIR assignments only; equal visits in our fixed network target."""
    hopping,onsite=mapping.cost_matrices()
    h,u=pair_model(cfg)
    terms=[(p,q,hopping) for (p,q),c in h.items() if c]
    terms += [(p,q,onsite) for (p,q),c in u.items() if c]
    incident=[[] for _ in range(mapping.n)]
    for index,(p,q,_) in enumerate(terms):
        incident[p].append(index); incident[q].append(index)
    assignment=list(mapping.assignment)
    def cost(ids): return sum(terms[k][2][assignment[terms[k][0]],assignment[terms[k][1]]] for k in ids)
    current=cost(range(len(terms))); initial=current
    best=current; best_assignment=assignment.copy(); rng=np.random.default_rng(seed)
    trace=[{'proposal':0,'cost':current}]
    for k in range(proposals):
        p,q=rng.choice(mapping.n,2,replace=False)
        touched=set(incident[p]+incident[q]); before=cost(touched)
        assignment[p],assignment[q]=assignment[q],assignment[p]
        delta=cost(touched)-before
        temperature=5.*(.01/5.)**(k/max(1,proposals-1))
        if delta<=0 or rng.random()<math.exp(-min(700,delta/temperature)):
            current+=delta
            if current<best-1e-10: best=current; best_assignment=assignment.copy()
        else: assignment[p],assignment[q]=assignment[q],assignment[p]
        if (k+1)%1000==0: trace.append({'proposal':k+1,'cost':current,'best':best})
    mapping.set_assignment(best_assignment)
    direct=sum(matrix[mapping.assignment[p],mapping.assignment[q]] for p,q,matrix in terms)
    if abs(direct-best)>1e-7: raise AssertionError('Annealing incremental-cost drift')
    return {'initial_proxy':initial,'best_proxy':float(direct),'assignment':best_assignment,
        'trace':trace,'proposals':proposals,'seed':seed,
        'cost_is_not_depth_or_fidelity':True}
