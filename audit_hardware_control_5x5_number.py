import json,math,time,signal
from pathlib import Path
from collections import defaultdict
import numpy as np
from qiskit import QuantumCircuit,qpy
from qiskit.quantum_info import Operator
from qiskit.circuit.library import CZGate,SXGate
from cuprate_2d_hubbard_pipeline import Cuprate2DConfig,initial_site_rows
signal.signal(signal.SIGALRM,lambda *_: (_ for _ in ()).throw(TimeoutError('180 second operator-audit bound')))
signal.alarm(180)
ROOT=Path('results_cuprate_2d/hardware_readout_cz_folding_6x6_2026-09-06')
plan=json.loads((ROOT/'plan.json').read_text())
cfg=Cuprate2DConfig(**plan['config'])
initial=[int(row['n_'+spin+'_initial']) for row in initial_site_rows(cfg) for spin in ('up','down')]
mats=[np.eye(2),np.array([[0,1],[1,0]]),np.diag([1,-1]),np.array([[0,-1j],[1j,0]])]
cztable={}
U=CZGate().to_matrix()
for a in range(4):
 for b in range(4):
  changed=U.conj().T@np.kron(mats[b],mats[a])@U
  options=[]
  for aa in range(4):
   for bb in range(4):
    coeff=np.trace(np.kron(mats[bb],mats[aa])@changed)/4
    if abs(coeff)>1e-12: options.append((aa,bb,int(round(coeff.real))))
  assert len(options)==1
  cztable[a,b]=options[0]
sxtable={}
U=SXGate().to_matrix()
for a in range(4):
 changed=U.conj().T@mats[a]@U
 options=[(aa,int(round((np.trace(mats[aa]@changed)/2).real))) for aa in range(4) if abs(np.trace(mats[aa]@changed)/2)>1e-12]
 assert len(options)==1
 sxtable[a]=options[0]

def propagate(qc,start,label,threshold=1e-12):
 current=start.copy(); dropped=0.; max_terms=len(current); began=time.perf_counter()
 for k,inst in enumerate(reversed(qc.data)):
  gate=inst.operation.name
  if gate in ('measure','barrier','delay'): continue
  wires=[qc.find_bit(q).index for q in inst.qubits]
  m=1<<wires[0]; nxt={}
  if gate=='rz':
   c=math.cos(float(inst.operation.params[0])); s=math.sin(float(inst.operation.params[0]))
   temp=defaultdict(float)
   for (x,z),v in current.items():
    if x&m:
     temp[x,z]+=c*v
     temp[x,z^m]+=(s if z&m else -s)*v
    else: temp[x,z]+=v
   for key,v in temp.items():
    if abs(v)<threshold: dropped+=abs(v)
    else: nxt[key]=v
  elif gate=='x':
   nxt={key:(-v if key[1]&m else v) for key,v in current.items()}
  elif gate=='sx':
   for (x,z),v in current.items():
    a=int(bool(x&m))+2*int(bool(z&m)); aa,sign=sxtable[a]
    nxt[((x&~m)|(m if aa&1 else 0),(z&~m)|(m if aa&2 else 0))]=v*sign
  elif gate=='cz':
   n=1<<wires[1]; mask=m|n
   for (x,z),v in current.items():
    a=int(bool(x&m))+2*int(bool(z&m)); b=int(bool(x&n))+2*int(bool(z&n))
    aa,bb,sign=cztable[a,b]
    xx=(x&~mask)|(m if aa&1 else 0)|(n if bb&1 else 0)
    zz=(z&~mask)|(m if aa&2 else 0)|(n if bb&2 else 0)
    nxt[xx,zz]=v*sign
  else: raise ValueError('Unsupported gate: '+gate)
  current=nxt; max_terms=max(max_terms,len(current))
  if len(current)>20000: raise RuntimeError('Pauli term budget exceeded')
  if k and k%20000==0:
   print(json.dumps({'progress':label,'gates_backward':k,'terms':len(current),'max_terms':max_terms,'seconds':time.perf_counter()-began}),flush=True)
 return current,{'dropped_coefficient_L1':dropped,'max_terms':max_terms,'seconds':time.perf_counter()-began}

