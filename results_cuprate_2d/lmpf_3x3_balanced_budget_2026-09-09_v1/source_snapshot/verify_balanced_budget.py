"""Independent KKT/complex-step covariance and Qiskit-target timing verification."""
from pathlib import Path
import argparse,hashlib,json,sys,time
import numpy as np
from scipy.linalg import block_diag
from qiskit import qpy
from qiskit.circuit import Measure,Parameter
from qiskit.circuit.library import XGate,SXGate,CZGate,RZGate
from qiskit.transpiler import Target,InstructionProperties
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
L=np.array([[-.5,-.5,0],[-.5,.5,0],[-.25,-.25,.25]])
BITS=np.array([[i%2,i//2] for i in range(4)])
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def oracle(n,e,masks,grams,q):
    dtype=np.result_type(e,float);single=[]
    for i in range(2):single.append(np.array([[1-e[0,i],e[1,i]],[e[0,i],1-e[1,i]]]))
    assignment=np.kron(single[1],single[0]);h=[];penalties=[]
    for mask in masks:
        z=1-2*(BITS^mask);features=np.column_stack([z,z[:,0]*z[:,1]])
        scores=np.linalg.solve(assignment.T,features)
        hi=np.argmax(scores.real,axis=0);lo=np.argmin(scores.real,axis=0)
        penalty=(scores[hi,range(3)]-scores[lo,range(3)])**2/(4*n)
        h.append(scores);penalties.append(penalty)
    h=np.asarray(h);penalties=np.asarray(penalties).T
    weights=[]
    for o in range(3):
        kkt=np.zeros((4,4),dtype=dtype)
        kkt[:3,:3]=grams[o,1:,1:]+np.diag(penalties[o]);kkt[3,:3]=1;kkt[:3,3]=1
        rhs=np.r_[grams[o,1:,0],1]
        weights.append(np.linalg.solve(kkt,rhs)[:3])
    weights=np.asarray(weights);maps=np.zeros((4,3,16),dtype=dtype)
    rawz=1-2*(BITS^masks[0]);raw=np.column_stack([rawz,rawz[:,0]*rawz[:,1]])
    for s,f in ((0,1/3),(1,2/3)):
        maps[0,:,4*s:4*s+4]=f*raw.T
        maps[1,:,4*s:4*s+4]=f*h[0].T
    for a,s in enumerate((0,2,3)):
        maps[2,:,4*s:4*s+4]=[4/3,1/3,-2/3][a]*h[a].T
        maps[3,:,4*s:4*s+4]=np.diag(weights[:,a])@h[a].T
    transfer=np.concatenate([L@x for x in maps],axis=0)
    mean=np.tile([1,0,.25],4)+transfer@q[[0,0,1,2]].ravel()
    sizes=[n,2*n,n,n]
    fcov=block_diag(*[(np.diag(p)-np.outer(p,p))/s for p,s in zip(q[[0,0,1,2]],sizes)])
    return mean,transfer@fcov@transfer.T,weights,penalties,transfer

def complex_jacobian(n,e,masks,grams,q):
    columns=[]
    for i in range(4):
        perturbed=e.astype(complex);perturbed.flat[i]+=1e-20j
        columns.append(oracle(n,perturbed,masks,grams,q)[0].imag/1e-20)
    return np.column_stack(columns)

def offline_target(props):
    target=Target(num_qubits=len(props['qubits']))
    factors={'s':1,'ms':.001,'us':.000001,'ns':.000000001,'ps':.000000000001}
    gates={'x':XGate(),'sx':SXGate(),'cz':CZGate(),'rz':RZGate(Parameter('theta')),'measure':Measure()}
    for name,gate in gates.items():
        mapping={}
        if name=='rz':mapping={(q,):InstructionProperties(duration=0) for q in range(len(props['qubits']))}
        elif name=='measure':
            for q,vals in enumerate(props['qubits']):
                r=next(r for r in vals if r['name']=='readout_length')
                mapping[(q,)]=InstructionProperties(duration=r['value']*factors[r['unit']])
        else:
            for entry in props['gates']:
                if entry['gate']!=name:continue
                r=next(r for r in entry['parameters'] if r['name']=='gate_length')
                mapping[tuple(entry['qubits'])]=InstructionProperties(duration=r['value']*factors[r['unit']])
                if name=='cz':mapping[tuple(entry['qubits'][::-1])]=mapping[tuple(entry['qubits'])]
        target.add_instruction(gate,mapping)
    return target

def verify(out):
    start=time.monotonic();dest=out/'verification';dest.mkdir(exist_ok=False)
    plan,summary,inputs=[read(out/name) for name in ('plan.json','summary.json','forecast_inputs.json')]
    if (plan['schema'],plan['backend'],plan['twirl'],plan['n_candidates'])!=(
        'offline-balanced-3x3-budget-v1','ibm_phoenix',1,[64,128,256,512]):raise ValueError('Wrong budget scope')
    if plan['calibration_per_state']!=256 or plan['proposed_cap_seconds']!=5:raise ValueError('Changed candidate design')
    if any(plan[k] for k in ('authorization','fresh_backend_verified','new_qpu_seconds','new_tn_states')):
        raise ValueError('Unauthorized resource scope')
    for name,h in read(out/'sha256.json').items():
        if digest(out/name)!=h:raise ValueError('Changed output')
    for name,h in plan['source_sha256'].items():
        if digest(ROOT/name)!=h or digest(out/'source_snapshot'/Path(name).name)!=h:raise ValueError('Changed source')
    for name,h in plan['input_sha256'].items():
        if digest(ROOT/name)!=h:raise ValueError('Changed source input')
    archive=ROOT/'results_cuprate_2d/hardware_readout_cz_folding_3x3_2026-09-06'
    target=offline_target(read(archive/'live_backend_properties.json'));timings=[]
    for record,i in zip(inputs['timing'],(0,1,25,19,2)):
        path=archive/'provider_inputs'/f'circuit_{i:03d}.qpy'
        if digest(path)!=record['qpy_sha256']:raise ValueError('Changed provider circuit')
        with path.open('rb') as f:qc=qpy.load(f)[0]
        elapsed=qc.estimate_duration(target,unit='s')
        np.testing.assert_allclose(elapsed,record['circuit_seconds'],atol=1e-12,rtol=0)
        if qc.depth()!=record['depth'] or qc.count_ops().get('cz',0)!=record['cz']:raise ValueError('Changed circuit')
        timings.append(float(elapsed))
    wparent=ROOT/'results_cuprate_2d/lmpf_3x3_twirl1_hardware_2026-09-09_v1'
    frozen=read(wparent/'frozen_weights.json')
    for key in ('grams','low_grams'):np.testing.assert_array_equal(inputs[key],frozen[key])
    truth=np.array(frozen['calibration_errors']);masks=np.array(frozen['masks'])[[0,2,3]]
    np.testing.assert_array_equal(truth,inputs['assumed_true_calibration_errors'])
    np.testing.assert_array_equal(masks,inputs['masks'])
    model=read(ROOT/'results_cuprate_2d/lmpf_3x3_twirl1_noise_model_2026-09-09_v2/model_predictions.json')
    matrices=[np.array([[1-truth[0,i],truth[1,i]],[truth[0,i],1-truth[1,i]]]) for i in range(2)]
    assignment=np.kron(matrices[1],matrices[0]);q=[]
    for a,(z,d,zz) in enumerate(model['pauli_means'][1:]):
        signs=1-2*BITS;p=(1+signs[:,0]*z+signs[:,1]*d+np.prod(signs,axis=1)*zz)/4
        q.append(assignment@p[np.arange(4)^(int(masks[a,0])+2*int(masks[a,1]))])
    q=np.asarray(q);np.testing.assert_allclose(q,inputs['noise_model_measured_probabilities'],atol=1e-14,rtol=0)
    center=(256*truth+.5)/257;var=256*truth*(1-truth)/257**2
    np.testing.assert_allclose(center,inputs['future_calibration_expansion_center'],atol=1e-15,rtol=0)
    grams=np.asarray(inputs['grams']);low=np.asarray(inputs['low_grams'])
    maximum={'weights':0.,'mean':0.,'shot_covariance':0.,'jacobian':0.,'total_covariance':0.};passed=[]
    with np.load(out/'forecast_covariance.npz',allow_pickle=False) as data:
        for n,rec in zip((64,128,256,512),summary['cases']):
            if rec['n_per_folded_factor']!=n or rec['strata_shots']!=[n,2*n,n,n]:raise ValueError('Changed strata')
            if (rec['total_union_shots'],rec['primary_target_shots'],rec['primary_with_calibration'])!=(5*n+512,3*n,3*n+512):
                raise ValueError('Unmatched budget')
            mean,shot,w,p,transfer=oracle(n,center,masks,grams,q)
            loww=oracle(n,center,masks,low,q)[2];change=abs(w-loww).sum(1)
            j=complex_jacobian(n,center,masks,grams,q)
            cal=(j*var.ravel())@j.T;total=shot+cal
            for key,value,saved in (('weights',w,rec['weights']),('mean',mean,rec['projected_model_physical_means']),
                ('shot_covariance',shot,data[f'n{n}_shot_covariance']),('jacobian',j,data[f'n{n}_jacobian']),
                ('total_covariance',total,data[f'n{n}_total_covariance'])):
                arr=np.asarray(saved).reshape(value.shape);err=float(abs(value-arr).max());maximum[key]=max(maximum[key],err)
                np.testing.assert_allclose(value,arr,atol=2e-7 if key=='jacobian' else 1e-9,rtol=0)
            np.testing.assert_allclose(p,rec['penalties'],atol=1e-12,rtol=0)
            np.testing.assert_allclose(loww,rec['low_weights'],atol=1e-11,rtol=0)
            np.testing.assert_allclose(change,rec['chi_coefficient_l1_changes'],atol=1e-11,rtol=0)
            np.testing.assert_allclose(w.sum(1),1,atol=1e-12,rtol=0)
            np.testing.assert_allclose(transfer,data[f'n{n}_scores'].transpose(2,0,1).reshape(12,16),atol=1e-11,rtol=0)
            np.testing.assert_allclose(cal,data[f'n{n}_calibration_covariance'],atol=1e-9,rtol=0)
            for value,key in ((shot,'shot_only_sd'),(cal,'calibration_delta_sd'),(total,'shot_plus_first_order_calibration_sd')):
                np.testing.assert_allclose(np.sqrt(np.diag(value)).reshape(4,3),rec[key],atol=1e-8,rtol=0)
            for name,k in (('readout',1),('zne',2)):
                cov=total[9:12,9:12]+total[3*k:3*k+3,3*k:3*k+3]-total[9:12,3*k:3*k+3]-total[3*k:3*k+3,9:12]
                np.testing.assert_allclose(np.sqrt(np.diag(cov)),rec['paired_lmpf_minus_baseline_sd'][name],atol=1e-8,rtol=0)
            flag=bool(np.all(change<=.05))
            if flag!=rec['archived_coefficient_flag_pass']:raise ValueError('Wrong coefficient flag')
            counts=[256,256,3*n,n,n]
            for delay,key,estkey in ((inputs['rep_delay_seconds'],'shot_execution_seconds','estimated_qpu_seconds_by_subjobs'),
                        (250e-6,'execution_seconds_rep250us_sensitivity','rep250us_qpu_seconds_by_subjobs')):
                cost=sum(k*(t+inputs['reset_seconds']+delay) for k,t in zip(counts,timings))
                np.testing.assert_allclose(cost,rec[key],atol=1e-12,rtol=0)
                for jobs in (1,2,3):np.testing.assert_allclose(2*jobs+cost,rec[estkey][str(jobs)],atol=1e-12,rtol=0)
            if flag and rec['estimated_qpu_seconds_by_subjobs']['2']<5 and rec['rep250us_qpu_seconds_by_subjobs']['2']<5:passed.append(n)
    if summary['candidate_n_under_planning_rule']!=(max(passed) if passed else None):raise ValueError('Wrong suggested candidate')
    if any(summary[k] for k in ('new_qpu_seconds','hardware_submission_ready','authorization','six_by_six_go')):raise ValueError('Unsupported hardware go')
    report={'status':'BALANCED_BUDGET_KKT_COMPLEX_STEP_AND_QISKIT_AUDIT_PASSED',
        'cases_checked':4,'covariance_dimensions':[12,12],'qpy_circuits_checked':5,
        'maximum_differences':maximum,'candidate_n_verified':summary['candidate_n_under_planning_rule'],
        'matching_shot_and_shared_calibration_verified':True,'new_qpu_seconds':0,'authorization':False,'seconds':time.monotonic()-start}
    with (dest/'verification.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path)
    with threadpool_limits(limits=1):verify(p.parse_args().output)
