"""Shared-shot bootstrap inference for equal512-bitshot raw and CZ-ZNE arms."""
import argparse
import io
import json
from pathlib import Path
import unittest
import numpy as np
from scipy.stats import chi2
import aer_cuprate_cz_zne_bitshots as b
import analyze_aer_noise_components as a
from analyze_aer_cuprate_cz_zne import physical_range
from cuprate_2d_tflo import physical_observables

METHODS=['raw512','linear_zne512_PRIMARY','quadratic_zne512_SECONDARY']
SIZES=(37,27,9,18)
WEIGHTS=np.array([[37/64,27/64,0,0],[4/3,0,1/3,-2/3],[3,0,-3,1.]])

def method_means(source,raw_counts=(37,27)):
    if np.shape(source)[-2:]!=(4,27) or min(raw_counts)<=0:
        raise ValueError('Expected four strata x27 moments and positive counts')
    weights=WEIGHTS.copy()
    weights[0,:2]=np.asarray(raw_counts)/sum(raw_counts)
    return np.einsum('ms,...sp->...mp',weights,source)

def split_strata(groups):
    if [np.shape(x) for x in groups]!=[(8,64,27),(8,9,27),(8,18,27)]:
        raise ValueError('Wrong factor sample shapes')
    return [groups[0][:,:37],groups[0][:,37:],groups[1],groups[2]]

def bootstrap(strata,repetitions=2000,seed=2027400000):
    if [np.shape(x) for x in strata]!=[(8,n,27) for n in SIZES]:
        raise ValueError('Wrong shared-shot strata')
    rng=np.random.default_rng(seed)
    draws=np.empty((repetitions,4,27))
    for k in range(repetitions):
        for s,(data,n) in enumerate(zip(strata,SIZES)):
            indices=rng.integers(0,n,(8,n))
            draws[k,s]=data[np.arange(8)[:,None],indices].mean(axis=(0,1))
    return draws

def benefits(metrics):
    v=np.asarray(metrics)
    if v.shape[-2:]!=(3,4):
        raise ValueError('Expected three methods x four metrics')
    return np.concatenate([v[...,0,:3]-v[...,1,:3],
                           (v[...,1,3]-v[...,0,3])[...,None]],axis=-1)

def load_samples(out):
    plan=b.z.c.a.read(out/'plan.json')
    groups=[]
    maximum=0.
    for g,n in enumerate(b.COUNTS):
        blocks=[]
        for t in range(8):
            folder=out/'blocks'/f'{g}_{t}'
            record=b.z.c.a.read(folder/'record.json')
            raw=b.z.c.a.read(folder/'aer_result.json')
            assert record['group']==g and record['twirl']==t
            assert record['seed']==b.seed_for(g,t) and record['shots']==n
            assert raw['success'] and raw['results'][0]['seed_simulator']==record['seed']
            memory=b.binary_memory(raw,18)
            assert memory==record['bitstrings']
            b.check_saved_counts(raw,memory,18)
            mask=plan['records'][t]['readout_mask_little_endian']
            bits=b.decode_bitstrings(memory,18,mask)
            np.testing.assert_array_equal(bits,record['decoded_bits'])
            paulis=b.pauli_samples(bits)
            np.testing.assert_array_equal(paulis,record['pauli_samples'])
            # Independent direct occupations, not the Pauli transformation.
            up,down=bits[:,::2].astype(float),bits[:,1::2].astype(float)
            direct=np.stack([up+down,up-down,up*down],axis=-1)
            maximum=max(maximum,float(np.max(np.abs(direct-physical_observables(paulis)))))
            blocks.append(paulis)
        groups.append(np.asarray(blocks))
    assert maximum<1e-12
    return groups,maximum

