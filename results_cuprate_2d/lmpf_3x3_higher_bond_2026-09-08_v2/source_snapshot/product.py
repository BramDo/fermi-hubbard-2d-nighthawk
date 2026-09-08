"""Batched chi=1 operator TN, with no dense 4**n allocation.

Each row is amplitude * tensor_product(local Pauli-coordinate vectors).
Local factors have Euclidean norm one. Rank-one SVD truncation is exactly
the chi=1 local Schmidt truncation; it is not a higher-bond approximation.
All quantities use normalized Hilbert-Schmidt coordinates and are dimensionless.
"""
from dataclasses import dataclass
import time
import numpy as np

@dataclass
class Products:
    local: np.ndarray
    amplitude: np.ndarray
    truncation_bound: np.ndarray
    minimum_schmidt_gap: np.ndarray

def evolve_products(n,supports,steps,scale=1.,*,deadline=None):
    count=len(supports);local=np.zeros((count,n,4));local[:,:,0]=1
    for i,support in enumerate(supports):
        for q,p in support.items():local[i,q]=np.eye(4)['IXYZ'.index(p)]
    amp=np.ones(count);bound=np.zeros(count);gap=np.ones(count)
    for j,step in enumerate(reversed(steps)):
        if deadline is not None and time.monotonic()>deadline:raise TimeoutError('Product TN budget exceeded')
        g=step.channel(scale);qs=step.qubits
        if len(qs)==1:
            q=qs[0];v=local[:,q]@g.T;norm=np.linalg.norm(v,axis=1)
            local[:,q]=np.divide(v,norm[:,None],out=np.tile([1.,0,0,0],(count,1)),where=norm[:,None]>0)
            amp*=norm
        elif len(qs)==2:
            a,b=qs;pair=np.einsum('bi,bj->bij',local[:,a],local[:,b]).reshape(count,16)
            matrix=(pair@g.T).reshape(count,4,4)
            u,s,vh=np.linalg.svd(matrix,full_matrices=False)
            discarded=np.linalg.norm(s[:,1:],axis=1)
            # Unital depolarizing/unitary channels contract the HS norm. Triangle
            # inequality accumulates this conservative truncation bound (not an
            # interval-arithmetic certificate). It is often too loose to be useful.
            bound+=np.abs(amp)*discarded
            relevant=(np.abs(amp)>1e-14)&(s[:,0]>1e-14)
            relgap=np.divide(s[:,0]-s[:,1],s[:,0],out=np.ones(count),where=s[:,0]>0)
            gap=np.minimum(gap,np.where(relevant,relgap,1.))
            local[:,a]=u[:,:,0];local[:,b]=vh[:,0,:];amp*=s[:,0]
        else:raise ValueError('Only local one/two-qubit channels are supported')
        if not (np.isfinite(local).all() and np.isfinite(amp).all()):raise FloatingPointError('Nonfinite product TN')
    return Products(local,amp,bound,gap)

def overlaps(a,b):
    if a.local.shape!=b.local.shape:raise ValueError('Operator batch dimensions differ')
    return a.amplitude*b.amplitude*np.prod(np.sum(a.local*b.local,axis=2),axis=1)

def gram_mixtures(mixtures):
    """Gram of equal-weight mixtures of product operators, including cross-twirls."""
    count=len(mixtures[0][0].amplitude);k=len(mixtures);f=np.empty((count,k,k))
    for i in range(k):
        for j in range(i,k):
            value=sum(overlaps(a,b) for a in mixtures[i] for b in mixtures[j])/(len(mixtures[i])*len(mixtures[j]))
            f[:,i,j]=f[:,j,i]=value
    return f

def expectations(state,bits):
    bits=np.asarray(bits);return state.amplitude*np.prod(state.local[:,:,0]+(1-2*bits)*state.local[:,:,3],axis=1)

def dense_product(state,index):
    if state.local.shape[1]>10:raise ValueError('Dense product test capped at ten qubits')
    result=np.array(state.amplitude[index])
    for factor in state.local[index]:result=np.multiply.outer(result,factor)
    return result
