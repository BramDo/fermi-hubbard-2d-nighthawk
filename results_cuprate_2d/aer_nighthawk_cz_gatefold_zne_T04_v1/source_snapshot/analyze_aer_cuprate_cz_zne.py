"""Fixed-weight inference for selective-CZ ZNE, not an all-noise-zero claim."""
from pathlib import Path
import argparse
import io
import json
import unittest
import numpy as np
from scipy.stats import chi2
import aer_cuprate_cz_zne as z
import analyze_aer_noise_components as a
from cuprate_2d_tflo import physical_observables
from verify_aer_noise_components import physical_by_enumeration

METHODS=['raw128','zne_linear_PRIMARY','zne_quadratic_SECONDARY','cz_noise_off_DIAGNOSTIC']
WEIGHTS=np.array([[1.,0.,0.,0.],[4/3,1/3,-2/3,0.],[3.,-3.,1.,0.],[0.,0.,0.,1.]])

def method_means(source):
    source=np.asarray(source)
    if source.shape[-3:] != (4,2,27):
        raise ValueError('Expected four groups x two readout variants x 27 moments')
    return np.einsum('mg,...gvp->...mvp',WEIGHTS,source)

def bootstrap(data,repetitions=2000,seed=2026700000):
    if np.shape(data)!=(4,8,16,2,27):
        raise ValueError('Expected four x eight x sixteen x two x 27')
    rng=np.random.default_rng(seed)
    draws=np.empty((repetitions,4,2,27))
    for b in range(repetitions):
        for g in range(4):
            indices=rng.integers(0,16,(8,16))
            draws[b,g]=data[g,np.arange(8)[:,None],indices].mean(axis=(0,1))
    return draws

def benefits(metrics):
    values=np.asarray(metrics)
    if values.shape[-3:]!=(4,2,4):
        raise ValueError('Expected method x variant x metric')
    return np.concatenate([values[...,0,1,:3]-values[...,1,1,:3],
        (values[...,1,1,3]-values[...,0,1,3])[...,None]],axis=-1)

def physical_range(paulis):
    p=np.asarray(paulis)
    up,down=p[...,0:18:2],p[...,1:18:2]
    zz=p[...,18:]
    probabilities=np.stack([(1+up+down+zz)/4,(1-up+down-zz)/4,
                            (1+up-down-zz)/4,(1-up-down+zz)/4],axis=-1)
    return {'minimum_two_mode_probability':float(probabilities.min()),
        'negative_two_mode_probabilities':int(np.sum(probabilities < -1e-10)),
        'max_abs_pauli':float(np.max(np.abs(p))),
        'paulis_outside_range':int(np.sum(np.abs(p)>1+1e-10)),
        'clipping_applied':False}

