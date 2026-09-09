"""Constrained observable-overlap minimization, not target-value regression.

Robertson et al. arXiv:2609.05024v1, Eqs. 17-19 and Appendix A.
All overlaps use Tr(A^dagger B)/2**n; the normalization changes no minimizer.
"""
from dataclasses import dataclass,asdict
import numpy as np
from scipy.linalg import null_space

@dataclass
class Fit:
    coefficients: list
    projection_residual: float
    condition_constrained: float
    gram_min_eigenvalue: float
    coefficient_l1: float
    coefficient_l2_squared: float
    constraint_error: float
    ridge: float
    rank_constrained: int

    def to_dict(self):return asdict(self)

def fit_coefficients(overlaps, *, coefficient_sum=1.0, ridge=0.0, rcond=1e-10,
                     psd_tolerance=1e-8):
    """Row/column zero is the noiseless operator, remaining rows are noisy.

    ridge=0 implements the overlap objective; a positive fixed ridge is an
    explicitly labelled variance-regularized adaptation. No expectation values
    or initial-state vectors are accepted by this function.
    """
    f=np.asarray(overlaps)
    if f.ndim!=2 or f.shape[0]!=f.shape[1] or f.shape[0]<3:
        raise ValueError('Need square Gram matrix: ideal plus >=2 noisy arms')
    if not np.all(np.isfinite(f)) or not np.isfinite(coefficient_sum) or ridge<0:
        raise ValueError('Nonfinite input or negative regularization')
    if np.max(np.abs(f.imag if np.iscomplexobj(f) else 0))>1e-9:
        raise ValueError('Non-real overlaps for Hermitian operators')
    f=f.real.astype(float)
    if not np.allclose(f,f.T,atol=1e-10,rtol=1e-9):raise ValueError('Non-Hermitian Gram matrix')
    f=(f+f.T)/2
    eig=np.linalg.eigvalsh(f);scale=max(float(np.max(np.abs(eig))),1.0)
    if eig.min() < -psd_tolerance*scale:
        raise ValueError(f'Overlap Gram matrix is not PSD: min eigenvalue={eig.min()}')
    g=f[1:,1:];b=f[1:,0];k=len(b)
    z=null_space(np.ones((1,k)));c0=np.full(k,coefficient_sum/k)
    a=z.T@(g+ridge*np.eye(k))@z
    rhs=z.T@(b-(g+ridge*np.eye(k))@c0)
    vals,vecs=np.linalg.eigh((a+a.T)/2)
    threshold=rcond*max(float(np.max(np.abs(vals))),np.finfo(float).eps)
    keep=vals>threshold
    v=vecs[:,keep]
    x=v@((v.T@rhs)/vals[keep]) if np.any(keep) else np.zeros(k-1)
    c=c0+z@x
    residual=float(f[0,0]-2*b@c+c@g@c)
    if residual < -psd_tolerance*scale:raise ValueError('Negative projection residual beyond tolerance')
    condition=float(vals[keep].max()/vals[keep].min()) if np.any(keep) else float('inf')
    return Fit(c.tolist(),residual,condition,float(eig.min()),float(abs(c).sum()),
               float(c@c),float(c.sum()-coefficient_sum),float(ridge),int(keep.sum()))

def richardson_weights(scales):
    scales=np.asarray(scales,dtype=float)
    if scales.ndim!=1 or len(scales)<2 or np.any(scales<=0) or len(set(scales))!=len(scales):
        raise ValueError('Need distinct positive noise scales')
    target=np.zeros(len(scales));target[0]=1
    return np.linalg.solve(np.vander(scales,N=len(scales),increasing=True).T,target)

def linear_zne_weights(scales):
    scales=np.asarray(scales,dtype=float)
    design=np.column_stack((np.ones(len(scales)),scales))
    if np.linalg.matrix_rank(design)!=2:raise ValueError('Degenerate noise scales')
    return np.linalg.pinv(design)[0]

def estimate(coefficients, means, covariance):
    c=np.asarray(coefficients,float);m=np.asarray(means,float);cov=np.asarray(covariance,float)
    if m.shape!=c.shape or cov.shape!=(len(c),len(c)):raise ValueError('Shape mismatch')
    if np.linalg.eigvalsh((cov+cov.T)/2).min() < -1e-12:raise ValueError('Covariance not PSD')
    variance=float(c@cov@c)
    return {'value':float(c@m),'shot_standard_error':float(np.sqrt(max(variance,0)))}
