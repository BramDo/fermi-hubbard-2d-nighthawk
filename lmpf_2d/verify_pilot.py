"""Recheck saved pilot coefficients, samples, covariance and input hashes."""
from pathlib import Path
import argparse,io,json,sys,unittest
import numpy as np
from qiskit import qpy
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from lmpf_2d.model import FrozenSurrogate,digest,features,moments,physical_transform
from lmpf_2d.operators import compile_steps,fuse_steps,initial_functional,apply_local
from lmpf_2d.fit import linear_zne_weights,richardson_weights

def read(p):return json.loads(Path(p).read_text())
def verify(folder):
    dest=folder/'verification'
    if dest.exists():raise FileExistsError('Preserve prior verification')
    dest.mkdir()
    plan=read(folder/'plan.json');summary=read(folder/'summary.json')
    if summary['fully_evaluated_observables']!=12:raise ValueError('Not a complete pilot')
    for path,h in plan['source_sha256'].items():
        if digest(folder/'source_snapshot'/Path(path).name)!=h:raise ValueError('Snapshot hash mismatch')
        # The post-run validator can evolve independently; it is never imported by the pilot.
        if path!='lmpf_2d/verify_pilot.py' and digest(ROOT/path)!=h:
            raise ValueError(f'Current implementation differs from executed snapshot: {path}')
    for path,h in read(folder/'input_output_sha256.json').items():
        if digest(folder/path)!=h:raise ValueError(f'Output hash mismatch: {path}')
    stream=io.StringIO();suite=unittest.TestSuite()
    for name in ['test_lmpf_2d','test_lmpf_hardware_inputs']:suite.addTests(unittest.defaultTestLoader.loadTestsFromName(name))
    tests=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    (dest/'tests.txt').write_text(stream.getvalue())
    if not tests.wasSuccessful():raise RuntimeError('Regression tests failed')
    profile=FrozenSurrogate()
    if digest(profile.path)!=plan['noise']['calibration_sha256']:raise ValueError('Changed calibration')
    with (folder/'native_dynamics.qpy').open('rb') as f:native=qpy.load(f)[0]
    steps=fuse_steps(compile_steps(native,profile.rate));n=8;d=2**n
    basis_bits=((np.arange(d)[:,None]>>np.arange(n))&1)
    diagonal_indices=tuple((3*basis_bits).T)
    walsh=1-2*((basis_bits@basis_bits.T)%2)
    assignment=np.array([[1.]])
    for e0,e1 in reversed(profile.readout):assignment=np.kron(assignment,[[1-e0,e0],[e1,1-e1]])
    corrected=features(basis_bits,plan['logical_to_final_physical'],profile.readout)
    raw_features=features(basis_bits,plan['logical_to_final_physical'])
    forward_means=[];forward_cov=[];raw_means=[];raw_cov=[]
    for scale in [1,2,3]:
        # Independent forward propagation of rho's Pauli coefficients.
        rho=initial_functional(plan['initial_bits_physical'])/d
        for step in steps:rho=apply_local(rho,step.channel(scale).T,step.qubits)
        prob=walsh@rho[diagonal_indices]
        if abs(prob.sum()-1)>1e-10 or prob.min() < -1e-10:raise ValueError('Invalid forward state probabilities')
        observed=prob@assignment
        m,c=moments(observed,corrected);forward_means.append(m);forward_cov.append(c)
        m,c=moments(observed,raw_features);raw_means.append(m);raw_cov.append(c)
    forward_means=np.array(forward_means);forward_cov=np.array(forward_cov)
    samples=[];raw_samples=[];full_samples=[];shots=plan['shots_per_lmpf_arm']
    for scale in [1,2,3]:
        memory=read(folder/f'arm_{scale}_memory.json')['memory']
        bits=np.array([[int(c) for c in s[::-1]] for s in memory])
        x=features(bits,plan['logical_to_final_physical'],profile.readout)
        samples.append(x[:shots].mean(0));full_samples.append(x.mean(0))
        raw_samples.append(features(bits,plan['logical_to_final_physical']).mean(0))
    samples=np.array(samples);a,offset=physical_transform(n)
    ideal=np.asarray(summary['ideal_paulis']);max_gradient=0.;max_loop_error=0.;nonconverged=0;accepted=0
    for index in range(12):
        op=read(folder/'operators'/f'operator_{index:02d}.json')
        np.testing.assert_allclose(op['dense_heisenberg_forward_check'][1:],forward_means[:,index],atol=1e-8)
        if abs(op['exact_overlaps'][0][0]-1)>1e-9:raise ValueError('Noiseless operator norm changed')
        for tn in op['tensor_networks'].values():
            if tn['overlap_loop_contraction_error_frobenius'] is not None:
                max_loop_error=max(max_loop_error,tn['overlap_loop_contraction_error_frobenius'])
            nonconverged+=sum(p['bp_nonconverged_updates'] for p in tn['propagation'])
            for name,fit in tn['fits'].items():
                if fit.get('rejected'):continue
                f=np.asarray(tn['overlaps_lcbp'] if '_lcbp_' in name else tn['overlaps_exact_contraction_same_tn'])
                c=np.asarray(fit['coefficients']);g=f[1:,1:];b=f[1:,0]
                if abs(c.sum()-1)>1e-9:raise ValueError('Coefficient normalization changed')
                residual=f[0,0]-2*b@c+c@g@c
                if abs(residual-fit['projection_residual'])>1e-8:raise ValueError('Projection residual mismatch')
                gradient=g@c-b+fit['ridge']*c
                projected=np.max(abs(gradient-gradient.mean()));max_gradient=max(max_gradient,float(projected))
                if projected>1e-7:raise ValueError('Constrained optimizer stationarity failed')
                accepted+=1
    max_sample_error=0.;max_cov_error=0.
    for name,result in summary['methods'].items():
        if name.startswith('classical_'):continue
        if name=='raw_equal_total_shots':
            expected=raw_means[0];sample=raw_samples[0];cov=raw_cov[0]/(3*shots)
        elif name=='readout_equal_total_shots':
            expected=forward_means[0];sample=full_samples[0];cov=forward_cov[0]/(3*shots)
        else:
            if name=='zne_linear':w=np.tile(linear_zne_weights([1,2,3]),(12,1))
            elif name=='zne_richardson':w=np.tile(richardson_weights([1,2,3]),(12,1))
            else:w=np.asarray(result['weights'])
            expected=np.einsum('ia,ai->i',w,forward_means)
            sample=np.einsum('ia,ai->i',w,samples)
            cov=sum(np.outer(w[:,j],w[:,j])*forward_cov[j]/shots for j in range(3))
        np.testing.assert_allclose(expected,result['pauli_expected'],atol=1e-8)
        error=float(np.max(abs(sample-result['pauli_sampled'])));max_sample_error=max(max_sample_error,error)
        if error>1e-10:raise ValueError('Saved sample estimate mismatch')
        np.testing.assert_allclose(a@sample+offset,result['physical_sampled'],atol=1e-10)
        errors=np.sqrt(np.maximum(np.diag(a@cov@a.T),0))
        max_cov_error=max(max_cov_error,float(np.max(abs(errors-result['physical_shot_standard_errors']))))
        np.testing.assert_allclose(errors,result['physical_shot_standard_errors'],atol=1e-8)
    if abs(np.asarray(summary['ideal_physical'])[:4].sum()-3)>1e-10:raise ValueError('Ideal particle number not conserved')
    report={'status':'SAVED_PILOT_VERIFIED','tests_passed':tests.testsRun,'operators':12,
        'accepted_tn_fits_checked':accepted,'rejected_tn_fits':len(summary['rejected_fits']),
        'max_optimizer_projected_gradient':max_gradient,'max_loop_vs_exact_contraction_frobenius':max_loop_error,
        'bp_propagation_nonconverged_updates':nonconverged,'max_sample_reconstruction_error':max_sample_error,
        'max_shot_standard_error_reconstruction_error':max_cov_error,
        'hardware_mitigation_validated':False,'new_qpu_seconds':0,
        'verification_source_sha256':{str(p.relative_to(ROOT)):digest(p) for p in
            [Path(__file__).resolve(),ROOT/'test_lmpf_2d.py',ROOT/'test_lmpf_hardware_inputs.py']},
        'post_run_validator_is_separate_from_pilot_source_snapshot':True,
        'scope':'Saved data, solver, sampling and matched-surrogate consistency; not a hardware or TN convergence certificate.'}
    (dest/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('folder',type=Path);args=p.parse_args()
    with threadpool_limits(limits=1):verify(args.folder)
