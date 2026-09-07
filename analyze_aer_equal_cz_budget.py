"""Offline post-hoc equal-CZ-budget analysis; never executes a quantum circuit."""
from __future__ import annotations
import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import io
import json
from pathlib import Path
import shutil
import time
import unittest
import numpy as np
import qiskit
from qiskit import qpy

ROOT=Path(__file__).resolve().parent
PARENT=ROOT/'results_cuprate_2d/aer_nighthawk_cz_zne_bitshots512_v2'
SOURCES=['analyze_aer_equal_cz_budget.py','test_aer_equal_cz_budget.py','AER_EQUAL_CZ_BUDGET_PROTOCOL.md']
SIZES=(30,34,5,8)
ALLOCATION=(30,5,8)
METHODS=['raw512','linear_zne344_primary','quadratic_zne344_secondary']
WEIGHTS=np.array([[30/64,34/64,0.,0.],[4/3,0.,1/3,-2/3],[3.,0.,-3.,1.]])
METRICS=['charge_rmse','spin_rmse','doublon_rmse','spin_contrast']

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def write(path,value):
    Path(path).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def verify_manifest(folder,name):
    folder=Path(folder).resolve()
    for relative,expected in read(folder/name).items():
        actual=(folder/relative).resolve()
        if not actual.is_relative_to(folder) or digest(actual)!=expected:
            raise ValueError(f'Unsafe/changed archive entry {relative}')
    return len(read(folder/name))

