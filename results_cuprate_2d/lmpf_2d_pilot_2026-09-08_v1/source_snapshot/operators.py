"""Pauli-coordinate Heisenberg channels and 2D BP operator tensor networks.

Axes are physical qubits in ascending order. Local basis is I,X,Y,Z,
orthonormal for the normalized Hilbert-Schmidt inner product Tr(A^dag B)/2**n.
No state-dependent expectation value enters the overlap calculation.
"""
from dataclasses import dataclass,field
import time
import numpy as np
import quimb.tensor as qtn
from quimb.tensor.belief_propagation.d2bp import D2BP
from quimb.tensor.belief_propagation.d1bp import D1BP
from qiskit.quantum_info import PTM,Operator

@dataclass
class Step:
    name: str
    qubits: tuple
    parameters: tuple
    adjoint_unitary: np.ndarray
    lindblad_decay_rate: float

    def channel(self,scale):
        if not np.isfinite(scale) or scale<0:raise ValueError('Invalid noise scale')
        decay=np.full(4**len(self.qubits),np.exp(-scale*self.lindblad_decay_rate))
        decay[0]=1.0
        # Forward channel = depolarization AFTER U; adjoint = U^dag AFTER D^dag.
        return self.adjoint_unitary*decay[None,:]

@dataclass
class ChannelBlock:
    """Exact composition on at most two qubits, with no change to QPU gates."""
    qubits: tuple
    steps: tuple
    cache: dict=field(default_factory=dict)
    @property
    def lindblad_decay_rate(self):return sum(s.lindblad_decay_rate for s in self.steps)
    def channel(self,scale):
        if scale not in self.cache:
            k=len(self.qubits);a=np.eye(4**k)
            for step in self.steps:
                g=step.channel(scale)
                if k==2 and len(step.qubits)==1:
                    g=np.kron(g,np.eye(4)) if step.qubits[0]==self.qubits[0] else np.kron(np.eye(4),g)
                elif k==2 and step.qubits!=self.qubits:
                    g=g.reshape(4,4,4,4).transpose(1,0,3,2).reshape(16,16)
                a=a@g
            self.cache[scale]=a
        return self.cache[scale]

def fuse_steps(steps):
    """Maximal consecutive <=2-qubit blocks, preserving noisy channel order."""
    blocks=[];current=[];qubits=set()
    for step in steps:
        new=qubits|set(step.qubits)
        disjoint_singletons=(len(qubits)==1 and len(step.qubits)==1 and len(new)==2)
        if len(new)>2 or disjoint_singletons:
            blocks.append(ChannelBlock(tuple(sorted(qubits)),tuple(current)))
            current=[];qubits=set()
        current.append(step);qubits.update(step.qubits)
    if current:blocks.append(ChannelBlock(tuple(sorted(qubits)),tuple(current)))
    return blocks

def adjoint_ptm(operation):
    k=operation.num_qubits
    if k not in (1,2):raise ValueError('Only one- and two-qubit gates are supported')
    a=np.asarray(PTM(Operator(operation)).data).conj().T
    if np.max(abs(a.imag))>1e-10:raise ValueError('Non-real unitary Pauli transfer matrix')
    a=a.real
    # Qiskit qarg 0 is least significant; quimb's first gate axis is most significant.
    if k==2:a=a.reshape(4,4,4,4).transpose(1,0,3,2).reshape(16,16)
    return a

def compile_steps(circuit,rate_for_gate):
    steps=[];cache={}
    for item in circuit.data:
        op=item.operation;qs=tuple(circuit.find_bit(q).index for q in item.qubits)
        if op.name=='barrier':continue
        if op.name in ['measure','reset','delay'] or op.num_clbits:
            raise ValueError('Pass a bound, unitary dynamics circuit without measurement/reset/delay')
        params=tuple(float(p) for p in op.params)
        key=(op.name,params)
        if key not in cache:cache[key]=adjoint_ptm(op)
        rate=float(rate_for_gate(op.name,qs))
        if not np.isfinite(rate) or rate<0:raise ValueError('Invalid effective Lindblad rate')
        steps.append(Step(op.name,qs,params,cache[key],rate))
    return steps

def pauli_vector(n,support):
    if n>10:raise ValueError('Dense oracle is capped at 10 qubits')
    vec=np.zeros((4,)*n,dtype=float);inds=[0]*n
    for q,p in support.items():inds[q]='IXYZ'.index(p)
    vec[tuple(inds)]=1
    return vec

def apply_local(vec,matrix,where):
    n=vec.ndim;where=tuple(where)
    order=where+tuple(q for q in range(n) if q not in where)
    x=vec.transpose(order).reshape(4**len(where),-1)
    y=(matrix@x).reshape((4,)*n)
    return y.transpose(np.argsort(order))

def evolve_dense(n,support,steps,scale=0):
    vec=pauli_vector(n,support)
    for step in reversed(steps):vec=apply_local(vec,step.channel(scale),step.qubits)
    return vec

def initial_functional(bits):
    if len(bits)>10:raise ValueError('Dense functional capped at 10 qubits')
    result=np.array(1.0)
    for bit in bits:result=np.multiply.outer(result,np.array([1.,0.,0.,1-2*int(bit)]))
    return result

def product_operator_tn(n,edges,support):
    edges=sorted({tuple(sorted(e)) for e in edges})
    tensors=[]
    for q in range(n):
        incident=[f'b{a}_{b}' for a,b in edges if q in (a,b)]
        data=np.zeros((4,)+(1,)*len(incident));data[('IXYZ'.index(support.get(q,'I')),)+(0,)*len(incident)]=1
        tensors.append(qtn.Tensor(data,inds=(f'k{q}',*incident),tags=(f'I{q}',)))
    tn=qtn.TensorNetwork(tensors)
    return tn.view_as_(qtn.TensorNetworkGenVector,sites=tuple(range(n)),site_tag_id='I{}',site_ind_id='k{}')

