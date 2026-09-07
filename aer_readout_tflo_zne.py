"""Offline calibrated-readout comparison; existing target shots, new U0 training."""
import argparse
import io
import json
from pathlib import Path
import shutil
import time
import unittest
import numpy as np
from qiskit import QuantumCircuit, qpy
from qiskit_aer import AerSimulator
from qiskit_ibm_runtime.models import BackendProperties
import aer_cuprate_nighthawk_smoke as a
import aer_cuprate_cz_zne_bitshots as b
import analyze_aer_noise_components as stats
from analyze_aer_cuprate_cz_zne import physical_range
from cuprate_2d_tflo import decode_bitstrings, pauli_samples, physical_observables, fit_tflo, apply_tflo

PARENT=a.RESULTS/'aer_nighthawk_cz_zne_bitshots512_v2'
SOURCES=['aer_readout_tflo_zne.py','test_aer_readout_tflo_zne.py','AER_READOUT_TFLO_ZNE_512_PROTOCOL.md']
METHODS=['raw512','readout384_plus_cal128','readout_TFLO_PRIMARY','readout_ZNE_PRIMARY',
         'TFLO_without_readout_DIAGNOSTIC','ZNE_without_readout_DIAGNOSTIC','classical_FLO']
F1_SIZES=(24,3,21,16)
ZNE_SHOTS=(27,7,14)
W=np.array([4/3,1/3,-2/3])

def train_seed(s,t):
    if s not in range(6) or t not in range(8):
        raise ValueError('Invalid setting/twirl')
    return 2028100000+10000*s+1000*t

def correct_moments(p,mask,errors):
    """Exact inverse product-readout map on single-Z and onsite-ZZ moments."""
    p,mask,errors=map(np.asarray,(p,mask,errors))
    if p.shape[-1]!=27 or mask.shape[-1]!=18 or errors.shape!=(2,18):
        raise ValueError('Expected27 moments,18 mask bits,2x18 errors')
    if not np.isfinite(errors).all() or np.any(errors<0) or np.any(errors>1):
        raise ValueError('Invalid calibration')
    if not np.all((mask==0)|(mask==1)):
        raise ValueError('Invalid mask')
    denom=1-errors.sum(axis=0)
    if np.any(denom<=.2):
        raise ValueError('Ill-conditioned calibration')
    offset=(1-2*mask.astype(float))*(errors[1]-errors[0])
    z=(p[...,:18]-offset)/denom
    zz=(p[...,18:]-offset[...,::2]*p[...,1:18:2]
        -offset[...,1::2]*p[...,:18:2]+offset[...,::2]*offset[...,1::2])
    zz=zz/(denom[::2]*denom[1::2])
    return np.concatenate([z,zz],axis=-1)

def calibration_counts(bits):
    x=np.asarray(bits)
    if x.shape!=(2,64,18) or not np.all((x==0)|(x==1)):
        raise ValueError('Expected2x64x18 calibration bits')
    return np.stack([x[0].sum(axis=0),(1-x[1]).sum(axis=0)])

def calibration_mean(counts):
    return (np.asarray(counts)+.5)/65

def all_methods(strata,training,masks,errors,refs,times):
    """No U8 target reference argument: predictions cannot use target truth."""
    strata,training=np.asarray(strata),np.asarray(training)
    if strata.shape!=(6,8,27) or training.shape!=(6,8,27):
        raise ValueError('Wrong stratified means')
    if np.shape(refs)!=(6,27) or np.shape(times)!=(6,):
        raise ValueError('Exactly six U0 training references required')
    raw=np.einsum('s,stp->p',np.array(F1_SIZES)/64,strata[:4])/8
    r=correct_moments(strata,masks,errors)
    readout=(24*r[0]+3*r[1]+21*r[2]).mean(axis=0)/48
    zne=W@np.stack([((24*r[0]+3*r[1])/27).mean(axis=0),r[4].mean(axis=0),r[5].mean(axis=0)])
    zne_raw=W@np.stack([((24*strata[0]+3*strata[1])/27).mean(axis=0),strata[4].mean(axis=0),strata[5].mean(axis=0)])
    train=correct_moments(training,masks,errors).mean(axis=1)
    model=fit_tflo(train,refs,times,ridge=.001)
    tflo=apply_tflo(model,r[0].mean(axis=0),.4)
    raw_model=fit_tflo(training.mean(axis=1),refs,times,ridge=.001)
    tflo_raw=apply_tflo(raw_model,strata[0].mean(axis=0),.4)
    classical=refs[int(np.flatnonzero(np.isclose(times,.4))[0])]
    return np.stack([raw,readout,tflo,zne,tflo_raw,zne_raw,classical]),model