def run(out):
    destination=out/'analysis'
    if destination.exists():
        raise ValueError('Refuse analysis overwrite')
    run_hash_count=a.verify_files(out,'run_archive_sha256.json')
    parent_hash_count=a.verify_files(z.PARENT,'final_archive_sha256.json')
    plan=z.c.a.read(out/'plan.json')
    z.verify_inputs(plan)
    matrices=np.asarray(z.c.a.read(out/'readout_matrices.json'))
    identity=np.tile(np.eye(2),(18,1,1))
    data=np.empty((4,8,16,2,27))
    independent=np.empty((4,8,16,2,9,3))
    for g in range(4):
        for t in range(8):
            folder=z.PARENT/'blocks'/f'0_{t}' if g==0 else out/'blocks'/f'{g}_{t}'
            record=z.c.a.read(folder/'record.json')
            raw=z.c.a.read(folder/'aer_result.json')
            assert record['seed']==z.seed_for(g,t)
            if g>0:
                assert record['group_index']==g and record['twirl']==t
            else:
                assert record['model']=='full_calibrated' and record['twirl_id']==t
            labels=[f'z_{q}' for q in range(18)]+[f'zz_{s}' for s in range(9)]
            native=np.asarray([raw['results'][0]['data'][key] for key in labels]).T
            assert raw['success'] and native.shape==(16,27)
            np.testing.assert_allclose(native,record['native_paulis'],atol=0,rtol=0)
            mask=plan['records'][t]['readout_mask_little_endian']
            decoded=z.c.unmask_paulis(native,mask)
            readout=z.c.apply_readout(decoded,mask,matrices)
            np.testing.assert_allclose(decoded,record['decoded_paulis'],atol=1e-14,rtol=0)
            np.testing.assert_allclose(readout,record['with_readout_paulis'],atol=1e-14,rtol=0)
            data[g,t]=np.stack([decoded,readout],axis=1)
            for variant,channel in enumerate([identity,matrices]):
                independent[g,t,:,variant]=physical_by_enumeration(native,mask,channel)
    error=float(np.max(np.abs(physical_observables(data)-independent)))
    assert error<1e-12
    exact=np.asarray(plan['setting']['reference'])
    means=data.mean(axis=(1,2))
    source_draws=bootstrap(data)
    methods=method_means(means)
    method_draws=method_means(source_draws)
    metrics=a.metrics(methods,exact)
    metric_draws=a.metrics(method_draws,exact)
    gain=benefits(metrics)
    gain_draws=benefits(metric_draws)
    # Independent linear least-squares computation must reproduce fixed weights.
    design=np.column_stack([np.ones(3),np.array([1.,2.,3.])])
    fitted=np.linalg.lstsq(design,means[:3].reshape(3,-1),rcond=None)[0][0].reshape(2,27)
    np.testing.assert_allclose(fitted,methods[1],atol=1e-12,rtol=0)
    # Reproduce primary gain from spin samples, without the metrics helper.
    spin=(method_draws[...,1:18:2]-method_draws[...,0:18:2])/2
    target_spin=(exact[1:18:2]-exact[0:18:2])/2
    rmse=np.sqrt(np.mean((spin-target_spin)**2,axis=-1))
    np.testing.assert_allclose(rmse[:,0,1]-rmse[:,1,1],gain_draws[:,1],atol=1e-13,rtol=0)
    curvature=means[0,1]-2*means[1,1]+means[2,1]
    curvature_draws=source_draws[:,0,1]-2*source_draws[:,1,1]+source_draws[:,2,1]
    curvature_radius=float(np.quantile(np.max(np.abs(curvature_draws-curvature),axis=-1),.95))
    # g is linear, so its pointwise curvature test is a one-degree-of-freedom diagnostic.
    group_metrics=a.metrics(means,exact)
    trajectory_g=a.metrics(data,exact)[...,3]
    g_variances=trajectory_g.var(axis=2,ddof=1).sum(axis=1)/(16*8**2)
    gc=float(group_metrics[0,1,3]-2*group_metrics[1,1,3]+group_metrics[2,1,3])
    gc_var=float(g_variances[0,1]+4*g_variances[1,1]+g_variances[2,1])
    diagnostic_chi2=gc**2/gc_var
    g_curvature_draws=(a.metrics(source_draws,exact)[:,0,1,3]
        -2*a.metrics(source_draws,exact)[:,1,1,3]+a.metrics(source_draws,exact)[:,2,1,3])
    zne_g_variance=float(np.sum(WEIGHTS[1]**2*g_variances[:,1]))
    floor_difference=methods[1,1]-methods[3,1]
    floor_draws=method_draws[:,1,1]-method_draws[:,3,1]
    floor_radius=float(np.quantile(np.max(np.abs(floor_draws-floor_difference),axis=-1),.95))
    ranges={name:physical_range(methods[m,1]) for m,name in enumerate(METHODS)}
    result={'schema':'cz-gatefolding-zne-analysis-v1','methods':METHODS,
        'groups':z.GROUPS,'variants':['pre_readout_secondary','with_readout_PRIMARY'],
        'metric_order':a.METRICS,'source_means':means.tolist(),
        'source_metrics':group_metrics.tolist(),'method_means':methods.tolist(),
        'physical_means':physical_observables(methods).tolist(),'metrics':metrics.tolist(),
        'metric_ci95':a.ci(metric_draws),'primary_benefits':gain.tolist(),
        'benefit_order':['charge_rmse_reduction','spin_rmse_reduction','doublon_rmse_reduction','spin_projection_increase'],
        'primary_benefit_ci95':a.ci(gain_draws),
        'relative_spin_rmse_reduction':float(gain[1]/metrics[0,1,1]),
        'relative_spin_rmse_reduction_ci95':a.ci(gain_draws[:,1]/metric_draws[:,0,1,1]),
        'ranges_primary':ranges,'weights':WEIGHTS.tolist(),
        'bootstrap_covariance_raw_zne_g':np.cov(a.metrics(method_draws,exact)[:,[0,1],1,3].T).tolist(),
        'predicted_g_se_raw':float(np.sqrt(g_variances[0,1])),
        'predicted_g_se_zne':float(np.sqrt(zne_g_variance)),
        'g_se_amplification_vs_raw':float(np.sqrt(zne_g_variance/g_variances[0,1])),
        'curvature':{'pauli_contrast':curvature.tolist(),'joint_95_radius':curvature_radius,
            'coordinates_excluding_zero':np.flatnonzero(np.abs(curvature)>curvature_radius).tolist(),
            'g_contrast':gc,'g_ci95':a.ci(g_curvature_draws),
            'g_chi2_one_dof':diagnostic_chi2,'g_p_value_asymptotic':float(chi2.sf(diagnostic_chi2,1)),
            'not_proof_of_linear_model':True},
        'linear_minus_quadratic_primary_paulis':(methods[1,1]-methods[2,1]).tolist(),
        'selective_floor_check':{'linear_minus_czoff':floor_difference.tolist(),
            'joint_95_radius':floor_radius,
            'coordinates_excluding_zero':np.flatnonzero(np.abs(floor_difference)>floor_radius).tolist(),
            'czoff_estimate_is_sampled_not_exact':True},
        'nested_64_128_metrics':{str(n*8):a.metrics(method_means(data[:,:,:n].mean(axis=(1,2))),exact).tolist()
                                for n in (8,16)},
        'benefit_ci_bootstrap_resolution':{str(n):a.ci(gain_draws[:n]) for n in (500,1000,2000)},
        'independent_physical_max_error':error,'independent_lstsq_match':True,
        'conditional_trajectory_uncertainty_only':True,
        'extrapolation_model_bias_in_ci':False,'equal_budget_advantage_test':False,
        'new_qpu_seconds':0,'run_summary':z.c.a.read(out/'run_summary.json')}
    log=io.StringIO()
    tests=unittest.TextTestRunner(stream=log,verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromName('test_aer_cuprate_cz_zne'))
    if not tests.wasSuccessful():
        raise AssertionError(log.getvalue())
    destination.mkdir()
    z.c.a.write(destination/'results.json',result)
    np.savez_compressed(destination/'bootstrap_draws.npz',source_means=source_draws,method_means=method_draws)
    (destination/'unit_tests.txt').write_text(log.getvalue(),encoding='utf-8')
    z.c.a.write(destination/'verification.json',{'status':'PASS','tests':tests.testsRun,
        'input_source_hashes':len(plan['input_sha256']),'parent_files_verified':parent_hash_count,
        'run_files_verified':run_hash_count,'independent_physical_max_error':error,
        'independent_linear_lstsq_match':True,'primary_spin_gain_independently_reproduced':True,
        'no_clipping':True})
    lines=['# CZ-gatefolding ZNE in Aer','',
        'Gecorrigeerde seedopzet; 128 trajecten per factor, acht vaste twirls, U/t=8, T=0.4.',
        'Primaire resultaten inclusief ongewijzigde analytische uitleesruis.','',
        '| Methode | Lading-RMSE | Spin-RMSE | Doublon-RMSE | Spincontrast g |',
        '|---|---:|---:|---:|---:|']
    for m,name in enumerate(METHODS):
        lines.append('| '+name+' | '+' | '.join(f'{x:.5f}' for x in metrics[m,1])+' |')
    lo,hi=result['primary_benefit_ci95']['low'][1],result['primary_benefit_ci95']['high'][1]
    lines += ['',f'Primaire lineaire ZNE: spin-RMSE-afname {gain[1]:.5f}, 95%-interval [{lo:.5f}, {hi:.5f}].',
        f'Relatieve afname {100*result["relative_spin_rmse_reduction"]:.1f}%.',
        ('Positieve spinverbetering opgelost binnen dit model en deze steekproef.'
         if lo>0 else 'Geen statistisch opgeloste positieve spinverbetering met deze steekproef.'),
        '', '## Opzet en grenzen','',
        'CZ-factoren 1,2,3 betekenen werkelijk 1008,2016,3024 uitgevoerde CZ-gates.',
        'Extra CZ-paren behouden de ideale berekening. Op elke toegevoegde CZ werkt',
        'hetzelfde volledige ruisproces: restdepolarisatie EN gate-time-relaxatie.',
        'Lineaire interceptgewichten [4/3,1/3,-2/3] waren vooraf vastgelegd.',
        'Kwadratisch [3,-3,1] is alleen een gevoeligheidscheck, niet achteraf gekozen.',
        'De CZ-off-controle behoudt alle ideale CZ-gates en alle overige fouten.',
        'Deze steekproefcontrole is geen fysiek beschikbare mitigation en geen exacte referentie.',
        'Readout- en eenqubitfouten worden niet naar nul geextrapoleerd.',
        'Geen clipping van onfysische extrapolaties; zie ranges_primary in results.json.',
        'Foutmarges behouden de correlatie tussen ZNE en de hergebruikte raw-controle.',
        'Het zijn alleen Monte-Carlo-intervallen voor conditionele verwachtingstrajecten,',
        'niet voor fysieke bitshots; finale meetruisvariatie en modelbias ontbreken.',
        f'Geschatte spincontrast-standaardfout groeit met factor {result["g_se_amplification_vs_raw"]:.2f} versus raw128.',
        f'Krommingsdiagnostiek spincontrast: {gc:.5f}; p={result["curvature"]["g_p_value_asymptotic"]:.3g} (asymptotisch).',
        f'ZNE-versus-CZ-off: {len(result["selective_floor_check"]["coordinates_excluding_zero"])} van 27 momenten buiten gezamenlijke Monte-Carlo-band.',
        'Afwezigheid van gedetecteerde kromming/verschil bewijst geen juiste extrapolatie.',
        '128 versus 64 zijn geneste subsets; geen volledige convergentieverklaring.','',
        '## Budget en verificatie','',
        'De ZNE-estimator gebruikt 384 trajecten (inclusief 128 hergebruikt), tegen raw128:',
        '3x de trajecten en 6x de CZ-applicaties. Dit is geen gelijke-budgetvergelijking.',
        'De afzonderlijke CZ-off-diagnose gebruikt nog 128 nieuwe trajecten.',
        f'Nieuwe simulatieruntijden: {json.dumps(result["run_summary"]["group_run_seconds"])}.',
        'Aer run+result-tijden zijn geen volledige end-to-end tijd of voorspelde QPU-facturatie.',
        'De oude QPU-limiet van 5 seconden blijft onaangeraakt. Nieuwe QPU-seconden: 0.',
        f'{tests.testsRun} tests geslaagd; onafhankelijke observabelefout {error:.3g}.',
        'Alle nieuwe seeds gescheiden; noise-off-folds en modelidentiteit gecontroleerd.',
        'Model mist idle-gap-ruis, coherente/contextuele fouten, crosstalk, leakage,',
        'preparatiefouten en drift. Geen hardwareverbetering of quantum advantage bewezen.','',
        'Protocol: AER_CZ_ZNE_PROTOCOL.md; alle input, broncode en resultaten zijn gehasht.','']
    (destination/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    z.c.a.write(destination/'sha256.json',{str(p.relative_to(destination)):z.c.a.digest(p)
                                          for p in destination.rglob('*') if p.is_file()})
    print(json.dumps({'primary_metrics':metrics[:,1].tolist(),'benefit':gain.tolist(),
        'benefit_ci95':result['primary_benefit_ci95'],'relative_spin_reduction':result['relative_spin_rmse_reduction'],
        'g_se_factor':result['g_se_amplification_vs_raw'],'ranges':ranges,'tests':tests.testsRun}),flush=True)

def finalize(out):
    if (out/'COMPLETION.json').exists():
        raise ValueError('Already finalized')
    counts=[a.verify_files(out,'run_archive_sha256.json'),a.verify_files(out/'analysis','sha256.json')]
    z.verify_inputs(z.c.a.read(out/'plan.json'))
    z.c.a.write(out/'COMPLETION.json',{'status':'COMPLETE_LOCAL_CZ_GATEFOLDING_ZNE_PILOT',
        'hash_counts':counts,'verification':z.c.a.read(out/'analysis/verification.json'),
        'new_qpu_seconds':0,'scope':'Selective-CZ ZNE conditional-trajectory screen, not hardware bitshot mitigation or equal-cost advantage.'})
    z.c.a.write(out/'final_archive_sha256.json',{str(p.relative_to(out)):z.c.a.digest(p)
                                                for p in out.rglob('*') if p.is_file()})
    print(json.dumps(z.c.a.read(out/'COMPLETION.json')))

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('stage',choices=['analyze','finalize'])
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    (run if args.stage=='analyze' else finalize)(args.output.resolve())
