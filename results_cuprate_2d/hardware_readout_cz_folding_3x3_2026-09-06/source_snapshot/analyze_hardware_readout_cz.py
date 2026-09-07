"""Frozen paired analysis of one readout+CZ-folding hardware job; no submission."""
import json
import numpy as np
import run_hardware_readout_cz_once as h
from cuprate_2d_tflo import decode_bitstrings,pauli_samples,physical_observables

METHODS=['raw512','readout384_cal128','readout_CZ_ZNE_PRIMARY','CZ_ZNE_no_readout_DIAGNOSTIC']
SIZES=(27,21,16,7,14)

def predictions(means,masks,errors):
    means=np.asarray(means)
    if means.shape!=(5,8,27): raise ValueError('Expected5 strata x8 twirls x27 moments')
    corrected=h.r.correct_moments(means,masks,errors)
    raw=np.einsum('s,stp->p',np.array([27,21,16])/64,means[:3])/8
    readout=(27*corrected[0]+21*corrected[1]).mean(axis=0)/48
    weights=np.array([4/3,1/3,-2/3])
    zne=weights@corrected[[0,3,4]].mean(axis=1)
    uncorrected=weights@means[[0,3,4]].mean(axis=1)
    return np.array([raw,readout,zne,uncorrected])

def main():
    out=h.RUN; dest=out/'analysis'
    if dest.exists(): raise FileExistsError('Refuse overwrite')
    verified=h.r.stats.verify_files(out,'hardware_archive_sha256.json')
    plan,_=h.frozen(); raw=h.safe.read(out/'raw_bitstrings.json')
    receipt=h.safe.read(out/'job_receipt.json')
    if raw['job_id']!=receipt['job_id']: raise ValueError('Wrong raw job')
    keyed={(rec['setting_id'],rec['twirl_id']):rec for rec in raw['records']}
    groups=[]; calibration=[]; direct_error=0.
    for state in range(2):
        row=keyed[f'readout_all{state}',0]
        calibration.append(decode_bitstrings(row['bitstrings'],18,[0]*18))
    for f,n in enumerate([64,7,14],1):
        data=[]
        for t in range(8):
            row=keyed[f'U8_T04_factor{f}',t]
            if len(row['bitstrings'])!=n: raise ValueError('Wrong samples')
            bits=decode_bitstrings(row['bitstrings'],18,row['readout_mask_little_endian'])
            ps=pauli_samples(bits); up=bits[:,::2].astype(float); down=bits[:,1::2].astype(float)
            direct=np.stack([up+down,up-down,up*down],axis=-1)
            direct_error=max(direct_error,float(np.max(np.abs(direct-physical_observables(ps)))))
            data.append(ps)
        groups.append(np.array(data))
    assert direct_error<1e-14
    masks=np.array([keyed['U8_T04_factor1',t]['readout_mask_little_endian'] for t in range(8)])
    for f in [2,3]:
        assert all(keyed[f'U8_T04_factor{f}',t]['readout_mask_little_endian']==masks[t].tolist() for t in range(8))
    strata=[groups[0][:,:27],groups[0][:,27:48],groups[0][:,48:],groups[1],groups[2]]
    counts=h.r.calibration_counts(np.array(calibration)); errors=h.r.calibration_mean(counts)
    means=np.stack([x.mean(axis=1) for x in strata]); methods=predictions(means,masks,errors)
    np.testing.assert_allclose(methods[0],groups[0].mean(axis=(0,1)),atol=1e-14)
    exact=np.array(plan['target']['reference'])
    rng=np.random.default_rng(2028600000); draws=[]; fixed=[]
    for k in range(2000):
        sm=[]
        for x,n in zip(strata,SIZES):
            indices=rng.integers(0,n,(8,n))
            sm.append(x[np.arange(8)[:,None],indices].mean(axis=1))
        e=rng.beta(counts+.5,64-counts+.5)
        draws.append(predictions(sm,masks,e)); fixed.append(predictions(sm,masks,errors))
    draws=np.array(draws); fixed=np.array(fixed)
    metrics=h.r.stats.metrics(methods,exact); dm=h.r.stats.metrics(draws,exact); fm=h.r.stats.metrics(fixed,exact)
    gain=dm[:,0,:3]-dm[:,2,:3]
    central_gain=metrics[0,:3]-metrics[2,:3]
    p=physical_observables(methods)
    result={'schema':'hardware-readout-cz-analysis-v1','job_id':receipt['job_id'],'methods':METHODS,
        'metrics_order':h.r.stats.METRICS,'metrics':metrics.tolist(),'metric_hybrid_interval95':h.r.stats.ci(dm),
        'method_moments':methods.tolist(),'physical_means':p.tolist(),'factor_moments':[x.mean(axis=(0,1)).tolist() for x in groups],
        'zne_selected_factor_moments':means[[0,3,4]].mean(axis=1).tolist(),
        'primary_rmse_reductions':central_gain.tolist(),'primary_reduction_hybrid95':h.r.stats.ci(gain),
        'primary_reduction_fixed_calibration95':h.r.stats.ci(fm[:,0,:3]-fm[:,2,:3]),
        'readout_increment_in_zne95':h.r.stats.ci(dm[:,3,:3]-dm[:,2,:3]),
        'pauli_mse':np.mean((methods-exact)**2,axis=1).tolist(),
        'number_expectation':p[:,:,0].sum(axis=1).tolist(),
        'number_absolute_deviation_from8':np.abs(p[:,:,0].sum(axis=1)-8).tolist(),
        'physical_ranges':{name:h.r.physical_range(methods[i]) for i,name in enumerate(METHODS)},
        'calibration':{'counts':counts.tolist(),'shots_per_state':64,'posterior_mean':errors.tolist(),
            'min_denominator':float(np.min(1-errors.sum(axis=0))),'prior':'Jeffreys Beta(0.5,0.5)'},
        'bootstrap_repetitions':2000,'bootstrap_resolution':{str(n):h.r.stats.ci(gain[:n]) for n in [200,1000,2000]},
        'direct_bit_physical_error':direct_error,'verified_hardware_files':verified,
        'provider_metrics':h.safe.read(out/'provider_metrics.json'),'actual_new_hardware_shots':808,
        'main_arm_shots_including_calibration':512,'equal_time_or_gate_budget':False,
        'cz_costs':{'raw':516096,'readout':387072,'readout_zne':669312,'sampled_union':967680},
        'caveats':['Hybrid intervals are not coverage-certified frequentist CIs.',
            'No drift/SPAM-model/correlated-readout/extrapolation bias in intervals.',
            'No postselection/clipping or post-hoc extrapolator selection.',
            'CZ folding amplifies only CZ exposure, not every noise source.',
            'Single small hardware pilot, not quantum advantage.']}
    dest.mkdir(); h.safe.exclusive_json(dest/'results.json',result)
    np.savez_compressed(dest/'bootstrap.npz',hybrid=draws,fixed_calibration=fixed)
    lines=['# Hardware: readout + CZ-folding ZNE','',f'Job `{receipt["job_id"]}`, backend `{h.BACKEND}`.',
        'Alle 808 nieuwe shots ontvangen. Analytische hoofdarmen elk 512 shots inclusief kalibratie.','',
        '| Methode | Lading-RMSE | Spin-RMSE | Doublon-RMSE |','|---|---:|---:|---:|']
    for name,row in zip(METHODS,metrics): lines.append('| '+name+' | '+' | '.join(f'{v:.5f}' for v in row[:3])+' |')
    ci=result['primary_reduction_hybrid95']
    lines+=['',f'Primaire spin-RMSE-afname: {central_gain[1]:.5f}; hybride95%-interval [{ci["low"][1]:.5f}, {ci["high"][1]:.5f}].',
        'Dit combineert gepaarde shot-bootstrap en kalibratieposterior; geen volledige systematische foutmarge.',
        'Lading, doublonen, deeltjesgetal en fysieke grenzen staan onverkort in results.json.',
        'Geen postselectie, clipping, PEA, PEC of TFLO toegepast.',
        'Gelijke shots zijn niet gelijke poort-/tijdkosten; geen quantum advantage aangetoond.',
        'Providergebruik: '+json.dumps(result['provider_metrics'].get('usage')),'']
    (dest/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    h.safe.exclusive_json(out/'analysis_archive_sha256.json',{str(p.relative_to(out)):h.safe.digest(p)
        for p in out.rglob('*') if p.is_file() and p.name!='status_history.jsonl'})
    print(json.dumps({'metrics':metrics.tolist(),'primary_gain95':ci,'usage':result['provider_metrics'].get('usage')}),flush=True)

if __name__=='__main__': main()
