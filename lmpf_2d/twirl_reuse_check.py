"""Offline structural/noisy-channel gate for reuse across archived twirls.

No target bitstrings, reference values, TN propagation or hardware service.
The log-determinant invariant distinguishes full surrogate channels; it is NOT
an observable-error bound or a proof that every operator differs.
"""
from pathlib import Path
import argparse, hashlib, io, json, math, shutil, sys, time, unittest
from qiskit import qpy
from threadpoolctl import threadpool_limits
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from lmpf_2d.archive_3x3 import ARCHIVE, active_circuit
from lmpf_2d.model import FrozenSurrogate, digest

TESTS = ('test_lmpf_2d','test_lmpf_hardware_inputs','test_lmpf_product',
         'test_lmpf_tn_storage','test_lmpf_canonical_chain','test_lmpf_chain_contract',
         'test_lmpf_zz_refine','test_lmpf_norm_control','test_lmpf_single_twirl',
         'test_lmpf_shot_aware','test_lmpf_twirl_reuse')
TOL = 1e-10

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def write(path,value):
    with path.open('x',encoding='utf-8') as f:
        json.dump(value,f,indent=2,allow_nan=False)
        f.write('\n')

def signatures(qc):
    result=[]
    for item in qc.data:
        op=item.operation
        if op.name not in ('rz','sx','x','cz') or op.is_parameterized():
            raise ValueError('Only bound native unitary gates')
        qs=tuple(qc.find_bit(q).index for q in item.qubits)
        if op.name=='cz':qs=tuple(sorted(qs))
        params=tuple(float(v) for v in op.params)
        if not all(math.isfinite(v) for v in params):
            raise ValueError('Nonfinite gate parameters')
        result.append((op.name,qs,params))
    return result

def per_wire_parts(rows,n):
    """Ignore only interleaving of gates on disjoint wires.

    On each wire, separate everything through its last CZ from the terminal
    one-qubit suffix. This is a necessary test for terminal-only transport,
    not a general channel-equivalence algorithm.
    """
    core=[];tails=[]
    for q in range(n):
        seq=[r for r in rows if q in r[1]]
        cut=max((i+1 for i,r in enumerate(seq) if r[0]=='cz'),default=0)
        core.append(seq[:cut]);tails.append(seq[cut:])
    return core,tails

def normalized_logdet(rows,rate,scale=1.):
    """log(abs(det(E_full)))/4**n, without constructing E_full.

    A k-qubit depolarizer has PTM eigenvalues 1 and exp(-scale*lambda)
    repeated 4**k-1 times. Embedding repeats these 4**(n-k) times.
    Unitary gates and ideal unmasking have absolute determinant one.
    """
    if not math.isfinite(scale) or scale<0:raise ValueError('Invalid scale')
    terms={}
    for name,qs,_ in rows:
        lam=rate(name,qs)
        if not math.isfinite(lam) or lam<0:raise ValueError('Invalid gate rate')
        terms.setdefault(name,[]).append(-scale*lam*(1-4.**(-len(qs))))
    parts={name:math.fsum(vals) for name,vals in terms.items()}
    return math.fsum(parts.values()),parts

def hash_rows(rows):
    return hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()

def compare(base,other,n=18):
    ca,ta=per_wire_parts(base,n);cb,tb=per_wire_parts(other,n)
    prefix=0
    for a,b in zip(base,other):
        if a!=b:break
        prefix+=1
    mismatched=[q for q in range(n) if ca[q]!=cb[q]]
    cz_same=all([r for r in ca[q] if r[0]=='cz']==[r for r in cb[q] if r[0]=='cz']
                for q in range(n))
    return {'exact_instruction_sequence_equal':base==other,
        'canonical_common_prefix_gates':prefix,
        'internal_mismatch_wires':mismatched,
        'internal_per_wire_equal':not mismatched,
        'cz_per_wire_sequence_equal':cz_same,
        'terminal_suffix_lengths_base':[len(s) for s in ta],
        'terminal_suffix_lengths_candidate':[len(s) for s in tb]}

