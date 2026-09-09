"""Prepare existing 3x3/6x6 hardware inputs for L-MPF, without fitting results.

This is readout/metadata preparation, NOT a claim of completed L-MPF mitigation.
No IBM service, submission, target-reference regression or N projection exists.
"""
from pathlib import Path
import argparse,json,re,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from lmpf_2d.model import digest

ARCHIVES=['hardware_readout_cz_folding_3x3_2026-09-06','hardware_readout_cz_folding_6x6_2026-09-06']
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def write(path,obj):Path(path).write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')
def decode(strings,n):
    if not strings or any(len(s)!=n or set(s)-{'0','1'} for s in strings):raise ValueError('Invalid bitstrings')
    return np.array([[int(c) for c in s[::-1]] for s in strings],dtype=float)
def moment_samples(bits,mask,errors):
    e0,e1=errors;a=1-e0-e1;b=e1-e0
    if np.min(a)<=.1:raise ValueError('Ill-conditioned readout inverse')
    z=((1-2*bits)-b)/a
    z*=1-2*np.asarray(mask)
    return np.column_stack((z,z[:,0::2]*z[:,1::2]))

def prepare(folder,dest):
    if dest.exists():raise FileExistsError('Preserve previous hardware preparations')
    dest.mkdir(parents=True)
    plan=read(folder/'plan.json');raw=read(folder/'raw_bitstrings.json');receipt=read(folder/'job_receipt.json')
    if raw['job_id']!=receipt['job_id'] or receipt['backend']!=plan['backend']:raise ValueError('Archive identity mismatch')
    if receipt.get('plan_sha256') and receipt['plan_sha256']!=digest(folder/'plan.json'):raise ValueError('Plan hash mismatch')
    n=int(raw['width']);records=raw['records'];keyed={(r['setting_id'],r['twirl_id']):r for r in records}
    if n not in (18,72) or len(plan['layout'])!=n:raise ValueError('Unexpected hardware width')
    cal=[decode(keyed[f'readout_all{s}',0]['bitstrings'],n) for s in [0,1]]
    counts=np.array([cal[0].sum(0),(1-cal[1]).sum(0)])
    totals=np.array([len(c) for c in cal])[:,None]
    errors=(counts+.5)/(totals+1)
    factors=sorted({int(m.group(1)) for r in records if (m:=re.fullmatch(r'U8_T04_factor([123])',r['setting_id']))})
    means=[];covs=[];shots=[];arm_records=[];source_stats=[]
    for factor in factors:
        group=sorted([r for r in records if r['setting_id']==f'U8_T04_factor{factor}'],key=lambda r:r['twirl_id'])
        if not group:raise ValueError('Missing factor')
        arm_mean=np.zeros(n+n//2);cov=np.zeros((len(arm_mean),len(arm_mean)));stats=[]
        for r in group:
            bits=decode(r['bitstrings'],n);mask=r['readout_mask_little_endian']
            if len(mask)!=n or not set(mask)<={0,1}:raise ValueError('Invalid readout twirl mask')
            samples=moment_samples(bits,mask,errors)
            arm_mean+=samples.mean(0)/len(group)
            cov+=np.cov(samples,rowvar=False,ddof=1)/len(samples)/len(group)**2
            z=1-2*bits
            stats.append((z.mean(0),(z[:,0::2]*z[:,1::2]).mean(0),np.array(mask)))
        means.append(arm_mean);covs.append(cov);shots.append(sum(len(r['bitstrings']) for r in group));source_stats.append(stats)
        arm_records.append({'factor':factor,'record_indices':[records.index(r) for r in group],
            'twirl_ids':[r['twirl_id'] for r in group],'shots_per_twirl':[len(r['bitstrings']) for r in group]})
    # Calibration posterior is shared across arms, hence its covariance is not diagonal.
    rng=np.random.default_rng(2026090881);cal_means=[]
    for _ in range(512):
        e=rng.beta(counts+.5,totals-counts+.5);a=1-e.sum(0);b=e[1]-e[0];row=[]
        for stats in source_stats:
            avg=np.zeros(n+n//2)
            for rawz,rawzz,mask in stats:
                sign=1-2*mask
                z=sign*(rawz-b)/a
                zz=sign[0::2]*sign[1::2]*(rawzz-b[0::2]*rawz[1::2]-b[1::2]*rawz[0::2]+b[0::2]*b[1::2])/(a[0::2]*a[1::2])
                avg+=np.r_[z,zz]/len(stats)
            row.extend(avg)
        cal_means.append(row)
    calibration_cov=np.cov(cal_means,rowvar=False,ddof=1)
    np.savez_compressed(dest/'moments_and_covariance.npz',means=means,
        conditional_shot_covariances=covs,shared_calibration_covariance=calibration_cov)
    learned_candidates=[p.name for p in folder.iterdir() if p.is_file() and re.search(r'lindblad|noise.learn|learned.*noise',p.name,re.I)]
    qpy_dir=folder/'provider_inputs'
    manifest={'schema':'lmpf-hardware-inputs-v1','archive':str(folder.relative_to(ROOT)),
        'job_id':raw['job_id'],'backend':plan['backend'],'width':n,'layout':plan['layout'],
        'factors':factors,'arm_records':arm_records,'target_shots_per_factor':shots,
        'calibration_shots':int(totals.sum()),'readout_error_posterior_mean':errors.tolist(),
        'readout_model':'independent bit assignment; Jeffreys posterior',
        'twirl_order':'invert readout first, then undo final X mask',
        'mean_order':'Z logical modes, then onsite ZZ; identity terms remain separate',
        'coefficient_conditioning_requires_actual_arm_channels':True,
        'calibration_uncertainty':'shared posterior covariance, approximate; not coverage-certified',
        'drift_and_correlated_readout_included':False,
        'native_qpy_files_present':len(list(qpy_dir.glob('circuit_*.qpy'))),
        'qpy_contents_reverified':False,'learned_noise_candidates_in_this_archive':learned_candidates,
        'ready_for_validated_lmpf':False,
        'blocking_inputs':['Validated arm-specific Heisenberg overlaps on the saved native circuits',
            'A learned Pauli-Lindblad model or independently validated noise surrogate at the job calibration'],
        'do_not_apply_8q_pilot_weights_to_this_archive':True,
        'not_an_lmpf_mitigated_hardware_result':True,'new_qpu_seconds':0,
        'input_sha256':{p.name:digest(p) for p in [folder/'plan.json',folder/'raw_bitstrings.json',folder/'job_receipt.json']},
        'moments_sha256':digest(dest/'moments_and_covariance.npz')}
    write(dest/'manifest.json',manifest)
    return {k:manifest[k] for k in ['archive','job_id','width','target_shots_per_factor','calibration_shots','ready_for_validated_lmpf','learned_noise_candidates_in_this_archive']}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise FileExistsError('Refuse overwrite')
    args.output.mkdir(parents=True)
    summaries=[prepare(ROOT/'results_cuprate_2d'/name,args.output/name) for name in ARCHIVES]
    write(args.output/'summary.json',{'archives':summaries,'new_qpu_seconds':0})
    print(json.dumps(summaries,indent=2))