def allocation(budget=64):
    if not isinstance(budget,int) or budget<6:
        raise ValueError('Positive integer budget must support all three factors')
    candidates=[]
    for n2 in range(1,budget//2+1):
        for n3 in range(1,budget//3+1):
            n1=budget-2*n2-3*n3
            if n1>0:
                counts=(n1,n2,n3)
                score=sum(Fraction(w,n) for w,n in zip((16,1,4),counts))
                candidates.append((score,counts))
    score,counts=min(candidates)
    return counts,score,len(candidates)

def split_groups(groups):
    if [np.shape(x) for x in groups]!=[(8,64,27),(8,9,27),(8,18,27)]:
        raise ValueError('Unexpected parent factor shapes')
    return [groups[0][:,:30],groups[0][:,30:],groups[1][:,:5],groups[2][:,:8]]

def arm_means(source,raw_counts=(30,34)):
    if np.shape(source)[-2:]!=(4,27) or min(raw_counts)<=0:
        raise ValueError('Require four stratum means and positive raw counts')
    weights=WEIGHTS.copy()
    weights[0,:2]=np.asarray(raw_counts)/sum(raw_counts)
    return np.einsum('ms,...sp->...mp',weights,np.asarray(source))

def physical(paulis):
    p=np.asarray(paulis)
    if p.shape[-1]!=27:
        raise ValueError('Require18 Z plus9 ZZ')
    up,down,zz=p[...,:18:2],p[...,1:18:2],p[...,18:]
    return np.stack([1-(up+down)/2,(down-up)/2,(1-up-down+zz)/4],axis=-1)

def metrics(paulis,exact):
    obs,target=physical(paulis),physical(exact)
    denominator=np.sum(target[:,1]**2)
    if denominator<=1e-14:
        raise ValueError('Undefined spin contrast')
    rmse=np.sqrt(np.mean((obs-target)**2,axis=-2))
    g=np.sum(obs[...,1]*target[:,1],axis=-1)/denominator
    return np.concatenate([rmse,g[...,None]],axis=-1)

def benefits(values):
    if np.shape(values)[-2:]!=(3,4):
        raise ValueError('Require three methods by four metrics')
    v=np.asarray(values)
    return np.concatenate([v[...,0,:3]-v[...,1,:3],
                           (v[...,1,3]-v[...,0,3])[...,None]],axis=-1)

def bootstrap(strata,repetitions=2000,seed=2027700000):
    if [np.shape(x) for x in strata]!=[(8,n,27) for n in SIZES]:
        raise ValueError('Unexpected equal-cost strata')
    rng=np.random.default_rng(seed)
    draws=np.empty((repetitions,4,27))
    for b in range(repetitions):
        for k,(data,n) in enumerate(zip(strata,SIZES)):
            selected=rng.integers(0,n,(8,n))
            draws[b,k]=data[np.arange(8)[:,None],selected].mean(axis=(0,1))
    return draws

def ci(data):
    return {'low':np.quantile(data,.025,axis=0).tolist(),
            'high':np.quantile(data,.975,axis=0).tolist()}

def ranges(paulis):
    p=np.asarray(paulis)
    up,down,zz=p[:18:2],p[1:18:2],p[18:]
    probs=np.stack([(1+up+down+zz)/4,(1-up+down-zz)/4,
                    (1+up-down-zz)/4,(1-up-down+zz)/4],axis=-1)
    return {'min_two_mode_probability':float(probs.min()),
            'negative_two_mode_probabilities':int(np.sum(probs < -1e-10)),
            'paulis_outside_range':int(np.sum(np.abs(p)>1+1e-10)),
            'max_abs_pauli':float(np.max(np.abs(p))),'clipped':False}

def load_parent(parent_plan):
    groups,bitgroups,selections=[],[],[]
    direct_error=0.
    for g,n in enumerate((64,9,18)):
        blocks,bitblocks=[],[]
        for t in range(8):
            record_path=PARENT/'blocks'/f'{g}_{t}'/'record.json'
            raw_path=PARENT/'blocks'/f'{g}_{t}'/'aer_result.json'
            rec,raw=read(record_path),read(raw_path)
            exp=raw['results'][0]
            assert raw['success'] and exp['success'] and exp['shots']==n
            assert rec['group']==g and rec['twirl']==t and rec['shots']==n
            assert rec['seed']==exp['seed_simulator']==2027100000+100000*g+1000*t
            integers=[int(s,16) for s in exp['data']['memory']]
            assert len(integers)==n
            assert Counter(integers)=={int(k,16):v for k,v in exp['data']['counts'].items()}
            binary=[format(value,'018b') for value in integers]
            assert binary==rec['bitstrings']
            mask=parent_plan['records'][t]['readout_mask_little_endian']
            bits=np.array([[((v>>q)&1)^mask[q] for q in range(18)] for v in integers],dtype=float)
            np.testing.assert_array_equal(bits,rec['decoded_bits'])
            z=1-2*bits
            paulis=np.concatenate([z,z[:,::2]*z[:,1::2]],axis=1)
            np.testing.assert_array_equal(paulis,rec['pauli_samples'])
            up,down=bits[:,::2],bits[:,1::2]
            direct=np.stack([up+down,up-down,up*down],axis=-1)
            direct_error=max(direct_error,float(np.max(np.abs(direct-physical(paulis)))))
            blocks.append(paulis)
            bitblocks.append(bits)
            retained=n if g==0 else ALLOCATION[g]
            selections.append({'factor':g+1,'twirl':t,
                'parent_record':str(record_path.relative_to(ROOT)),
                'record_sha256':digest(record_path),'aer_result_sha256':digest(raw_path),
                'raw_indices':list(range(n)) if g==0 else [],
                'zne_indices':list(range(ALLOCATION[g])),
                'retained_bitstrings':binary[:retained]})
        groups.append(np.asarray(blocks))
        bitgroups.append(np.asarray(bitblocks))
    return groups,bitgroups,selections,direct_error

def cost_audit(parent_plan):
    raw,zne=Counter(),Counter()
    raw_edges,zne_edges=Counter(),Counter()
    layout=parent_plan['layout']
    assert len(layout)==len(set(layout))==18
    for g in range(3):
        for t in range(8):
            with (PARENT/'circuits'/f'{g}_{t}.qpy').open('rb') as handle:
                circuit=qpy.load(handle)[0]
            counts=circuit.count_ops()
            assert counts['cz']==1008*(g+1) and counts['measure']==18
            for name,count in counts.items():
                if g==0:
                    raw[name]+=64*count
                zne[name]+=ALLOCATION[g]*count
            for item in circuit.data:
                if item.operation.name=='cz':
                    qs=tuple(layout[circuit.find_bit(q).index] for q in item.qubits)
                    if g==0:
                        raw_edges[qs]+=64
                    zne_edges[qs]+=ALLOCATION[g]
    assert raw_edges==zne_edges and raw['cz']==zne['cz']==516096
    for name in ('x','sx','rz','measure'):
        assert zne[name]*64==raw[name]*43
    return {'raw_native_applications':dict(raw),'zne_native_applications':dict(zne),
        'identical_cz_counts_every_ordered_physical_support':True,
        'cz_supports':[{'physical_qubits':list(q),'raw':raw_edges[q],'zne':zne_edges[q]}
                       for q in sorted(raw_edges)],
        'raw_shots':512,'zne_shots':344,'selected_existing_union_bitshots':616,
        'shared_existing_bitshots':240,'unused_parent_bitshots_preserved':112,
        'new_executed_shots':0,'new_qpu_seconds':0,'equal_wall_time_claim':False}

def analyze(out):
    if out.exists():
        raise ValueError('Refuse overwrite or repeated selection')
    started=time.perf_counter()
    alloc,score,candidate_count=allocation()
    assert alloc==ALLOCATION and str(score)=='37/30'
    assert allocation(32)[0]==(14,3,4)
    parent_verified=verify_manifest(PARENT,'final_archive_sha256.json')
    parent_plan=read(PARENT/'plan.json')
    input_paths=[ROOT/name for name in SOURCES]+[PARENT/'final_archive_sha256.json',PARENT/'plan.json']
    input_paths += [PARENT/'blocks'/f'{g}_{t}'/file
                    for g in range(3) for t in range(8) for file in ('record.json','aer_result.json')]
    input_paths += [PARENT/'circuits'/f'{g}_{t}.qpy' for g in range(3) for t in range(8)]
    locked={str(p.relative_to(ROOT)):digest(p) for p in input_paths}
    out.mkdir(parents=True)
    (out/'source_snapshot').mkdir()
    for name in SOURCES:
        shutil.copyfile(ROOT/name,out/'source_snapshot'/name)
    write(out/'plan.json',{'schema':'exploratory-equal-cz-budget-v1','parent':str(PARENT.relative_to(ROOT)),
        'parent_files_verified':parent_verified,'setting':parent_plan['setting'],'layout':parent_plan['layout'],
        'allocation_per_twirl':alloc,'stratum_sizes':SIZES,'raw_shots':512,'zne_shots':344,
        'cz_applications_each_arm':516096,'coefficient_only_objective':str(score),
        'integer_candidates_checked':candidate_count,'bootstrap_seed':2027700000,
        'bootstrap_repetitions':2000,'exploratory_posthoc':True,'independent_replication':False,
        'selection_adjusted_inference':False,'new_shots':0,'new_qpu_seconds':0,
        'numpy_version':np.__version__,'qiskit_version':qiskit.__version__,'input_sha256':locked})
    log=io.StringIO()
    tests=unittest.TextTestRunner(stream=log,verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromName('test_aer_equal_cz_budget'))
    if not tests.wasSuccessful():
        (out/'FAILED_TESTS.txt').write_text(log.getvalue(),encoding='utf-8')
        raise AssertionError(log.getvalue())
    groups,bits,selections,error=load_parent(parent_plan)
    assert error<1e-12
    strata=split_groups(groups)
    mean=np.stack([x.mean(axis=(0,1)) for x in strata])
    methods=arm_means(mean)
    np.testing.assert_allclose(methods[0],groups[0].mean(axis=(0,1)),atol=1e-14,rtol=0)
    exact=np.asarray(parent_plan['setting']['reference'])
    source_draws=bootstrap(strata)
    draws=arm_means(source_draws)
    values=metrics(methods,exact)
    value_draws=metrics(draws,exact)
    gain=benefits(values)
    gain_draws=benefits(value_draws)
    # Independent occupations, without using physical(Pauli).
    bs=[bits[0][:,:30],bits[0][:,30:],bits[1][:,:5],bits[2][:,:8]]
    direct=[]
    for sample in bs:
        u,d=sample[...,::2],sample[...,1::2]
        direct.append(np.stack([u+d,u-d,u*d],axis=-1).mean(axis=(0,1)))
    expected=np.stack([(30*direct[0]+34*direct[1])/64,
        (4*direct[0]+direct[2]-2*direct[3])/3,3*direct[0]-3*direct[2]+direct[3]])
    arm_error=float(np.max(np.abs(expected-physical(methods))))
    assert arm_error<1e-12
    fitted=np.linalg.lstsq(np.column_stack([np.ones(3),[1.,2.,3.]]),mean[[0,2,3]],rcond=None)[0][0]
    np.testing.assert_allclose(fitted,methods[1],atol=1e-12,rtol=0)
    # Independent spin-CI reconstruction from source bootstrap vectors.
    ss=(source_draws[...,1:18:2]-source_draws[...,0:18:2])/2
    raw_spin=(30*ss[:,0]+34*ss[:,1])/64
    zne_spin=(4*ss[:,0]+ss[:,2]-2*ss[:,3])/3
    target=(exact[1:18:2]-exact[0:18:2])/2
    independent_gain=np.sqrt(np.mean((raw_spin-target)**2,axis=-1))-np.sqrt(np.mean((zne_spin-target)**2,axis=-1))
    np.testing.assert_allclose(independent_gain,gain_draws[:,1],atol=1e-13,rtol=0)
    gvars=np.array([metrics(s,exact)[...,3].var(axis=1,ddof=1).sum()/(64*s.shape[1]) for s in strata])
    gcov=WEIGHTS@np.diag(gvars)@WEIGHTS.T
    half=[s[:,:n] for s,n in zip(strata,(14,18,3,4))]
    half_values=metrics(arm_means(np.stack([s.mean(axis=(0,1)) for s in half]),(14,18)),exact)
    cost=cost_audit(parent_plan)
    result={'schema':'equal-cz-budget-result-v1','exploratory_posthoc':True,
        'methods':METHODS,'metric_order':METRICS,'stratum_means':mean.tolist(),
        'method_means':methods.tolist(),'physical_means':physical(methods).tolist(),
        'metrics':values.tolist(),'metric_ci95':ci(value_draws),
        'benefit_order':['charge_rmse_reduction','spin_rmse_reduction','doublon_rmse_reduction','spin_contrast_increase'],
        'primary_benefits':gain.tolist(),'primary_benefit_ci95':ci(gain_draws),
        'relative_spin_rmse_reduction':float(gain[1]/values[0,1]),
        'relative_spin_rmse_reduction_ci95':ci(gain_draws[:,1]/value_draws[:,0,1]),
        'conditional_not_selection_adjusted_ci':True,
        'predicted_g_covariance':gcov.tolist(),'bootstrap_g_covariance':np.cov(value_draws[:,:,3].T).tolist(),
        'g_standard_error_ratio_zne_raw':float(np.sqrt(gcov[1,1]/gcov[0,0])),
        'ranges':{name:ranges(methods[m]) for m,name in enumerate(METHODS)},
        'half_budget_diagnostic':{'cz_each_arm':258048,'raw_shots':256,'zne_shots':168,
            'allocation_per_twirl':[14,3,4],'metrics':half_values.tolist(),'not_convergence_proof':True},
        'bootstrap_resolution':{str(n):ci(gain_draws[:n]) for n in (500,1000,2000)},
        'cost':cost,'new_shots':0,'new_qpu_seconds':0}
    write(out/'selected_bitstrings.json',{'selection':'Fixed positional prefixes','records':selections})
    write(out/'results.json',result)
    np.savez_compressed(out/'bootstrap_draws.npz',stratum_means=source_draws,method_means=draws)
    (out/'unit_tests.txt').write_text(log.getvalue(),encoding='utf-8')
    verification={'status':'PASS','unit_tests':tests.testsRun,'direct_bit_physical_error':error,
        'independent_arm_physical_error':arm_error,'independent_ols_match':True,
        'independent_primary_spin_ci':ci(independent_gain),
        'exact_per_support_cz_cost_match':True,'parent_hashes_verified':parent_verified,
        'new_shots':0,'new_qpu_seconds':0,'independent_replicate':False}
    write(out/'verification.json',verification)
    rel_ci=result['relative_spin_rmse_reduction_ci95']
    lo,hi=result['primary_benefit_ci95']['low'][1],result['primary_benefit_ci95']['high'][1]
    lines=['# ZNE bij gelijk CZ-budget: verkennende heranalyse','',
        'Dit hergebruikt de eerder bekeken bitshots. Het is geen nieuwe, onafhankelijke proef.',
        'De shotverdeling is op de kostenformule gekozen, niet op de prestaties van subsets.','',
        '| Grootheid | Zonder ZNE: 512 shots | Lineaire ZNE: 344 shots |',
        '|---|---:|---:|']
    for j,name in enumerate(['Lading-RMSE','Spin-RMSE','Doublon-RMSE','Spincontrast g']):
        lines.append(f'| {name} | {values[0,j]:.5f} | {values[1,j]:.5f} |')
    lines += ['',f'Spin-RMSE-afname: {gain[1]:.5f}; voorwaardelijk 95%-interval [{lo:.5f}, {hi:.5f}].',
        f'Relatieve puntinschatting: {100*result["relative_spin_rmse_reduction"]:.1f}% minder spinfout;',
        f'interval [{100*rel_ci["low"]:.1f}%, {100*rel_ci["high"]:.1f}%].',
        ('Het interval ligt boven nul binnen deze vaste subset- en modelanalyse.'
         if lo>0 else 'Het interval ondersteunt bij dit budget geen eenduidige positieve spinverbetering.'),
        'Deze intervallen zijn niet gecorrigeerd voor eerdere analyses en zijn geen bevestiging',
        'door een onafhankelijke herhaling. Extrapolatiebias en modelonzekerheid ontbreken.','',
        '## Kosten en selectie','',
        'Beide armen: exact 516.096 CZ-applicaties, ook gelijk per fysieke geordende koppeling.',
        'ZNE gebruikt factoren 1/2/3 met respectievelijk 240/40/64 shots: totaal 344.',
        'De eerste 240 factor-1-shots zijn gedeeld met raw512; die correlatie zit in de bootstrap.',
        'De unieke geselecteerde deelverzameling bevat 616 bestaande bitstrings.',
        'De overige 112 parent-bitstrings blijven ongewijzigd bewaard.',
        'ZNE heeft 43/64 van de eenqubitgate- en meetcounts van raw512.',
        'Gelijk CZ-budget is niet bewezen gelijke wandklok- of gefactureerde QPU-tijd.',
        'Aan deze heranalyse wordt geen deel van oude simulatietijden als nieuwe meting toegekend.',
        'Nieuwe shots: 0. Nieuwe QPU-seconden: 0.','',
        '## Controles en beperkingen','',
        f'{tests.testsRun} deterministische tests geslaagd; geen quantumcircuit uitgevoerd.',
        f'Onafhankelijke bit-naar-observabelefout {error:.3g}; armreconstructiefout {arm_error:.3g}.',
        'Alle parent-hashes, ruwe hexdata, tellingen, maskers en selectie-indices gecontroleerd.',
        'De lineaire extrapolatie en de primaire foutmarge zijn onafhankelijk nagerekend.',
        f'Spincontrast-standaardfout ZNE/raw: {result["g_standard_error_ratio_zne_raw"]:.2f}.',
        f'Negatieve lokale kansen in primaire puntschatting: {result["ranges"][METHODS[1]]["negative_two_mode_probabilities"]}; geen clipping.',
        f'Kwadratisch geeft spin-RMSE {values[2,1]:.5f} en blijft alleen een gevoeligheidscheck.',
        'De halve-budgetsubset is geen onafhankelijke herhaling of convergentieverklaring.',
        'Dit is dezelfde 3x3, 18-mode Hubbard-instantie, U/t=8, T=0.4, twee Trotterstappen.',
        'De referentie is het ideale eindige circuit; geen extra claim over Trotterfout.',
        'Spin is n_up-n_down=2*S_z. g is geen fidelity.',
        'Het approximate Aer-model mist onder meer idle-gap-ruis, coherente/contextuele fouten,',
        'crosstalk, leakage, preparatiefouten en drift. Geen hardware- of quantum-advantagebewijs.',
        'Protocol, broncode, volledige foutmarges en exacte selectie zijn in dit archief bewaard.','']
    (out/'BEVINDINGEN.md').write_text('\n'.join(lines),encoding='utf-8')
    for relative,sha in locked.items():
        if digest(ROOT/relative)!=sha:
            raise ValueError('Input/source changed during analysis')
    verify_manifest(PARENT,'final_archive_sha256.json')
    write(out/'COMPLETION.json',{'status':'COMPLETE_EXPLORATORY_EQUAL_CZ_REANALYSIS',
        'verification':verification,'analysis_wall_seconds':time.perf_counter()-started,
        'new_shots':0,'new_qpu_seconds':0})
    write(out/'final_archive_sha256.json',{str(p.relative_to(out)):digest(p)
        for p in out.rglob('*') if p.is_file()})
    print(json.dumps({'metrics':values.tolist(),'benefits':gain.tolist(),
        'benefit_ci95':result['primary_benefit_ci95'],
        'relative_spin_reduction':result['relative_spin_rmse_reduction'],
        'relative_ci95':rel_ci,'g_se_ratio':result['g_standard_error_ratio_zne_raw'],
        'tests':tests.testsRun,'posthoc':True,'new_shots':0,'new_qpu_seconds':0}),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    analyze(args.output.resolve())