def verify_inputs(plan):
    for name,h in plan['inputs'].items():
        if a.digest(a.ROOT/name)!=h:
            raise ValueError('Changed input '+name)

def save_block(folder,circuit,sim,shots,seed,mask):
    if folder.exists():
        raise ValueError('Refuse overwrite '+str(folder))
    tick=time.perf_counter()
    result=sim.run(circuit,shots=shots,memory=True,seed_simulator=seed).result()
    elapsed=time.perf_counter()-tick
    if not result.success:
        raise RuntimeError(result.status)
    memory=result.get_memory(0)
    assert len(memory)==shots and b.binary_memory(result.to_dict(),18)==memory
    b.check_saved_counts(result.to_dict(),memory,18)
    bits=decode_bitstrings(memory,18,mask)
    folder.mkdir()
    a.write(folder/'record.json',{'seed':seed,'shots':shots,'mask':mask,'bitstrings':memory,
        'decoded_bits':bits.tolist(),'run_seconds':elapsed})
    a.write(folder/'aer_result.json',result.to_dict())
    a.write(folder/'sha256.json',{p.name:a.digest(p) for p in folder.iterdir()})
    return elapsed

def run(out):
    if out.exists():
        raise ValueError('Refuse overwrite or implicit retry')
    tick=time.perf_counter()
    parent_files=stats.verify_files(PARENT,'final_archive_sha256.json')
    parent=a.read(PARENT/'plan.json')
    manifest=a.read(a.PLAN/'manifest.json')
    settings=[s for s in manifest['settings'] if s['role']=='train']
    assert len(settings)==6 and all(s['u_over_t']==0 for s in settings)
    assert manifest['initial_layout']==parent['layout']
    inputs=[a.ROOT/x for x in SOURCES]+[a.ROOT/x for x in b.SOURCES]
    inputs += [a.PLAN/'manifest.json',PARENT/'final_archive_sha256.json',PARENT/'plan.json',PARENT/'noise_model.json']
    inputs += [b.z.c.BASELINE/'restricted_backend_properties.json',b.z.h.PARENT/'decomposition.json']
    records=[]
    for s,setting in enumerate(settings):
        for t in range(8):
            index,record=next((i,r) for i,r in enumerate(manifest['records'])
                if r['setting_id']==setting['id'] and r['twirl_id']==t)
            path=a.RUN/'provider_inputs'/f'circuit_{index:03d}.qpy'
            inputs.append(path)
            assert record['readout_mask_little_endian']==parent['records'][t]['readout_mask_little_endian']
            records.append({'s':s,'t':t,'record':record,'source':str(path.relative_to(a.ROOT))})
    labels=[train_seed(s,t)+k for s in range(6) for t in range(8) for k in range(4)]
    labels += [2028200000+1000*c+k for c in range(2) for k in range(64)]
    old={b.seed_for(g,t)+k for g in range(3) for t in range(8) for k in range(b.COUNTS[g])}
    assert len(labels)==len(set(labels))==320 and not old.intersection(labels)
    out.mkdir(parents=True)
    (out/'source_snapshot').mkdir(); (out/'circuits').mkdir(); (out/'blocks').mkdir()
    for p in dict.fromkeys(inputs):
        if p.suffix=='.py' or p.name in SOURCES:
            shutil.copyfile(p,out/'source_snapshot'/p.name)
    plan={'schema':'readout-tflo-zne-512-v1','created_utc':a.datetime.now(a.timezone.utc).isoformat(),
        'retrospective_target_reuse':True,'settings':settings,'target':parent['setting'],
        'records':records,'masks':[r['readout_mask_little_endian'] for r in parent['records']],
        'layout':parent['layout'],'methods':METHODS,'new_aer_shots':320,'new_qpu_seconds':0,
        'arm_total_shots':{'raw':512,'readout':512,'readout_tflo':512,'readout_zne':512},
        'cz_applications':{'raw':516096,'readout':387072,'readout_tflo':387072,'readout_zne':669312},
        'equal_time_or_cz_budget':False,'qiskit':a.qiskit.__version__,'aer':a.qiskit_aer.__version__,
        'parent_files_verified':parent_files,'inputs':{str(p.relative_to(a.ROOT)):a.digest(p) for p in inputs}}
    a.write(out/'plan.json',plan)
    log=io.StringIO()
    tests=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('test_aer_readout_tflo_zne'))
    (out/'unit_tests.txt').write_text(log.getvalue(),encoding='utf-8')
    assert tests.wasSuccessful(),log.getvalue()
    noise_dict=a.read(PARENT/'noise_model.json')
    props=BackendProperties.from_dict(a.read(b.z.c.BASELINE/'restricted_backend_properties.json'))
    noise,_=b.z.h.scaled_full_model(props,a.read(b.z.h.PARENT/'decomposition.json'),1.)
    model_audit=b.z.h.validate_saved_control(noise,noise_dict)
    a.write(out/'noise_model.json',noise_dict)
    checks=[]
    circuits={}
    for rec in records:
        s,t=rec['s'],rec['t']
        with (a.ROOT/rec['source']).open('rb') as f:
            physical=qpy.load(f)[0]
        circuit=b.canonical_measured(a.remap_measured(physical,plan['layout']))
        assert circuit.count_ops()['cz']==1008
        p,norm,sector=a.exact_paulis(circuit,rec['record']['readout_mask_little_endian'])
        err=float(np.max(np.abs(p-settings[s]['reference'])))
        assert err<1e-9 and abs(norm-1)<1e-9 and sector<1e-9
        with (out/'circuits'/f'train_{s}_{t}.qpy').open('wb') as f:
            qpy.dump(circuit,f)
        circuits[s,t]=circuit
        checks.append({'s':s,'t':t,'noise_off_error':err,'norm':norm,'outside_sector':sector,'ops':dict(circuit.count_ops())})
        if t==7:
            print(json.dumps({'preflight_training_setting':s,'max_error':max(x['noise_off_error'] for x in checks)}),flush=True)
    a.write(out/'preflight.json',{'tests':tests.testsRun,'checks':checks,'unique_new_seed_labels':320,'model_audit':model_audit})
    sim=AerSimulator(method='statevector',precision='double',noise_model=noise,
        max_parallel_threads=2,max_parallel_shots=2,enable_truncation=False)
    for state in range(2):
        qc=QuantumCircuit(18,18)
        if state:
            qc.x(range(18))
        qc.measure(range(18),range(18))
        with (out/'circuits'/f'cal_{state}.qpy').open('wb') as f:
            qpy.dump(qc,f)
        save_block(out/'blocks'/f'cal_{state}',qc,sim,64,2028200000+1000*state,[0]*18)
    for s in range(6):
        seconds=0.
        for t in range(8):
            if time.perf_counter()-tick>1200:
                raise TimeoutError('1200-second bound; preserve partial run')
            seconds+=save_block(out/'blocks'/f'train_{s}_{t}',circuits[s,t],sim,4,train_seed(s,t),plan['masks'][t])
        print(json.dumps({'completed_training_settings':s+1,'new_training_shots':32*(s+1),'seconds':seconds}),flush=True)
    verify_inputs(plan)
    a.write(out/'run_summary.json',{'status':'COMPLETE_LOCAL_SAMPLING','new_aer_shots':320,
        'new_qpu_seconds':0,'wall_seconds':time.perf_counter()-tick})
    a.write(out/'run_sha256.json',{str(p.relative_to(out)):a.digest(p) for p in out.rglob('*') if p.is_file()})