def run(out):
    start=time.monotonic()
    if out.exists():raise FileExistsError('Preserve existing results')
    out.mkdir(parents=True);(out/'source_snapshot').mkdir()
    source_paths=[ROOT/'lmpf_2d'/n for n in ('twirl_reuse_check.py',
        'verify_twirl_reuse.py','PLAN_TWIRL_REUSE.md','archive_3x3.py','model.py')]
    source_paths += [ROOT/(n+'.py') for n in TESTS]
    for path in source_paths:shutil.copyfile(path,out/'source_snapshot'/path.name)
    sources={str(p.relative_to(ROOT)):digest(p) for p in source_paths}
    plan=read(ARCHIVE/'plan.json');receipt=read(ARCHIVE/'job_receipt.json')
    if digest(ARCHIVE/'plan.json')!=receipt['plan_sha256']:
        raise ValueError('Archive plan receipt mismatch')
    if receipt['backend']!=plan['backend'] or len(plan['layout'])!=18:
        raise ValueError('Archive backend/width mismatch')
    profile=FrozenSurrogate(ARCHIVE/'live_backend_properties.json',plan['layout'])
    if profile.backend!=plan['backend']:raise ValueError('Calibration backend mismatch')
    inputs={str(p.relative_to(ROOT)):digest(p) for p in
        (ARCHIVE/'plan.json',ARCHIVE/'job_receipt.json',profile.path)}
    write(out/'plan.json',{'schema':'twirl-reuse-gate-v1','job_id':receipt['job_id'],
        'backend':plan['backend'],'layout':plan['layout'],'source_sha256':sources,
        'input_sha256':inputs,'factors':[1,2,3],'twirls':list(range(8)),
        'new_qpu_seconds':0,'new_tn_states':0,'target_bitstrings_read':False,
        'reference_values_used':False,'logdet_tolerance':TOL,
        'scope':'necessary structural and full-surrogate-channel checks; no hardware validation'})
    stream=io.StringIO();suite=unittest.TestSuite()
    for name in TESTS:suite.addTests(unittest.defaultTestLoader.loadTestsFromName(name))
    tests=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    (out/'tests.txt').write_text(stream.getvalue(),encoding='utf-8')
    if not tests.wasSuccessful():raise RuntimeError('Tests failed')
    entries={};all_rows={}
    for index,record in enumerate(plan['records']):
        if record.get('role')!='target':continue
        factor,twirl=record['factor'],record['twirl_id']
        key=(factor,twirl)
        if key in entries:raise ValueError('Duplicate target key')
        path=ARCHIVE/'provider_inputs'/f'circuit_{index:03d}.qpy'
        bound=ARCHIVE/'bound_inputs'/path.name
        if digest(path)!=digest(bound):raise ValueError('Provider/bound mismatch')
        with path.open('rb') as f:
            circuits=qpy.load(f)
        if len(circuits)!=1:raise ValueError('Expected one provider circuit')
        qc=active_circuit(circuits[0],plan['layout']);rows=signatures(qc)
        mask=record['readout_mask_little_endian']
        if len(mask)!=18 or set(mask)-{0,1}:raise ValueError('Invalid mask')
        if qc.count_ops().get('cz')!=1008*factor:raise ValueError('CZ count mismatch')
        total,parts=normalized_logdet(rows,profile.rate)
        core,tail=per_wire_parts(rows,18)
        entries[key]={'record_index':index,'factor':factor,'twirl':twirl,
            'source_qpy':record['source_qpy'],'provider_qpy':str(path.relative_to(ROOT)),
            'provider_sha256':digest(path),'bound_sha256':digest(bound),
            'gates':dict(qc.count_ops()),'unitary_gate_count':len(rows),'depth':qc.depth(),
            'global_phase':float(qc.global_phase),'mask':mask,'signature_sha256':hash_rows(rows),
            'core_wire_sha256':[hash_rows(s) for s in core],
            'terminal_wire_sha256':[hash_rows(s) for s in tail],
            'normalized_logabsdet':total,'logdet_parts':parts}
        all_rows[key]=rows
    if set(entries)!={(f,t) for f in (1,2,3) for t in range(8)}:
        raise ValueError('Missing/extra archived target')
    comparisons=[]
    for factor in (1,2,3):
        for twirl in range(1,8):
            key=(factor,twirl);base=(factor,0)
            item=compare(all_rows[base],all_rows[key])
            delta=entries[key]['normalized_logabsdet']-entries[base]['normalized_logabsdet']
            item.update(factor=factor,twirl=twirl,normalized_logdet_delta=delta,
                full_surrogate_channel_distinguished=abs(delta)>TOL,
                terminal_only_reuse_established=False,
                general_operator_transport_ruled_out=False)
            comparisons.append(item)
    summary={'status':'NO_TWIRL0_REUSE_ESTABLISHED',
        'records':list(entries.values()),'comparisons':comparisons,
        'target_circuits':len(entries),'nonzero_twirl_comparisons':len(comparisons),
        'internal_mismatch_pairs':sum(not x['internal_per_wire_equal'] for x in comparisons),
        'full_surrogate_channels_distinguished':sum(x['full_surrogate_channel_distinguished'] for x in comparisons),
        'safe_reuse_pairs':0,'tests_run':tests.testsRun,
        'new_qpu_seconds':0,'new_tn_states':0,'hardware_means_changed':False,
        'hardware_robustness_validated':False,'six_by_six_go':False,
        'elapsed_seconds':time.monotonic()-start,
        'limitations':['Surrogate invariant is not an experimentally learned channel.',
            'Unequal full channels need not differ on every Pauli or input state.',
            'Internal signature mismatch does not rule out more sophisticated transport.',
            'No observable-error size is inferred from normalized log determinants.',
            'No new target scoring or claim of improved hardware results.',
            'Other twirls were used in old aggregate analyses; not untouched holdouts.']}
    write(out/'summary.json',summary)
    manifest={str(p.relative_to(out)):digest(p) for p in sorted(out.rglob('*')) if p.is_file()}
    write(out/'sha256.json',manifest)
    print(json.dumps({k:summary[k] for k in ('status','target_circuits',
        'internal_mismatch_pairs','full_surrogate_channels_distinguished','tests_run',
        'elapsed_seconds','new_qpu_seconds')}),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    with threadpool_limits(limits=1):run(args.output)
