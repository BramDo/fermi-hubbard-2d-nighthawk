"""Independent analytic/numerical checks; these floats are not Lean certificates.
ASSERT_CONVENTION: natural_units=lattice, state_normalization=non-relativistic
Uses the earlier independent full-bitstring builder, not an archive propagator.
"""
from pathlib import Path
from itertools import combinations
import datetime,hashlib,json,time
import numpy as np
import scipy
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import expm_multiply
import sympy as sp
from check import advance,INITIAL,projected

HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    out=HERE/'dynamics-checks'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out.mkdir(parents=True)
    tick=time.perf_counter()
    masks=[sum(1<<i for i in c) for c in combinations(range(9),4)]
    basis=[sum(((u>>i)&1)<<(2*i) for i in range(9))+sum(((d>>i)&1)<<(2*i+1) for i in range(9)) for u in masks for d in masks]
    index={s:i for i,s in enumerate(basis)}
    rr=[];cc=[];vv=[]
    for col,s in enumerate(basis):
        for target,a in advance({s:1}).items():
            rr.append(index[target]);cc.append(col);vv.append(a/4)
    H=coo_matrix((vv,(rr,cc)),shape=(15876,15876)).tocsr()
    assert (H-H.T).nnz==0
    psi0=np.zeros(15876,dtype=complex);psi0[index[INITIAL]]=1
    centre=np.array([projected(s) for s in basis])
    checks=[]
    for T in [0.005,0.01,0.02]:
        psi=expm_multiply((-1j*T)*H,psi0)
        value=float(np.sum(np.abs(psi[centre])**2)); leading=T**4
        checks.append(dict(T=T,numerical_doublon=value,leading_T4=leading,ratio=value/leading,
            relative_leading_error=abs(value-leading)/value,norm=float(np.vdot(psi,psi).real)))
    assert all(abs(row['norm']-1)<1e-12 for row in checks)
    assert all(abs(row['ratio']-1)<0.004 for row in checks)
    scaled=[(1-row['ratio'])/row['T']**2 for row in checks]
    assert all(abs(v-293/36)<0.03 for v in scaled)
    # Independent symbolic noncommuting two-level example and commuting limit.
    T=sp.symbols('T',real=True);X=sp.Matrix([[0,1],[1,0]]);O=sp.diag(0,1)
    evolved=sp.exp(sp.I*T*X)*O*sp.exp(-sp.I*T*X)
    toy_series=sp.series(evolved[0,0],T,0,6).removeO().expand()
    assert sp.simplify(toy_series-(T**2-T**4/3))==0
    diagonal=sp.diag(1,2)
    assert sp.simplify(sp.exp(sp.I*T*diagonal)*O*sp.exp(-sp.I*T*diagonal)-O)==sp.zeros(2)
    result=dict(status='EXPONENTIAL_PILOT_NUMERICAL_AND_SYMBOLIC_CHECKS_PASSED',
        dimension=15876,nnz=int(H.nnz),small_time_checks=checks,
        scaled_next_order_estimates=scaled,archived_next_coefficient='-293/36 (not Lean-certified here)',
        toy_two_level_series=str(toy_series),commuting_limit='unchanged observable',
        numpy=np.__version__,scipy=scipy.__version__,sympy=sp.__version__,seconds=time.perf_counter()-tick,
        source_sha256=sha(Path(__file__)),builder_sha256=sha(HERE/'check.py'),
        rigorous_floating_point_enclosure=False,qpu_seconds=0)
    (out/'result.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    (HERE/'latest-dynamics-check.json').write_text(json.dumps(dict(path=str(out),status=result['status']),indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True)
if __name__=='__main__':main()
