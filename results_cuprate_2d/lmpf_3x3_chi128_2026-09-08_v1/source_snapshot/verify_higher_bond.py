"""Audit saved higher-bond operator states and independently reconstruct flags."""
from pathlib import Path
import argparse,json,sys,time
import importlib.metadata as md
import numpy as np
import quimb.tensor as qtn
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from lmpf_2d.model import digest
from lmpf_2d.tn_storage import load_tn,bounded_contract,expectation_zero
from lmpf_2d.operators import overlap_network

def read(path):return json.loads(path.read_text())
def verify(folder):
    dest=folder/'verification'
    if dest.exists():raise FileExistsError('Preserve previous verification')
    dest.mkdir();started=time.monotonic();plan=read(folder/'plan.json');summary=read(folder/'summary.json')
    for path,h in read(folder/'sha256.json').items():
        if digest(folder/path)!=h:raise ValueError('Changed output '+path)
    for path,h in plan['source_sha256'].items():
        if digest(ROOT/path)!=h or digest(folder/'source_snapshot'/Path(path).name)!=h:raise ValueError('Changed source '+path)
    gram_error=0.;gradient_error=0.;expectation_error=0.;checked=0;failures=[];flags=[];cost=0
    for observable in plan['observables']:
        path=folder/f'observable_{observable:02d}.json'
        if not path.exists():failures.append({'observable':observable,'reason':'Not evaluated'});continue
        record=read(path)
        for chi,result in record['chi_results'].items():
            if result['failure']:
                failures.append({'observable':observable,'chi':chi,'reason':result['failure']});continue
            states=[load_tn(folder/'states'/f'obs{observable:02d}_chi{chi}_arm{arm}') for arm in range(4)]
            exact=np.asarray(result['overlaps_exact']);alternative=np.zeros((4,4))
            for i in range(4):
                for j in range(i,4):
                    network=(states[i].H & states[j]) if plan.get('overlap_contraction')=='raw_tn_for_independent_audit' else overlap_network(states[i],states[j])
                    # Different tensor ordering feeds a fresh greedy contraction tree.
                    reverse=qtn.TensorNetwork([t.copy() for t in reversed(network.tensors)])
                    reverse.exponent=network.exponent
                    value,info=bounded_contract(reverse);cost=max(cost,info['max_elements'])
                    alternative[i,j]=alternative[j,i]=value
            gram_error=max(gram_error,float(np.max(abs(exact-alternative))))
            np.testing.assert_allclose(exact,alternative,atol=1e-10,rtol=1e-9)
            value=expectation_zero(states[0]);expectation_error=max(expectation_error,abs(value-result['ideal_tn_expectation']))
            if abs(value-result['ideal_tn_expectation'])>1e-10:raise ValueError('Changed ideal TN expectation')
            for kind,fits in result['fits'].items():
                if fits.get('rejected',False):continue
                f=np.asarray(result['overlaps_exact' if kind=='exact' else 'overlaps_lcbp'])
                if np.linalg.eigvalsh(f).min() < -1e-8:raise ValueError('Accepted indefinite Gram')
                for fit in fits.values():
                    c=np.asarray(fit['coefficients']);gradient=f[1:,1:]@c-f[1:,0]+fit['ridge']*c
                    delta=float(np.max(abs(gradient-gradient.mean())));gradient_error=max(gradient_error,delta)
                    if abs(c.sum()-1)>1e-9 or delta>1e-7:raise ValueError('Fit constraints or stationarity failed')
                    residual=f[0,0]-2*f[1:,0]@c+c@f[1:,1:]@c
                    if abs(residual-fit['projection_residual'])>1e-8:raise ValueError('Wrong projection residual')
                    checked+=1
        # Reconstruct the acceptance flag without calling the production predicate.
        levels=plan.get('comparison_levels',[2,4])
        low=record['chi_results'].get(str(levels[0]));high=record['chi_results'].get(str(levels[1]));available=True
        for item in (low,high):
            if item is None or item['failure'] or 'ridge' not in item.get('fits',{}).get('exact',{}):available=False
        if available:
            delta=np.linalg.norm(np.array(high['overlaps_exact'])-low['overlaps_exact'])/np.linalg.norm(high['overlaps_exact'])
            dc=np.linalg.norm(np.array(high['fits']['exact']['ridge']['coefficients'])-low['fits']['exact']['ridge']['coefficients'],ord=1)
            passed=bool(delta<=.01 and dc<=.05)
            np.testing.assert_allclose([delta,dc],[record['stability']['relative_gram_change'],record['stability']['ridge_coefficient_l1_change']],atol=1e-12)
        else:passed=False
        if passed!=record['stability']['passes_local_flags']:raise ValueError('Incorrect local stability classification')
        flags.append(passed)
    expected_pass=len(flags)==len(plan['observables']) and all(flags)
    if expected_pass!=summary['local_stability_flags_pass']:raise ValueError('Incorrect overall stability classification')
    report={'status':'HIGHER_BOND_SAVED_EVIDENCE_VERIFIED','fits_checked':checked,'preserved_failures':failures,
        'maximum_gram_reconstruction_error':gram_error,'maximum_optimizer_projected_gradient':gradient_error,
        'maximum_ideal_expectation_reconstruction_error':expectation_error,'largest_contracted_intermediate_elements':cost,
        'local_stability_flags_pass':expected_pass,'full_profile_or_8_twirl_validation':False,
        'new_qpu_seconds':0,'seconds':time.monotonic()-started,'verification_source_sha256':digest(Path(__file__)),
        'versions':{name:md.version(name) for name in ('numpy','scipy','qiskit','qiskit-aer','quimb','cotengra')},
        'scope':'Saved-state, alternate-contraction, fitting and classification audit; not a physical convergence or noise-model certificate.'}
    (dest/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('folder',type=Path);args=p.parse_args()
    with threadpool_limits(limits=1):verify(args.folder)
