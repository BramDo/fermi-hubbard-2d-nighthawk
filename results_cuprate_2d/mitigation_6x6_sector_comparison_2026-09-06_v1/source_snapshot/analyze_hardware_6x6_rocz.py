"""Frozen descriptive 6x6 readout/CZ-ZNE analysis; no provider calls."""
from pathlib import Path
import json
import time
import numpy as np
from threadpoolctl import threadpool_limits
from cuprate_2d_tflo import decode_bitstrings,pauli_samples,physical_observables
import run_cuprate_2d_tflo_once as safe

ROOT=Path(__file__).resolve().parent
RUN=ROOT/'results_cuprate_2d/hardware_readout_cz_folding_6x6_2026-09-06'
ARMS=['raw_factor1','readout_factor1','readout_cz_zne','cz_zne_without_readout_diagnostic']
WEIGHTS=np.array([4/3,1/3,-2/3])

def correct(means,masks,errors):
    means=np.asarray(means,float); masks=np.asarray(masks); errors=np.asarray(errors,float)
    if means.shape!=(3,8,108) or masks.shape!=(8,72) or errors.shape!=(2,72):
        raise ValueError('Unexpected dimensions')
    if not np.all(np.isfinite(means)) or not np.all(np.isfinite(errors)):
        raise ValueError('Nonfinite input')
    if np.any(errors<0) or np.any(errors>1) or np.any(1-errors.sum(axis=0)<=.1):
        raise ValueError('Unstable readout inverse')
    a=(1-2*masks.astype(float))*(errors[1]-errors[0])
    b=1-errors.sum(axis=0)
    z=(means[:,:,:72]-a)/b
    zz=(means[:,:,72:]-a[:,::2]*means[:,:,1:72:2]
        -a[:,1::2]*means[:,:,:72:2]+a[:,::2]*a[:,1::2])/(b[::2]*b[1::2])
    return np.concatenate([z,zz],axis=-1)

def predictions(means,masks,errors):
    corrected=correct(means,masks,errors).mean(axis=1)
    raw=means.mean(axis=1)
    return np.array([raw[0],corrected[0],WEIGHTS@corrected,WEIGHTS@raw])

def pair_probabilities(p):
    z0=p[..., :72:2]; z1=p[...,1:72:2]; zz=p[...,72:]
    return np.stack([(1+s*z0+t*z1+s*t*zz)/4 for s,t in [(1,1),(1,-1),(-1,1),(-1,-1)]],axis=-1)

