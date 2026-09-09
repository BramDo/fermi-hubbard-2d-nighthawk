"""Independent small-matrix and archive audit for the twirl reuse gate."""
from pathlib import Path
import argparse, itertools, json, math, sys, time
import numpy as np
from qiskit import QuantumCircuit, qpy
from qiskit.quantum_info import Operator
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from lmpf_2d.model import digest

PAULIS=np.array([[[1,0],[0,1]],[[0,1],[1,0]],
                 [[0,-1j],[1j,0]],[[1,0],[0,-1]]],complex)

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def basis(n):
    labels=np.array(list(itertools.product(range(4),repeat=n)))
    mats=[]
    for label in labels:
        m=np.array([[1.]])
        for digit in label[::-1]:m=np.kron(m,PAULIS[digit])
        mats.append(m)
    return labels,np.array(mats)

def direct_adjoint(unitary,labels,mats,qs,decay):
    # Every basis Pauli with a nonidentity restriction to qs is attenuated.
    conjugated=unitary.conj().T @ mats @ unitary
    matrix=np.einsum('aij,bji->ab',mats,conjugated)/len(unitary)
    matrix*=np.where(np.any(labels[:,list(qs)]!=0,axis=1),decay,1.)[None,:]
    if np.max(abs(matrix.imag))>1e-12:raise ValueError('Non-real PTM')
    return matrix.real

def dense_logdet(qc,rate,scale=1.,mask=None):
    if qc.num_qubits>3:raise ValueError('Dense oracle capped at THREE qubits')
    n=qc.num_qubits;labels,mats=basis(n);channel=np.eye(4**n)
    for item in qc.data:
        qs=tuple(qc.find_bit(q).index for q in item.qubits)
        embedded=QuantumCircuit(n);embedded.append(item.operation,qs)
        local=direct_adjoint(Operator(embedded).data,labels,mats,qs,
                             math.exp(-scale*rate(item.operation.name,qs)))
        channel=channel@local
    if mask is not None:
        unmask=QuantumCircuit(n)
        for q,v in enumerate(mask):
            if v:unmask.x(q)
        channel=channel@direct_adjoint(Operator(unmask).data,labels,mats,tuple(range(n)),1.)
    sign,value=np.linalg.slogdet(channel)
    if sign<=0:raise ValueError('Unexpected channel determinant sign')
    return float(value/4**n)

def calibrated_rate(data,layout,name,qs):
    physical=[layout[q] for q in qs];found=None
    for gate in data['gates']:
        if gate['gate']!=name:continue
        if gate['qubits']!=physical and not (name=='cz' and gate['qubits']==physical[::-1]):continue
        for parameter in gate['parameters']:
            if parameter['name']=='gate_error':found=float(parameter['value'])
        if found is not None:break
    if found is None:
        if name=='rz':return 0.
        raise ValueError('Missing calibration')
    d=2**len(qs);p=d*found/(d-1)
    if not 0<=p<1:raise ValueError('Invalid depolarizer')
    return -math.log1p(-p)