def analyze(out):
    dest=out/'analysis'
    if dest.exists():
        raise ValueError('Refuse overwrite')
    count=a.verify_files(out,'run_archive_sha256.json')
    plan=b.z.c.a.read(out/'plan.json')
    b.z.verify_inputs(plan)
    groups,error=load_samples(out)
    strata=split_strata(groups)
    means=np.stack([x.mean(axis=(0,1)) for x in strata])
    methods=method_means(means)
    np.testing.assert_allclose(methods[0],groups[0].mean(axis=(0,1)),atol=1e-14,rtol=0)
    exact=np.asarray(plan['setting']['reference'])
    source_draws=bootstrap(strata)
    draws=method_means(source_draws)
    metrics=a.metrics(methods,exact)
    metric_draws=a.metrics(draws,exact)
    gain=benefits(metrics)
    gain_draws=benefits(metric_draws)
    # Independent OLS intercept only using ZNE's own prefix A, C, D.
    design=np.column_stack([np.ones(3),[1.,2.,3.]])
    intercept=np.linalg.lstsq(design,means[[0,2,3]],rcond=None)[0][0]
    np.testing.assert_allclose(intercept,methods[1],atol=1e-12,rtol=0)
    gvars=np.array([a.metrics(x,exact)[...,3].var(axis=1,ddof=1).sum()/(8**2*x.shape[1])
                   for x in strata])
    gcov=WEIGHTS@np.diag(gvars)@WEIGHTS.T
    curvature_weights=np.array([1.,0.,-2.,1.])
    gc=float(curvature_weights@a.metrics(means,exact)[:,3])
    gcvar=float(np.sum(curvature_weights**2*gvars))
    curvature=(means[0]-2*means[2]+means[3])
    curvature_draws=source_draws[:,0]-2*source_draws[:,2]+source_draws[:,3]
    radius=float(np.quantile(np.max(np.abs(curvature_draws-curvature),axis=-1),.95))
    half=[x[:,:n] for x,n in zip(strata,(18,14,5,9))]
    half_methods=method_means(np.stack([x.mean(axis=(0,1)) for x in half]),raw_counts=(18,14))
    result={'schema':'equal512-bitshot-analysis-v1','methods':METHODS,'metric_order':a.METRICS,
        'stratum_sizes':SIZES,'stratum_means':means.tolist(),'method_means':methods.tolist(),
        'physical_means':physical_observables(methods).tolist(),
        'metrics':metrics.tolist(),'metric_ci95':a.ci(metric_draws),
        'primary_benefits':gain.tolist(),'primary_benefit_ci95':a.ci(gain_draws),
        'benefit_order':['charge_rmse_reduction','spin_rmse_reduction','doublon_rmse_reduction','spin_contrast_increase'],
        'relative_spin_rmse_reduction':float(gain[1]/metrics[0,1]),
        'relative_spin_rmse_reduction_ci95':a.ci(gain_draws[:,1]/metric_draws[:,0,1]),
        'predicted_g_covariance':gcov.tolist(),
        'bootstrap_g_covariance':np.cov(metric_draws[:,:,3].T).tolist(),
        'g_standard_error_ratio_zne_over_raw':float(np.sqrt(gcov[1,1]/gcov[0,0])),
        'physical_ranges':{name:physical_range(methods[m]) for m,name in enumerate(METHODS)},
        'curvature':{'g_contrast':gc,'g_chi2_1dof':gc**2/gcvar,
            'g_pvalue_asymptotic':float(chi2.sf(gc**2/gcvar,1)),
            'pauli_joint95_radius':radius,
            'paulis_excluding_zero':np.flatnonzero(np.abs(curvature)>radius).tolist()},
        'nested_diagnostic':{'256_each_metrics':a.metrics(half_methods,exact).tolist(),
            '512_each_metrics':metrics.tolist(),'half_stratum_sizes':[18,14,5,9],
            'not_a_convergence_certificate':True},
        'bootstrap_resolution':{str(n):a.ci(gain_draws[:n]) for n in (500,1000,2000)},
        'run_summary':b.z.c.a.read(out/'run_summary.json'),
        'independent_physical_error':error,'independent_ols_match':True,
        'equal_shots':True,'equal_time_or_gate_cost':False,
        'shared_samples_accounted_in_bootstrap':True,'readout_sampled_once':True,
        'measurement_noise_included':True,'extrapolation_bias_in_ci':False,'new_qpu_seconds':0}
    log=io.StringIO()
    suite=unittest.defaultTestLoader.loadTestsFromNames(['test_aer_cuprate_cz_zne_bitshots','test_aer_cuprate_cz_zne'])
    tests=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    if not tests.wasSuccessful():
        raise AssertionError(log.getvalue())
    dest.mkdir()
    b.z.c.a.write(dest/'results.json',result)
    np.savez_compressed(dest/'bootstrap_draws.npz',stratum_means=source_draws,method_means=draws)
    (dest/'unit_tests.txt').write_text(log.getvalue(),encoding='utf-8')
    b.z.c.a.write(dest/'verification.json',{'status':'PASS','tests':tests.testsRun,'run_files_verified':count,
        'source_input_hashes_verified':len(plan['input_sha256']),'independent_physical_error':error,
        'independent_ols_match':True,'shared_prefix_size':296,'both_arm_shot_counts':512})
    lines=['# Aer:512 bitshots zonder ZNE versus512 totaal met ZNE','',
        'Zelfde3x3-circuit, U/t=8, T=0.4; alle acht twirls en volledige gekalibreerde ruis.','',
        '| Methode | Lading-RMSE | Spin-RMSE | Doublon-RMSE | Spincontrast g |',
        '|---|---:|---:|---:|---:|']
    for m,name in enumerate(METHODS):
        lines.append('| '+name+' | '+' | '.join(f'{v:.5f}' for v in metrics[m])+' |')
    low,high=result['primary_benefit_ci95']['low'][1],result['primary_benefit_ci95']['high'][1]
    lines += ['',f'Primaire spin-RMSE-afname {gain[1]:.5f};95%-interval [{low:.5f},{high:.5f}].',
        f'Relatieve verbetering {100*result["relative_spin_rmse_reduction"]:.1f}%.',
        ('Positieve verbetering opgelost binnen de steekproefonzekerheid van dit model.'
         if low>0 else 'Geen statistisch opgeloste positieve verbetering met deze512-shotpilot.'),'',
        'Raw512 gebruikt8x64; ZNE512 gebruikt8x[37,9,18]=[296,72,144].',
        'De eerste296 factor1-shots zijn gedeeld;728 unieke nieuwe bitshots uitgevoerd.',
        'Bootstrap resamplet gedeelde prefix en raw-only suffix afzonderlijk en behoudt',
        'de correlatie tussen beide armen. Factor1 van ZNE gebruikt niet alle512 raw-shots.',
        'Bitstrings bevatten werkelijke Aer-meet- en uitleesruissampling, niet alleen',
        'conditionele verwachtingswaarden. Alleen de bekende X-maskers zijn teruggedraaid.',
        'Geen postselectie, clipping of analytische readoutmitigatie.',
        'Lineaire gewichten[4/3,1/3,-2/3] en shotverdeling stonden vooraf vast.',
        'Kwadratisch is alleen een gevoeligheidscheck, geen achteraf gekozen hoofdresultaat.',
        f'Spincontrast-standaardfout ZNE/raw: {result["g_standard_error_ratio_zne_over_raw"]:.2f}.',
        'Intervallen bevatten steekproefruis, maar niet extrapolatiebias of ontbrekende modelruis.',
        'De geneste256/512-check bewijst geen volledige convergentie of herhaalbaarheid.','',
        'Gelijk shotbudget is niet gelijk gate-/tijdbudget:ZNE gebruikt1.703125x zoveelCZ.',
        'CPU-tijden zijn geen QPU-facturatie. Deel37/64 van een gemeten raw-bloktijd',
        'wordt niet als een gemeten ZNE-armruntime gepresenteerd.',
        'Het oude5-seconden-QPU-budget is onaangeraakt; nieuwe QPU-seconden:0.',
        f'Nieuwe run+result-tijden: {json.dumps(result["run_summary"]["group_run_seconds"])}.',
        f'{tests.testsRun} tests geslaagd; onafhankelijke observabelefout {error:.3g}.',
        'Geen Nighthawk-hardwareverbetering of quantum advantage aangetoond.','']
    (dest/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    b.z.c.a.write(dest/'sha256.json',{p.name:b.z.c.a.digest(p) for p in dest.iterdir() if p.is_file()})
    print(json.dumps({'metrics':metrics.tolist(),'benefits':gain.tolist(),
        'benefit_ci95':result['primary_benefit_ci95'],'relative_spin_reduction':result['relative_spin_rmse_reduction'],
        'relative_ci95':result['relative_spin_rmse_reduction_ci95'],'g_se_ratio':result['g_standard_error_ratio_zne_over_raw'],
        'tests':tests.testsRun,'new_qpu_seconds':0}),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    analyze(args.output.resolve())