def main():
    import run_hardware_6x6_rocz_once as h
    h.verify_files(RUN,'hardware_archive_sha256.json')
    plan=safe.read(RUN/'plan.json'); raw=safe.read(RUN/'raw_bitstrings.json')
    h.validate_records(raw['records'])
    if raw['job_id']!=safe.read(RUN/'job_receipt.json')['job_id'] or raw['width']!=72:
        raise ValueError('Provenance mismatch')
    out=RUN/'analysis'
    if out.exists(): raise FileExistsError('Analysis already exists; do not overwrite')
    blocks={}; calibration={}; masks=np.zeros((8,72),dtype=int)
    for rec,wanted in zip(raw['records'],plan['records']):
        if any(rec[k]!=v for k,v in wanted.items()): raise ValueError('Record mismatch')
        bits=decode_bitstrings(rec['bitstrings'],72,rec['readout_mask_little_endian'])
        if rec['role']=='calibration':
            calibration[rec['state']]=bits
        else:
            masks[rec['twirl_id']]=rec['readout_mask_little_endian']
            blocks[rec['factor']-1,rec['twirl_id']]=pauli_samples(bits)
    failures=np.array([calibration[0].sum(axis=0),(1-calibration[1]).sum(axis=0)])
    errors=(failures+.5)/513
    means=np.array([[blocks[f,t].mean(axis=0) for t in range(8)] for f in range(3)])
    point=predictions(means,masks,errors)
    B=plan['bootstrap_replicates']; rng=np.random.default_rng(plan['bootstrap_seed'])
    boot_means=np.empty((B,3,8,108)); tick=time.perf_counter()
    with threadpool_limits(limits=1):
        for f in range(3):
            for t in range(8):
                weights=rng.multinomial(512,np.full(512,1/512),size=B)
                boot_means[:,f,t]=weights@blocks[f,t]/512
            print(json.dumps({'bootstrapped_factor':f+1,'replicates':B}),flush=True)
    errors_boot=rng.beta(failures+.5,512-failures+.5,size=(B,2,72))
    boot=np.array([predictions(boot_means[k],masks,errors_boot[k]) for k in range(B)])
    physical=physical_observables(point); boot_physical=physical_observables(boot)
    ci=np.quantile(boot_physical,[.025,.975],axis=0)
    rows=[]
    for j,name in enumerate(ARMS):
        N=physical[j,:,0].sum()
        rows.append({'arm':name,'physical_charge_spin_doublon':physical[j].tolist(),
            'physical_95pct_intervals':ci[:,j].tolist(),'N':float(N),'N_error_from32':float(N-32),
            'N_95pct_interval':np.quantile(boot_physical[:,j,:,0].sum(axis=1),[.025,.975]).tolist(),
            'min_onsite_pair_probability':float(pair_probabilities(point[j]).min()),
            'out_of_range_pauli_count':int(np.sum(np.abs(point[j])>1)),
            'shot_cost':[4096,5120,13312,12288][j]})
    classical=safe.read(h.CLASSICAL/'summary.json')
    comparisons=[]
    for ref in classical['results']:
        if ref['config']['lx']!=6: continue
        difference=physical-np.asarray(ref['physical_means'])
        comparisons.append({'profile':ref['profile'],'kernel_seconds':ref['kernel_seconds'],
            'differences_RMS_charge_spin_doublon':np.sqrt(np.mean(difference**2,axis=1)).tolist(),
            'is_error_against_exact_reference':False})
    result={'status':'DESCRIPTIVE_6X6_ANALYSIS_NO_CERTIFIED_ACCURACY','job_id':raw['job_id'],
        'arms':rows,'factor_means':means.tolist(),'point_paulis':point.tolist(),
        'readout_error_rates_Jeffreys':errors.tolist(),'classical_comparisons':comparisons,
        'bootstrap_replicates':B,'bootstrap_seconds':time.perf_counter()-tick,
        'raw_and_zne_equal_shot_budget':False,'classical_reference_converged':False,
        'quantum_advantage_demonstrated':False,'values_clipped':False,
        'uncertainty_scope':'Pointwise hybrid intervals: whole-shot conditional bootstrap at fixed twirls, shared independent Jeffreys readout-channel draws. Not simultaneous or coverage-certified; excludes drift, correlated SPAM, folding/extrapolation bias, Trotter error and MPS truncation.'}
    out.mkdir()
    safe.exclusive_json(out/'results.json',result)
    np.savez_compressed(out/'bootstrap.npz',paulis=boot,physical=boot_physical)
    lines=['# 6x6 readout + CZ-ZNE hardwarepilot','',
        '36 sites, 72 modes, T=0.4, U/t=8, t-prime/t=-0.25, two steps.',
        'Raw4096 shots; readout5120; readout+ZNE13312. No equal-budget mitigation claim.','',
        '| Arm | N (target32) | N95% interval | Lowest onsite joint probability |',
        '|---|---:|---|---:|']
    for r in rows: lines.append(f"| {r['arm']} | {r['N']:.5f} | {r['N_95pct_interval']} | {r['min_onsite_pair_probability']:.5f} |")
    lines+=['','No certified 6x6 reference: chi8/16/32 failed the stability screen.',
        'Differences to MPS are discrepancies, not measured absolute quantum errors.',
        'No local matched-accuracy speed advantage established.',result['uncertainty_scope'],'']
    (out/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    safe.exclusive_json(RUN/'analysis_archive_sha256.json',{str(p.relative_to(RUN)):safe.digest(p)
        for p in out.rglob('*') if p.is_file()})
    print(json.dumps({'status':result['status'],'job_id':raw['job_id'],
        'N_by_arm':[r['N'] for r in rows],'quantum_advantage_demonstrated':False}),flush=True)

if __name__=='__main__': main()

