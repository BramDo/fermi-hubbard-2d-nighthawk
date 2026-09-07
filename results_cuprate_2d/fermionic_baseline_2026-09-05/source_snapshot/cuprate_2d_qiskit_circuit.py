#!/usr/bin/env python3
"""Build an explicit Jordan-Wigner Qiskit circuit for the 2D cuprate target.

This exports a real quantum circuit for the separate 2D Hubbard pipeline. The
implementation is deliberately conservative: row-major Jordan-Wigner strings
and first-order Trotter Pauli rotations. It is useful as a correctness and
bookkeeping circuit, not yet a hardware-optimized 2D fermionic routing.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from qiskit import QuantumCircuit, qpy
from qiskit.circuit.library import XXPlusYYGate
import qiskit.qasm2 as qasm2

from advantage_scale_fermi_hubbard_model import (
    PAULI_Z,
    jw_hopping_terms,
    pauli_rotation,
)
from cuprate_2d_hubbard_pipeline import (
    SPIN_DOWN,
    SPIN_UP,
    SPINS,
    Cuprate2DConfig,
    all_hopping_bonds,
    initial_site_rows,
    mode_qubit,
    validate_config,
)

CIRCUIT_FAMILY_EXPLICIT_JW = "explicit_jw"
CIRCUIT_FAMILY_NUMBER_PRESERVING_T_ONLY = "number_preserving_t_only"
CIRCUIT_FAMILY_NUMBER_PRESERVING_T_TPRIME = "number_preserving_t_tprime"
CIRCUIT_FAMILY_FERMIONIC_SYMMETRIC = "fermionic_jw_symmetric"
CIRCUIT_FAMILY_FSWAP_NETWORK = "fermionic_fswap_network"
CIRCUIT_FAMILY_FSWAP_ADAPTIVE = "fermionic_fswap_adaptive"
SUPPORTED_CIRCUIT_FAMILIES = (
    CIRCUIT_FAMILY_EXPLICIT_JW,
    CIRCUIT_FAMILY_NUMBER_PRESERVING_T_ONLY,
    CIRCUIT_FAMILY_NUMBER_PRESERVING_T_TPRIME,
    CIRCUIT_FAMILY_FERMIONIC_SYMMETRIC,
    CIRCUIT_FAMILY_FSWAP_NETWORK,
    CIRCUIT_FAMILY_FSWAP_ADAPTIVE,
)


def load_config(path: Path) -> Cuprate2DConfig:
    raw = json.loads(path.read_text())
    return Cuprate2DConfig(
        lx=int(raw["lx"]),
        ly=int(raw["ly"]),
        holes=int(raw["holes"]),
        hopping_t=float(raw["hopping_t"]),
        t_prime_over_t=float(raw["t_prime_over_t"]),
        u_over_t=float(raw["u_over_t"]),
        chemical_potential=float(raw["chemical_potential"]),
        steps=int(raw["steps"]),
        dt=float(raw["dt"]),
        boundary_x=str(raw["boundary_x"]),
        boundary_y=str(raw["boundary_y"]),
        initial_state=str(raw["initial_state"]),
        shots=int(raw.get("shots", 20_000)),
    )


def prepare_initial_state(qc: QuantumCircuit, cfg: Cuprate2DConfig) -> None:
    for row in initial_site_rows(cfg):
        site = int(row["site"])
        if int(row["n_up_initial"]):
            qc.x(mode_qubit(site, SPIN_UP))
        if int(row["n_down_initial"]):
            qc.x(mode_qubit(site, SPIN_DOWN))


def physical_2d_hubbard_terms(cfg: Cuprate2DConfig) -> list[tuple[float, dict[int, str], str]]:
    """Return Pauli coefficients for the row-major JW 2D Hubbard Hamiltonian.

    Identity constants from n=(I-Z)/2 and n_up n_down are omitted. The hopping
    coefficient in the bond list is the coefficient multiplying
    c_i^dagger c_j + h.c.; JW maps that term to 0.5*(XZX + YZY).
    """
    terms: list[tuple[float, dict[int, str], str]] = []

    onsite_z = -0.25 * cfg.interaction_u + 0.5 * cfg.chemical_potential
    onsite_zz = 0.25 * cfg.interaction_u
    for site in range(cfg.sites):
        up = mode_qubit(site, SPIN_UP)
        down = mode_qubit(site, SPIN_DOWN)
        terms.append((onsite_z, {up: PAULI_Z}, f"onsite_z_up_{site}"))
        terms.append((onsite_z, {down: PAULI_Z}, f"onsite_z_down_{site}"))
        terms.append((onsite_zz, {up: PAULI_Z, down: PAULI_Z}, f"onsite_zz_{site}"))

    for bond in all_hopping_bonds(cfg):
        site_a = int(bond["site_a"])
        site_b = int(bond["site_b"])
        coefficient = 0.5 * float(bond["coefficient"])
        family = str(bond["family"])
        orientation = str(bond["orientation"])
        for spin in SPINS:
            p = mode_qubit(site_a, spin)
            q = mode_qubit(site_b, spin)
            x_term, y_term = jw_hopping_terms(p, q)
            label = f"{family}_{orientation}_{spin}_{site_a}_{site_b}"
            terms.append((coefficient, x_term, f"{label}_x"))
            terms.append((coefficient, y_term, f"{label}_y"))

    return terms


def add_trotter_step(qc: QuantumCircuit, cfg: Cuprate2DConfig, terms: list[tuple[float, dict[int, str], str]]) -> None:
    for coefficient, ops, _label in terms:
        pauli_rotation(qc, ops, coefficient * cfg.dt)


def add_onsite_terms(qc: QuantumCircuit, cfg: Cuprate2DConfig) -> None:
    onsite_z = -0.25 * cfg.interaction_u + 0.5 * cfg.chemical_potential
    onsite_zz = 0.25 * cfg.interaction_u
    for site in range(cfg.sites):
        up = mode_qubit(site, SPIN_UP)
        down = mode_qubit(site, SPIN_DOWN)
        qc.rz(2.0 * onsite_z * cfg.dt, up)
        qc.rz(2.0 * onsite_z * cfg.dt, down)
        qc.rzz(2.0 * onsite_zz * cfg.dt, up, down)


def greedy_hopping_layers(pairs: list[tuple[int, int, float]]) -> list[list[tuple[int, int, float]]]:
    layers: list[list[tuple[int, int, float]]] = []
    occupied: list[set[int]] = []
    for a, b, coefficient in pairs:
        for index, used in enumerate(occupied):
            if a not in used and b not in used:
                layers[index].append((a, b, coefficient))
                used.update({a, b})
                break
        else:
            layers.append([(a, b, coefficient)])
            occupied.append({a, b})
    return layers


def add_number_preserving_hopping_ansatz(qc: QuantumCircuit, cfg: Cuprate2DConfig, *, include_tprime: bool) -> None:
    pairs: list[tuple[int, int, float]] = []
    for bond in all_hopping_bonds(cfg):
        if str(bond["family"]) == "next_nearest_t_prime" and not include_tprime:
            continue
        for spin in SPINS:
            pairs.append(
                (
                    mode_qubit(int(bond["site_a"]), spin),
                    mode_qubit(int(bond["site_b"]), spin),
                    float(bond["coefficient"]),
                )
            )
    for layer in greedy_hopping_layers(pairs):
        for a, b, coefficient in layer:
            qc.append(XXPlusYYGate(2.0 * coefficient * cfg.dt), [a, b])
        qc.barrier()


def build_circuit(
    cfg: Cuprate2DConfig,
    *,
    measured: bool,
    circuit_family: str = CIRCUIT_FAMILY_EXPLICIT_JW,
) -> tuple[QuantumCircuit, list[tuple[float, dict[int, str], str]]]:
    if circuit_family not in SUPPORTED_CIRCUIT_FAMILIES:
        raise ValueError(f"Unsupported circuit_family {circuit_family!r}")
    terms = physical_2d_hubbard_terms(cfg)
    if circuit_family in {CIRCUIT_FAMILY_FSWAP_NETWORK, CIRCUIT_FAMILY_FSWAP_ADAPTIVE}:
        from cuprate_2d_fermionic_mapping import build_network, build_adaptive
        builder = build_network if circuit_family == CIRCUIT_FAMILY_FSWAP_NETWORK else build_adaptive
        return builder(cfg, measured=measured), terms
    if circuit_family == CIRCUIT_FAMILY_FERMIONIC_SYMMETRIC:
        from cuprate_2d_fermionic_dynamics import build_fermionic_circuit
        return build_fermionic_circuit(cfg, measured=measured), terms
    qc = QuantumCircuit(cfg.qubits)
    prepare_initial_state(qc, cfg)
    if circuit_family == CIRCUIT_FAMILY_EXPLICIT_JW:
        for _ in range(cfg.steps):
            add_trotter_step(qc, cfg, terms)
    else:
        include_tprime = circuit_family == CIRCUIT_FAMILY_NUMBER_PRESERVING_T_TPRIME
        for _ in range(cfg.steps):
            add_onsite_terms(qc, cfg)
            add_number_preserving_hopping_ansatz(qc, cfg, include_tprime=include_tprime)
    if measured:
        qc.measure_all()
    return qc, terms


def two_qubit_depth(circuit: QuantumCircuit) -> int | None:
    try:
        return int(circuit.depth(filter_function=lambda instruction: len(instruction.qubits) == 2))
    except Exception:
        return None


def term_rows(cfg: Cuprate2DConfig, terms: list[tuple[float, dict[int, str], str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for coefficient, ops, label in terms:
        rows.append(
            {
                "label": label,
                "coefficient": coefficient,
                "single_step_angle": coefficient * cfg.dt,
                "pauli_weight": len(ops),
                "qubits": " ".join(str(qubit) for qubit in sorted(ops)),
                "paulis": " ".join(ops[qubit] for qubit in sorted(ops)),
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("")
        return
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_report(path: Path, summary: dict[str, Any]) -> None:
    config = summary["config"]
    family = summary['circuit_family']
    method = (
        'It includes full JW parity, t and t-prime hopping, onsite U and second-order symmetric splitting.'
        if family in {CIRCUIT_FAMILY_FERMIONIC_SYMMETRIC, CIRCUIT_FAMILY_FSWAP_NETWORK, CIRCUIT_FAMILY_FSWAP_ADAPTIVE} else
        'It uses explicit row-major Jordan-Wigner strings and first-order Trotterization.'
        if family == CIRCUIT_FAMILY_EXPLICIT_JW else
        'This legacy shallow ansatz omits nonlocal JW strings; it is not the full fermionic Hamiltonian.'
    )
    lines = [
        "# 2D Cuprate Hubbard Qiskit Circuit",
        "",
        "This is a real Qiskit circuit for the separate 2D cuprate Hubbard target.",
        method,
        "",
        "## Target",
        "",
        f"- lattice: {config['lx']}x{config['ly']}",
        f"- sites/qubits: {summary['sites']}/{summary['qubits']}",
        f"- holes/doping: {config['holes']}/{summary['hole_doping']:.6f}",
        f"- U/t: {config['u_over_t']}",
        f"- t'/t: {config['t_prime_over_t']}",
        f"- steps/dt/time: {config['steps']}/{config['dt']}/{summary['total_time']}",
        "",
        "## Circuit",
        "",
        f"- qiskit circuit family: `{summary['circuit_family']}`",
        f"- measured: {summary['measured']}",
        f"- Hamiltonian Pauli terms per step: {summary['pauli_terms_per_step']}",
        f"- circuit depth: {summary['depth']}",
        f"- two-qubit depth: {summary['two_qubit_depth']}",
        f"- operation counts: `{summary['operation_counts']}`",
        "",
        "## Artifacts",
        "",
        f"- QPY: `{summary['artifacts']['qpy']}`",
        f"- OpenQASM 2: `{summary['artifacts']['qasm2']}`",
        f"- terms CSV: `{summary['artifacts']['terms_csv']}`",
        f"- summary JSON: `{summary['artifacts']['summary_json']}`",
        "",
        "Claim boundary: this is not yet hardware-routed. A hardware run still needs layout/routing, backend inspection, and a submit gate.",
        "",
    ]
    path.write_text("\n".join(lines))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a 2D cuprate Hubbard Qiskit circuit.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--circuit-family", choices=SUPPORTED_CIRCUIT_FAMILIES, default=CIRCUIT_FAMILY_EXPLICIT_JW)
    parser.add_argument("--no-measure", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)
    validate_config(cfg)
    args.outdir.mkdir(parents=True, exist_ok=True)

    qc, terms = build_circuit(cfg, measured=not args.no_measure, circuit_family=args.circuit_family)
    circuit_stem = ("cuprate_2d_fermionic_jw_symmetric" if args.circuit_family == CIRCUIT_FAMILY_FERMIONIC_SYMMETRIC
                    else "cuprate_2d_explicit_jw_trotter")
    qpy_path = args.outdir / f"{circuit_stem}.qpy"
    qasm_path = args.outdir / f"{circuit_stem}.qasm"
    terms_csv = args.outdir / "cuprate_2d_explicit_jw_terms.csv"
    summary_json = args.outdir / "cuprate_2d_qiskit_circuit_summary.json"
    report_md = args.outdir / "cuprate_2d_qiskit_circuit_report.md"

    with qpy_path.open("wb") as handle:
        qpy.dump(qc, handle)
    qasm_path.write_text(qasm2.dumps(qc))
    write_csv(terms_csv, term_rows(cfg, terms))

    operation_counts = {str(name): int(count) for name, count in qc.count_ops().items()}
    summary = {
        "circuit_family": args.circuit_family,
        "claim_boundary": (
            "Real Qiskit circuit for the 2D Hubbard target. The explicit_jw family is the current "
            "row-major JW reference; fermionic_jw_symmetric includes full parity and t-t'-U with second-order splitting. "
            "number_preserving_* families are shallow resource candidates "
            "that omit nonlocal row-major JW parity strings and need separate validation before physics claims."
        ),
        "config": asdict(cfg),
        "sites": cfg.sites,
        "qubits": qc.num_qubits,
        "hole_doping": cfg.hole_doping,
        "total_time": cfg.total_time,
        "measured": not args.no_measure,
        "pauli_terms_per_step": len(terms),
        "depth": qc.depth(),
        "two_qubit_depth": two_qubit_depth(qc),
        "operation_counts": operation_counts,
        "artifacts": {
            "qpy": qpy_path.as_posix(),
            "qasm2": qasm_path.as_posix(),
            "terms_csv": terms_csv.as_posix(),
            "summary_json": summary_json.as_posix(),
            "report_md": report_md.as_posix(),
        },
    }
    summary_json.write_text(json.dumps(summary, indent=2) + "\n")
    write_report(report_md, summary)
    print(report_md)


if __name__ == "__main__":
    main()
