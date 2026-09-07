"""Full t-t'-U Hubbard dynamics with JW signs and a symmetric product formula.

Modes are row-major and spin-interleaved: up=2*site, down=2*site+1.
H = sum_b c_b (a_p^dagger a_q + h.c.) + U sum_i n_up n_down - mu N,
where c_b=-t or -t'. Qiskit basis indices use little-endian occupation bits.
This is a correctness route; the extra parity gates still require hardware
routing and a new, circuit-matched classical baseline.
"""
from __future__ import annotations

from qiskit import QuantumCircuit
from qiskit.circuit.library import XXPlusYYGate

from cuprate_2d_hubbard_pipeline import (
    Cuprate2DConfig, SPINS, all_hopping_bonds, initial_site_rows,
    mode_qubit, validate_config,
)

CIRCUIT_FAMILY = 'fermionic_jw_symmetric'


def add_fermionic_hopping(qc: QuantumCircuit, p: int, q: int,
                          coefficient: float, duration: float) -> None:
    """Append exp[-i duration*c*(a_p^dagger a_q + h.c.)] exactly.

    C=product_{p<k<q} CZ(k,q) dresses X_q and Y_q with the intervening Z
    parity string. Thus C XXPlusYY(2*c*duration) C is the fermionic hop.
    The dressing is uncomputed and the mode order never changes.
    """
    if p == q or min(p, q) < 0 or max(p, q) >= qc.num_qubits:
        raise ValueError('Hopping requires two distinct in-range modes')
    p, q = sorted((p, q))
    if coefficient == 0 or duration == 0:
        return
    for spectator in range(p + 1, q):
        qc.cz(spectator, q)
    qc.append(XXPlusYYGate(2.0 * coefficient * duration), [p, q])
    for spectator in reversed(range(p + 1, q)):
        qc.cz(spectator, q)


def add_onsite_interactions(qc: QuantumCircuit, cfg: Cuprate2DConfig,
                            duration: float) -> None:
    """Exact onsite evolution, including its identity/global-phase part."""
    for site in range(cfg.sites):
        up, down = 2 * site, 2 * site + 1
        if cfg.interaction_u != 0:
            qc.cp(-cfg.interaction_u * duration, up, down)
        if cfg.chemical_potential != 0:
            qc.p(cfg.chemical_potential * duration, up)
            qc.p(cfg.chemical_potential * duration, down)


def hopping_operations(cfg: Cuprate2DConfig) -> list[tuple[int, int, float]]:
    return [(mode_qubit(int(b['site_a']), spin),
             mode_qubit(int(b['site_b']), spin), float(b['coefficient']))
            for b in all_hopping_bonds(cfg) for spin in SPINS]


def add_symmetric_step(qc: QuantumCircuit, cfg: Cuprate2DConfig) -> None:
    """Palindromic second-order splitting, with the U interaction in the middle.

    Each hop is applied for dt/2, then all onsite terms for dt, followed by
    the reversed hop list for dt/2. Local error is O(dt^3), global O(dt^2)
    at fixed physical time. Noncommuting hopping bonds are not regrouped.
    """
    operations = hopping_operations(cfg)
    for p, q, coefficient in operations:
        add_fermionic_hopping(qc, p, q, coefficient, cfg.dt / 2)
    add_onsite_interactions(qc, cfg, cfg.dt)
    for p, q, coefficient in reversed(operations):
        add_fermionic_hopping(qc, p, q, coefficient, cfg.dt / 2)


def build_fermionic_circuit(cfg: Cuprate2DConfig, *, measured: bool = False,
                             prepare: bool = True) -> QuantumCircuit:
    validate_config(cfg)
    qc = QuantumCircuit(cfg.qubits)
    if prepare:
        for row in initial_site_rows(cfg):
            for spin in SPINS:
                if int(row[f'n_{spin}_initial']):
                    qc.x(mode_qubit(int(row['site']), spin))
    for _ in range(cfg.steps):
        add_symmetric_step(qc, cfg)
    qc.metadata = {
        'model': 'full_2d_fermi_hubbard', 'circuit_family': CIRCUIT_FAMILY,
        'fermionic_parity_strings': True, 'includes_t_prime': True,
        'includes_onsite_U': True, 'trotter_order': 2,
        'steps': cfg.steps, 'dt': cfg.dt, 'time': cfg.total_time,
        'mode_order': 'row_major_spin_interleaved',
        'mode_order_restored': True,
    }
    if measured:
        qc.measure_all()
    return qc
