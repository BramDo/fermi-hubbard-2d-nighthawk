"""Frozen affine TFLO/DD analysis. No provider calls or target-reference training."""
import json,time
from pathlib import Path
import numpy as np
import cuprate_2d_tflo_dd6 as m
import run_tflo_dd6_once as run
from cuprate_2d_tflo import decode_bitstrings,pauli_samples,physical_observables
from cuprate_2d_hardware_controls import corrected_paulis


def transform(points,training_exact):
    """points[DD,setting,raw/readout,Pauli], reference ONLY for train rows."""
    points=np.asarray(points,float)
    if points.shape!=(2,9,2,108) or np.shape(training_exact)!=(6,108):
        raise ValueError('Wrong fixed training shape')
    result=np.empty((2,9,3,108)); models=[]; nulls=[]
    for dd in range(2):
        result[dd,:,:2]=points[dd]
        beta=m.fit_affine(points[dd,:6,1],training_exact)
        models.append(beta)
        for s in range(9): result[dd,s,2]=m.apply_affine(beta,points[dd,s,1])
        nulls.append(m.apply_affine(beta,points[dd,:6,1].mean(axis=0)))
    return result,np.array(models),np.array(nulls)


def row(name,physical,boot,reference,reference_exact):
    rms=np.sqrt(np.mean((physical-reference)**2,axis=0))
    brms=np.sqrt(np.mean((boot-reference)**2,axis=1))
    c,s,d=physical.T
    probs=np.stack([1-c+d,(c-s)/2-d,(c+s)/2-d,d],axis=-1)
    return {'arm':name,'physical_charge_spin_doublon':physical.tolist(),
        'pointwise_95pct_intervals':np.quantile(boot,[.025,.975],axis=0).tolist(),
        'N':float(c.sum()),'N_95pct_interval':np.quantile(boot[:,:,0].sum(axis=1),[.025,.975]).tolist(),
        'mean_doublon':float(d.mean()),'spin_profile_rms':float(np.sqrt(np.mean(s*s))),
        'RMS_charge_spin_doublon':rms.tolist(),
        'RMS_95pct_intervals':np.quantile(brms,[.025,.975],axis=0).tolist(),
        'is_exact_reference':reference_exact,'min_onsite_probability':float(probs.min()),
        'physical_bounds_satisfied_at_point':bool(probs.min()>=-1e-12),'clipped':False,
        'bootstrap_quantile_endpoint_shift_first200_to400':float(np.max(np.abs(
            np.quantile(brms[:200],[.025,.975],axis=0)-np.quantile(brms,[.025,.975],axis=0))))}


