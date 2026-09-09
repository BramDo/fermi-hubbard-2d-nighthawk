"""Independent raw-TN contraction and KKT audit of twirl1 central Z_up."""
from pathlib import Path
import argparse, json, sys, time
import numpy as np
import quimb.tensor as qtn
from qiskit import qpy
from qiskit.quantum_info import Operator
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from lmpf_2d.model import digest
from lmpf_2d.tn_storage import load_tn,bounded_contract

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def kkt(gram,penalty):
    matrix=np.zeros((4,4));matrix[:3,:3]=gram[1:,1:]+np.diag(penalty)
    matrix[:3,3]=1.;matrix[3,:3]=1.
    return np.linalg.solve(matrix,np.r_[gram[1:,0],1.])[:3]

def verify(out):
    start=time.monotonic();dest=out/'verification'
    if dest.exists():raise FileExistsError('Preserve earlier audit')
    dest.mkdir();plan=read(out/'plan.json');summary=read(out/'summary.json')
    if (plan['twirl'],plan['observable'],plan['chi'],plan['shot_allocation'],plan['eta'])!=(1,8,[64,128],[43,7,14],1.):
        raise ValueError('Changed bounded scientific scope')
    if plan['process_timeout_seconds']!=600 or summary['new_states']!=8:
        raise ValueError('Changed resource scope')
    for path,h in read(out/'sha256.json').items():
        if digest(out/path)!=h:raise ValueError('Changed artifact '+path)
    for path,h in plan['source_sha256'].items():
        if digest(ROOT/path)!=h or digest(out/'source_snapshot'/Path(path).name)!=h:
            raise ValueError('Changed source '+path)
    for path,h in plan['input_sha256'].items():
        if digest(ROOT/path)!=h:raise ValueError('Changed input '+path)
    archive=ROOT/'results_cuprate_2d/hardware_readout_cz_folding_3x3_2026-09-06'
    original=read(archive/'plan.json');gate_matrices={};native_error=0.;native_gates=0
    for rec in plan['inputs']:
        path=ROOT/rec['qpy']
        if digest(path)!=rec['qpy_sha256'] or digest(archive/'bound_inputs'/path.name)!=rec['qpy_sha256']:
            raise ValueError('Changed provider/bound')
        saved=original['records'][rec['record_index']]
        if saved['twirl_id']!=1 or saved['factor']!=rec['factor'] or saved['readout_mask_little_endian']!=rec['mask']:
            raise ValueError('Wrong native record')
        with path.open('rb') as f:qc=qpy.load(f)[0]
        measured=[];ended=False
        for item in qc.data:
            op=item.operation
            if op.name=='barrier':continue
            physical=[qc.find_bit(q).index for q in item.qubits]
            if any(q not in plan['layout'] for q in physical):raise ValueError('Active extra wire')
            if op.name=='measure':
                ended=True;measured.append((physical[0],qc.find_bit(item.clbits[0]).index));continue
            if ended or op.name not in ('rz','sx','x','cz'):raise ValueError('Unexpected operation')
            key=op.name,tuple(float(v) for v in op.params)
            if key not in gate_matrices:
                u=np.asarray(Operator(op).data)
                gate_matrices[key]=float(np.max(abs(u.conj().T@u-np.eye(len(u)))))
            native_error=max(native_error,gate_matrices[key]);native_gates+=1
        if sorted(measured,key=lambda x:x[1])!=list(zip(plan['layout'],range(18))):
            raise ValueError('Measurement mapping changed')
    if native_error>1e-12:raise ValueError('Nonunitary ideal arm')
    # Exact single-Pauli identity: Tr[(U^dag Z U)^dag(U^dag Z U)]/2^18=1.
    e=np.asarray(plan['calibration_errors'])[:,0]
    penalty=1/(1-e.sum())**2/np.array([43,7,14])
    np.testing.assert_allclose(penalty,plan['penalty'],atol=1e-14,rtol=1e-13)
    results={};max_gram=0.;max_weight=0.;max_stationarity=0.;max_objective=0.;peak=0;cost=0.
    for chi in (64,128):
        saved=read(out/f'chi{chi}.json')
        states=[load_tn(out/'states'/f'obs08_chi{chi}_arm{arm}') for arm in range(4)]
        for arm,meta in enumerate(saved['states']):
            factor=max(arm,1)
            mask=next(r for r in plan['inputs'] if r['factor']==factor)['mask']
            if meta['unmask_sign']!=(-1 if mask[8] else 1) or meta['native_factor']!=factor:
                raise ValueError('Changed arm/sign')
            prefix=out/'states'/f'obs08_chi{chi}_arm{arm}'
            if digest(prefix.with_suffix('.npz'))!=meta['npz_sha256'] or digest(prefix.with_suffix('.json'))!=meta['metadata_sha256']:
                raise ValueError('Changed state')
        gram=np.empty((4,4))
        for i in range(4):
            for j in range(i,4):
                raw=states[i].H & states[j]
                reverse=qtn.TensorNetwork([t.copy() for t in reversed(raw.tensors)])
                reverse.exponent=raw.exponent
                value,info=bounded_contract(reverse)
                gram[i,j]=gram[j,i]=value
                peak=max(peak,info['max_elements']);cost=max(cost,info['estimated_flops'])
        err=float(np.max(abs(gram-np.array(saved['raw_gram']))));max_gram=max(max_gram,err)
        np.testing.assert_allclose(gram,saved['raw_gram'],atol=1e-10,rtol=1e-9)
        if np.linalg.eigvalsh(gram).min() < -1e-8 or gram[0,0]>1+1e-10:
            raise ValueError('Unphysical overlap Gram')
        fixed=gram.copy();fixed[0,0]=1.
        np.testing.assert_allclose(fixed,saved['exact_norm_gram'],atol=1e-10,rtol=1e-9)
        weights=kkt(fixed,penalty)
        max_weight=max(max_weight,float(np.max(abs(weights-saved['weights']))))
        gradient=(fixed[1:,1:]+np.diag(penalty))@weights-fixed[1:,0]
        max_stationarity=max(max_stationarity,float(np.ptp(gradient)))
        projection=1.-2*fixed[1:,0]@weights+weights@fixed[1:,1:]@weights
        variance=weights@np.diag(penalty)@weights
        got=saved['objectives']
        max_objective=max(max_objective,abs(projection-got['projection_loss']),
            abs(variance-got['conditional_sampling_variance_bound']),
            abs(projection+variance-got['surrogate_objective']))
        if abs(weights.sum()-1)>1e-12:raise ValueError('Constraint failure')
        results[str(chi)]={'raw':gram,'fixed':fixed,'weights':weights}
    low,high=results['64'],results['128']
    ratio=lambda a,b:float(np.linalg.norm(b-a)/np.linalg.norm(b))
    flags={'raw_full_gram_relative_change':ratio(low['raw'],high['raw']),
        'exact_norm_full_gram_relative_change':ratio(low['fixed'],high['fixed']),
        'G_relative_change':ratio(low['raw'][1:,1:],high['raw'][1:,1:]),
        'b_relative_change':ratio(low['raw'][1:,0],high['raw'][1:,0]),
        'shot_aware_coefficient_l1_change':float(np.linalg.norm(high['weights']-low['weights'],1))}
    flag_error=max(abs(value-summary['stability'][key]) for key,value in flags.items())
    rawpass=flags['raw_full_gram_relative_change']<=.01 and flags['shot_aware_coefficient_l1_change']<=.05
    followup=all(flags[key]<=.01 for key in ('exact_norm_full_gram_relative_change','G_relative_change','b_relative_change')) and flags['shot_aware_coefficient_l1_change']<=.05
    if rawpass!=summary['stability']['raw_flags_pass'] or followup!=summary['stability']['exact_norm_local_flags_pass']:
        raise ValueError('Acceptance classification failure')
    if max(max_gram,max_weight,max_stationarity,max_objective,flag_error)>1e-9:
        raise ValueError('Independent calculation disagreement')
    report={'status':'TWIRL1_ZUP_RAW_TN_KKT_AUDIT_PASSED',
        'independent_overlaps':20,'independent_fits':2,'native_gates_checked':native_gates,
        'unique_native_unitaries':len(gate_matrices),'maximum_native_unitarity_error':native_error,
        'maximum_gram_error':max_gram,'maximum_weight_error':max_weight,
        'maximum_projected_gradient':max_stationarity,'maximum_objective_error':max_objective,
        'maximum_stability_metric_error':flag_error,
        'largest_contraction_intermediate_elements':peak,'largest_estimated_contraction_flops':cost,
        'raw_flags_pass':bool(rawpass),'exact_norm_local_flags_pass':bool(followup),
        'hardware_accuracy_validated':False,'new_qpu_seconds':0,
        'all_source_input_output_hashes_verified':True,'seconds':time.monotonic()-start}
    with (dest/'verification.json').open('x') as f:
        json.dump(report,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(report),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('output',type=Path)
    with threadpool_limits(limits=1):verify(parser.parse_args().output)
