"""Independent standard-library check of decoded raw profiles and reported RMS."""
import hashlib,json,math
from pathlib import Path

ROOT=Path(__file__).resolve().parent
RUN=ROOT/'results_cuprate_2d/hardware_compact_tflo_2026-09-07_v1'
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    summary=read(RUN/'analysis/summary.json'); raw=read(RUN/'raw_bitstrings.json')
    refs=read(RUN/'references.json')
    classical=ROOT/'results_cuprate_2d/classical_full_6x6_mps_T04_chi64_v1/summary.json'
    target=read(classical)['result']['physical_means']
    assert digest(classical)==summary['classical_source_sha256']
    max_raw=0.; max_rms=0.; max_n=0.; checked=0
    for arm in ('original','compact'):
        counts=[[0,0,0] for _ in range(36)]; nshots=0
        for rec in raw['records']:
            if rec['arm']!=arm or rec['role']!='target': continue
            mask=sum(int(v)<<q for q,v in enumerate(rec['readout_mask_little_endian']))
            for bitstring in rec['bitstrings']:
                value=int(bitstring,2)^mask; nshots+=1
                for site in range(36):
                    up=(value>>(2*site))&1; down=(value>>(2*site+1))&1
                    counts[site][0]+=up+down; counts[site][1]+=up-down; counts[site][2]+=up*down
        assert nshots==2048
        row=next(x for x in summary['target_rows'] if x['circuit_arm']==arm and x['arm']=='raw')
        for i in range(36):
            for c in range(3): max_raw=max(max_raw,abs(counts[i][c]/nshots-row['physical_charge_spin_doublon'][i][c]))
    for row in summary['target_rows']+summary['holdout_rows']+summary['no_target_input_rows']:
        reference=refs[row['setting_id']]['physical'] if 'setting_id' in row else target
        points=row['physical_charge_spin_doublon']
        for col in range(3):
            rms=math.sqrt(math.fsum((points[i][col]-reference[i][col])**2 for i in range(36))/36)
            max_rms=max(max_rms,abs(rms-row['RMS_charge_spin_doublon'][col]))
        max_n=max(max_n,abs(math.fsum(x[0] for x in points)-row['N'])); checked+=1
    screens=[]
    for arm in ('original','compact'):
        rows=[x for x in summary['holdout_rows'] if x['circuit_arm']==arm and x['arm']=='readout_tflo']
        assert len(rows)==2
        screens.append(all(x['RMS_95pct_intervals'][1][c]<=limit for x in rows for c,limit in enumerate((.05,.05,.03))))
    assert screens==summary['holdout_screen_pass']==[False,False]
    assert max_raw<1e-12 and max_rms<1e-12 and max_n<1e-12
    result=dict(status='PASS',method='independent Python integer bit extraction and math.fsum; no NumPy or fit helper',
        raw_target_profile_max_abs=max_raw,RMS_max_abs=max_rms,N_max_abs=max_n,rows_checked=checked,
        holdout_screen_recomputed=screens,source_sha256=digest(Path(__file__)))
    with (RUN/'independent_result_verification.json').open('x',encoding='utf-8') as f: json.dump(result,f,indent=2)
    print(json.dumps(result))

if __name__=='__main__': main()
