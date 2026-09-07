"""Exact blockwise native synthesis of the unchanged parameterized network."""
import math,time
from collections import Counter
import numpy as np
from qiskit import QuantumCircuit,transpile
from qiskit.quantum_info import Operator
from cuprate_2d_tflo import parameterized_network,skeleton


def compile_blocks(logical):
    """Compile each fSWAP+hopping+optional onsite block; never rebind/approximate."""
    result=QuantumCircuit(logical.num_qubits)
    cache={}; phase_constants=[]; phase_coefficients={}; cells=Counter(); i=0
    data=logical.data
    while i<len(data):
        inst=data[i]; op=inst.operation
        wires=[logical.find_bit(q).index for q in inst.qubits]
        if op.name=='x':
            result.append(op,wires); i+=1; continue
        if op.name!='xx_plus_yy':
            raise ValueError('Unexpected operation in exact network parser: '+op.name)
        a,b=wires
        if i+2>=len(data): raise ValueError('Incomplete fSWAP phase block')
        local=QuantumCircuit(2); local.append(op,[0,1])
        for offset,q in [(1,a),(2,b)]:
            nxt=data[i+offset]
            if nxt.operation.name!='p' or [logical.find_bit(x).index for x in nxt.qubits]!=[q] or abs(float(nxt.operation.params[0])-math.pi/2)>1e-13:
                raise ValueError('fSWAP phase block mismatch')
            local.append(nxt.operation,[0 if q==a else 1])
        used=3
        if i+3<len(data) and data[i+3].operation.name=='cp':
            nxt=data[i+3]
            if [logical.find_bit(x).index for x in nxt.qubits]!=wires: raise ValueError('Onsite wire mismatch')
            local.append(nxt.operation,[0,1]); used=4
        key=tuple((x.operation.name,tuple(map(str,x.operation.params))) for x in local.data)
        if key not in cache:
            native=transpile(local,basis_gates=['rz','sx','x','cz'],optimization_level=3,
                approximation_degree=1.,seed_transpiler=9)
            errors=[]
            # Full two-qubit unitary equality including the global phase, at several independent parameters.
            for k in range(5):
                values={p:(j+1)*(.037+k*.19) for j,p in enumerate(local.parameters)}
                lhs=Operator(local.assign_parameters(values)).data
                rhs=Operator(native.assign_parameters({p:values[p] for p in native.parameters})).data
                err=float(np.max(np.abs(lhs-rhs))); errors.append(err)
                if err>1e-11: raise ValueError('Native cell operator mismatch')
            phase=native.global_phase
            parameters=list(getattr(phase,'parameters',[]))
            constant=float(phase.bind({p:0. for p in parameters})) if parameters else float(phase)
            coefficients={p:float(phase.gradient(p)) for p in parameters}
            for k in range(3):
                values={p:.11*(k+1)*(j+1) for j,p in enumerate(parameters)}
                before=float(phase.bind(values)) if parameters else float(phase)
                after=constant+sum(coefficients[p]*values[p] for p in parameters)
                if abs(np.exp(1j*before)-np.exp(1j*after))>1e-12: raise ValueError('Nonaffine cell phase')
            cache[key]=(native,constant,coefficients,max(errors))
        native,constant,coefficients,_=cache[key]
        phase_constants.append(constant)
        for p,c in coefficients.items(): phase_coefficients.setdefault(p,[]).append(c)
        for gate in native.data:
            result.append(gate.operation,[wires[native.find_bit(q).index] for q in gate.qubits])
        cells[str(key)]+=1; i+=used
    phase=math.fsum(phase_constants)+float(logical.global_phase)
    # Normalize only the constant global phase; preserve all parameter dependence.
    phase=phase%(2*math.pi)
    for p,values in phase_coefficients.items(): phase=phase+math.fsum(values)*p
    result.global_phase=phase
    result.metadata={**(logical.metadata or {}),'native_compiler':'exact_two_qubit_block_synthesis',
        'global_optimization':False,'approximation_degree':1.,'model_and_event_order_unchanged':True}
    return result,{'unique_cells':len(cache),'cell_counts':dict(cells),
        'dense_cell_unitary_max_abs':max(v[3] for v in cache.values()),
        'native_counts':dict(result.count_ops()),'depth':result.depth(),'skeleton':skeleton(result)}


def main():
    import run_tflo_dd6_once as r
    from cuprate_2d_hubbard_pipeline import Cuprate2DConfig
    from dataclasses import asdict
    r.require(not r.LOCK.exists() and not (r.RUN/'plan.json').exists(),'Attempt/plan exists')
    folder=r.RUN/'local_only'; path=folder/'parameterized72_blocks.qpy'
    r.require(not path.exists() and not (folder/'compile.json').exists(),'Do not overwrite compilation')
    cfg=Cuprate2DConfig(**r.read(r.OLD/'plan.json')['config'])
    start=time.perf_counter(); circuit,info=compile_blocks(parameterized_network(cfg))
    r.circuit_file(path,circuit)
    r.save(folder/'compile.json',{'source_sha256':r.digest(r.ROOT/'cuprate_2d_tflo.py'),
        'block_compiler_sha256':r.digest(r.ROOT/'compile_tflo_dd6_blocks.py'),
        'template_file':path.name,'qpy_sha256':r.digest(path),'seconds':time.perf_counter()-start,
        'config':asdict(cfg),'compiler':'exact_blockwise_fallback',**info})
    r.log('block_compile_done',seconds=time.perf_counter()-start,CZ=circuit.count_ops().get('cz',0),
        dense_cell_unitary_max_abs=info['dense_cell_unitary_max_abs'],qpu_seconds=0)


if __name__=='__main__': main()