def evolve_tn(n,edges,support,steps,scale=0,*,chi=4,bp_tolerance=1e-8,bp_iterations=50,
              deadline=None):
    if chi<1:raise ValueError('chi must be positive')
    edge_set={tuple(sorted(e)) for e in edges}
    tn=product_operator_tn(n,edges,support)
    bp=D2BP(tn,inplace=True,optimize='greedy',damping=0.1,local_convergence=False,
             normalize='L2',distance='L2')
    info={};bp.run(max_iterations=bp_iterations,tol=bp_tolerance,info=info)
    convergence=[];truncation=[];dirty=False;roundoff_psd_repairs=0
    for j,step in enumerate(reversed(steps)):
        if deadline is not None and time.monotonic()>deadline:raise TimeoutError('TN time budget reached')
        if len(step.qubits)==2 and tuple(sorted(step.qubits)) not in edge_set:
            raise ValueError('Nonlocal gate: native circuit must match the 2D TN graph')
        if len(step.qubits)==2 and dirty:
            bp.run(max_iterations=bp_iterations,tol=bp_tolerance)
            dirty=False
        for key,m in bp.messages.items():
            vals,vecs=np.linalg.eigh((m+m.conj().T)/2)
            maximum=float(np.max(np.abs(vals)))
            if not np.all(np.isfinite(vals)) or maximum==0 or vals.min() < -1e-9*maximum:
                raise ValueError(f'Invalid PSD BP message at step {j}, scale {scale}, chi {chi}: {vals.tolist()}')
            if vals.min()<0:
                bp.messages[key]=(vecs*np.maximum(vals,0))@vecs.conj().T
                roundoff_psd_repairs+=1
        gate_info={}
        bp.gate_(step.channel(scale),step.qubits,max_bond=chi,cutoff=1e-12,
                 cutoff_mode='rsum2',renorm=0,info=gate_info)
        if j%16==0:
            # Positive scalar balancing is exact; retain tn.exponent.
            bp.tn.equalize_norms_(value=1.0)
        # quimb 1.13 caches array references in its BP expressions. Rebuild
        # after gates/rescaling even if bond shapes stayed unchanged.
        for ix in bp.tn.ind_map:
            if ix not in bp.output_inds:bp.build_expr(ix)
        if len(step.qubits)==2:
            inf={};bp.run(max_iterations=bp_iterations,tol=bp_tolerance,info=inf)
            convergence.append(inf)
            # quimb may expose local discarded weights; never invent a certified sum if absent.
            truncation.append({str(k):float(v) for k,v in gate_info.items() if np.isscalar(v)})
        elif scale*step.lindblad_decay_rate>0:
            dirty=True
    return bp.tn,{'two_qubit_updates':len(convergence),
        'bp_nonconverged_updates':sum(not c.get('converged',False) for c in convergence),
        'bp_max_message_residual':max((float(c.get('max_mdiff',0)) for c in convergence),default=0),
        'chi':chi,'local_truncation_diagnostics':truncation,
        'roundoff_psd_repairs':roundoff_psd_repairs,
        'tensor_scale_exponent':float(bp.tn.exponent),
        'global_truncation_error_certified':False}

def dense_tn(tn):
    if tn.nsites>10:raise ValueError('Dense TN check capped at 10 sites')
    return tn.contract(all,output_inds=tuple(tn.site_ind(q) for q in tn.sites),optimize='greedy').data

def overlap_network(a,b):
    tn=a.H & b
    for tag in a.site_tags:tn.contract_tags_(tag,which='any')
    tn.fuse_multibonds_()
    return tn

def overlap(a,b,*,loop_size=4,exact=False,tolerance=1e-8,max_iterations=100):
    tn=overlap_network(a,b)
    if exact:
        value=tn.contract(all,optimize='greedy')
        return float(np.real_if_close(value)),{'method':'exact_contraction_of_truncated_2d_tn'}
    bp=D1BP(tn,damping=0.1)
    info={};bp.run(max_iterations=max_iterations,tol=tolerance,info=info)
    base=bp.contract()
    value=bp.contract_loop_series_expansion(gloops=loop_size,multi_excitation_correct=False,optimize='greedy')
    if not np.isfinite(value) or abs(np.imag(value))>1e-8:raise ValueError('Invalid loop-corrected overlap')
    return float(np.real(value)),{**info,'method':'2d_bp_loop_series','loop_size':loop_size,
        'bp_value':float(np.real(base)),'loop_correction':float(np.real(value-base))}

def gram_tn(states,*,loop_size=4,exact=False):
    k=len(states);f=np.zeros((k,k));diagnostics=[]
    for i in range(k):
        for j in range(i,k):
            value,info=overlap(states[i],states[j],loop_size=loop_size,exact=exact)
            f[i,j]=f[j,i]=value;diagnostics.append({'i':i,'j':j,**info})
    return f,diagnostics

def expectation_tn(tn,bits):
    if len(bits)>10:raise ValueError('Exact low-chi expectation contraction capped at 10 sites')
    out=tn.copy()
    for q,bit in enumerate(bits):out.add_tensor(qtn.Tensor([1.,0.,0.,1-2*int(bit)],inds=(tn.site_ind(q),),tags=(f'RHO{q}',)))
    return float(np.real_if_close(out.contract(all,optimize='greedy')))
