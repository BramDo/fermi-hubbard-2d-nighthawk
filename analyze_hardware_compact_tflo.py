"""Paired original/compact analysis with fixed U0-only TFLO and target-free null."""
import argparse,io,json,shutil,time,unittest
import numpy as np
import run_hardware_compact_tflo as r
import cuprate_2d_tflo_dd6 as m
from analyze_tflo_dd6 import transform,row
from cuprate_2d_tflo import decode_bitstrings,pauli_samples,physical_observables
from cuprate_2d_hardware_controls import corrected_paulis

METHODS=('raw','readout','readout_tflo')

def gain(point,boots,reference):
    rms=np.sqrt(np.mean((point-reference)**2,axis=-2))
    brms=np.sqrt(np.mean((boots-reference)**2,axis=-2))
    return dict(original_minus_compact_RMS=(rms[0]-rms[1]).tolist(),
        conditional_95pct_interval=np.quantile(brms[:,0]-brms[:,1],[.025,.975],axis=0).tolist(),
        positive_favors_compact=True)

def freeze():
    r.require(not r.LOCK.exists(),'Freeze analysis before hardware attempt')
    r.require(not (r.RUN/'analysis_protocol.json').exists(),'Analysis already frozen')
    stream=io.StringIO(); tests=unittest.TextTestRunner(stream=stream,verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromNames(['test_hardware_compact_tflo','test_compact_symbolic_tflo','test_analysis_hardware_compact_tflo']))
    r.require(tests.wasSuccessful(),'Pre-hardware tests failed')
    names=['analyze_hardware_compact_tflo.py','test_analysis_hardware_compact_tflo.py',
        'analyze_tflo_dd6.py','cuprate_2d_hardware_controls.py']
    folder=r.RUN/'analysis_sources'; folder.mkdir()
    for name in names: shutil.copyfile(r.ROOT/name,folder/name)
    with (folder/'unit_tests.txt').open('x',encoding='utf-8') as f: f.write(stream.getvalue())
    r.save(r.RUN/'analysis_protocol.json',dict(protocol_sha256=r.digest(r.ROOT/'HARDWARE_COMPACT_TFLO_PROTOCOL.md'),
        source_sha256={n:r.digest(r.ROOT/n) for n in names},tests_passed=tests.testsRun,
        plan_sha256=r.digest(r.RUN/'plan.json'),frozen_before_submission=True,created_unix=time.time()))
    r.log('analysis_frozen',tests_passed=tests.testsRun)