def audit(out):
    start=time.monotonic();plan=read(out/'plan.json');saved=read(out/'summary.json')
    for name,expected in read(out/'sha256.json').items():
        if digest(out/name)!=expected:raise ValueError('Saved artifact hash mismatch '+name)
    for field in ('input_sha256','source_sha256'):
        for name,expected in plan[field].items():
            if digest(ROOT/name)!=expected:raise ValueError('Input/source hash mismatch '+name)
    archive=ROOT/'results_cuprate_2d/hardware_readout_cz_folding_3x3_2026-09-06'
    original=read(archive/'plan.json');cal=read(archive/'live_backend_properties.json')
    layout=plan['layout'];lookup={q:i for i,q in enumerate(layout)}
    rates={};matrices={};wire_cores={};dets={};max_error=0.;local_error=0.
    for rec in saved['records']:
        file=ROOT/rec['provider_qpy']
        if digest(file)!=rec['provider_sha256']:raise ValueError('QPY mismatch')
        if digest(archive/'bound_inputs'/file.name)!=rec['bound_sha256']:raise ValueError('Bound mismatch')
        raw=original['records'][rec['record_index']]
        if raw['twirl_id']!=rec['twirl'] or raw['factor']!=rec['factor'] or raw['readout_mask_little_endian']!=rec['mask']:
            raise ValueError('Record metadata mismatch')
        with file.open('rb') as f:qc=qpy.load(f)[0]
        wires=[[] for _ in layout];measurement=[];terms=[]
        for item in qc.data:
            name=item.operation.name
            if name=='barrier':continue
            physical=[qc.find_bit(q).index for q in item.qubits]
            qs=tuple(lookup[q] for q in physical)
            if name=='measure':
                measurement.append((physical[0],qc.find_bit(item.clbits[0]).index));continue
            if measurement:raise ValueError('Nonterminal measurement')
            key=(name,qs)
            if key not in rates:rates[key]=calibrated_rate(cal,layout,name,qs)
            lam=rates[key];terms.append(-(4**len(qs)-1)*lam/(4**len(qs)))
            mk=(name,tuple(float(v) for v in item.operation.params),lam)
            if mk not in matrices:
                labels,mats=basis(len(qs))
                matrix=direct_adjoint(Operator(item.operation).data,labels,mats,tuple(range(len(qs))),math.exp(-lam))
                sign,ld=np.linalg.slogdet(matrix)
                if sign<=0:raise ValueError('Local determinant sign')
                matrices[mk]=float(ld/len(matrix))
                local_error=max(local_error,abs(matrices[mk]+(1-1/len(matrix))*lam))
            canonical=tuple(sorted(qs)) if name=='cz' else qs
            row=(name,canonical,tuple(float(v) for v in item.operation.params))
            for q in qs:wires[q].append(row)
        if sorted(measurement,key=lambda x:x[1])!=list(zip(layout,range(18))):
            raise ValueError('Measurement mapping failure')
        core=[]
        for seq in wires:
            while seq and seq[-1][0]!='cz':seq.pop()
            core.append(seq)
        key=rec['factor'],rec['twirl'];wire_cores[key]=core;dets[key]=math.fsum(terms)
        max_error=max(max_error,abs(dets[key]-rec['normalized_logabsdet']))
    distinguished=0
    for pair in saved['comparisons']:
        f,t=pair['factor'],pair['twirl']
        mismatch=[q for q in range(18) if wire_cores[f,0][q]!=wire_cores[f,t][q]]
        if mismatch!=pair['internal_mismatch_wires']:raise ValueError('Core mismatch audit failed')
        delta=dets[f,t]-dets[f,0]
        max_error=max(max_error,abs(delta-pair['normalized_logdet_delta']))
        flag=abs(delta)>plan['logdet_tolerance']
        if flag!=pair['full_surrogate_channel_distinguished']:raise ValueError('Distinction flag mismatch')
        distinguished+=flag
    # Noncommuting 3-qubit composition; no production PTM helper.
    toy=QuantumCircuit(3);toy.rz(.37,0);toy.sx(0);toy.cz(1,0)
    toy.x(2);toy.cz(2,1);toy.sx(1);toy.rz(-.91,2);toy.x(0)
    rate=lambda name,qs: .013*(1+sum(qs)) if name!='rz' else 0.
    expected=math.fsum(-(1-4.**(-len(i.qubits)))*rate(i.operation.name,tuple(toy.find_bit(q).index for q in i.qubits)) for i in toy.data)
    toy_errors=[]
    for scale in (0.,.3,1.):
        for mask in (None,[1,0,1]):
            got=dense_logdet(toy,rate,scale,mask)
            toy_errors.append(abs(got-scale*expected))
    if max(max_error,local_error,*toy_errors)>2e-11:raise ValueError('Independent logdet calculation failed')
    result={'status':'TWIRL_REUSE_MATRIX_AUDIT_PASSED','native_circuits':len(saved['records']),
        'comparison_pairs':len(saved['comparisons']),'full_surrogate_channels_distinguished':int(distinguished),
        'independent_calibration_reconstruction':True,'unique_local_matrices':len(matrices),
        'maximum_archive_logdet_error':max_error,'maximum_local_matrix_logdet_error':local_error,
        'dense_three_qubit_checks':len(toy_errors),'maximum_dense_logdet_error':max(toy_errors),
        'all_source_input_output_hashes_verified':True,
        'hardware_robustness_validated':False,'new_qpu_seconds':0,
        'elapsed_seconds':time.monotonic()-start}
    with (out/'verification.json').open('x',encoding='utf-8') as f:
        json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(result),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path)
    with threadpool_limits(limits=1):audit(p.parse_args().output)

