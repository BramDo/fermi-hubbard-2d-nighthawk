#!/usr/bin/env python3
"""Advantage-scale Fermi-Hubbard circuit and resource scaffold.

This file is intentionally separate from toy_fermi_hubbard_experiment.py.

Purpose:
  - Keep the small toy simulation as a local sanity check.
  - Define a paper-scale 1D Fermi-Hubbard configuration like the Q-CTRL
    widest run: L=60 sites, 120 qubits, 30 Trotter steps.
  - Produce auditable resource reports without pretending that local Aer
    simulation of 120 qubits is possible.

This is not a claim of local quantum advantage. A practical-advantage run would
require real hardware execution, calibrated benchmarking against TDVP, and the
error-suppression/runtime stack discussed in arXiv:2605.04025.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import XXPlusYYGate


SPIN_UP = "up"
SPIN_DOWN = "down"
CIRCUIT_FAMILY_LOGICAL = "logical"
CIRCUIT_FAMILY_NATIVE_FSWAP_CZ = "native-fswap-cz"
CIRCUIT_FAMILY_NATIVE_FSWAP_CZ_SKELETON = "native-fswap-cz-skeleton"
CIRCUIT_FAMILY_PHYSICAL_JW = "physical-jw"
SUPPORTED_CIRCUIT_FAMILIES = {
    CIRCUIT_FAMILY_LOGICAL,
    CIRCUIT_FAMILY_NATIVE_FSWAP_CZ,
    CIRCUIT_FAMILY_NATIVE_FSWAP_CZ_SKELETON,
    CIRCUIT_FAMILY_PHYSICAL_JW,
}

PAULI_X = "X"
PAULI_Y = "Y"
PAULI_Z = "Z"


@dataclass(frozen=True)
class MitigationConfig:
    layout_selection: bool = True
    dynamical_decoupling: bool = True
    dd_sequence: str = "XY4"
    dd_scheduling_method: str = "alap"
    pauli_twirling: bool = True
    twirl_randomizations: int = 10
    twirl_strategy: str = "active-accum"
    zne_mitigation: bool = False
    zne_noise_factors: tuple[int, ...] = (1,)
    zne_extrapolator: str = "linear"
    zne_fold_scope: str = "global"
    readout_correction: bool = True
    readout_calibration_shots_per_state: int = 16_384
    decay_recovery: bool = True
    decay_confidence: float = 0.5
    symmetry_postselection: bool = False


@dataclass(frozen=True)
class AdvantageScaleConfig:
    sites: int = 60
    steps: int = 30
    dt: float = 0.2
    hopping: float = 1.0
    interaction_u: float = -2.0
    chemical_potential: float = 0.0
    shots: int = 20_000
    twirls: int = 10
    vacancy_site: int | None = None
    measured: bool = True
    circuit_family: str = CIRCUIT_FAMILY_LOGICAL
    mitigation: MitigationConfig = field(default_factory=MitigationConfig)

    @property
    def qubits(self) -> int:
        return 2 * self.sites

    @property
    def total_time(self) -> float:
        return self.steps * self.dt


@dataclass(frozen=True)
class PaperResourceEstimate:
    sites: int
    qubits: int
    steps: int
    total_time: float
    shots: int
    twirls: int
    native_two_qubit_depth: int
    native_two_qubit_gates: int
    paper_qpu_time_main_seconds: float | None
    paper_qpu_time_with_rem_decay_seconds: float | None
    mitigation_stack: str
    calibration_circuit_count: int
    echo_circuit_count: int
    total_shots_main: int
    total_shots_readout_calibration: int
    notes: str


def pair_interleaved_qubit(site: int, spin: str) -> int:
    """Qubit index for the paper's pair-interleaved JW ordering.

    Sequence:
      c0_down, c0_up, c1_up, c1_down, c2_down, c2_up, ...
    """
    if spin not in {SPIN_UP, SPIN_DOWN}:
        raise ValueError(f"spin must be {SPIN_UP!r} or {SPIN_DOWN!r}")

    if site % 2 == 0:
        return 2 * site if spin == SPIN_DOWN else 2 * site + 1
    return 2 * site if spin == SPIN_UP else 2 * site + 1


def mode_order_for_sites(sites: int) -> list[dict[str, object]]:
    """Return the logical-qubit to fermion-mode map used by this scaffold."""
    modes = []
    for site in range(sites):
        for spin in (SPIN_UP, SPIN_DOWN):
            modes.append(
                {
                    "logical_qubit": pair_interleaved_qubit(site, spin),
                    "site": site,
                    "spin": spin,
                }
            )
    return sorted(modes, key=lambda item: int(item["logical_qubit"]))


def native_fswap_cz_final_mode_order(sites: int, steps: int) -> list[dict[str, object]]:
    """Final logical-qubit to fermion-mode map for the fSWAP network.

    Each physical native step applies one layer of onsite fSWAPs. The mode order
    therefore toggles inside every onsite pair and returns to the initial order
    for even step counts.
    """
    order = [dict(item) for item in mode_order_for_sites(sites)]
    if steps % 2:
        for site in range(sites):
            a, b = 2 * site, 2 * site + 1
            order[a], order[b] = order[b], order[a]
    final_order = []
    for qubit, item in enumerate(order):
        final_order.append(
            {
                "logical_qubit": qubit,
                "site": int(item["site"]),
                "spin": str(item["spin"]),
            }
        )
    return final_order


def initial_logical_bits(cfg: AdvantageScaleConfig) -> list[int]:
    """Initial Neel occupations in logical-qubit order q0, q1, ... ."""
    bits = [0] * cfg.qubits
    for site in range(cfg.sites):
        if cfg.vacancy_site is not None and site == cfg.vacancy_site:
            continue
        spin = SPIN_UP if site % 2 == 0 else SPIN_DOWN
        bits[pair_interleaved_qubit(site, spin)] = 1
    return bits


def qiskit_counts_key_from_logical_bits(bits: list[int]) -> str:
    """Return the Qiskit counts-key display string for c[i] = q[i]."""
    return "".join(str(bits[qubit]) for qubit in reversed(range(len(bits))))


def semantic_mapping_manifest(cfg: AdvantageScaleConfig) -> dict[str, object]:
    """Semantic contract for postprocessing measured bitstrings.

    The circuits in this scaffold use one measured classical register generated
    by measure_all(), which maps logical qubit q[i] to classical bit c[i].
    Qiskit count strings display c[n-1] on the left and c[0] on the right.
    """
    mode_order_initial = mode_order_for_sites(cfg.sites)
    if cfg.circuit_family == CIRCUIT_FAMILY_NATIVE_FSWAP_CZ:
        mode_order_final = native_fswap_cz_final_mode_order(cfg.sites, cfg.steps)
    else:
        mode_order_final = mode_order_initial
    by_qubit = {int(item["logical_qubit"]): item for item in mode_order_final}
    bits = initial_logical_bits(cfg)
    if cfg.circuit_family == CIRCUIT_FAMILY_NATIVE_FSWAP_CZ:
        mode_order_warning = (
            "The native-fswap-cz circuit family uses a fermionic onsite fSWAP "
            "network with explicit final mode-order bookkeeping. For even step "
            "counts the final order equals the initial order; for odd step counts "
            "onsite spin modes are swapped in each site pair."
        )
    elif cfg.circuit_family == CIRCUIT_FAMILY_NATIVE_FSWAP_CZ_SKELETON:
        mode_order_warning = (
            "The native-fswap-cz-skeleton circuit family is a backend-targeted "
            "resource/depth placeholder. It is not a validated fermionic "
            "Hamiltonian implementation and should not be used for physics claims."
        )
    elif cfg.circuit_family == CIRCUIT_FAMILY_PHYSICAL_JW:
        mode_order_warning = (
            "The physical-jw circuit family uses explicit pair-interleaved "
            "Jordan-Wigner Pauli strings. It is physically validated at small L "
            "against dense Trotter and exact-Hamiltonian checks, but it is not "
            "resource optimized for large hardware runs."
        )
    else:
        mode_order_warning = (
            "This logical scaffold does not yet implement dynamic fSWAP mode-order "
            "bookkeeping for a native circuit rewrite. Keep mode_order_final explicit "
            "before making physical charge-density claims."
        )
    return {
        "mode_order_initial": mode_order_initial,
        "mode_order_final": mode_order_final,
        "classical_bit_to_mode": {
            str(qubit): {
                "logical_qubit": qubit,
                "site": by_qubit[qubit]["site"],
                "spin": by_qubit[qubit]["spin"],
            }
            for qubit in range(cfg.qubits)
        },
        "measurement_mapping": "measure_all logical q[i] -> classical c[i]",
        "qiskit_counts_key_order": "leftmost bit is c[n-1]; rightmost bit is c[0]",
        "initial_logical_bits_q0_first": bits,
        "initial_qiskit_counts_key": qiskit_counts_key_from_logical_bits(bits),
        "circuit_family": cfg.circuit_family,
        "mode_order_warning": mode_order_warning,
    }


def onsite_pair(site: int) -> tuple[int, int]:
    return 2 * site, 2 * site + 1


def short_hop_pairs(sites: int) -> list[tuple[int, int]]:
    """Pairs used by HS in the pair-interleaved ordering."""
    return [(2 * j + 1, 2 * j + 2) for j in range(sites - 1)]


def native_skeleton_overhead_pairs(sites: int) -> list[tuple[int, int]]:
    """Two shallow setup layers matching the paper-native resource overhead."""
    hop_pairs = short_hop_pairs(sites)
    return hop_pairs + hop_pairs[:-1]


def add_fswap_skeleton(qc: QuantumCircuit, a: int, b: int) -> None:
    """Add a logical fSWAP skeleton as CZ followed by SWAP.

    This is a logical representation for circuit inspection, not Q-CTRL's native
    Fire Opal decomposition.
    """
    qc.cz(a, b)
    qc.swap(a, b)


def prepare_neel_state(
    qc: QuantumCircuit,
    sites: int,
    vacancy_site: int | None,
) -> None:
    """Prepare |up, down, up, down, ...> with optional central vacancy."""
    for site in range(sites):
        if vacancy_site is not None and site == vacancy_site:
            continue
        spin = SPIN_UP if site % 2 == 0 else SPIN_DOWN
        qc.x(pair_interleaved_qubit(site, spin))


def add_logical_trotter_step(qc: QuantumCircuit, cfg: AdvantageScaleConfig) -> None:
    """Add one paper-inspired logical Trotter step.

    The sequence mirrors the high-level construction:
      RZ half layer, short-hop XX/YY layer, onsite ZZ layer, fSWAP layer,
      second short-hop XX/YY layer, RZ half layer.

    Gate angles use Qiskit's convention RPP(theta)=exp(-i theta P/2).
    """
    rz_angle = (cfg.chemical_potential - 0.5 * cfg.interaction_u) * cfg.dt
    hop_angle = -cfg.hopping * cfg.dt
    zz_angle = 0.5 * cfg.interaction_u * cfg.dt

    for q in range(cfg.qubits):
        qc.rz(0.5 * rz_angle, q)

    for a, b in short_hop_pairs(cfg.sites):
        qc.rxx(hop_angle, a, b)
        qc.ryy(hop_angle, a, b)

    for site in range(cfg.sites):
        a, b = onsite_pair(site)
        qc.rzz(zz_angle, a, b)

    for site in range(cfg.sites):
        a, b = onsite_pair(site)
        add_fswap_skeleton(qc, a, b)

    for a, b in short_hop_pairs(cfg.sites):
        qc.rxx(hop_angle, a, b)
        qc.ryy(hop_angle, a, b)

    for q in range(cfg.qubits):
        qc.rz(0.5 * rz_angle, q)


def pauli_rotation(qc: QuantumCircuit, ops: Mapping[int, str], angle: float) -> None:
    """Append exp(-i * angle * P) for a Pauli string P."""
    if not ops:
        return

    qubits = sorted(int(qubit) for qubit in ops)
    for qubit in qubits:
        op = ops[qubit]
        if op == PAULI_X:
            qc.h(qubit)
        elif op == PAULI_Y:
            qc.sdg(qubit)
            qc.h(qubit)
        elif op != PAULI_Z:
            raise ValueError(f"unsupported Pauli operator {op!r}")

    target = qubits[-1]
    for qubit in qubits[:-1]:
        qc.cx(qubit, target)

    qc.rz(2.0 * angle, target)

    for qubit in reversed(qubits[:-1]):
        qc.cx(qubit, target)

    for qubit in reversed(qubits):
        op = ops[qubit]
        if op == PAULI_X:
            qc.h(qubit)
        elif op == PAULI_Y:
            qc.h(qubit)
            qc.s(qubit)


def jw_hopping_terms(p: int, q: int) -> tuple[dict[int, str], dict[int, str]]:
    """Return pair-interleaved JW XZX and YZY strings for p < q."""
    if p == q:
        raise ValueError("hopping endpoints must be distinct")
    if p > q:
        p, q = q, p
    parity = {index: PAULI_Z for index in range(p + 1, q)}
    return {p: PAULI_X, **parity, q: PAULI_X}, {p: PAULI_Y, **parity, q: PAULI_Y}


def physical_hubbard_terms(cfg: AdvantageScaleConfig) -> list[tuple[float, dict[int, str], str]]:
    """Pauli terms for open-boundary 1D Fermi-Hubbard in pair-interleaved JW order.

    Identity constants from n=(I-Z)/2 and n_up n_down are omitted. They add a
    global phase and do not affect Z-basis observables.
    """
    terms: list[tuple[float, dict[int, str], str]] = []
    for site in range(cfg.sites):
        up = pair_interleaved_qubit(site, SPIN_UP)
        down = pair_interleaved_qubit(site, SPIN_DOWN)
        terms.append((-0.25 * cfg.interaction_u + 0.5 * cfg.chemical_potential, {up: PAULI_Z}, f"onsite_z_up_{site}"))
        terms.append((-0.25 * cfg.interaction_u + 0.5 * cfg.chemical_potential, {down: PAULI_Z}, f"onsite_z_down_{site}"))
        terms.append((0.25 * cfg.interaction_u, {up: PAULI_Z, down: PAULI_Z}, f"onsite_zz_{site}"))

    for site in range(cfg.sites - 1):
        for spin in (SPIN_UP, SPIN_DOWN):
            p = pair_interleaved_qubit(site, spin)
            q = pair_interleaved_qubit(site + 1, spin)
            x_term, y_term = jw_hopping_terms(p, q)
            label = f"hop_{spin}_{site}_{site + 1}"
            terms.append((-0.5 * cfg.hopping, x_term, f"{label}_x"))
            terms.append((-0.5 * cfg.hopping, y_term, f"{label}_y"))

    return terms


def add_physical_jw_trotter_step(qc: QuantumCircuit, cfg: AdvantageScaleConfig) -> None:
    """Add one physically explicit pair-interleaved JW Trotter step."""
    for coefficient, ops, _label in physical_hubbard_terms(cfg):
        pauli_rotation(qc, ops, coefficient * cfg.dt)


def build_logical_circuit(cfg: AdvantageScaleConfig) -> QuantumCircuit:
    qc = QuantumCircuit(cfg.qubits)
    prepare_neel_state(qc, cfg.sites, cfg.vacancy_site)
    for _ in range(cfg.steps):
        add_logical_trotter_step(qc, cfg)
    if cfg.measured:
        qc.measure_all()
    return qc


def build_physical_jw_circuit(
    cfg: AdvantageScaleConfig,
    *,
    steps: int | None = None,
    measured: bool | None = None,
    prepare_initial: bool = True,
) -> QuantumCircuit:
    active_steps = cfg.steps if steps is None else steps
    qc = QuantumCircuit(cfg.qubits)
    if prepare_initial:
        prepare_neel_state(qc, cfg.sites, cfg.vacancy_site)
    for _ in range(active_steps):
        add_physical_jw_trotter_step(qc, cfg)
    should_measure = cfg.measured if measured is None else measured
    if should_measure:
        qc.measure_all()
    return qc


def add_native_cz_layer(
    qc: QuantumCircuit,
    pairs: list[tuple[int, int]],
    *,
    angle: float,
    basis_mixing: bool,
) -> None:
    """Add one resource-layer of native nearest-neighbor CZ primitives.

    The single-qubit rotations keep the layer from being an empty diagonal
    placeholder while leaving the two-qubit count equal to the native CZ count.
    Barriers preserve the intended layer/depth structure through transpilation.
    """
    if not pairs:
        return
    for a, b in pairs:
        if basis_mixing:
            qc.sx(a)
            qc.sx(b)
        qc.rz(0.5 * angle, a)
        qc.rz(-0.5 * angle, b)
        qc.cz(a, b)
        qc.rz(-0.5 * angle, a)
        qc.rz(0.5 * angle, b)
    qc.barrier()


def add_native_onsite_gate(qc: QuantumCircuit, cfg: AdvantageScaleConfig, a: int, b: int) -> None:
    rz_angle = (cfg.chemical_potential - 0.5 * cfg.interaction_u) * cfg.dt
    zz_angle = 0.5 * cfg.interaction_u * cfg.dt
    qc.rz(rz_angle, a)
    qc.rz(rz_angle, b)
    qc.rzz(zz_angle, a, b)


def add_native_hopping_gate(qc: QuantumCircuit, cfg: AdvantageScaleConfig, a: int, b: int) -> None:
    hop_angle = -cfg.hopping * cfg.dt
    # XXPlusYYGate(phi) equals RXX(phi / 2) RYY(phi / 2), up to global phase.
    qc.append(XXPlusYYGate(2.0 * hop_angle), [a, b])


def add_native_fswap_gate(qc: QuantumCircuit, a: int, b: int) -> None:
    qc.cz(a, b)
    qc.swap(a, b)


def adjacent_same_spin_hops(mode_order: list[dict[str, object]]) -> list[tuple[int, int]]:
    pairs = []
    for left in range(len(mode_order) - 1):
        a = mode_order[left]
        b = mode_order[left + 1]
        if a["spin"] == b["spin"] and abs(int(a["site"]) - int(b["site"])) == 1:
            pairs.append((left, left + 1))
    return pairs


def add_native_fswap_cz_physical_prefix(
    qc: QuantumCircuit,
    cfg: AdvantageScaleConfig,
    *,
    steps: int,
) -> list[dict[str, object]]:
    """Add a physical fSWAP/hopping network and return the final mode order."""
    mode_order = [dict(item) for item in mode_order_for_sites(cfg.sites)]
    if steps <= 0:
        return mode_order

    for _ in range(steps):
        for site in range(cfg.sites):
            add_native_onsite_gate(qc, cfg, 2 * site, 2 * site + 1)
        qc.barrier()

        for a, b in adjacent_same_spin_hops(mode_order):
            add_native_hopping_gate(qc, cfg, a, b)
        qc.barrier()

        for site in range(cfg.sites):
            a, b = 2 * site, 2 * site + 1
            add_native_fswap_gate(qc, a, b)
            mode_order[a], mode_order[b] = mode_order[b], mode_order[a]
        qc.barrier()

        for a, b in adjacent_same_spin_hops(mode_order):
            add_native_hopping_gate(qc, cfg, a, b)
        qc.barrier()

    return [
        {
            "logical_qubit": qubit,
            "site": int(mode["site"]),
            "spin": str(mode["spin"]),
        }
        for qubit, mode in enumerate(mode_order)
    ]


def add_native_fswap_cz_skeleton_prefix(
    qc: QuantumCircuit,
    cfg: AdvantageScaleConfig,
    *,
    steps: int,
) -> None:
    """Add a backend-native CZ skeleton for the first ``steps`` Trotter layers.

    This intentionally targets resource/depth reduction first. For L sites, the
    main circuit has ``(5L-2) * steps + 2(L-1)-1`` CZ gates and two-qubit depth
    ``5 * steps + 2`` for steps > 0, matching the paper-native resource shape.
    It is not yet a validated Hamiltonian implementation.
    """
    if steps <= 0:
        return
    hop_angle = -cfg.hopping * cfg.dt
    onsite_angle = 0.5 * cfg.interaction_u * cfg.dt
    fswap_angle = np.pi

    overhead = native_skeleton_overhead_pairs(cfg.sites)
    first_hop_count = len(short_hop_pairs(cfg.sites))
    add_native_cz_layer(qc, overhead[:first_hop_count], angle=hop_angle, basis_mixing=True)
    add_native_cz_layer(qc, overhead[first_hop_count:], angle=-hop_angle, basis_mixing=True)

    onsite = [onsite_pair(site) for site in range(cfg.sites)]
    hops = short_hop_pairs(cfg.sites)
    for _ in range(steps):
        add_native_cz_layer(qc, onsite, angle=onsite_angle, basis_mixing=False)
        add_native_cz_layer(qc, hops, angle=hop_angle, basis_mixing=True)
        add_native_cz_layer(qc, onsite, angle=fswap_angle, basis_mixing=True)
        add_native_cz_layer(qc, hops, angle=-hop_angle, basis_mixing=True)
        add_native_cz_layer(qc, onsite, angle=onsite_angle, basis_mixing=False)


def build_native_fswap_cz_skeleton_circuit(
    cfg: AdvantageScaleConfig,
    *,
    steps: int | None = None,
    measured: bool | None = None,
    prepare_initial: bool = True,
) -> QuantumCircuit:
    if cfg.circuit_family != CIRCUIT_FAMILY_NATIVE_FSWAP_CZ_SKELETON:
        raise ValueError("native skeleton builder requires circuit_family='native-fswap-cz-skeleton'")
    active_steps = cfg.steps if steps is None else steps
    qc = QuantumCircuit(cfg.qubits)
    if prepare_initial:
        prepare_neel_state(qc, cfg.sites, cfg.vacancy_site)
    add_native_fswap_cz_skeleton_prefix(qc, cfg, steps=active_steps)
    should_measure = cfg.measured if measured is None else measured
    if should_measure:
        qc.measure_all()
    return qc


def build_native_fswap_cz_circuit(
    cfg: AdvantageScaleConfig,
    *,
    steps: int | None = None,
    measured: bool | None = None,
    prepare_initial: bool = True,
) -> QuantumCircuit:
    if cfg.circuit_family != CIRCUIT_FAMILY_NATIVE_FSWAP_CZ:
        raise ValueError("native fSWAP/CZ builder requires circuit_family='native-fswap-cz'")
    active_steps = cfg.steps if steps is None else steps
    qc = QuantumCircuit(cfg.qubits)
    if prepare_initial:
        prepare_neel_state(qc, cfg.sites, cfg.vacancy_site)
    add_native_fswap_cz_physical_prefix(qc, cfg, steps=active_steps)
    should_measure = cfg.measured if measured is None else measured
    if should_measure:
        qc.measure_all()
    return qc


def build_main_circuit(cfg: AdvantageScaleConfig) -> QuantumCircuit:
    if cfg.circuit_family == CIRCUIT_FAMILY_LOGICAL:
        return build_logical_circuit(cfg)
    if cfg.circuit_family == CIRCUIT_FAMILY_PHYSICAL_JW:
        return build_physical_jw_circuit(cfg)
    if cfg.circuit_family == CIRCUIT_FAMILY_NATIVE_FSWAP_CZ:
        return build_native_fswap_cz_circuit(cfg)
    if cfg.circuit_family == CIRCUIT_FAMILY_NATIVE_FSWAP_CZ_SKELETON:
        return build_native_fswap_cz_skeleton_circuit(cfg)
    raise ValueError(f"unsupported circuit family: {cfg.circuit_family}")


def runtime_sampler_options(cfg: AdvantageScaleConfig) -> dict[str, object]:
    """IBM Runtime options for mitigation that is supported by SamplerV2.

    DD and gate twirling are requested from the Runtime stack instead of
    hand-inserting backend-specific pulse schedules in this scaffold.
    """
    options: dict[str, object] = {}
    if cfg.mitigation.dynamical_decoupling:
        options["dynamical_decoupling"] = {
            "enable": True,
            "sequence_type": cfg.mitigation.dd_sequence,
            "scheduling_method": cfg.mitigation.dd_scheduling_method,
        }
    if cfg.mitigation.pauli_twirling:
        options["twirling"] = {
            "enable_gates": True,
            "num_randomizations": int(cfg.mitigation.twirl_randomizations),
            "strategy": cfg.mitigation.twirl_strategy,
        }
    return options


def build_readout_calibration_circuits(qubits: int) -> list[QuantumCircuit]:
    """All-0 and all-1 calibration circuits for local readout correction."""
    cal0 = QuantumCircuit(qubits)
    cal0.measure_all()

    cal1 = QuantumCircuit(qubits)
    for qubit in range(qubits):
        cal1.x(qubit)
    cal1.measure_all()

    return [cal0, cal1]


def build_decay_recovery_echo_circuit(cfg: AdvantageScaleConfig, echo_steps: int) -> QuantumCircuit:
    """Build an echo circuit C_k = U^dagger(k) U(k) S_init.

    Qiskit inverts the logical step circuit by reversing gate order and
    inverting each operation. A barrier is inserted between the forward and
    inverse halves so the transpiler cannot cancel away the intended echo
    depth. Hardware-native compiled echo circuits still need backend-aware
    compilation.
    """
    if echo_steps < 0:
        raise ValueError("decay recovery echo_steps must be non-negative")

    qc = QuantumCircuit(cfg.qubits)
    prepare_neel_state(qc, cfg.sites, cfg.vacancy_site)

    if cfg.circuit_family == CIRCUIT_FAMILY_NATIVE_FSWAP_CZ:
        forward = build_native_fswap_cz_circuit(
            cfg,
            steps=echo_steps,
            measured=False,
            prepare_initial=False,
        )
        qc.compose(forward, inplace=True)
        if echo_steps:
            qc.barrier()
        qc.compose(forward.inverse(), inplace=True)
        if cfg.measured:
            qc.measure_all()
        return qc
    if cfg.circuit_family == CIRCUIT_FAMILY_NATIVE_FSWAP_CZ_SKELETON:
        forward = build_native_fswap_cz_skeleton_circuit(
            cfg,
            steps=echo_steps,
            measured=False,
            prepare_initial=False,
        )
        qc.compose(forward, inplace=True)
        if echo_steps:
            qc.barrier()
        qc.compose(forward.inverse(), inplace=True)
        if cfg.measured:
            qc.measure_all()
        return qc
    if cfg.circuit_family == CIRCUIT_FAMILY_PHYSICAL_JW:
        forward = build_physical_jw_circuit(
            cfg,
            steps=echo_steps,
            measured=False,
            prepare_initial=False,
        )
        qc.compose(forward, inplace=True)
        if echo_steps:
            qc.barrier()
        qc.compose(forward.inverse(), inplace=True)
        if cfg.measured:
            qc.measure_all()
        return qc
    if cfg.circuit_family != CIRCUIT_FAMILY_LOGICAL:
        raise ValueError(f"unsupported circuit family: {cfg.circuit_family}")

    step = QuantumCircuit(cfg.qubits, name="fh_step")
    add_logical_trotter_step(step, cfg)

    for _ in range(echo_steps):
        qc.compose(step, inplace=True)
    if echo_steps:
        qc.barrier()
    inverse_step = step.inverse()
    for _ in range(echo_steps):
        qc.compose(inverse_step, inplace=True)

    if cfg.measured:
        qc.measure_all()
    return qc


def decay_recovery_echo_steps(total_steps: int) -> list[int]:
    """Even echo depths matching available Trotter depths."""
    return list(range(0, total_steps + 1, 2))


def all_decay_recovery_echo_steps(total_steps: int) -> list[int]:
    """Every echo depth up to the requested Trotter depth."""
    return list(range(0, total_steps + 1))


def bit_from_qiskit_bitstring(bitstring: str, qubit: int, n_qubits: int) -> int:
    compact = str(bitstring).replace(" ", "").zfill(n_qubits)
    return int(compact[n_qubits - 1 - qubit])


def estimate_local_readout_params(
    counts_all0: Mapping[str, int],
    counts_all1: Mapping[str, int],
    *,
    n_qubits: int,
) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    """Estimate asymmetric per-qubit readout errors p(1|0), p(0|1)."""
    shots0 = float(sum(counts_all0.values()))
    shots1 = float(sum(counts_all1.values()))
    if shots0 <= 0.0 or shots1 <= 0.0:
        raise ValueError("Calibration counts are empty")

    ones_given_0 = np.zeros(n_qubits, dtype=float)
    zeros_given_1 = np.zeros(n_qubits, dtype=float)
    for bitstring, value in counts_all0.items():
        for qubit in range(n_qubits):
            if bit_from_qiskit_bitstring(bitstring, qubit, n_qubits) == 1:
                ones_given_0[qubit] += float(value)
    for bitstring, value in counts_all1.items():
        for qubit in range(n_qubits):
            if bit_from_qiskit_bitstring(bitstring, qubit, n_qubits) == 0:
                zeros_given_1[qubit] += float(value)

    p01 = np.clip(ones_given_0 / shots0, 0.0, 0.499999)
    p10 = np.clip(zeros_given_1 / shots1, 0.0, 0.499999)
    return p01, p10, {
        "shots_all0": int(shots0),
        "shots_all1": int(shots1),
        "p01_mean": float(np.mean(p01)),
        "p10_mean": float(np.mean(p10)),
        "p01_max": float(np.max(p01)),
        "p10_max": float(np.max(p10)),
    }


def aggregate_counts_on_qubits(
    counts: Mapping[Any, Any],
    *,
    n_qubits: int,
    qubits_desc: list[int],
) -> dict[str, int]:
    aggregated: dict[str, int] = {}
    for key, value in counts.items():
        bitstring = format(key, f"0{n_qubits}b") if isinstance(key, int) else str(key).replace(" ", "").zfill(n_qubits)
        sub = "".join("1" if bit_from_qiskit_bitstring(bitstring, q, n_qubits) else "0" for q in qubits_desc)
        aggregated[sub] = aggregated.get(sub, 0) + int(round(float(value)))
    return aggregated


def counts_to_prob_vector(counts: Mapping[str, int], n_qubits: int) -> np.ndarray:
    probs = np.zeros(2**n_qubits, dtype=float)
    total = 0.0
    for bitstring, value in counts.items():
        idx = int(str(bitstring).replace(" ", "").zfill(n_qubits), 2)
        probs[idx] += float(value)
        total += float(value)
    if total <= 0.0:
        raise ValueError("Counts are empty")
    return probs / total


def build_assignment_matrix(p01: np.ndarray, p10: np.ndarray, qubits_desc: list[int]) -> np.ndarray:
    if not qubits_desc:
        raise ValueError("Readout correction qubit subset is empty")
    assignment = np.asarray(
        [
            [1.0 - p01[qubits_desc[0]], p10[qubits_desc[0]]],
            [p01[qubits_desc[0]], 1.0 - p10[qubits_desc[0]]],
        ],
        dtype=float,
    )
    for qubit in qubits_desc[1:]:
        mat = np.asarray(
            [
                [1.0 - p01[qubit], p10[qubit]],
                [p01[qubit], 1.0 - p10[qubit]],
            ],
            dtype=float,
        )
        assignment = np.kron(assignment, mat)
    return assignment


def mitigated_z_expectation_from_counts(
    counts: Mapping[Any, Any],
    *,
    qubits: list[int],
    num_qubits: int,
    p01: np.ndarray,
    p10: np.ndarray,
) -> tuple[float, dict[str, float]]:
    """Correct a low-weight Z-string expectation using local readout matrices."""
    qubits_desc = sorted(qubits, reverse=True)
    sub_counts = aggregate_counts_on_qubits(counts, n_qubits=num_qubits, qubits_desc=qubits_desc)
    p_obs = counts_to_prob_vector(sub_counts, n_qubits=len(qubits_desc))
    assignment = build_assignment_matrix(p01, p10, qubits_desc)
    p_true = np.linalg.pinv(assignment, rcond=1e-12) @ p_obs
    negative_mass = float(-np.minimum(p_true, 0.0).sum())
    p_true = np.clip(p_true, 0.0, None)
    norm = float(p_true.sum())
    if norm <= 0.0:
        raise ValueError("Readout-corrected probability vector has zero mass")
    p_true /= norm

    expectation = 0.0
    for idx, probability in enumerate(p_true):
        bitstring = format(idx, f"0{len(qubits_desc)}b")
        parity = -1.0 if bitstring.count("1") % 2 else 1.0
        expectation += parity * float(probability)
    return float(expectation), {"negative_mass_before_clip": negative_mass}


def particle_numbers_from_bitstring(bitstring: str, sites: int) -> tuple[int, int]:
    n_qubits = 2 * sites
    up_count = 0
    down_count = 0
    for site in range(sites):
        up_count += bit_from_qiskit_bitstring(bitstring, pair_interleaved_qubit(site, SPIN_UP), n_qubits)
        down_count += bit_from_qiskit_bitstring(bitstring, pair_interleaved_qubit(site, SPIN_DOWN), n_qubits)
    return up_count, down_count


def expected_neel_particle_numbers(sites: int, vacancy_site: int | None) -> tuple[int, int]:
    up_count = 0
    down_count = 0
    for site in range(sites):
        if vacancy_site is not None and site == vacancy_site:
            continue
        if site % 2 == 0:
            up_count += 1
        else:
            down_count += 1
    return up_count, down_count


def postselect_particle_number_sector(
    counts: Mapping[Any, Any],
    *,
    sites: int,
    vacancy_site: int | None,
) -> tuple[dict[str, int], dict[str, float]]:
    """Keep only shots preserving N_up and N_down."""
    n_qubits = 2 * sites
    target = expected_neel_particle_numbers(sites, vacancy_site)
    kept: dict[str, int] = {}
    total = 0
    kept_total = 0
    for key, value in counts.items():
        bitstring = format(key, f"0{n_qubits}b") if isinstance(key, int) else str(key).replace(" ", "").zfill(n_qubits)
        count = int(round(float(value)))
        total += count
        if particle_numbers_from_bitstring(bitstring, sites) == target:
            kept[bitstring] = kept.get(bitstring, 0) + count
            kept_total += count
    discard_rate = 1.0 - (kept_total / total if total else 0.0)
    return kept, {
        "target_n_up": float(target[0]),
        "target_n_down": float(target[1]),
        "kept_shots": float(kept_total),
        "total_shots": float(total),
        "discard_rate": float(discard_rate),
    }


def mitigation_manifest(cfg: AdvantageScaleConfig) -> dict[str, object]:
    echo_steps = decay_recovery_echo_steps(cfg.steps) if cfg.mitigation.decay_recovery else []
    shots_per_twirled = (
        cfg.shots // max(int(cfg.mitigation.twirl_randomizations), 1)
        if cfg.mitigation.pauli_twirling
        else cfg.shots
    )
    return {
        "circuit_family": cfg.circuit_family,
        "resource_skeleton": cfg.circuit_family == CIRCUIT_FAMILY_NATIVE_FSWAP_CZ_SKELETON,
        "runtime_sampler_options": runtime_sampler_options(cfg),
        "layout_selection": {
            "enabled": cfg.mitigation.layout_selection,
            "strategy": "quality-chain / avoid high-error qubits when backend properties are available",
        },
        "dynamical_decoupling": {
            "enabled": cfg.mitigation.dynamical_decoupling,
            "sequence": cfg.mitigation.dd_sequence,
            "scheduling_method": cfg.mitigation.dd_scheduling_method,
        },
        "pauli_twirling": {
            "enabled": cfg.mitigation.pauli_twirling,
            "randomizations": cfg.mitigation.twirl_randomizations,
            "shots_per_randomization": shots_per_twirled,
            "strategy": cfg.mitigation.twirl_strategy,
        },
        "zero_noise_extrapolation": {
            "enabled": cfg.mitigation.zne_mitigation,
            "implementation": "client-side global circuit folding for SamplerV2 counts",
            "noise_factors": list(cfg.mitigation.zne_noise_factors),
            "extrapolator": cfg.mitigation.zne_extrapolator,
            "fold_scope": cfg.mitigation.zne_fold_scope,
            "runtime_native_zne": False,
            "note": "SamplerOptions expose DD and twirling in this SamplerV2 workflow, not Estimator-style resilience.zne.",
        },
        "readout_correction": {
            "enabled": cfg.mitigation.readout_correction,
            "model": "independent per-qubit asymmetric assignment matrix",
            "calibration_circuits": 2 if cfg.mitigation.readout_correction else 0,
            "shots_per_calibration_state": cfg.mitigation.readout_calibration_shots_per_state,
        },
        "decay_recovery": {
            "enabled": cfg.mitigation.decay_recovery,
            "confidence": cfg.mitigation.decay_confidence,
            "echo_steps": echo_steps,
            "echo_circuit_count": len(echo_steps),
            "echo_convention": "U_dagger(k) U(k), with a barrier at the echo boundary",
        },
        "symmetry_postselection": {
            "enabled": cfg.mitigation.symmetry_postselection,
            "conserved_quantities": ["N_up", "N_down"],
            "used_for_headline": False,
        },
    }


def qctrl_paper_native_resources(cfg: AdvantageScaleConfig) -> PaperResourceEstimate:
    """Paper formulas from the supplement for native two-qubit resources."""
    native_depth = 5 * cfg.steps + 2
    native_gates = (5 * cfg.sites - 2) * cfg.steps + 2 * (cfg.sites - 1) - 1
    manifest = mitigation_manifest(cfg)
    active_twirls = cfg.mitigation.twirl_randomizations if cfg.mitigation.pauli_twirling else 0

    qpu_main = None
    qpu_with_overhead = None
    if cfg.steps == 30:
        qpu_main = 2 * 60 + 46
        qpu_with_overhead = 4 * 60 + 25
    elif cfg.steps == 60:
        qpu_main = 5 * 60 + 36
        qpu_with_overhead = 8 * 60 + 42
    elif cfg.steps == 90:
        qpu_main = 8 * 60 + 46
        qpu_with_overhead = 13 * 60 + 26

    notes = (
        "Native resource formulas follow arXiv:2605.04025 supplement: "
        "D2Q=5*nstep+2 and N2Q=(5L-2)*nstep+2(L-1)-1. "
        "QPU times are paper-reported only for nstep in {30,60,90}."
    )
    return PaperResourceEstimate(
        sites=cfg.sites,
        qubits=cfg.qubits,
        steps=cfg.steps,
        total_time=cfg.total_time,
        shots=cfg.shots,
        twirls=active_twirls,
        native_two_qubit_depth=native_depth,
        native_two_qubit_gates=native_gates,
        paper_qpu_time_main_seconds=qpu_main,
        paper_qpu_time_with_rem_decay_seconds=qpu_with_overhead,
        mitigation_stack=", ".join(
            name
            for name in [
                "layout_selection",
                "dynamical_decoupling",
                "pauli_twirling",
                "zero_noise_extrapolation",
                "readout_correction",
                "decay_recovery",
                "symmetry_postselection",
            ]
            if bool(manifest[name]["enabled"])
        ),
        calibration_circuit_count=int(manifest["readout_correction"]["calibration_circuits"]),
        echo_circuit_count=int(manifest["decay_recovery"]["echo_circuit_count"]),
        total_shots_main=int(cfg.shots),
        total_shots_readout_calibration=(
            2 * int(cfg.mitigation.readout_calibration_shots_per_state)
            if cfg.mitigation.readout_correction
            else 0
        ),
        notes=notes,
    )


def write_resource_artifacts(cfg: AdvantageScaleConfig, outdir: Path) -> tuple[Path, Path, Path, Path]:
    outdir.mkdir(parents=True, exist_ok=True)
    estimate = qctrl_paper_native_resources(cfg)
    manifest = mitigation_manifest(cfg)

    config_path = outdir / "advantage_scale_config.json"
    csv_path = outdir / "advantage_scale_resources.csv"
    md_path = outdir / "advantage_scale_report.md"
    manifest_path = outdir / "mitigation_manifest.json"

    config_path.write_text(json.dumps(asdict(cfg), indent=2) + "\n")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(estimate)), lineterminator="\n")
        writer.writeheader()
        writer.writerow(asdict(estimate))

    qpu_main = format_seconds(estimate.paper_qpu_time_main_seconds)
    qpu_overhead = format_seconds(estimate.paper_qpu_time_with_rem_decay_seconds)
    validation_text = (
        "For the Q-CTRL widest run, the paper reports TDVP chi=4096 agreement "
        "near 1 percent RMSE up to about t=5.2, then divergence where correctness "
        "is explicitly indeterminate. This scaffold keeps that boundary explicit."
    )

    md_path.write_text(
        "\n".join(
            [
                "# Advantage-Scale 1D Fermi-Hubbard Scaffold",
                "",
                "This is a paper-scale configuration file and resource report, not a local advantage claim.",
                "",
                "## Configuration",
                "",
                f"- sites L: {cfg.sites}",
                f"- qubits: {cfg.qubits}",
                f"- Trotter steps: {cfg.steps}",
                f"- dt: {cfg.dt}",
                f"- total simulated time: {cfg.total_time:g}",
                f"- U/th: {cfg.interaction_u:g}",
                f"- shots per circuit: {cfg.shots}",
                f"- circuit family: {cfg.circuit_family}",
                f"- active Pauli twirls: {estimate.twirls}",
                f"- vacancy site: {cfg.vacancy_site}",
                "",
                "## Mitigation / Suppression Stack",
                "",
                f"- layout selection: {cfg.mitigation.layout_selection}",
                f"- dynamical decoupling: {cfg.mitigation.dynamical_decoupling} ({cfg.mitigation.dd_sequence}, {cfg.mitigation.dd_scheduling_method})",
                f"- Pauli gate twirling: {cfg.mitigation.pauli_twirling} ({cfg.mitigation.twirl_randomizations} randomizations)",
                f"- zero-noise extrapolation: {cfg.mitigation.zne_mitigation} ({list(cfg.mitigation.zne_noise_factors)}, {cfg.mitigation.zne_extrapolator}, {cfg.mitigation.zne_fold_scope})",
                f"- readout correction: {cfg.mitigation.readout_correction} ({cfg.mitigation.readout_calibration_shots_per_state} shots per all-0/all-1 calibration)",
                f"- decay recovery: {cfg.mitigation.decay_recovery} (confidence {cfg.mitigation.decay_confidence})",
                f"- symmetry post-selection: {cfg.mitigation.symmetry_postselection} (available, not used for headline by default)",
                f"- mitigation manifest: `{manifest_path.name}`",
                "",
                "## Paper Native Resource Estimate",
                "",
                f"- two-qubit depth: {estimate.native_two_qubit_depth}",
                f"- two-qubit gates: {estimate.native_two_qubit_gates}",
                f"- paper QPU main-circuit time: {qpu_main}",
                f"- paper QPU time with readout/decay characterization: {qpu_overhead}",
                f"- readout calibration circuits: {estimate.calibration_circuit_count}",
                f"- decay echo circuits: {estimate.echo_circuit_count}",
                f"- total readout calibration shots: {estimate.total_shots_readout_calibration}",
                "",
                "## Framing",
                "",
                validation_text,
                "",
                "A real practical-advantage experiment would still need hardware execution, "
                "runtime error suppression, and a TDVP or equivalent classical baseline.",
                "",
            ]
        )
    )

    return config_path, csv_path, md_path, manifest_path


def two_qubit_count(circuit: QuantumCircuit) -> int:
    return sum(1 for instruction in circuit.data if len(instruction.qubits) == 2)


def two_qubit_depth(circuit: QuantumCircuit) -> int | None:
    try:
        return int(circuit.depth(filter_function=lambda instruction: len(instruction.qubits) == 2))
    except Exception:
        return None


def write_circuit_summary(cfg: AdvantageScaleConfig, outdir: Path) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    qc = build_main_circuit(cfg)
    if cfg.circuit_family == CIRCUIT_FAMILY_NATIVE_FSWAP_CZ:
        path = outdir / "native_fswap_cz_circuit_summary.json"
        warning = (
            "This is the physical native fSWAP/CZ circuit. It uses an onsite "
            "fermionic fSWAP network plus local hopping and onsite gates, and "
            "must pass small-L charge/spin validation before hardware physics claims."
        )
    elif cfg.circuit_family == CIRCUIT_FAMILY_NATIVE_FSWAP_CZ_SKELETON:
        path = outdir / "native_fswap_cz_circuit_summary.json"
        warning = (
            "This is the native-fswap-cz-skeleton resource placeholder. It targets lower "
            "two-qubit count/depth for staging and echo diagnostics, but it is "
            "not yet a validated fermionic fSWAP Hamiltonian implementation."
        )
    elif cfg.circuit_family == CIRCUIT_FAMILY_PHYSICAL_JW:
        path = outdir / "physical_jw_circuit_summary.json"
        warning = (
            "This is the physically explicit pair-interleaved Jordan-Wigner "
            "circuit. It is validated at small L by physical_fermi_hubbard_validation.py, "
            "but it is expected to be much deeper than the native-fswap-cz skeleton."
        )
    else:
        path = outdir / "logical_circuit_summary.json"
        warning = (
            "This is a logical Qiskit skeleton. It is not the native Fire Opal "
            "compiled circuit and should not be compared directly to paper-native "
            "two-qubit depth/gate counts."
        )
    summary = {
        "config": asdict(cfg),
        "circuit_family": cfg.circuit_family,
        "resource_skeleton": cfg.circuit_family == CIRCUIT_FAMILY_NATIVE_FSWAP_CZ_SKELETON,
        "runtime_sampler_options": runtime_sampler_options(cfg),
        "qubits": qc.num_qubits,
        "clbits": qc.num_clbits,
        "depth": qc.depth(),
        "two_qubit_depth": two_qubit_depth(qc),
        "two_qubit_count": two_qubit_count(qc),
        "size": qc.size(),
        "operation_counts": dict(qc.count_ops()),
        "warning": warning,
    }
    path.write_text(json.dumps(summary, indent=2) + "\n")
    return path


def write_mitigation_circuit_summaries(cfg: AdvantageScaleConfig, outdir: Path) -> tuple[Path, Path]:
    """Write circuit-count summaries for calibration and echo circuits."""
    outdir.mkdir(parents=True, exist_ok=True)

    readout_path = outdir / "readout_calibration_circuit_summary.json"
    readout_circuits = build_readout_calibration_circuits(cfg.qubits)
    readout_path.write_text(
        json.dumps(
            {
                "enabled": cfg.mitigation.readout_correction,
                "shots_per_state": cfg.mitigation.readout_calibration_shots_per_state,
                "circuits": [
                    {
                        "index": index,
                        "qubits": circuit.num_qubits,
                        "clbits": circuit.num_clbits,
                        "depth": circuit.depth(),
                        "two_qubit_depth": two_qubit_depth(circuit),
                        "two_qubit_count": two_qubit_count(circuit),
                        "size": circuit.size(),
                        "operation_counts": dict(circuit.count_ops()),
                    }
                    for index, circuit in enumerate(readout_circuits)
                ],
            },
            indent=2,
        )
        + "\n"
    )

    echo_path = outdir / "decay_recovery_echo_circuit_summary.json"
    echo_summaries = []
    if cfg.mitigation.decay_recovery:
        for echo_step in decay_recovery_echo_steps(cfg.steps):
            circuit = build_decay_recovery_echo_circuit(cfg, echo_step)
            echo_summaries.append(
                {
                    "echo_steps": echo_step,
                    "qubits": circuit.num_qubits,
                    "clbits": circuit.num_clbits,
                    "depth": circuit.depth(),
                    "two_qubit_depth": two_qubit_depth(circuit),
                    "two_qubit_count": two_qubit_count(circuit),
                    "size": circuit.size(),
                    "operation_counts": dict(circuit.count_ops()),
                }
            )
    if cfg.circuit_family == CIRCUIT_FAMILY_NATIVE_FSWAP_CZ:
        echo_warning = (
            "Physical native fSWAP/CZ echo circuits use the fSWAP/hopping builder; "
            "backend-native scheduling/compilation is still required before hardware claims."
        )
    elif cfg.circuit_family == CIRCUIT_FAMILY_NATIVE_FSWAP_CZ_SKELETON:
        echo_warning = (
            "Native-fswap-cz-skeleton echo circuits are resource skeletons only; "
            "backend-native scheduling/compilation and physical validation are still required."
        )
    elif cfg.circuit_family == CIRCUIT_FAMILY_PHYSICAL_JW:
        echo_warning = (
            "Physical-jw echo circuits use the validated explicit JW builder; "
            "backend-native scheduling/compilation is still required before hardware claims."
        )
    else:
        echo_warning = "Logical echo circuits only; backend-native scheduling/compilation is still required."

    echo_path.write_text(
        json.dumps(
            {
                "enabled": cfg.mitigation.decay_recovery,
                "confidence": cfg.mitigation.decay_confidence,
                "circuit_family": cfg.circuit_family,
                "resource_skeleton": cfg.circuit_family == CIRCUIT_FAMILY_NATIVE_FSWAP_CZ_SKELETON,
                "circuits": echo_summaries,
                "warning": echo_warning,
            },
            indent=2,
        )
        + "\n"
    )

    return readout_path, echo_path


def write_mitigation_selftest(outdir: Path) -> Path:
    """Exercise local readout correction and particle post-selection on tiny data."""
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / "mitigation_selftest.json"

    counts0 = {"00": 90, "01": 5, "10": 4, "11": 1}
    counts1 = {"11": 88, "10": 6, "01": 5, "00": 1}
    p01, p10, cal = estimate_local_readout_params(counts0, counts1, n_qubits=2)
    raw_counts = {"00": 20, "01": 10, "10": 10, "11": 60}
    zz_exp, zz_meta = mitigated_z_expectation_from_counts(
        raw_counts,
        qubits=[0, 1],
        num_qubits=2,
        p01=p01,
        p10=p10,
    )
    post_counts, post_meta = postselect_particle_number_sector(
        {"01": 40, "10": 40, "00": 10, "11": 10},
        sites=1,
        vacancy_site=None,
    )

    path.write_text(
        json.dumps(
            {
                "readout_calibration": cal,
                "mitigated_zz_expectation": zz_exp,
                "mitigated_zz_metadata": zz_meta,
                "postselected_counts": post_counts,
                "postselection_metadata": post_meta,
            },
            indent=2,
        )
        + "\n"
    )
    return path


def format_seconds(seconds: float | None) -> str:
    if seconds is None:
        return "not reported for this step count"
    minutes, secs = divmod(int(seconds), 60)
    return f"{minutes}m{secs:02d}s"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sites", type=int, default=60)
    parser.add_argument("--steps", type=int, default=30)
    parser.add_argument("--dt", type=float, default=0.2)
    parser.add_argument("--hopping", type=float, default=1.0)
    parser.add_argument("--U", type=float, default=-2.0)
    parser.add_argument("--mu", type=float, default=0.0)
    parser.add_argument("--shots", type=int, default=20_000)
    parser.add_argument("--twirls", type=int, default=10)
    parser.add_argument("--vacancy-site", type=int, default=None)
    parser.add_argument("--no-measure", action="store_true")
    parser.add_argument("--circuit-family", default=CIRCUIT_FAMILY_LOGICAL, choices=sorted(SUPPORTED_CIRCUIT_FAMILIES))
    parser.add_argument("--disable-layout-selection", action="store_true")
    parser.add_argument("--disable-dd", action="store_true")
    parser.add_argument("--dd-sequence", default="XY4")
    parser.add_argument("--dd-scheduling-method", default="alap")
    parser.add_argument("--disable-twirling", action="store_true")
    parser.add_argument("--twirl-strategy", default="active-accum")
    parser.add_argument("--disable-readout-correction", action="store_true")
    parser.add_argument("--readout-cal-shots", type=int, default=16_384)
    parser.add_argument("--disable-decay-recovery", action="store_true")
    parser.add_argument("--decay-confidence", type=float, default=0.5)
    parser.add_argument("--symmetry-postselection", action="store_true")
    parser.add_argument("--outdir", type=Path, default=Path("results_advantage_scale"))
    parser.add_argument(
        "--build-logical-circuit",
        "--build-main-circuit",
        dest="build_logical_circuit",
        action="store_true",
        help="Also build the selected main circuit family and write operation counts.",
    )
    parser.add_argument(
        "--build-mitigation-circuits",
        action="store_true",
        help="Also build readout-calibration and decay-echo logical circuit summaries.",
    )
    parser.add_argument(
        "--mitigation-selftest",
        action="store_true",
        help="Run a tiny local self-test of readout correction and post-selection helpers.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    mitigation = MitigationConfig(
        layout_selection=not args.disable_layout_selection,
        dynamical_decoupling=not args.disable_dd,
        dd_sequence=args.dd_sequence,
        dd_scheduling_method=args.dd_scheduling_method,
        pauli_twirling=not args.disable_twirling,
        twirl_randomizations=args.twirls,
        twirl_strategy=args.twirl_strategy,
        readout_correction=not args.disable_readout_correction,
        readout_calibration_shots_per_state=args.readout_cal_shots,
        decay_recovery=not args.disable_decay_recovery,
        decay_confidence=args.decay_confidence,
        symmetry_postselection=args.symmetry_postselection,
    )
    cfg = AdvantageScaleConfig(
        sites=args.sites,
        steps=args.steps,
        dt=args.dt,
        hopping=args.hopping,
        interaction_u=args.U,
        chemical_potential=args.mu,
        shots=args.shots,
        twirls=args.twirls,
        vacancy_site=args.vacancy_site,
        measured=not args.no_measure,
        circuit_family=args.circuit_family,
        mitigation=mitigation,
    )

    config_path, csv_path, md_path, manifest_path = write_resource_artifacts(cfg, args.outdir)
    print(f"Wrote {config_path}")
    print(f"Wrote {csv_path}")
    print(f"Wrote {md_path}")
    print(f"Wrote {manifest_path}")

    if args.build_logical_circuit:
        circuit_summary = write_circuit_summary(cfg, args.outdir)
        print(f"Wrote {circuit_summary}")

    if args.build_mitigation_circuits:
        readout_summary, echo_summary = write_mitigation_circuit_summaries(cfg, args.outdir)
        print(f"Wrote {readout_summary}")
        print(f"Wrote {echo_summary}")

    if args.mitigation_selftest:
        selftest = write_mitigation_selftest(args.outdir)
        print(f"Wrote {selftest}")


if __name__ == "__main__":
    main()