def matrix(poly,n):
 result=np.zeros((1<<n,1<<n),complex)
 for (x,z),coeff in poly.items():
  term=np.array([[1.]])
  for q in reversed(range(n)): term=np.kron(term,mats[((x>>q)&1)+2*((z>>q)&1)])
  result+=coeff*term
 return result

# Independent dense check on non-number-conserving random circuits, not only easy conserved examples.
rng=np.random.default_rng(915)
check_errors=[]
for trial in range(6):
 qc=QuantumCircuit(3)
 for _ in range(30):
  q=int(rng.integers(3)); name=rng.choice(['rz','sx','x','cz'])
  if name=='rz': qc.rz(float(rng.uniform(-5,5)),q)
  elif name=='cz': qc.cz(q,(q+1)%3)
  else: getattr(qc,name)(q)
 start={(0,1<<q):float(rng.uniform(-1,1)) for q in range(3)}
 output,_=propagate(qc,start,'dense_test',threshold=1e-14)
 U=Operator(qc).data
 err=float(np.max(np.abs(matrix(output,3)-U.conj().T@matrix(start,3)@U)))
 assert err<2e-12
 check_errors.append(err)
print(json.dumps({'dense_checks':len(check_errors),'max_abs_error':max(check_errors),
 'prediction':'The full backward number operator must match the known preparation, with22 or32 particles for target controls.'}),flush=True)


import hashlib
import run_cuprate_2d_tflo_once as safe
control=Path('results_cuprate_2d/hardware_controls_5x5_2026-09-06_v1')
control_plan=json.loads((control/'plan.json').read_text())
control_refs=json.loads((control/'references.json').read_text())
evidence=[]
for index,rec in enumerate(control_plan['records']):
 name=rec['setting_id']+'_variant'+str(rec['twirl_id'])
 path=control/'provider_inputs'/f'circuit_{index:03d}.qpy'
 with path.open('rb') as f: qc=qpy.load(f)[0]
 layout=rec['physical_layout']; mask=rec['readout_mask_little_endian']; width=rec['width']
 if rec['role']=='calibration': occ=[rec['state']]*width
 else: occ=control_refs['prep5' if width==50 else 'prep6']['initial_bits_little_endian']
 start={(0,1<<q):float(1-2*mask[j]) for j,q in enumerate(layout)}
 expected={(0,1<<q):float(1-2*occ[j]) for j,q in enumerate(layout)}
 output,info=propagate(qc,start,name)
 residual=sum(abs(output.get(key,0)-expected.get(key,0)) for key in output.keys()|expected.keys())
 ideal_N=width/2-.5*sum(v for (x,z),v in output.items() if x==0)
 numerical_bound=.5*(residual+info['dropped_coefficient_L1'])
 assert numerical_bound<1e-7 and abs(ideal_N-sum(occ))<1e-8
 row={'index':index,'setting':name,'width':width,'ideal_N':ideal_N,
      'expected_N':sum(occ),'N_operator_residual_and_pruning':numerical_bound,
      'source_qpy_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),**info}
 evidence.append(row)
 print(json.dumps(row),flush=True)
safe.exclusive_json(control/'native_number_verification.json',{'status':'PASS_ALL12_ACTUAL_CIRCUITS',
 'job_id':json.loads((control/'job_receipt.json').read_text())['job_id'],
 'checks':evidence,'dense_random_circuit_checks':len(check_errors),'dense_check_max_abs':max(check_errors),
 'method':'Backward propagation of sum of masked physical Z operators through actual provider QPY; compared with preparation-conjugated number operator.',
 'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
 'numerical_scope':'Coefficient residual plus cumulative discarded L1 mass; floating roundoff checked numerically, not interval certified.',
 'no_QPU_or_provider_calls':True})
