"""Independent arithmetic audit of the completed pilot; no provider calls."""
import hashlib,json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parent
RUN=ROOT/'results_cuprate_2d/hardware_tflo_dd6_2026-09-06_v1'
def read(path): return json.loads(path.read_text())

def main():
    summary=read(RUN/'analysis/summary.json')
    raw=read(RUN/'raw_bitstrings.json')
    reference=np.array(read(ROOT/'results_cuprate_2d/classical_full_6x6_mps_T04_chi64_v1/summary.json')['result']['physical_means'])
    counts_delta=0.; rms_delta=0.; null_delta=0.; ablations=[]
    for dd in (False,True):
        records=[r for r in raw['records'] if r['role']!='calibration' and r['dd']==dd and r['U']==8]
        assert len(records)==4
        sums=np.zeros((36,3)); shots=0
        for rec in records:
            mask=sum(int(v)<<q for q,v in enumerate(rec['readout_mask_little_endian']))
            for string in rec['bitstrings']:
                value=int(string,2)^mask; shots+=1
                for site in range(36):
                    up=(value>>(2*site))&1; down=(value>>(2*site+1))&1
                    sums[site]+=(up+down,up-down,up*down)
        row=next(r for r in summary['target_rows'] if r['dd']==dd and r['arm']=='raw')
        counts_delta=max(counts_delta,float(np.max(np.abs(sums/shots-np.array(row['physical_charge_spin_doublon'])))))
        tflo=next(r for r in summary['target_rows'] if r['dd']==dd and r['arm']=='readout_tflo')
        points=np.array(read(RUN/'analysis/calibration_and_points.json')['raw_readout_point_paulis'])
        beta=np.array(summary['fit_coefficients'])[int(dd)]
        p=beta[:,0]*points[int(dd),:6,1].mean(0)+beta[:,1]
        zup,zdown=p[:72:2],p[1:72:2]
        physical=np.stack((1-(zup+zdown)/2,(zdown-zup)/2,(1-zup-zdown+p[72:])/4),axis=-1)
        rms=np.sqrt(np.mean((physical-reference)**2,axis=0))
        gain=next(g for g in summary['gain_diagnostics'] if g['dd']==dd and g['comparator']=='fit_without_target_hardware_input')
        null_delta=max(null_delta,float(np.max(np.abs(rms-np.array(tflo['RMS_charge_spin_doublon'])-np.array(gain['gain_charge_spin_doublon'])))))
        ablations.append({'dd':dd,'RMS_without_U8_hardware_input':rms.tolist()})
    for row in summary['target_rows']:
        rms=np.sqrt(np.mean((np.array(row['physical_charge_spin_doublon'])-reference)**2,axis=0))
        rms_delta=max(rms_delta,float(np.max(np.abs(rms-np.array(row['RMS_charge_spin_doublon'])))))
    refs=read(RUN/'references.json')
    pure=np.mean([refs[f'train{i}']['physical'] for i in range(6)],axis=0)
    assert counts_delta==0 and rms_delta<1e-14 and null_delta<1e-14
    result={'job_id':raw['job_id'],'direct_integer_raw_profiles_max_abs':counts_delta,
        'independent_RMS_max_abs':rms_delta,'independent_no_target_input_comparator_max_abs':null_delta,
        'fixed_ablation_reproduced':ablations,
        'additional_posthoc_diagnostic_not_a_selected_method':{
            'name':'arithmetic mean of six exact U0 training profiles, no hardware input',
            'RMS_to_uncertified_U8_chi64':np.sqrt(np.mean((pure-reference)**2,axis=0)).tolist(),
            'N':float(pure[:,0].sum()),'not_validation_or_quantum_advantage':True},
        'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    with (RUN/'delivery_audit.json').open('x',encoding='utf-8') as f:
        json.dump(result,f,indent=2,allow_nan=False); f.write('\n')
    print(json.dumps(result),flush=True)

if __name__=='__main__': main()
