"""Offline TFLO building blocks; this module cannot submit a QPU job.

Conventions: hbar=1, H_hop=c(a^dag_p a_q+h.c.), c=-t or -t';
spin-interleaved little-endian occupations, spin_z=n_up-n_down (not S_z).
TFLO is an empirical transfer model, not an exact inverse noise channel.
Inspired by arXiv:2510.26845v2 Appendix E; not a full paper reproduction.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import replace
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.circuit import Parameter
from qiskit.circuit.library import XXPlusYYGate
from qiskit.transpiler import CouplingMap

from cuprate_2d_hubbard_pipeline import initial_site_rows, validate_config
from cuprate_2d_fermionic_mapping import network_schedule, pair_model, prepare_state


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def initial_occupations(cfg):
    return np.array([[r['n_up_initial'], r['n_down_initial']]
                     for r in initial_site_rows(cfg)], dtype=np.uint8).ravel()


def parameterized_network(cfg):
    """Preserve all onsite CP gates, even after binding exactly U=0.

    Compile this ONCE, before binding. Recompiling a bound circuit is forbidden
    in the TFLO path because it can change the calibration noise exposure.
    """
    validate_config(cfg)
    if cfg.steps < 1:
        raise ValueError('TFLO requires a fixed positive number of steps')
    dt, interaction_phase = Parameter('step_time'), Parameter('interaction_phase')
    circuit = QuantumCircuit(cfg.qubits)
    prepare_state(circuit, cfg)
    hops, _ = pair_model(cfg)
    layers = network_schedule(cfg.qubits)
    onsite_pairs = {(2*s, 2*s+1) for s in range(cfg.sites)}
    for _ in range(cfg.steps):
        for schedule in (layers, list(reversed(layers))):
            for layer in schedule:
                for a, b, modes in layer:
                    coefficient = hops.get(modes, 0.0)
                    # 0*Parameter can retain a symbolic type in Qiskit, hiding
                    # a constant fSWAP from the compiler (extra CZ gates).
                    angle = math.pi + coefficient*dt if coefficient else math.pi
                    circuit.append(XXPlusYYGate(angle), [a, b])
                    circuit.p(math.pi/2, a)
                    circuit.p(math.pi/2, b)
                    if modes in onsite_pairs:
                        circuit.cp(-interaction_phase/2, a, b)
        if cfg.chemical_potential:
            for q in range(cfg.qubits):
                circuit.p(cfg.chemical_potential*dt, q)
    circuit.metadata = {'family': 'tflo_fixed_network', 'steps': cfg.steps,
                        'binding_rule': 'step_time=T/steps; interaction_phase=U*T/steps',
                        'compile_before_bind': True, 'mode_order_restored': True}
    return circuit


def compile_template(circuit):
    """Offline CZ basis and path only, NOT a live backend scheduling check."""
    result = transpile(circuit, basis_gates=['rz', 'sx', 'x', 'cz'],
                       coupling_map=CouplingMap.from_line(circuit.num_qubits),
                       initial_layout=list(range(circuit.num_qubits)),
                       routing_method='none', optimization_level=3,
                       approximation_degree=1.0, seed_transpiler=9)
    if result.layout.final_index_layout() != list(range(circuit.num_qubits)):
        raise ValueError('Compilation changed the logical path ordering')
    return result


def bind(circuit, cfg, total_time, u_over_t):
    if not np.isfinite(total_time) or total_time < 0 or not np.isfinite(u_over_t):
        raise ValueError('Non-finite parameter or negative time')
    values = {'step_time': total_time/cfg.steps,
              'interaction_phase': u_over_t*cfg.hopping_t*total_time/cfg.steps}
    return circuit.assign_parameters({p: values[p.name] for p in circuit.parameters})


def skeleton(circuit):
    """Gate names, ordered wires and classical map; ignores angle VALUES only."""
    records = [(i.operation.name, [circuit.find_bit(q).index for q in i.qubits],
                [circuit.find_bit(c).index for c in i.clbits]) for i in circuit.data]
    return hashlib.sha256(json.dumps(records).encode()).hexdigest()


def explicit_twirl(template, seed):
    """CZ Pauli twirls and terminal readout-X mask; no bound recompilation.

    CZ conjugation sends (x1,z1;x2,z2) -> (x1,z1^x2;x2,z2^x1).
    Global Pauli phases do not affect observables. Each seed is an explicit
    experimental unit, retained in the archive for hierarchical resampling.
    """
    if template.num_clbits:
        raise ValueError('Expected an unmeasured template')
    rng = np.random.default_rng(seed)
    circuit = QuantumCircuit(template.num_qubits)
    circuit.global_phase = template.global_phase
    def pauli(q, x, z):
        if x:
            circuit.x(q)
        if z:
            circuit.rz(math.pi, q)
    for instruction in template.data:
        wires = [template.find_bit(q).index for q in instruction.qubits]
        if instruction.operation.name == 'cz':
            a, b = wires
            x1, z1, x2, z2 = rng.integers(0, 2, 4).tolist()
            pauli(a, x1, z1)
            pauli(b, x2, z2)
            circuit.cz(a, b)
            pauli(a, x1, z1 ^ x2)
            pauli(b, x2, z2 ^ x1)
        else:
            circuit.append(instruction.operation, wires)
    mask = rng.integers(0, 2, template.num_qubits).astype(np.uint8)
    for q in np.flatnonzero(mask):
        circuit.x(int(q))
    circuit.metadata = {**(template.metadata or {}), 'twirl_seed': int(seed),
                        'readout_mask_little_endian': mask.tolist()}
    return circuit, mask


def embed_measurement(circuit, layout, physical_width):
    """Physical qubits map explicitly to a logical-order classical register."""
    if len(layout) != circuit.num_qubits or len(set(layout)) != len(layout):
        raise ValueError('Invalid injective layout')
    if min(layout) < 0 or max(layout) >= physical_width:
        raise ValueError('Layout outside device width')
    result = QuantumCircuit(physical_width)
    result.compose(circuit, qubits=layout, inplace=True)
    from qiskit import ClassicalRegister
    meas = ClassicalRegister(len(layout), 'meas')
    result.add_register(meas)
    result.measure(layout, meas)
    result.metadata = {**(circuit.metadata or {}), 'logical_to_physical': list(layout)}
    return result


def flo_reference(cfg, total_time):
    """Polynomial-cost exact U=0 FINITE-CIRCUIT reference, not exp(-iHT).

    Evolve occupied single-particle orbitals through precisely the same
    palindromic network ordering. Routing swaps only relabel slots and cancel.
    t-prime remains quadratic. Onsite U is zero ONLY in this reference.
    """
    if total_time < 0 or not np.isfinite(total_time):
        raise ValueError('Invalid time')
    occupations = initial_occupations(cfg)
    orbitals = np.eye(cfg.qubits, dtype=complex)[:, occupations.astype(bool)]
    hops, _ = pair_model(replace(cfg, u_over_t=0.0))
    layers = network_schedule(cfg.qubits)
    for _ in range(cfg.steps):
        for schedule in (layers, list(reversed(layers))):
            for layer in schedule:
                for _, _, modes in layer:
                    coefficient = hops.get(modes, 0.0)
                    if coefficient:
                        p, q = modes
                        angle = coefficient*total_time/(2*cfg.steps)
                        c, s = np.cos(angle), -1j*np.sin(angle)
                        old_p, old_q = orbitals[p].copy(), orbitals[q].copy()
                        orbitals[p] = c*old_p+s*old_q
                        orbitals[q] = s*old_p+c*old_q
    covariance = orbitals @ orbitals.conj().T
    density = covariance.diagonal().real
    z = 1-2*density
    zz = np.array([z[2*i]*z[2*i+1]-4*abs(covariance[2*i, 2*i+1])**2
                   for i in range(cfg.sites)])
    return np.concatenate([z, zz]), covariance


def decode_bitstrings(bitstrings, width, readout_mask):
    """Qiskit printed bit strings are MSB first; output columns are q0,q1,..."""
    if not bitstrings or any(len(s) != width or set(s)-{'0', '1'} for s in bitstrings):
        raise ValueError('Expected nonempty full-width binary strings')
    mask = np.asarray(readout_mask)
    if mask.shape != (width,) or not np.all((mask == 0) | (mask == 1)):
        raise ValueError('Invalid readout mask')
    bits = np.array([[int(c) for c in s[::-1]] for s in bitstrings], dtype=np.uint8)
    return bits ^ mask.astype(np.uint8)


def pauli_samples(bits):
    bits = np.asarray(bits)
    if bits.ndim != 2 or bits.shape[1] % 2 or not np.all((bits == 0) | (bits == 1)):
        raise ValueError('Expected a shots-by-even-width binary array')
    z = 1-2*bits.astype(float)
    return np.concatenate([z, z[:, ::2]*z[:, 1::2]], axis=1)


def physical_observables(paulis):
    p = np.asarray(paulis)
    if p.shape[-1] % 3:
        raise ValueError('Expected 2*sites Z and sites onsite ZZ values')
    n = p.shape[-1]//3
    up, down = p[..., :2*n:2], p[..., 1:2*n:2]
    return np.stack([1-(up+down)/2, (down-up)/2,
                     (1-up-down+p[..., 2*n:])/4], axis=-1)


def sector_mask(bits, n_up, n_down, tolerance=0):
    if int(tolerance) != tolerance or tolerance < 0:
        raise ValueError('Sector tolerance must be a nonnegative integer')
    # L1 distance of the TWO spin counts, not just total charge.
    return (np.abs(bits[:, ::2].sum(axis=1).astype(int)-n_up)
            + np.abs(bits[:, 1::2].sum(axis=1).astype(int)-n_down)) <= tolerance


def fit_tflo(noisy, exact, times, *, ridge=1e-3):
    """Per-Pauli linear-linear fit y=m*x+c*T+b, U=0 training only.

    Fixed weak ridge towards the identity prevents singular low-SNR fits;
    it is NOT the paper's learned three-stage regularizer. Diagnostics expose
    ill-conditioning. No clipping or target-reference fitting is performed.
    """
    noisy, exact, times = map(lambda a: np.asarray(a, dtype=float), (noisy, exact, times))
    if noisy.ndim != 2 or noisy.shape != exact.shape or len(times) != len(noisy):
        raise ValueError('Mismatched training dimensions')
    if len(times) < 4 or not all(np.isfinite(a).all() for a in (noisy, exact, times)):
        raise ValueError('Need at least four finite training settings')
    if ridge <= 0 or not np.isfinite(ridge):
        raise ValueError('Positive fixed regularization required')
    scale = max(float(np.ptp(times)), 1e-12)
    coefficients, diagnostics = [], []
    for column in range(noisy.shape[1]):
        design = np.column_stack([noisy[:, column], times/scale, np.ones(len(times))])
        singular = np.linalg.svd(design, compute_uv=False)
        regularized = np.vstack([design, np.sqrt(ridge)*np.eye(3)])
        response = np.r_[exact[:, column], np.sqrt(ridge)*np.array([1., 0., 0.])]
        beta = np.linalg.lstsq(regularized, response, rcond=None)[0]
        coefficients.append(beta)
        diagnostics.append({'rank': int(np.linalg.matrix_rank(design)),
                            'condition': float(singular[0]/singular[-1]) if singular[-1] > 1e-14 else None,
                            'training_rmse': float(np.sqrt(np.mean((design@beta-exact[:, column])**2))),
                            'slope': float(beta[0])})
    return {'coefficients': np.array(coefficients).tolist(), 'time_scale': scale,
            'ridge': ridge, 'diagnostics': diagnostics}


def apply_tflo(model, noisy, total_time):
    beta = np.asarray(model['coefficients'])
    return beta[:, 0]*noisy + beta[:, 1]*total_time/model['time_scale'] + beta[:, 2]


def archive_sampler_results(destination, result, records, *, job_id, width):
    """Lossless scalar-PUB SamplerV2 adapter; no network or submission call.

    Keep bitstrings per explicit twirl (not aggregated counts). Atomic file
    creation refuses overwrite. Caller must bind each template before Sampler.
    """
    if len(result) != len(records) or not records or not job_id:
        raise ValueError('Missing provenance or incorrect PUB count')
    seen, archived = set(), []
    for pub, record in zip(result, records):
        key = (record['setting_id'], record['twirl_id'])
        if key in seen:
            raise ValueError('Duplicate setting/twirl')
        seen.add(key)
        bits = pub.data.meas
        if bits.shape != () or bits.num_bits != width:
            raise ValueError('Expected one scalar PUB and a logical-width meas register')
        strings = bits.get_bitstrings()
        if len(strings) != record['shots']:
            raise ValueError('Actual shot count differs from frozen plan')
        decode_bitstrings(strings, width, record['readout_mask_little_endian'])
        archived.append({**record, 'bitstrings': strings})
    payload = {'schema': 'tflo-raw-v1', 'job_id': job_id, 'width': width, 'records': archived}
    with Path(destination).open('x', encoding='utf-8') as handle:
        json.dump(payload, handle, indent=2, allow_nan=False)
        handle.write('\n')
    return payload


def analyze(settings, raw, n_up, n_down, *, tolerance=0, bootstrap=200, seed=20260905):
    """PS -> TFLO; common twirl IDs resampled jointly across settings.

    Fit uses U=0 train rows ONLY. Held-out reference arrays never enter fit.
    Noise-transfer bias is not covered by bootstrap confidence intervals.
    """
    if bootstrap < 2:
        raise ValueError('Need at least two bootstrap replicates')
    ids = [s['id'] for s in settings]
    if len(ids) != len(set(ids)) or set(raw) != set(ids):
        raise ValueError('Setting IDs must be unique and exactly match raw data')
    train = [i for i, s in enumerate(settings) if s['role'] == 'train']
    if any(settings[i]['u_over_t'] != 0 for i in train):
        raise ValueError('Interacting references may never train TFLO')
    twirls = sorted(raw[ids[0]])
    if len(twirls) < 2 or any(sorted(raw[k]) != twirls for k in ids):
        raise ValueError('Need matching explicit twirl IDs for each setting')
    if any(len(bits) == 0 for k in ids for bits in raw[k].values()):
        raise ValueError('Empty twirl block')
    rng = np.random.default_rng(seed)
    def evaluate(resample=False):
        chosen = rng.choice(twirls, len(twirls), replace=True) if resample else twirls
        means, unfiltered, kept, fractions = [], [], [], []
        for setting in settings:
            blocks = []
            for twirl in chosen:
                bits = raw[setting['id']][int(twirl)]
                blocks.append(bits[rng.integers(len(bits), size=len(bits))] if resample else bits)
            bits = np.concatenate(blocks)
            unfiltered.append(pauli_samples(bits).mean(axis=0))
            selected = sector_mask(bits, n_up, n_down, tolerance)
            if selected.sum() < 32:
                raise ValueError('Fewer than 32 retained shots; fit not trustworthy')
            means.append(pauli_samples(bits[selected]).mean(axis=0))
            kept.append(int(selected.sum()))
            fractions.append(float(selected.mean()))
        means = np.array(means)
        model = fit_tflo(means[train], [settings[i]['reference'] for i in train],
                         [settings[i]['time'] for i in train])
        mitigated = np.array([apply_tflo(model, p, s['time']) for p, s in zip(means, settings)])
        return np.asarray(unfiltered), means, mitigated, kept, fractions, model
    central = evaluate()
    replicates, failures = [], 0
    for _ in range(bootstrap):
        try:
            replicates.append(np.array(evaluate(True)[:3]))
        except ValueError:
            failures += 1
    if not replicates:
        raise ValueError('All bootstrap replicates failed')
    samples = np.asarray(replicates)
    report = {'method': 'PS + regularized linear-linear TFLO (no MESR/GPR)',
              'sector_tolerance': tolerance, 'bootstrap_replicates': bootstrap,
              'bootstrap_failures': failures, 'bootstrap_reliable': failures/bootstrap <= .05,
              'model': central[5], 'settings': [],
              'uncertainty_boundary': 'Sampling and fit uncertainty only; excludes transfer bias and Trotter error.'}
    for i, setting in enumerate(settings):
        row = {k: v for k, v in setting.items() if k != 'reference'}
        row.update(retained_shots=central[3][i], retained_fraction=central[4][i])
        for j, name in enumerate(('raw', 'postselected', 'tflo')):
            estimate = physical_observables(central[j][i])
            dist = physical_observables(samples[:, j, i, :])
            values = {'observables': estimate.tolist(),
                      'ci95_low': np.quantile(dist, .025, axis=0).tolist(),
                      'ci95_high': np.quantile(dist, .975, axis=0).tolist()}
            if 'reference' in setting:
                ref = physical_observables(setting['reference'])
                values['rmse_charge_spin_double'] = np.sqrt(np.mean((estimate-ref)**2, axis=0)).tolist()
            values['out_of_bounds_count'] = int(np.sum((estimate < [0., -1., 0.]) | (estimate > [2., 1., 1.])))
            row[name] = values
        report['settings'].append(row)
    return report
