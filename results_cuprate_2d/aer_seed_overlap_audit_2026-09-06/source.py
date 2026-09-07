"""Reproduce adjacent Aer run-seed overlap on a cheap local Kraus circuit."""
import argparse
import shutil
from pathlib import Path
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Pauli
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, amplitude_damping_error
import aer_cuprate_nighthawk_smoke as a

SOURCE = 'https://github.com/Qiskit/qiskit-aer/blob/0.17.2/src/simulators/circuit_executor.hpp'
def probe(parallel):
    circuit = QuantumCircuit(1)
    circuit.ry(1.2, 0)
    circuit.x(0)
    circuit.ry(.7, 0)
    circuit.x(0)
    circuit.save_expectation_value(Pauli('Z'), [0], label='z', pershot=True)
    noise = NoiseModel()
    noise.add_all_qubit_quantum_error(amplitude_damping_error(.4), ['x'])
    sim = AerSimulator(method='statevector', noise_model=noise,
                       max_parallel_threads=parallel, max_parallel_shots=parallel)
    rows = []
    for seed in (2026092000, 2026092001, 2026093000):
        result = sim.run(circuit, shots=32, seed_simulator=seed).result()
        assert result.success
        rows.append({'seed': seed, 'values': np.asarray(result.data()['z']).tolist(),
                     'metadata': result.results[0].metadata})
    left, adjacent, distant = [np.asarray(r['values']) for r in rows]
    overlap = float(np.max(np.abs(left[1:]-adjacent[:-1])))
    independent = float(np.max(np.abs(left[1:]-distant[:-1])))
    assert overlap < 1e-12
    assert independent > 1e-3
    return {'parallel': parallel, 'adjacent_shift_max_error': overlap,
            'disjoint_shift_max_difference': independent, 'runs': rows}

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Refuse overwrite')
    result = {'status': 'CONFIRMED_ADJACENT_RUN_SEED_OVERLAP',
              'qiskit': a.qiskit.__version__, 'aer': a.qiskit_aer.__version__,
              'official_source': SOURCE, 'source_lines': [823, 834],
              'source_rule': 'circ.seed + shot_index (shot zero uses init_rng)',
              'tests': [probe(1), probe(2)], 'new_qpu_seconds': 0,
              'interpretation': 'Cross-twirl independence cannot be assumed for old base+twirl seeds. Does not prove identical trajectories for different twirls or fully explain historical control discrepancy.'}
    args.output.mkdir(parents=True)
    shutil.copyfile(Path(__file__), args.output/'source.py')
    a.write(args.output/'results.json', result)
    a.write(args.output/'sha256.json', {'results.json': a.digest(args.output/'results.json'),
                                      'source.py': a.digest(args.output/'source.py')})
    print(result['status'])
    print([(r['parallel'], r['adjacent_shift_max_error'], r['disjoint_shift_max_difference']) for r in result['tests']])
