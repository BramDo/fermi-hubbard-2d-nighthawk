"""Compare new measured QPY native sequences with archived expectation circuits."""
import argparse
from pathlib import Path
import shutil
from qiskit import qpy
import aer_cuprate_cz_zne_bitshots as b

def native_signature(circuit):
    return [(i.operation.name,tuple(circuit.find_bit(q).index for q in i.qubits),
             tuple(float(p) for p in i.operation.params))
            for i in circuit.data if i.operation.name in b.z.c.a.NATIVE]

def run(out):
    destination=out/'supplementary_gate_audit'
    if destination.exists():
        raise ValueError('Refuse overwrite')
    checked=[]
    inputs=[]
    for g in range(3):
        for t in range(8):
            old=(b.z.PARENT/'circuits'/f'twirl_{t}.qpy' if g==0
                 else b.PARENT/'circuits'/f'{g}_{t}.qpy')
            current=out/'circuits'/f'{g}_{t}.qpy'
            with old.open('rb') as handle:
                previous=qpy.load(handle)[0]
            with current.open('rb') as handle:
                measured=qpy.load(handle)[0]
            assert previous.num_qubits==measured.num_qubits==18
            assert native_signature(previous)==native_signature(measured)
            b.check_measured(measured)
            checked.append({'factor':g+1,'twirl':t,'global_native_sequence_identical':True,
                'native_operations':len(native_signature(measured)),
                'cz_count':measured.count_ops()['cz']})
            inputs.extend([old,current])
    destination.mkdir()
    shutil.copyfile(Path(__file__),destination/'source.py')
    b.z.c.a.write(destination/'results.json',{'status':'PASS_EXACT_NATIVE_ARCHIVE_COMPARISON',
        'checks':checked,'barriers_and_measurement_or_save_instructions_excluded_from_native_comparison':True,
        'physical_gates_angles_and_order_compared_exactly':True,
        'new_measurement_identity_mapping_verified':True,'new_qpu_seconds':0,
        'input_sha256':{str(p.relative_to(b.z.c.a.ROOT)):b.z.c.a.digest(p) for p in inputs}})
    b.z.c.a.write(destination/'sha256.json',{p.name:b.z.c.a.digest(p) for p in destination.iterdir() if p.is_file()})
    print('PASS: all24 measured circuit native sequences identical to frozen prior circuits')

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    run(args.output.resolve())