def main():
    begun=time.perf_counter(); out=run.RUN/'analysis'
    if out.exists(): raise FileExistsError('Do not overwrite analysis')
    run.verify(run.RUN,'hardware_archive_sha256.json')
    plan=run.read(run.RUN/'plan.json'); raw=run.read(run.RUN/'raw_bitstrings.json')
    refs=run.read(run.RUN/'references.json')
    retrieval=run.read(run.RUN/'retrieval_verification.json')
    assert retrieval['status']=='DONE_ARCHIVED_VERIFIED' and raw['job_id']==retrieval['job_id']
    assert len(raw['records'])==len(plan['records'])==m.PUBS
    ids=[s['id'] for s in m.settings()]
    training_exact=np.array([refs[s]['paulis'] for s in ids[:6]])
    calibration={}; targets=[]
    for rec,wanted in zip(raw['records'],plan['records']):
        assert all(rec[k]==v for k,v in wanted.items())
        bits=decode_bitstrings(rec['bitstrings'],72,rec['readout_mask_little_endian'])
        assert len(bits)==m.SHOTS
        if rec['role']=='calibration': calibration[rec['state'],rec['block']]=bits
        else: targets.append((rec,bits))
    fail=np.array([sum(calibration[0,b].sum(0) for b in ('start','end')),
        sum((1-calibration[1,b]).sum(0) for b in ('start','end'))])
    errors=(fail+.5)/1025
    rng=np.random.default_rng(plan['bootstrap_seed'])
    errors_boot=rng.beta(fail+.5,1024-fail+.5,size=(m.BOOTSTRAP,2,72))
    points=np.zeros((2,9,2,108)); boot=np.zeros((m.BOOTSTRAP,2,9,2,108))
    accepted=np.zeros((2,9),int); per_twirl=[]; independent_delta=0.; count_delta=0.
    for rec,bits in targets:
        dd=int(rec['dd']); s=ids.index(rec['setting_id']); mask=np.array(rec['readout_mask_little_endian'])
        samples=pauli_samples(bits); means=samples.mean(0)
        corrected=corrected_paulis(means,mask,errors)
        points[dd,s]+=np.stack([means,corrected])/m.TWIRLS
        weights=rng.multinomial(m.SHOTS,np.full(m.SHOTS,1/m.SHOTS),size=m.BOOTSTRAP)
        bm=weights@samples/m.SHOTS
        boot[:,dd,s]+=np.stack([bm,corrected_paulis(bm,mask,errors_boot)],axis=1)/m.TWIRLS
        keep=(bits[:,::2].sum(1)==16)&(bits[:,1::2].sum(1)==16)
        accepted[dd,s]+=int(keep.sum())
        per_twirl.append({'setting_id':rec['setting_id'],'dd':rec['dd'],'twirl_id':rec['twirl_id'],
            'accepted':int(keep.sum()),'shots':m.SHOTS})
        # Independent integer mask/popcount, and native pair probability inversion.
        mask_integer=sum(int(v)<<q for q,v in enumerate(mask))
        direct=np.mean([(int(st,2)^mask_integer).bit_count() for st in rec['bitstrings']])
        count_delta=max(count_delta,abs(direct-physical_observables(means)[:,0].sum()))
        native=bits^mask
        physical=[]
        for i in range(36):
            a,b=2*i,2*i+1
            probs=np.bincount(2*native[:,a]+native[:,b],minlength=4)/m.SHOTS
            matrices=[]
            for q in (a,b):
                e0,e1=errors[:,q]; matrices.append(np.array([[1-e0,e1],[e0,1-e1]]))
            corrected_probs=np.linalg.solve(np.kron(*matrices),probs)
            corrected_probs=corrected_probs[np.arange(4)^(2*mask[a]+mask[b])]
            physical.append([corrected_probs[1]+corrected_probs[2]+2*corrected_probs[3],
                corrected_probs[2]-corrected_probs[1],corrected_probs[3]])
        independent_delta=max(independent_delta,float(np.max(np.abs(np.array(physical)-physical_observables(corrected)))))
    predicted,models,nulls=transform(points,training_exact)
    pred_boot=np.empty((m.BOOTSTRAP,2,9,3,108)); null_boot=np.empty((m.BOOTSTRAP,2,108))
    for b in range(m.BOOTSTRAP):
        pred_boot[b],_,null_boot[b]=transform(boot[b],training_exact)
    phys=physical_observables(predicted); bphys=physical_observables(pred_boot)
    thresholds=np.array([.05,.05,.03]); holdouts=[]; validated=[]
    for dd in range(2):
        passing=True
        for si in (6,7):
            reference=np.array(refs[ids[si]]['physical'])
            for method,label in enumerate(('raw','readout','readout_tflo')):
                record=row(label,phys[dd,si,method],bphys[:,dd,si,method],reference,True)
                record.update(dd=bool(dd),setting_id=ids[si],T=m.settings()[si]['T'])
                holdouts.append(record)
                if method==2:
                    passing=passing and bool(np.all(np.array(record['RMS_95pct_intervals'])[1]<=thresholds))
        validated.append(passing)
    classical_path=run.ROOT/'results_cuprate_2d/classical_full_6x6_mps_T04_chi64_v1/summary.json'
    classical=run.read(classical_path)
    ref_target=np.array(classical['result']['physical_means'])
    assert ref_target.shape==(36,3) and not classical['certified_6x6_error_bound']
    target=[]
    for dd in range(2):
        for method,label in enumerate(('raw','readout','readout_tflo')):
            record=row(label,phys[dd,8,method],bphys[:,dd,8,method],ref_target,False)
            record.update(dd=bool(dd),TFLO_validation_status=('PROVISIONAL_HOLDOUT_SCREEN_PASS' if validated[dd] else 'DIAGNOSTIC_UNVALIDATED') if method==2 else 'NOT_TFLO')
            target.append(record)
    flo=np.array(refs['holdout1']['physical'])
    A=np.column_stack([m.TRAIN,np.ones(6)])
    time_only_paulis=np.array([.4,1.])@np.linalg.lstsq(A,training_exact,rcond=None)[0]
    time_only=physical_observables(time_only_paulis)
    comparators=[]
    for name,p in [('classical_U0_FLO',flo),('classical_time_only_linear',time_only)]:
        comparators.append({'name':name,'physical':p.tolist(),
            'RMS_discrepancy_to_U8_chi64':np.sqrt(np.mean((p-ref_target)**2,axis=0)).tolist()})
    null_phys=physical_observables(nulls); null_bphys=physical_observables(null_boot)
    gains=[]
    for dd in range(2):
        tflo_rms=np.sqrt(np.mean((bphys[:,dd,8,2]-ref_target)**2,axis=1))
        for name,base,baseboot in [('readout',phys[dd,8,1],bphys[:,dd,8,1]),
            ('classical_U0_FLO',flo,np.broadcast_to(flo,(m.BOOTSTRAP,36,3))),
            ('fit_without_target_hardware_input',null_phys[dd],null_bphys[:,dd])]:
            gain=np.sqrt(np.mean((base-ref_target)**2,axis=0))-np.sqrt(np.mean((phys[dd,8,2]-ref_target)**2,axis=0))
            bgain=np.sqrt(np.mean((baseboot-ref_target)**2,axis=1))-tflo_rms
            gains.append({'dd':bool(dd),'comparator':name,'gain_charge_spin_doublon':gain.tolist(),
                'conditional_95pct_interval':np.quantile(bgain,[.025,.975],axis=0).tolist(),
                'is_certified_accuracy_gain':False})
    dd_gain=np.sqrt(np.mean((bphys[:,0,8,1]-ref_target)**2,axis=1))-np.sqrt(np.mean((bphys[:,1,8,1]-ref_target)**2,axis=1))
    independent_fit=0.; conditioning=[]
    for dd in range(2):
        for col in range(108):
            x=points[dd,:6,1,col]; design=np.column_stack([x,np.ones(6)])
            beta=np.linalg.lstsq(np.vstack([design,np.sqrt(m.RIDGE)*np.eye(2)]),
                np.r_[training_exact[:,col],np.sqrt(m.RIDGE)*np.array([1.,0.])],rcond=None)[0]
            independent_fit=max(independent_fit,float(np.max(np.abs(beta-models[dd,col]))))
            condition=float(np.linalg.cond(design))
            conditioning.append({'dd':bool(dd),'column':col,'slope':float(models[dd,col,0]),
                'condition':condition if np.isfinite(condition) else None})
    assert independent_delta<1e-12 and count_delta<1e-12 and independent_fit<1e-8
    result={'status':'COMPLETE_FIXED_TFLO_DD_PILOT_ANALYSIS','job_id':raw['job_id'],
        'target_rows':target,'holdout_rows':holdouts,'DD_off_on_TFLO_holdout_screen_pass':validated,
        'classical_comparators':comparators,'gain_diagnostics':gains,
        'readout_DD_off_minus_on_RMS_gain_95pct':np.quantile(dd_gain,[.025,.975],axis=0).tolist(),
        'particle_sector_counts_by_DD_setting':accepted.tolist(),'per_twirl_sector_counts':per_twirl,
        'sector_postselection_applied':False,'TFLO_time_feature':False,'ridge':m.RIDGE,
        'fit_coefficients':models.tolist(),'fit_conditioning':conditioning,
        'readout_errors_Jeffreys':errors.tolist(),'bootstrap_replicates':m.BOOTSTRAP,
        'bootstrap_seed':plan['bootstrap_seed'],'classical_source_sha256':run.digest(classical_path),
        'classical_chi32_to_chi64':classical['comparisons'],'classical_reference_certified':False,
        'quantum_advantage_demonstrated':False,'no_additional_hardware_submission':True,
        'uncertainty_scope':'Whole-shot conditional bootstrap at fixed twirls plus shared independent readout-channel Beta draws and training refit. Excludes drift, correlated SPAM, TFLO transfer bias, Trotter and MPS truncation. Not simultaneous or coverage-certified.',
        'seconds':time.perf_counter()-begun}
    verification={'independent_pair_inversion_max_abs':independent_delta,'integer_popcount_max_abs':count_delta,
        'independent_affine_lstsq_max_abs':independent_fit,'training_U0_only':True,'heldout_excluded_from_fit':True,
        'target_reference_excluded_from_fit':True,'records':len(raw['records']),'shots':sum(len(r['bitstrings']) for r in raw['records']),
        'all_source_hardware_hashes_verified':True}
    out.mkdir(); run.save(out/'summary.json',result); run.save(out/'verification.json',verification)
    for dd in range(2):
        np.savez_compressed(out/f'bootstrap_dd{dd}.npz',physical=bphys[:,dd],null_physical=null_bphys[:,dd])
    run.save(out/'calibration_and_points.json',{'raw_readout_point_paulis':points.tolist(),'calibration_failures':fail.tolist()})
    lines=['# 6x6 TFLO + DD: vaste pilotanalyse','',
        'Job '+raw['job_id']+'. Geen tweede hardwarejob. Alle 38912 shots geverifieerd.','',
        'TFLO-holdoutscreen DD uit/aan: '+str(validated)+'.',
        'Als de screen niet slaagt zijn de TFLO-uitkomsten DIAGNOSTIC_UNVALIDATED, geen herstelde observabelen.','',
        '| DD | Methode | N | RMS lading | RMS spin | RMS doublon | Minimum lokale kans |',
        '|---|---|---:|---:|---:|---:|---:|']
    for r in target:
        rms=r['RMS_charge_spin_doublon']
        lines.append(f"| {r['dd']} | {r['arm']} | {r['N']:.4f} | {rms[0]:.4f} | {rms[1]:.4f} | {rms[2]:.4f} | {r['min_onsite_probability']:.4f} |")
    lines+=['','Afstanden hierboven tegenover niet-gecertificeerde chi64, geen exacte hardwarefouten.',
        'Readout en handmatige twirling in beide armen; DD-X-X-pulsen expliciet in de aan-circuits.',
        'TFLO zonder tijdfeature, uitsluitend zes U=0-trainingspunten per DD-arm; geen filtering of clipping.',
        'Alle holdouts, klassiek-only vergelijkingen, onzekerheden en fitdiagnostiek staan in summary.json.','',
        result['uncertainty_scope'],'','## Onafhankelijke rekencontroles','',
        '```json',json.dumps(verification,indent=2),'```','',
        'Physics- en veilige-API-skills bewaakten onafhankelijke validatie, de budgetgrens en behoud van ruwe data.',
        'Geen quantum advantage aangetoond.','']
    (out/'RAPPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    run.save(run.RUN/'analysis_sha256.json',{str(p.relative_to(run.RUN)):run.digest(p) for p in out.rglob('*') if p.is_file()})
    print(json.dumps({'job_id':raw['job_id'],'holdout_screen':validated,
        'target':[{'dd':r['dd'],'arm':r['arm'],'N':r['N'],'RMS':r['RMS_charge_spin_doublon']} for r in target],
        'verification':verification,'seconds':result['seconds']}),flush=True)


if __name__=='__main__': main()
