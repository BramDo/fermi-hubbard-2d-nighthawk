"""Exact left-to-right contraction of a verified open operator-MPS chain.

Avoid precontracting every pair of local bra/ket tensors, which creates chi^4
objects unnecessarily. All contractions retain the normalized Pauli-basis HS
convention; no rescaling of the observable or target fitting is introduced.
"""
import numpy as np

def chain_arrays(tn):
    sites=tuple(tn.sites)
    if sites!=tuple(range(len(sites))):raise ValueError('Expected ordered open chain sites')
    arrays=[]
    for q in sites:
        tensor=tn[f'I{q}'];physical=tn.site_ind(q);inds=[];dimensions=[]
        for neighbour in (q-1,q+1):
            if neighbour not in sites:dimensions.append(1);continue
            shared=set(tensor.inds)&set(tn[f'I{neighbour}'].inds)
            if len(shared)!=1:raise ValueError('Missing or multiple neighbour bonds')
            bond=shared.pop();inds.append(bond);dimensions.append(tensor.ind_size(bond))
        if physical not in tensor.inds or set(tensor.inds)!=set(inds+[physical]):
            raise ValueError('Non-chain index or missing physical index')
        if tensor.ind_size(physical)!=4:raise ValueError('Expected dimension-four Pauli coordinates')
        arrays.append(tensor.transpose(*inds,physical).data.reshape(*dimensions,4))
    return arrays

def chain_overlap(left,right,*,max_elements=2**22,max_flops=2e9):
    a=chain_arrays(left);b=chain_arrays(right)
    if len(a)!=len(b):raise ValueError('Different chain lengths')
    environment=np.ones((1,1),dtype=np.result_type(a[0],b[0]));peak=1;flops=0
    for aa,bb in zip(a,b):
        la,ra,p=aa.shape;lb,rb,pb=bb.shape
        if environment.shape!=(la,lb) or p!=pb:raise ValueError('Incompatible chain environments')
        peak=max(peak,aa.size,bb.size,environment.size,lb*ra*p,ra*rb)
        flops+=2*(lb*la*ra*p+ra*lb*p*rb)
        if peak>max_elements or flops>max_flops:raise ValueError('Chain contraction resource guard')
        temporary=(environment.T@aa.conj().reshape(la,ra*p)).reshape(lb,ra,p)
        environment=temporary.transpose(1,0,2).reshape(ra,lb*p)@bb.transpose(0,2,1).reshape(lb*p,rb)
    if environment.shape!=(1,1):raise ValueError('Open right boundary required')
    value=environment[0,0]*10**(left.exponent+right.exponent)
    if not np.isfinite(value) or abs(np.imag(value))>1e-9:raise ValueError('Invalid real operator inner product')
    return float(np.real(value)),{'max_elements':int(peak),'estimated_flops':int(flops),'method':'exact_open_chain_environment'}

def chain_expectation_zero(tn):
    environment=np.ones(1)
    for array in chain_arrays(tn):environment=environment@(array[:,:,0]+array[:,:,3])
    value=environment.item()*10**tn.exponent
    if not np.isfinite(value) or abs(np.imag(value))>1e-9:raise ValueError('Invalid real expectation')
    return float(np.real(value))
