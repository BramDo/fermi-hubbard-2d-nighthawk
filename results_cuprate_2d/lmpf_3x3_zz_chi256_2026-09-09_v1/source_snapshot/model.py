"""Frozen-calibration *surrogate* channels and readout, not learned device noise."""
from pathlib import Path
import hashlib,json
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import DensityMatrix
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel,ReadoutError,depolarizing_error

ROOT=Path(__file__).resolve().parents[1]
CALIBRATION=ROOT/'results_cuprate_2d/hardware_readout_cz_folding_3x3_2026-09-06/live_backend_properties.json'
PILOT_LAYOUT=(102,103,104,105,112,113,114,115)
PILOT_EDGES=((0,1),(1,2),(2,3),(4,5),(5,6),(6,7),(0,4),(1,5),(2,6),(3,7))

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

class FrozenSurrogate:
    def __init__(self,path=CALIBRATION,layout=PILOT_LAYOUT):
        self.path=Path(path);self.layout=tuple(layout)
        if len(set(layout))!=len(layout):raise ValueError('Duplicate physical wires')
        data=json.loads(self.path.read_text(encoding='utf-8-sig'))
        self.backend=data['backend_name'];self.date=data['last_update_date']
        self.errors={};self.readout=[]
        for g in data['gates']:
            p={v['name']:v['value'] for v in g['parameters']}
            if 'gate_error' in p:self.errors[g['gate'],tuple(g['qubits'])]=float(p['gate_error'])
        for q in self.layout:
            p={v['name']:v['value'] for v in data['qubits'][q]}
            # qiskit conventions: P(1|0), P(0|1).
            e0=float(p['prob_meas1_prep0']);e1=float(p['prob_meas0_prep1'])
            if not (0<=e0<1 and 0<=e1<1 and e0+e1<.9):raise ValueError('Invalid readout calibration')
            self.readout.append((e0,e1))
    def rate(self,name,qubits):
        physical=tuple(self.layout[q] for q in qubits)
        key=(name,physical)
        if key not in self.errors and name=='cz':key=(name,tuple(reversed(physical)))
        if name=='rz' and key not in self.errors:return 0.0  # explicit virtual-RZ modelling assumption
        if key not in self.errors:raise ValueError(f'Missing gate calibration {key}')
        r=self.errors[key];d=2**len(qubits);p=d*r/(d-1)
        if not 0<=p<1:raise ValueError(f'Unphysical RB-derived surrogate strength {key}: {p}')
        return float(-np.log1p(-p))
    def metadata(self):
        return {'backend':self.backend,'calibration_date':self.date,'physical_layout':list(self.layout),
            'calibration_file':str(self.path.relative_to(ROOT)),'calibration_sha256':digest(self.path),
            'noise_model':'local effective Pauli-Lindblad depolarizing surrogate from average gate infidelity',
            'learned_sparse_pauli_lindblad':False,'uses_T1_T2':False,'virtual_rz_without_reported_error_assumed_ideal':True,
            'mapping':'p=d*r/(d-1); decay_rate=-log(1-p); scale multiplies decay_rate',
            'readout_prob_1_given_0_and_0_given_1':self.readout,
            'readout_calibration_treated_as_known':True,
            'warning':'Archived backend numbers are not a learned or current hardware noise model.'}

def native_edges_validate(profile,edges):
    for edge in edges:profile.rate('cz',edge)

def sample_arm(circuit,steps,bits,profile,scale,shots,seed):
    """Exact Aer density-matrix propagation, then real finite-shot sampling.

    Noise scaling is simulated directly, not claimed to be hardware PEA.
    Preparation is ideal and excluded from the dynamics noise model.
    """
    n=len(bits)
    if n>10:raise ValueError('Aer density-matrix pilot capped at 10 qubits')
    qc=QuantumCircuit(n);qc.set_density_matrix(DensityMatrix.from_label(''.join(map(str,reversed(bits)))))
    si=0
    for item in circuit.data:
        if item.operation.name=='barrier':continue
        step=steps[si];si+=1
        qc.append(item.operation,step.qubits)
        p=1-np.exp(-scale*step.lindblad_decay_rate)
        if p>0:qc.append(depolarizing_error(p,len(step.qubits)).to_instruction(),step.qubits)
    qc.save_probabilities(label='quantum_probabilities');qc.measure_all()
    ro=NoiseModel()
    for q,(e0,e1) in enumerate(profile.readout):ro.add_readout_error(ReadoutError([[1-e0,e0],[e1,1-e1]]),[q])
    simulator=AerSimulator(method='density_matrix',precision='double',noise_model=ro,max_parallel_threads=1)
    result=simulator.run(qc,shots=shots,memory=True,seed_simulator=seed).result()
    if not result.success:raise RuntimeError(result.status)
    memory=result.get_memory();array=np.array([[int(c) for c in text.replace(' ','')[::-1]] for text in memory])
    probabilities=np.asarray(result.data(0)['quantum_probabilities'],float)
    assignment=np.array([[1.]])
    for e0,e1 in reversed(profile.readout):assignment=np.kron(assignment,[[1-e0,e0],[e1,1-e1]])
    observed=probabilities@assignment
    return array,probabilities,observed,memory

def features(bits,logical_to_final,readout=None):
    z=1-2*np.asarray(bits,dtype=float)
    if readout is not None:
        e0,e1=np.asarray(readout,float).T
        z=(z-(e1-e0))/(1-e0-e1)
    z=z[:,logical_to_final]
    return np.column_stack((z,z[:,0::2]*z[:,1::2]))

def physical_transform(n):
    """Affine map [Z modes, ZZ sites] -> [charge sites, spin sites, D sites]."""
    sites=n//2;matrix=np.zeros((3*sites,n+sites));offset=np.zeros(3*sites)
    for i in range(sites):
        matrix[i,2*i:2*i+2]=-.5;offset[i]=1
        matrix[sites+i,2*i:2*i+2]=[-.5,.5]
        matrix[2*sites+i,2*i:2*i+2]=-.25;matrix[2*sites+i,n+i]=.25;offset[2*sites+i]=.25
    return matrix,offset

def moments(probabilities,sample_features):
    mean=probabilities@sample_features
    cov=(sample_features.T*probabilities)@sample_features-np.outer(mean,mean)
    return mean,(cov+cov.T)/2
