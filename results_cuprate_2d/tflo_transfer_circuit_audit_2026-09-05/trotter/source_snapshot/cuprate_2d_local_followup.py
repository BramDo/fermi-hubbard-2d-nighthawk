"""Pure local tools for exploratory TFLO transfer and same-order routing."""
from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.circuit import Parameter
from qiskit.circuit.library import XXPlusYYGate
from qiskit_aer import AerSimulator

from cuprate_2d_tflo import fit_tflo, apply_tflo, sector_mask, pauli_samples
from cuprate_2d_fermionic_mapping import pair_model, network_schedule, prepare_state, choose_route, add_fswap

METHODS = ('linear_linear', 'affine_no_time', 'time_only')


def means(settings, raw, tolerance=1, minimum=32):
    values, counts = [], []
    for setting in settings:
        blocks = raw[setting['id']]
        bits = np.concatenate([blocks[k] for k in sorted(blocks)])
        mask = sector_mask(bits, 4, 4, tolerance)
        if mask.sum() < minimum:
            raise ValueError('Below fixed retained-shot minimum')
        values.append(pauli_samples(bits[mask]).mean(axis=0))
        counts.append(int(mask.sum()))
    return np.asarray(values), counts


def fit_models(settings, raw):
    if any(s['u_over_t'] != 0 for s in settings) or set(raw) != {s['id'] for s in settings}:
        raise ValueError('Fit API accepts U=0 settings and their data only')
    train = [s for s in settings if s['role'] == 'train']
    if len(train) != 6:
        raise ValueError('Expected six U=0 training settings')
    x, _ = means(train, raw)
    y = np.asarray([s['reference'] for s in train])
    times = np.asarray([s['time'] for s in train])
    scale = float(np.ptp(times))
    output = {'linear_linear': {**fit_tflo(x, y, times, ridge=.001), 'kind': 'linear_linear'}}
    for kind in ('affine_no_time', 'time_only'):
        coefficients, conditions = [], []
        for k in range(x.shape[1]):
            feature = x[:, k] if kind == 'affine_no_time' else times/scale
            design = np.column_stack([feature, np.ones(len(times))])
            prior = np.array([1., 0.]) if kind == 'affine_no_time' else np.zeros(2)
            beta = np.linalg.lstsq(np.vstack([design, np.sqrt(.001)*np.eye(2)]),
                np.r_[y[:, k], np.sqrt(.001)*prior], rcond=None)[0]
            coefficients.append(beta.tolist())
            value = float(np.linalg.cond(design))
            conditions.append(value if np.isfinite(value) else None)
        output[kind] = {'kind': kind, 'coefficients': coefficients, 'time_scale': scale,
                        'ridge': .001, 'conditions': conditions}
    return output


def predict(model, measured, times):
    if model['kind'] == 'linear_linear':
        return np.array([apply_tflo(model, p, t) for p, t in zip(measured, times)])
    beta = np.asarray(model['coefficients'])
    feature = measured if model['kind'] == 'affine_no_time' else np.asarray(times)[:, None]/model['time_scale']
    return feature*beta[:, 0] + beta[:, 1]


def ordered_terms(cfg):
    hops, _ = pair_model(cfg)
    onsite = {(2*s, 2*s+1) for s in range(cfg.sites)}
    terms = []
    for layer in network_schedule(cfg.qubits):
        for _, _, modes in layer:
            if modes in hops and hops[modes] != 0:
                terms.append({'p': modes[0], 'q': modes[1], 'kind': 'hop', 'coefficient': hops[modes]})
            elif modes in onsite:
                terms.append({'p': modes[0], 'q': modes[1], 'kind': 'onsite'})
    if len(terms) != sum(c != 0 for c in hops.values()) + cfg.sites:
        raise ValueError('Incomplete interaction list')
    return terms


def half_gate(circuit, a, b, term, dt, phase):
    if term['kind'] == 'hop':
        circuit.append(XXPlusYYGate(term['coefficient']*dt), [a, b])
    else:
        circuit.cp(-phase/2, a, b)


def sparse_template(cfg, strategy='look12', prepare=True):
    """Preserve the full original noncommuting term sequence exactly.

    Only routing changes. Reverse the forward routing after the reverse
    sequence of half terms, restoring the original fermionic mode order.
    """
    dt, phase = Parameter('step_time'), Parameter('interaction_phase')
    circuit = QuantumCircuit(cfg.qubits)
    if prepare:
        prepare_state(circuit, cfg)
    terms = ordered_terms(cfg)
    horizon = int(strategy[4:]) if strategy.startswith('look') else 0
    count = 0
    for _ in range(cfg.steps):
        order, records = list(range(cfg.qubits)), []
        for i, term in enumerate(terms):
            p, q = term['p'], term['q']
            future = [(t['p'], t['q'], 1.) for t in terms[i+1:i+1+horizon]]
            order, swaps = choose_route(order, p, q, future, strategy)
            for a in swaps:
                add_fswap(circuit, a, a+1)
            a, b = order.index(p), order.index(q)
            if abs(a-b) != 1:
                raise ValueError('Routing did not make the modes adjacent')
            half_gate(circuit, a, b, term, dt, phase)
            records.append((a, b, term, swaps))
            count += 2*len(swaps)
        for a, b, term, swaps in reversed(records):
            if {order[a], order[b]} != {term['p'], term['q']}:
                raise ValueError('Reverse routing mode mismatch')
            half_gate(circuit, a, b, term, dt, phase)
            for k in reversed(swaps):
                add_fswap(circuit, k, k+1)
                order[k], order[k+1] = order[k+1], order[k]
        if order != list(range(cfg.qubits)):
            raise ValueError('Final mode order changed')
        if cfg.chemical_potential:
            for q in range(cfg.qubits):
                circuit.p(cfg.chemical_potential*dt, q)
    circuit.metadata = {'family': 'sparse_same_order_fswap', 'strategy': strategy,
        'same_original_term_order': True, 'mode_order_restored': True,
        'routing_fswaps': count, 'compile_before_bind': True, 'new_QPU_seconds': 0}
    return circuit


def local_state(circuit):
    simulator = AerSimulator(method='statevector', max_parallel_threads=1,
        precision='double', enable_truncation=False)
    qc = circuit.copy()
    qc.save_statevector()
    compiled = transpile(qc, backend=simulator, optimization_level=0, seed_transpiler=9)
    result = simulator.run(compiled, shots=1).result()
    if not result.success:
        raise ValueError('Local statevector simulation failed')
    return np.asarray(result.get_statevector(), dtype=complex)


def phase_distance(a, b):
    overlap = np.vdot(b, a)
    phase = overlap/abs(overlap) if abs(overlap) else 1.
    return float(np.linalg.norm(a - phase*b))


def two_qubit_depth(circuit):
    clocks = np.zeros(circuit.num_qubits, dtype=int)
    for item in circuit.data:
        if len(item.qubits) == 2:
            wires = [circuit.find_bit(q).index for q in item.qubits]
            clocks[wires] = int(max(clocks[wires])) + 1
    return int(max(clocks))


def interval(values):
    values = np.asarray(values)
    keep = np.isfinite(values).all(axis=tuple(range(1, values.ndim))) if values.ndim > 1 else np.isfinite(values)
    values = values[keep]
    if not len(values):
        return None
    return {'low': np.quantile(values, .025, axis=0).tolist(),
            'high': np.quantile(values, .975, axis=0).tolist(), 'valid': len(values)}
