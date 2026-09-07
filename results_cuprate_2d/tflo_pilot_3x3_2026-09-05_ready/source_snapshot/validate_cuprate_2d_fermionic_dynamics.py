"""Independent numerical checks and small-lattice time series; no provider calls."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
from scipy.linalg import expm
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import expm_multiply
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator, Statevector
from qiskit.circuit.library import XXPlusYYGate

from cuprate_2d_hubbard_pipeline import Cuprate2DConfig
from cuprate_2d_fermionic_dynamics import (
    CIRCUIT_FAMILY, add_fermionic_hopping, add_onsite_interactions,
    build_fermionic_circuit,
)
from cuprate_2d_exact_sector_baseline import (
    MODEL_FULL, build_hamiltonian, sector_basis, initial_state_vector, diagonal_site_rows,
)
from cuprate_2d_qiskit_circuit import build_circuit


def independent_hamiltonian(cfg, basis):
    """Occupation-basis oracle; enumerates the square lattice independently.

    No Pauli/JW or circuit-builder helper is used for hopping matrix elements.
    The exchange sign counts occupied modes strictly between the endpoints.
    """
    assert cfg.boundary_x == cfg.boundary_y == 'open'
    lookup = {state: i for i, state in enumerate(basis)}
    bonds = []
    for a in range(cfg.sites):
        for b in range(a + 1, cfg.sites):
            dx, dy = abs(a % cfg.lx - b % cfg.lx), abs(a // cfg.lx - b // cfg.lx)
            if dx + dy == 1:
                bonds.append((a, b, -cfg.hopping_t))
            elif dx == dy == 1 and cfg.t_prime:
                bonds.append((a, b, -cfg.t_prime))
    rr, cc, vv = [], [], []
    for col, state in enumerate(basis):
        double = sum(((state >> (2*s)) & 1) * ((state >> (2*s+1)) & 1)
                     for s in range(cfg.sites))
        rr.append(col); cc.append(col)
        vv.append(cfg.interaction_u * double - cfg.chemical_potential * state.bit_count())
        for a, b, coefficient in bonds:
            for spin in (0, 1):
                p, q = 2*a+spin, 2*b+spin
                if ((state >> p) & 1) == ((state >> q) & 1):
                    continue
                mask = ((1 << q) - 1) ^ ((1 << (p+1)) - 1)
                sign = (-1) ** ((state & mask).bit_count())
                target = state ^ (1 << p) ^ (1 << q)
                rr.append(lookup[target]); cc.append(col); vv.append(coefficient * sign)
    return coo_matrix((vv, (rr, cc)), shape=(len(basis), len(basis)), dtype=complex).tocsr()


def phase_distance(a, b):
    overlap = np.vdot(b, a)
    return float(np.linalg.norm(a - b * (overlap / abs(overlap) if abs(overlap) else 1)))


def write_csv(path, rows):
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def run(outdir: Path):
    outdir.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    checks = []

    def check(name, value, tolerance, *, minimum=False):
        passed = value >= tolerance if minimum else value <= tolerance
        row = {'check': name, 'value': float(value), 'threshold': tolerance,
               'relation': '>=' if minimum else '<=', 'passed': bool(passed)}
        checks.append(row)
        print(json.dumps(row), flush=True)
        if not passed:
            (outdir / 'failed_checks.json').write_text(json.dumps(checks, indent=2))
            raise AssertionError(name)

    # A single hop must change phase when the intervening spectator is occupied.
    for width, p, q in ((3, 0, 2), (4, 0, 3), (4, 3, 1)):
        h = np.zeros((1 << width, 1 << width), dtype=complex)
        low, high = sorted((p, q))
        for state in range(1 << width):
            if ((state >> low) & 1) != ((state >> high) & 1):
                parity = sum((state >> k) & 1 for k in range(low+1, high))
                target = state ^ (1 << low) ^ (1 << high)
                h[target, state] = -0.7 * (-1)**parity
        qc = QuantumCircuit(width)
        add_fermionic_hopping(qc, p, q, -0.7, 0.23)
        check(f'hopping_matrix_{width}_{p}_{q}', np.max(np.abs(Operator(qc).data - expm(-0.23j*h))), 2e-12)
    dressed = QuantumCircuit(3); bare = QuantumCircuit(3)
    add_fermionic_hopping(dressed, 0, 2, -1, 0.2)
    bare.append(XXPlusYYGate(-0.4), [0, 2])
    check('missing_parity_negative_control', abs(Operator(dressed).data[6,3] - Operator(bare).data[6,3]), 0.3, minimum=True)

    cfg = Cuprate2DConfig(lx=2, ly=2, holes=0, chemical_potential=0.31, steps=1)
    onsite = QuantumCircuit(cfg.qubits); add_onsite_interactions(onsite, cfg, 0.13)
    expected = []
    for state in range(1 << cfg.qubits):
        doubles = sum(((state >> (2*s)) & 3) == 3 for s in range(cfg.sites))
        expected.append(np.exp(-0.13j*(cfg.interaction_u*doubles-cfg.chemical_potential*state.bit_count())))
    check('onsite_U_and_mu_matrix', np.max(np.abs(Operator(onsite).data - np.diag(expected))), 2e-12)

    basis, index, _, _ = sector_basis(cfg)
    oracle = independent_hamiltonian(cfg, basis)
    old_h, _ = build_hamiltonian(cfg, MODEL_FULL)
    check('independent_vs_existing_ED_H', np.max(np.abs((old_h-oracle).toarray())), 1e-12)
    tiny = replace(cfg, dt=1e-6)
    evolution = Operator(build_fermionic_circuit(tiny, prepare=False)).data[np.ix_(basis, basis)]
    generator = 1j*(evolution-evolution.conj().T)/(2*tiny.dt)
    check('full_H_generator', np.max(np.abs(generator-oracle.toarray())), 1e-7)

    # Exact sector conservation and reversibility are checked independently of ED.
    unitary = Operator(build_fermionic_circuit(replace(cfg, dt=0.1), prepare=False)).data
    for spin in (0, 1):
        particles = np.array([sum((state >> (2*s+spin)) & 1 for s in range(cfg.sites))
                              for state in range(1 << cfg.qubits)])
        check(f'N_spin_{spin}_commutator', np.max(np.abs((particles[:,None]-particles[None,:])*unitary)), 2e-12)
    check('unitarity', np.max(np.abs(unitary.conj().T@unitary-np.eye(len(unitary)))), 3e-12)

    dynamics, convergence, site_output = [], [], []
    for lx, ly, holes in ((2,2,0), (2,3,2)):
        cfg = Cuprate2DConfig(lx=lx, ly=ly, holes=holes, steps=1)
        basis, index, nup, ndn = sector_basis(cfg)
        h = independent_hamiltonian(cfg, basis)
        check(f'H_hermiticity_{lx}x{ly}', np.max(np.abs((h-h.conj().T).toarray())), 1e-12)
        initial = initial_state_vector(cfg, index)
        for steps in (1,2,4,8):
            selected = replace(cfg, steps=steps)
            exact = expm_multiply(-1j*h*selected.total_time, initial)
            state = Statevector.from_instruction(build_fermionic_circuit(selected)).data
            sector = state[basis]
            check(f'sector_leakage_{lx}x{ly}_{steps}', abs(1-float(np.vdot(sector,sector).real)), 5e-11)
            exact_rows = diagonal_site_rows(selected, basis, exact, steps, selected.total_time, 'exact_full_hubbard')
            circuit_rows = diagonal_site_rows(selected, basis, sector, steps, selected.total_time, CIRCUIT_FAMILY)
            result = {'lattice': f'{lx}x{ly}', 'steps': steps, 'dt': cfg.dt, 'time': selected.total_time,
                      'state_distance': phase_distance(sector,exact)}
            for name in ('charge','spin_z','double_occupancy'):
                result[name+'_rmse'] = float(np.sqrt(np.mean([(a[name]-b[name])**2 for a,b in zip(exact_rows,circuit_rows)])))
            dynamics.append(result)
            for row in exact_rows+circuit_rows:
                site_output.append({'lattice': f'{lx}x{ly}', **row})
        fixed_time = 0.4
        exact = expm_multiply(-1j*h*fixed_time, initial)
        errors = []
        for steps in (4,8,16):
            selected = replace(cfg, steps=steps, dt=fixed_time/steps)
            sector = Statevector.from_instruction(build_fermionic_circuit(selected)).data[basis]
            error = phase_distance(sector, exact)
            errors.append(error)
            convergence.append({'lattice': f'{lx}x{ly}', 'steps': steps, 'dt': selected.dt,
                                'time': fixed_time, 'state_distance': error})
        for i in range(2):
            check(f'second_order_{lx}x{ly}_{i}', errors[i]/errors[i+1], 3.4, minimum=True)
        check(f'fine_state_distance_{lx}x{ly}', errors[-1], 0.01)

    cfg = Cuprate2DConfig(lx=2, ly=2, holes=0, steps=16, dt=0.05)
    state = Statevector.from_instruction(build_fermionic_circuit(cfg)).data
    free = Statevector.from_instruction(build_fermionic_circuit(replace(cfg,u_over_t=0))).data
    check('U_changes_dynamics', phase_distance(state,free), 0.1, minimum=True)
    # Doping opens diagonal hopping channels that the half-filled 2x2 Neel
    # symmetry suppresses. Keep the signal test distinct from the matrix test.
    doped = replace(cfg, holes=2)
    with_prime = Statevector.from_instruction(build_fermionic_circuit(doped)).data
    no_prime = Statevector.from_instruction(build_fermionic_circuit(replace(doped,t_prime_over_t=0))).data
    check('t_prime_changes_doped_dynamics', phase_distance(with_prime,no_prime), 0.01, minimum=True)
    legacy, _ = build_circuit(cfg, measured=False, circuit_family='number_preserving_t_only')
    check('legacy_is_not_physical_replacement', phase_distance(state,Statevector.from_instruction(legacy).data), 0.1, minimum=True)

    from cuprate_2d_mps_circuit_baseline import apply_circuit_mps, site_rows
    cfg = replace(cfg, steps=2, dt=0.1, chemical_potential=0.11)
    # No truncation in this small-system gate implementation check. Finite
    # cutoff errors belong to a separate MPS convergence study.
    psi, _, _ = apply_circuit_mps(cfg,circuit_family=CIRCUIT_FAMILY,max_bond=64,cutoff=0.0)
    mps_rows = site_rows(cfg,psi,profile='mps')
    basis, index, _, _ = sector_basis(cfg)
    sv = Statevector.from_instruction(build_fermionic_circuit(cfg)).data[basis]
    sv_rows = diagonal_site_rows(cfg,basis,sv,cfg.steps,cfg.total_time,'statevector')
    check('MPS_new_gates_vs_statevector', max(abs(a[k]-b[k]) for a,b in zip(mps_rows,sv_rows)
                                             for k in ('n_up','n_down','double_occupancy')), 1e-10)

    sources = ['cuprate_2d_fermionic_dynamics.py','cuprate_2d_qiskit_circuit.py',
               'cuprate_2d_mps_circuit_baseline.py','validate_cuprate_2d_fermionic_dynamics.py']
    hashes = {name:hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() for name in sources}
    summary = {'passed': all(c['passed'] for c in checks), 'checks': checks, 'dynamics': dynamics,
               'convergence': convergence, 'source_sha256':hashes,'elapsed_seconds':time.perf_counter()-start,
               'boundary':'Small open lattices; finite dt remains approximate; no hardware submission.'}
    (outdir/'validation.json').write_text(json.dumps(summary,indent=2)+'\n')
    write_csv(outdir/'dynamics_rmse.csv',dynamics)
    write_csv(outdir/'trotter_convergence.csv',convergence)
    write_csv(outdir/'site_observables.csv',site_output)
    lines = ['# Full fermionic Hubbard dynamics validation','',f'{len(checks)} numerical checks passed.','',
             'Independent Fock-space Hamiltonian, exact sparse evolution, Qiskit statevectors and MPS agree within the stated checks.',
             '', '| lattice | steps | time | charge RMSE | spin-z RMSE | doublon RMSE |',
             '|---|---:|---:|---:|---:|---:|']
    for r in dynamics:
        lines.append(f"| {r['lattice']} | {r['steps']} | {r['time']:.2f} | {r['charge_rmse']:.6g} | {r['spin_z_rmse']:.6g} | {r['double_occupancy_rmse']:.6g} |")
    lines += ['', 'The RMSE here is Trotter error against exact full Hubbard evolution, without hardware noise.',
              'Fixed-time dt refinement validates second-order convergence; this is not a quantum-advantage result.',
              '', 'All check values, thresholds, convergence rows and source hashes are in validation.json.']
    (outdir/'validation.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'passed':True,'checks':len(checks),'elapsed_seconds':summary['elapsed_seconds'],'report':str(outdir/'validation.md')}))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--outdir',type=Path,required=True)
    run(parser.parse_args().outdir)
