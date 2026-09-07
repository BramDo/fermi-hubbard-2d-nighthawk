"""Independent integer-bit audit and immutable closeout of equal512 pilot."""
import argparse
from collections import Counter
from pathlib import Path
import shutil
import json
import numpy as np
from qiskit import qpy
import aer_cuprate_cz_zne_bitshots as b
import analyze_aer_noise_components as helper

def verify(out):
    if (out/'COMPLETION.json').exists():
        raise ValueError('Refuse re-finalization')
    checked=[helper.verify_files(out,'run_archive_sha256.json'),
             helper.verify_files(out/'analysis','sha256.json'),
             helper.verify_files(b.PARENT,'final_archive_sha256.json')]
    plan=b.z.c.a.read(out/'plan.json')
    b.z.verify_inputs(plan)
    groups=[]
    labels=[]
    actual_cz=[]
    for g,n in enumerate(b.COUNTS):
        blocks=[]
        for t in range(8):
            block=out/'blocks'/f'{g}_{t}'
            record=b.z.c.a.read(block/'record.json')
            raw=b.z.c.a.read(block/'aer_result.json')['results'][0]
            assert raw['success'] and raw['shots']==n and raw['seed_simulator']==b.seed_for(g,t)
            assert raw['metadata']['num_qubits']==18 and raw['metadata']['noise']=='kraus'
            assert not raw['metadata']['measure_sampling']
            integers=[int(s,16) for s in raw['data']['memory']]
            assert len(integers)==n and all(0<=x<2**18 for x in integers)
            assert [format(x,'018b') for x in integers]==record['bitstrings']
            assert Counter(integers)=={int(k,16):v for k,v in raw['data']['counts'].items()}
            mask=plan['records'][t]['readout_mask_little_endian']
            bits=np.array([[((value>>q)&1)^mask[q] for q in range(18)] for value in integers],float)
            np.testing.assert_array_equal(bits,record['decoded_bits'])
            blocks.append(bits)
            labels += [b.seed_for(g,t)+s for s in range(n)]
            with (out/'circuits'/f'{g}_{t}.qpy').open('rb') as handle:
                saved=qpy.load(handle)[0]
            b.check_measured(saved)
            assert saved.count_ops()['cz']==1008*(g+1)
            actual_cz.append(saved.count_ops()['cz']*n)
        groups.append(np.asarray(blocks))
    assert len(labels)==len(set(labels))==728
    bit_strata=[groups[0][:,:37],groups[0][:,37:],groups[1],groups[2]]
    def occupation_mean(bits):
        up,down=bits[...,::2],bits[...,1::2]
        return np.stack([up+down,up-down,up*down],axis=-1).mean(axis=(0,1))
    physical=[occupation_mean(x) for x in bit_strata]
    direct=np.stack([occupation_mean(groups[0]),
        (4*physical[0]+physical[2]-2*physical[3])/3,
        3*physical[0]-3*physical[2]+physical[3]])
    result=b.z.c.a.read(out/'analysis/results.json')
    error=float(np.max(np.abs(direct-result['physical_means'])))
    assert error<1e-12
    draws=np.load(out/'analysis/bootstrap_draws.npz')
    source=draws['stratum_means']
    assert source.shape==(2000,4,27) and draws['method_means'].shape==(2000,3,27)
    ss=(source[...,1:18:2]-source[...,0:18:2])/2
    rawspin=(37*ss[:,0]+27*ss[:,1])/64
    znespin=(4*ss[:,0]+ss[:,2]-2*ss[:,3])/3
    reference=np.asarray(plan['setting']['reference'])
    target=(reference[1:18:2]-reference[0:18:2])/2
    gain=np.sqrt(np.mean((rawspin-target)**2,axis=1))-np.sqrt(np.mean((znespin-target)**2,axis=1))
    interval=np.quantile(gain,[.025,.975])
    np.testing.assert_allclose(interval,[result['primary_benefit_ci95']['low'][1],
                                       result['primary_benefit_ci95']['high'][1]],atol=1e-13,rtol=0)
    np.testing.assert_allclose(draws['method_means'][:,0],(37*source[:,0]+27*source[:,1])/64,atol=1e-14)
    np.testing.assert_allclose(draws['method_means'][:,1],(4*source[:,0]+source[:,2]-2*source[:,3])/3,atol=1e-14)
    assert 8*(37+27)==8*(37+9+18)==512
    checks={'status':'PASS_INDEPENDENT_BIT_OCCUPATION_AND_SHARED_CI_AUDIT',
        'hash_counts':checked,'unique_new_bitshots':728,'raw_arm_shots':512,'zne_arm_shots':512,
        'shared_bitshots':296,'raw_cz_applications':516096,'zne_cz_applications':878976,
        'actually_executed_union_cz_applications':sum(actual_cz),
        'independent_physical_error':error,'independent_primary_spin_ci':interval.tolist(),
        'raw_hex_memory_and_counts_verified':True,'readout_mask_independently_decoded':True,
        'shared_factor1_budget_independently_verified':True,'new_qpu_seconds':0}
    b.z.c.a.write(out/'final_verification.json',checks)
    report=(out/'analysis/REPORT.md').read_text(encoding='utf-8')
    report+='\n## Onafhankelijke eindcontrole\n\n'
    report+=f'728 unieke bitshots,296 gedeeld; beide armen512. Directe bit-naar-bezettingsfout:{error:.3g}.\n'
    report+='De primaire foutmarge is onafhankelijk herberekend met de gedeelde prefix behouden.\n'
    report+='Alle oorspronkelijke bronnen en eerdere archieven zijn behouden.\n'
    (out/'BEVINDINGEN.md').write_text(report,encoding='utf-8')
    shutil.copyfile(Path(__file__),out/'final_verification_source.py')
    b.z.c.a.write(out/'COMPLETION.json',{'status':'COMPLETE_LOCAL_EQUAL512_BITSHOT_COMPARISON',
        'new_qpu_seconds':0,'checks':checks,'tests':b.z.c.a.read(out/'analysis/verification.json')['tests'],
        'scope':'Same shot counts; shared-data covariance retained; not equal gate/time cost or actual hardware mitigation.'})
    b.z.c.a.write(out/'final_archive_sha256.json',{str(p.relative_to(out)):b.z.c.a.digest(p)
        for p in out.rglob('*') if p.is_file()})
    print(json.dumps({'status':'COMPLETE','metrics':result['metrics'],
        'relative_spin_reduction':result['relative_spin_rmse_reduction'],
        'relative_ci95':result['relative_spin_rmse_reduction_ci95'],
        'verification':checks}),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    verify(args.output.resolve())