def main():
    begun=time.perf_counter(); out=r.RUN/'analysis'; r.require(not out.exists(),'Preserve existing analysis')
    r.verify(r.RUN,'hardware_archive_sha256.json')
    ap=r.read(r.RUN/'analysis_protocol.json'); r.require(ap['frozen_before_submission'],'Missing analysis freeze')
    for name,h in ap['source_sha256'].items(): r.require(r.digest(r.ROOT/name)==h,'Frozen analysis source changed')
    plan=r.read(r.RUN/'plan.json'); raw=r.read(r.RUN/'raw_bitstrings.json'); refs=r.read(r.RUN/'references.json')
    retrieval=r.read(r.RUN/'retrieval_verification.json')
    r.require(ap['plan_sha256']==r.digest(r.RUN/'plan.json'),'Analysis plan changed')
    r.require(retrieval['status']=='DONE_ARCHIVED_VERIFIED' and raw['job_id']==retrieval['job_id'],'Unverified hardware')
    r.validate_records(plan['records']); r.require(len(raw['records'])==76,'Record count')
    ids=[s['id'] for s in m.settings()]; exact=np.array([refs[s]['paulis'] for s in ids[:6]])
    cal={}; targets=[]
    for rec,want in zip(raw['records'],plan['records']):
        r.require(all(rec[k]==v for k,v in want.items()),'Record identity')
        bits=decode_bitstrings(rec['bitstrings'],72,rec['readout_mask_little_endian']); r.require(len(bits)==512,'Shot count')
        if rec['role']=='calibration': cal[rec['state'],rec['block']]=bits
        else: targets.append((rec,bits))
    fail=np.array([sum(cal[0,b].sum(0) for b in ('start','end')),sum((1-cal[1,b]).sum(0) for b in ('start','end'))])
    errors=(fail+.5)/1025; rng=np.random.default_rng(plan['bootstrap_seed'])
    eb=rng.beta(fail+.5,1024-fail+.5,size=(400,2,72))
    points=np.zeros((2,9,2,108)); boots=np.zeros((400,2,9,2,108)); sector=np.zeros((2,9),int)
    inversion_delta=0.; popcount_delta=0.; per_twirl=[]
    for rec,bits in targets:
        arm=r.ARMS.index(rec['arm']); si=ids.index(rec['setting_id']); mask=np.array(rec['readout_mask_little_endian'])
        samples=pauli_samples(bits); means=samples.mean(0); corrected=corrected_paulis(means,mask,errors)
        points[arm,si]+=np.stack([means,corrected])/4
        weights=rng.multinomial(512,np.full(512,1/512),size=400); bm=weights@samples/512
        boots[:,arm,si]+=np.stack([bm,corrected_paulis(bm,mask,eb)],axis=1)/4
        keep=(bits[:,::2].sum(1)==16)&(bits[:,1::2].sum(1)==16); sector[arm,si]+=int(keep.sum())
        per_twirl.append(dict(arm=rec['arm'],setting_id=rec['setting_id'],twirl=rec['twirl_id'],pair_id=rec['pair_id'],
            sector_shots=int(keep.sum()),shots=512,raw_readout_paulis=np.stack([means,corrected]).tolist()))
        mi=sum(int(v)<<q for q,v in enumerate(mask))
        direct=np.mean([(int(st,2)^mi).bit_count() for st in rec['bitstrings']])
        popcount_delta=max(popcount_delta,abs(direct-physical_observables(means)[:,0].sum()))
        native=bits^mask; independent=[]
        for site in range(36):
            a,b=2*site,2*site+1; probs=np.bincount(2*native[:,a]+native[:,b],minlength=4)/512
            mats=[]
            for q in (a,b):
                e0,e1=errors[:,q]; mats.append(np.array([[1-e0,e1],[e0,1-e1]]))
            corrected_probs=np.linalg.solve(np.kron(*mats),probs)
            p=corrected_probs[np.arange(4)^(2*mask[a]+mask[b])]
            independent.append([p[1]+p[2]+2*p[3],p[2]-p[1],p[3]])
        inversion_delta=max(inversion_delta,float(np.max(np.abs(np.array(independent)-physical_observables(corrected)))))
    pred,models,null=transform(points,exact)
    predboot=np.empty((400,2,9,3,108)); nullboot=np.empty((400,2,108))
    for i in range(400): predboot[i],_,nullboot[i]=transform(boots[i],exact)
    phys=physical_observables(pred); bp=physical_observables(predboot)
    nullp=physical_observables(null); nullbp=physical_observables(nullboot)
    fitdelta=0.; conditioning=[]
    for a in range(2):
        for col in range(108):
            design=np.column_stack([points[a,:6,1,col],np.ones(6)])
            beta=np.linalg.lstsq(np.vstack([design,np.sqrt(.001)*np.eye(2)]),np.r_[exact[:,col],np.sqrt(.001)*np.array([1.,0.])],rcond=None)[0]
            fitdelta=max(fitdelta,float(np.max(np.abs(beta-models[a,col]))))
            cond=float(np.linalg.cond(design)); conditioning.append(dict(arm=r.ARMS[a],column=col,condition=cond if np.isfinite(cond) else None))
    r.require(inversion_delta<1e-12 and popcount_delta<1e-12 and fitdelta<1e-8,'Independent numerical check failed')
    classical_path=r.ROOT/'results_cuprate_2d/classical_full_6x6_mps_T04_chi64_v1/summary.json'
    classical=r.read(classical_path); r.require(not classical['certified_6x6_error_bound'],'Reference status changed')
    target_ref=np.array(classical['result']['physical_means']); holdouts=[]; targets_out=[]; gains=[]; screens=[]; nullrows=[]
    thresholds=np.array([.05,.05,.03])
    for a,arm in enumerate(r.ARMS):
        passed=True
        for si in (6,7):
            ref=np.array(refs[ids[si]]['physical'])
            for method,label in enumerate(METHODS):
                item=row(label,phys[a,si,method],bp[:,a,si,method],ref,True)
                item.update(circuit_arm=arm,setting_id=ids[si],T=m.settings()[si]['T']); holdouts.append(item)
                if method==2: passed=passed and bool(np.all(np.array(item['RMS_95pct_intervals'])[1]<=thresholds))
        screens.append(passed)
        for method,label in enumerate(METHODS):
            item=row(label,phys[a,8,method],bp[:,a,8,method],target_ref,False)
            item.update(circuit_arm=arm,TFLO_validation_status=('PROVISIONAL_HOLDOUT_SCREEN_PASS' if passed else 'DIAGNOSTIC_UNVALIDATED') if method==2 else 'NOT_TFLO')
            targets_out.append(item)
        item=row('fit_without_target_hardware_input',nullp[a],nullbp[:,a],target_ref,False); item['circuit_arm']=arm; nullrows.append(item)
    for si in (6,7,8):
        ref=target_ref if si==8 else np.array(refs[ids[si]]['physical'])
        for method,label in enumerate(METHODS):
            gains.append(dict(setting_id=ids[si],T=m.settings()[si]['T'],method=label,reference_exact=si!=8,
                **gain(phys[:,si,method],bp[:,:,si,method],ref)))
    verification=dict(independent_readout_pair_inversion_max_abs=inversion_delta,independent_integer_popcount_max_abs=popcount_delta,
        independent_augmented_lstsq_max_abs=fitdelta,training_U0_only=True,holdouts_and_target_excluded_from_fit=True,
        shots=38912,records=76,old_archives_not_modified=True)
    summary=dict(status='COMPLETE_ORIGINAL_COMPACT_TFLO_ANALYSIS',job_id=raw['job_id'],arms=list(r.ARMS),
        target_rows=targets_out,holdout_rows=holdouts,holdout_screen_pass=screens,paired_gain_rows=gains,
        no_target_input_rows=nullrows,fit_coefficients=models.tolist(),fit_conditioning=conditioning,
        readout_errors_Jeffreys=errors.tolist(),sector_counts=sector.tolist(),sector_postselection_applied=False,
        classical_reference_certified=False,classical_source_sha256=r.digest(classical_path),
        classical_chi32_to_chi64=classical['comparisons'],quantum_advantage_demonstrated=False,
        bootstrap_replicates=400,bootstrap_seed=plan['bootstrap_seed'],analysis_plan_sha256=r.digest(r.RUN/'analysis_protocol.json'),
        uncertainty_scope='Conditional whole-shot bootstrap at fixed twirls, shared independent readout Beta draws and training refit. Excludes drift, correlated SPAM, TFLO transfer bias, Trotter and MPS truncation; not simultaneous or coverage-certified.',
        seconds=time.perf_counter()-begun)
    out.mkdir(); r.save(out/'summary.json',summary); r.save(out/'verification.json',verification)
    r.save(out/'per_twirl.json',per_twirl); r.save(out/'calibration_and_points.json',dict(calibration_failures=fail.tolist(),points=points.tolist()))
    np.savez_compressed(out/'bootstrap.npz',physical=bp,null_physical=nullbp)
    lines=['# 6x6: origineel versus compact','',f"Job {raw['job_id']}; 38.912 shots geverifieerd.",'',
        f'TFLO-holdoutscreen origineel/compact: {screens}.','',
        '| Circuit | Methode | N | RMS lading | RMS spin | RMS doublon | Minimum lokale kans |',
        '|---|---|---:|---:|---:|---:|---:|']
    for item in targets_out+nullrows:
        x=item['RMS_charge_spin_doublon']; lines.append(f"| {item['circuit_arm']} | {item['arm']} | {item['N']:.4f} | {x[0]:.4f} | {x[1]:.4f} | {x[2]:.4f} | {item['min_onsite_probability']:.4f} |")
    lines+=['','U8-afstanden tegenover niet-gecertificeerde chi64, geen exacte hardwarefouten.',
        'Geen clipping, postselectie, extra DD, ZNE of PEC. TFLO gebruikt uitsluitend zes U0-trainingspunten.',
        'De controle zonder doelhardware-input gebruikt dezelfde fit met het gemiddelde trainingsinput.',
        'Bij falende holdouts blijven TFLO-uitkomsten DIAGNOSTIC_UNVALIDATED.','',
        '## Primaire gepaarde holdoutvergelijking','',
        '| Tijd | Methode | Winst lading | Winst spin | Winst doublon |',
        '|---|---|---:|---:|---:|']
    for item in gains:
        if item['reference_exact']:
            x=item['original_minus_compact_RMS']; lines.append(f"| {item['T']} | {item['method']} | {x[0]:+.4f} | {x[1]:+.4f} | {x[2]:+.4f} |")
    lines+=['','Positief betekent lagere RMS-fout voor compact; onzekerheidsintervallen staan in summary.json.',
        summary['uncertainty_scope'],'','## Onafhankelijke controles','', '```json',json.dumps(verification,indent=2),'```','',
        'De physics- en veilige-API-skills bewaakten de budgetgrens, controles en archivering. Geen quantum advantage aangetoond.','']
    with (out/'RAPPORT.md').open('x',encoding='utf-8') as f: f.write('\n'.join(lines))
    with (out/'VERIFICATION.md').open('x',encoding='utf-8') as f: f.write('# Executed independent checks\n\n```json\n'+json.dumps(verification,indent=2)+'\n```\n')
    r.save(r.RUN/'analysis_sha256.json',{str(p.relative_to(r.RUN)):r.digest(p) for p in out.rglob('*') if p.is_file()})
    r.log('analysis_complete',holdout_screen=screens,target=[dict(circuit_arm=x['circuit_arm'],method=x['arm'],N=x['N'],RMS=x['RMS_charge_spin_doublon']) for x in targets_out],verification=verification)

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('action',choices=('freeze','analyze'))
    if parser.parse_args().action=='freeze': freeze()
    else: main()