def read_block(folder):
    stats.verify_files(folder,'sha256.json')
    record=a.read(folder/'record.json'); raw=a.read(folder/'aer_result.json')
    assert raw['success'] and raw['results'][0]['seed_simulator']==record['seed']
    assert b.binary_memory(raw,18)==record['bitstrings']
    b.check_saved_counts(raw,record['bitstrings'],18)
    bits=decode_bitstrings(record['bitstrings'],18,record['mask'])
    np.testing.assert_array_equal(bits,record['decoded_bits'])
    return bits

def analyze(out):
    dest=out/'analysis'
    if dest.exists():
        raise ValueError('Refuse overwrite')
    verified=stats.verify_files(out,'run_sha256.json')
    plan=a.read(out/'plan.json'); verify_inputs(plan)
    stats.verify_files(PARENT,'final_archive_sha256.json')
    groups=[]
    for g in range(3):
        blocks=[]
        for t in range(8):
            record=a.read(PARENT/'blocks'/f'{g}_{t}'/'record.json')
            raw=a.read(PARENT/'blocks'/f'{g}_{t}'/'aer_result.json')
            assert b.binary_memory(raw,18)==record['bitstrings']
            bits=decode_bitstrings(record['bitstrings'],18,plan['masks'][t])
            np.testing.assert_array_equal(bits,record['decoded_bits'])
            blocks.append(pauli_samples(bits))
        groups.append(np.stack(blocks))
    strata=[groups[0][:,:24],groups[0][:,24:27],groups[0][:,27:48],groups[0][:,48:],groups[1][:,:7],groups[2][:,:14]]
    training=np.array([[pauli_samples(read_block(out/'blocks'/f'train_{s}_{t}')) for t in range(8)] for s in range(6)])
    calbits=np.stack([read_block(out/'blocks'/f'cal_{c}') for c in range(2)])
    counts=calibration_counts(calbits); errors=calibration_mean(counts)
    refs=np.array([s['reference'] for s in plan['settings']]); times=np.array([s['time'] for s in plan['settings']])
    masks=np.array(plan['masks']); exact=np.array(plan['target']['reference'])
    means=np.stack([x.mean(axis=1) for x in strata]); train=training.mean(axis=2)
    methods,fit=all_methods(means,train,masks,errors,refs,times)
    np.testing.assert_allclose(methods[0],groups[0].mean(axis=(0,1)),atol=1e-14)
    oracle=np.zeros((2,18))
    for e in a.read(out/'noise_model.json')['errors']:
        if e['type']=='roerror':
            q=e['gate_qubits'][0][0]
            oracle[:,q]=[e['probabilities'][0][1],e['probabilities'][1][0]]
    oracle_methods,_=all_methods(means,train,masks,oracle,refs,times)
    rng=np.random.default_rng(2028500000)
    draws=[]; fixed=[]; rejected=0
    for k in range(2000):
        sm=[]
        for x in strata:
            n=x.shape[1]; ids=rng.integers(0,n,(8,n))
            sm.append(x[np.arange(8)[:,None],ids].mean(axis=1))
        ids=rng.integers(0,4,(6,8,4))
        tm=training[np.arange(6)[:,None,None],np.arange(8)[None,:,None],ids].mean(axis=2)
        sampled=rng.beta(counts+.5,64-counts+.5)
        try:
            d,_=all_methods(sm,tm,masks,sampled,refs,times)
        except ValueError:
            rejected+=1
            continue
        f,_=all_methods(sm,tm,masks,errors,refs,times)
        draws.append(d); fixed.append(f)
    assert rejected==0,'Do not condition inference on successful calibration draws'
    draws,fixed=np.array(draws),np.array(fixed)
    metrics=stats.metrics(methods,exact); dm=stats.metrics(draws,exact)
    fm=stats.metrics(fixed,exact)
    delta=dm[:,3,1]-dm[:,2,1]
    p_mse=np.mean((methods-exact)**2,axis=1)
    gain=dm[:,0,:3]-dm[:,2,:3]
    results={'schema':'readout-tflo-zne-512-analysis-v1','methods':METHODS,'metrics_order':stats.METRICS,
        'metrics':metrics.tolist(),'method_moments':methods.tolist(),'physical_means':physical_observables(methods).tolist(),
        'pauli_mse':p_mse.tolist(),'hybrid_interval95':stats.ci(dm),
        'primary_spin_rmse_zne_minus_tflo':float(metrics[3,1]-metrics[2,1]),
        'primary_hybrid_interval95':stats.ci(delta),
        'primary_fixed_calibration_bootstrap95':stats.ci(fm[:,3,1]-fm[:,2,1]),
        'raw_minus_tflo_rmse_interval95':stats.ci(gain),
        'raw_minus_readout_rmse_interval95':stats.ci(dm[:,0,:3]-dm[:,1,:3]),
        'tflo_readout_increment_interval95':stats.ci(dm[:,4,:3]-dm[:,2,:3]),
        'zne_readout_increment_interval95':stats.ci(dm[:,5,:3]-dm[:,3,:3]),
        'classical_minus_tflo_spin_interval95':stats.ci(dm[:,6,1]-dm[:,2,1]),
        'classical_minus_tflo_pauli_mse_interval95':stats.ci(p_mse[6]-np.mean((draws[:,2]-exact)**2,axis=1)),
        'calibration':{'error_counts':counts.tolist(),'shots_per_state':64,'posterior_mean':errors.tolist(),
            'known_model_errors_ORACLE':oracle.tolist(),'min_denominator':float(np.min(1-errors.sum(axis=0))),
            'prior':'independent Jeffreys Beta(0.5,0.5)','includes_noisy_X_preparation':True},
        'oracle_only_metrics':stats.metrics(oracle_methods,exact).tolist(),'tflo_fit':fit,
        'physical_ranges':{name:physical_range(methods[m]) for m,name in enumerate(METHODS)},
        'bootstrap_replicates':2000,'calibration_draw_failures':rejected,
        'bootstrap_resolution':{str(n):stats.ci(delta[:n]) for n in [200,1000,2000]},
        'arm_total_shots':plan['arm_total_shots'],'cz_applications':plan['cz_applications'],
        'equal_time_or_cz_budget':False,'retrospective_target_reuse':True,'postselection':False,
        'new_qpu_seconds':0,'verified_run_files':verified,'run_summary':a.read(out/'run_summary.json'),
        'limitations':['Hybrid bootstrap/calibration posterior intervals are not coverage-certified CIs.',
            'Only4 training shots per twirl; no training convergence certificate.',
            'No transfer/extrapolation/model bias, drift or SPAM preparation systematic in intervals.',
            'Reuses previously inspected target shots; exploratory only.','No hardware or quantum advantage claim.']}
    dest.mkdir()
    a.write(dest/'results.json',results)
    np.savez_compressed(dest/'bootstrap.npz',hybrid=draws,fixed_calibration=fixed)
    lines=['# Aer: readout + TFLO versus readout + ZNE','',
        'Exploratieve uitbreiding met bestaande U8-data en320 nieuwe Aer-shots. Nieuwe QPU-seconden:0.',
        'Iedere hoofdarm heeft512 shots inclusief benodigde kalibratie/training; CZ-/tijdbudget niet gelijk.','',
        '| Methode | Lading-RMSE | Spin-RMSE | Doublon-RMSE |','|---|---:|---:|---:|']
    for name,row in zip(METHODS,metrics):
        lines.append('| '+name+' | '+' | '.join(f'{v:.5f}' for v in row[:3])+' |')
    ci=results['primary_hybrid_interval95']
    lines += ['',f'Primair spin-RMSE(ZNE)-spin-RMSE(TFLO):{results["primary_spin_rmse_zne_minus_tflo"]:.5f};',
        f'95%-hybride onzekerheidsinterval [{ci["low"]:.5f},{ci["high"]:.5f}]. Positief bevoordeelt TFLO.',
        'Dit interval combineert shot-bootstrap en een Jeffreys-kalibratieposterior; geen gegarandeerd frequentistisch95%-interval.',
        'Readout + TFLO krijgt een nieuwe U0-fit; geen U8-referentiedata in training.',
        'Geen postselectie: deze pilot is niet gelijk aan de eerdere hardware-TFLO-analyse.',
        'Readout-correctie is een lokale inverse-momentmethode, geen M3/TREX.',
        'Bekende-noisematrixresultaten zijn alleen een oracle-diagnose, geen gratis kalibratie.',
        'Een betere centrale waarde is zonder guardrails en onzekerheid geen algemene winnaar.',
        'Modelbias, extrapolatiebias, TFLO-transferbias, hardwaredrift en calibratie-preparatiefout zijn niet afgedekt.',
        'Geen hardwarewinst,5-secondenuitvoerbaarheid of quantum advantage aangetoond.','',
        'Bronnen: [TFLO](https://arxiv.org/abs/2102.02120); [measurement mitigation](https://qiskit.github.io/qiskit-addon-mthree/).','']
    (dest/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    a.write(out/'final_sha256.json',{str(p.relative_to(out)):a.digest(p) for p in out.rglob('*') if p.is_file()})
    print(json.dumps({'metrics':metrics.tolist(),'primary_interval':ci,'new_qpu_seconds':0}),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['run','analyze'])
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    (run if args.stage=='run' else analyze)(args.output.resolve())
