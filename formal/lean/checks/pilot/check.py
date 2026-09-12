"""Independent finite integer check of the 3x3 central doublon pilot.
ASSERT_CONVENTION: natural_units=lattice, state_normalization=non-relativistic
Does not import Lean exporters or the original power/convolution helpers.
"""
from pathlib import Path
from collections import defaultdict
from fractions import Fraction
import hashlib,json,math
HERE=Path(__file__).resolve().parent
INITIAL=sum(1<<(2*i) for i in [0,2,6,8])+sum(1<<(2*i+1) for i in [1,3,5,7])
def projected(s): return ((s>>8)&3)==3
def advance(v,U=8,diagonal=True):
    out=defaultdict(int)
    for s,a in v.items():
        out[s]+=a*4*U*sum(((s>>(2*i))&3)==3 for i in range(9))
        for i in range(9):
            for j in range(i+1,9):
                dx=abs(i%3-j%3);dy=abs(i//3-j//3)
                if dx+dy==1: w=-4
                elif diagonal and dx==dy==1: w=1
                else: continue
                for spin in range(2):
                    p,q=2*i+spin,2*j+spin
                    if ((s>>p)&1)==((s>>q)&1):continue
                    source,target=(p,q) if (s>>p)&1 else (q,p)
                    sign=(-1)**((s&((1<<source)-1)).bit_count())
                    removed=s^(1<<source)
                    sign*=(-1)**((removed&((1<<target)-1)).bit_count())
                    out[removed|(1<<target)]+=a*w*sign
    return {s:a for s,a in out.items() if a}
def calculation(U=8,diagonal=True):
    powers=[{INITIAL:1}]
    for _ in range(4): powers.append(advance(powers[-1],U,diagonal))
    result=[]
    for n in [0,2,4]:
        numerator=0
        for k in range(n+1):
            dot=sum(a*powers[n-k].get(s,0) for s,a in powers[k].items() if projected(s))
            numerator+=(-1)**k*math.comb(n,k)*dot
        result.append(Fraction((-1)**(n//2)*numerator,4**n*math.factorial(n)))
    proj2={s:a for s,a in powers[2].items() if projected(s)}
    return result,proj2,[len(v) for v in powers]
def main():
    result,proj,support=calculation()
    archive=HERE.parent/'lean-hubbard-3x3-verification/inputs/coefficients.json'
    saved=json.loads(archive.read_text())['coefficients']['D_centre'][:3]
    assert list(map(str,result))==saved==['0','0','1']
    assert len(proj)==16 and sum(a*a for a in proj.values())==1024
    free,_,_=calculation(U=0); no_diagonal,_,_=calculation(diagonal=False)
    assert free==result and no_diagonal==[0,0,0]
    numerical=[dict(T=str(t),leading=float(t**4)) for t in [Fraction(1,100),Fraction(1,50),Fraction(1,10)]]
    report=dict(status='INDEPENDENT_INTEGER_PILOT_PASSED',coefficients=list(map(str,result)),
        projected_two_step_states=len(proj),h4_projected_square_norm=1024,
        h_projected_square_norm=4,support_sizes=support,
        U0_coefficients=list(map(str,free)),no_diagonal_coefficients=list(map(str,no_diagonal)),
        sample_leading_values=numerical,archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        warning='Leading T4 term alone is insensitive to U; not a test of full interacting dynamics.',qpu_seconds=0)
    (HERE/'independent-check.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
