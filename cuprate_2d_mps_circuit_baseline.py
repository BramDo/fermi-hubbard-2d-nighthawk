#!/usr/bin/env python3
"""Quimb MPS baseline for shallow 2D cuprate hardware circuits.

This simulates the circuit family submitted to hardware. It is a tensor-network
circuit reference, not a Hamiltonian TDVP convergence proof for the full 2D
Hubbard model.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import time
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import numpy as np
import quimb.tensor as qtn

from cuprate_2d_hubbard_pipeline import (
    SPIN_DOWN,
    SPIN_UP,
    Cuprate2DConfig,
    all_hopping_bonds,
    mode_qubit,
    site_coord,
    validate_config,
)
from cuprate_2d_qiskit_circuit import SUPPORTED_CIRCUIT_FAMILIES, build_circuit, load_config


Z = np.asarray([[1.0, 0.0], [0.0, -1.0]], dtype=complex)
X = np.asarray([[0.0, 1.0], [1.0, 0.0]], dtype=complex)
ZZ = np.kron(Z, Z)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("")
        return
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def parse_int_list(value: str) -> list[int]:
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def rz_matrix(theta: float) -> np.ndarray:
    return np.asarray(
        [[np.exp(-0.5j * theta), 0.0], [0.0, np.exp(0.5j * theta)]],
        dtype=complex,
    )


def rzz_matrix(theta: float) -> np.ndarray:
    return np.diag(
        [
            np.exp(-0.5j * theta),
            np.exp(0.5j * theta),
            np.exp(0.5j * theta),
            np.exp(-0.5j * theta),
        ]
    ).astype(complex)


def xxyy_matrix(theta: float) -> np.ndarray:
    """Matrix convention matching Qiskit's XXPlusYYGate(theta, beta=0)."""
    c = math.cos(0.5 * theta)
    s = -1.0j * math.sin(0.5 * theta)
    return np.asarray(
        [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, c, s, 0.0],
            [0.0, s, c, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=complex,
    )


def qubit_index(circuit: Any, qubit: Any) -> int:
    try:
        return int(circuit.find_bit(qubit).index)
    except Exception:
        index = getattr(qubit, "_index", None)
        if index is None:
            raise
        return int(index)


def circuit_operation(instruction: Any) -> Any:
    if hasattr(instruction, "operation"):
        return instruction.operation
    return instruction[0]


def max_bond_dimension(psi: qtn.MatrixProductState) -> int:
    return int(max(psi.bond_sizes())) if psi.num_tensors > 1 else 1


def apply_circuit_mps(
    cfg: Cuprate2DConfig,
    *,
    circuit_family: str,
    max_bond: int,
    cutoff: float,
) -> tuple[qtn.MatrixProductState, list[dict[str, Any]], dict[str, Any]]:
    circuit, _terms = build_circuit(cfg, measured=False, circuit_family=circuit_family)
    bits = ["0"] * cfg.qubits
    for instruction in circuit.data:
        op = circuit_operation(instruction)
        if op.name == "x":
            q = qubit_index(circuit, instruction.qubits[0])
            bits[q] = "1" if bits[q] == "0" else "0"
        elif op.name not in {"barrier"}:
            break

    psi = qtn.MPS_computational_state("".join(bits), dtype="complex128")
    gate_count = 0
    two_qubit_gate_count = 0
    diagnostics: list[dict[str, Any]] = []
    for instruction in circuit.data:
        op = circuit_operation(instruction)
        name = str(op.name)
        qubits = [qubit_index(circuit, qubit) for qubit in instruction.qubits]
        if name == "barrier":
            diagnostics.append(
                {
                    "after_gate": gate_count,
                    "barrier_index": len(diagnostics),
                    "max_bond_observed": max_bond_dimension(psi),
                }
            )
            continue
        if name == "x":
            continue
        if name == "rz":
            psi.gate_(rz_matrix(float(op.params[0])), qubits[0], contract=True)
            gate_count += 1
            continue
        if name == "rzz":
            psi.gate_(
                rzz_matrix(float(op.params[0])),
                tuple(qubits),
                contract="swap+split",
                max_bond=max_bond,
                cutoff=cutoff,
            )
            gate_count += 1
            two_qubit_gate_count += 1
            continue
        if name == "xx_plus_yy":
            theta = float(op.params[0])
            beta = float(op.params[1]) if len(op.params) > 1 else 0.0
            if abs(beta) > 1e-15:
                raise ValueError("Only XXPlusYYGate beta=0 is supported")
            psi.gate_(
                xxyy_matrix(theta),
                tuple(qubits),
                contract="swap+split",
                max_bond=max_bond,
                cutoff=cutoff,
            )
            gate_count += 1
            two_qubit_gate_count += 1
            continue
        if name in {"cz", "cp", "p"}:
            matrix = np.asarray(op.to_matrix(), dtype=complex)
            if len(qubits) == 1:
                psi.gate_(matrix, qubits[0], contract=True)
            else:
                # CZ and controlled phase are symmetric under qubit reversal.
                psi.gate_(matrix, tuple(qubits), contract="swap+split",
                          max_bond=max_bond, cutoff=cutoff)
                two_qubit_gate_count += 1
            gate_count += 1
            continue
        raise ValueError(f"Unsupported circuit operation in MPS baseline: {name}")

    psi.normalize()
    metadata = {
        "logical_depth": int(circuit.depth() or 0),
        "logical_size": int(circuit.size() or 0),
        "operation_counts": dict(circuit.count_ops()),
        "applied_gate_count": gate_count,
        "applied_two_qubit_gate_count": two_qubit_gate_count,
        "max_bond_observed": max_bond_dimension(psi),
        "barrier_diagnostics": diagnostics,
    }
    return psi, diagnostics, metadata


def local_expectation(psi: qtn.MatrixProductState, operator: np.ndarray, where: int | tuple[int, int]) -> float:
    value = psi.local_expectation_canonical(operator, where, normalized=True)
    return float(np.real_if_close(value))


def pair_occupation(psi: qtn.MatrixProductState, z_by_qubit: list[float], a: int, b: int) -> float:
    zz = local_expectation(psi, ZZ, (a, b))
    return 0.25 * (1.0 - z_by_qubit[a] - z_by_qubit[b] + zz)


def site_rows(
    cfg: Cuprate2DConfig,
    psi: qtn.MatrixProductState,
    *,
    profile: str,
) -> list[dict[str, Any]]:
    z_by_qubit = [local_expectation(psi, Z, qubit) for qubit in range(cfg.qubits)]
    rows: list[dict[str, Any]] = []
    for site in range(cfg.sites):
        x, y = site_coord(cfg, site)
        up = mode_qubit(site, SPIN_UP)
        down = mode_qubit(site, SPIN_DOWN)
        n_up = 0.5 * (1.0 - z_by_qubit[up])
        n_down = 0.5 * (1.0 - z_by_qubit[down])
        charge = n_up + n_down
        spin = n_up - n_down
        double = pair_occupation(psi, z_by_qubit, up, down)
        rows.append(
            {
                "profile": profile,
                "step": cfg.steps,
                "time": cfg.total_time,
                "site": site,
                "x": x,
                "y": y,
                "n_up": float(n_up),
                "n_down": float(n_down),
                "charge": float(charge),
                "spin_z": float(spin),
                "hole_density": float(1.0 - charge),
                "double_occupancy": float(double),
            }
        )
    return rows


def bond_rows(
    cfg: Cuprate2DConfig,
    psi: qtn.MatrixProductState,
    *,
    profile: str,
) -> list[dict[str, Any]]:
    z_by_qubit = [local_expectation(psi, Z, qubit) for qubit in range(cfg.qubits)]
    rows: list[dict[str, Any]] = []
    for bond in [item for item in all_hopping_bonds(cfg) if str(item["family"]) == "nearest_t"]:
        site_a = int(bond["site_a"])
        site_b = int(bond["site_b"])
        a_up = mode_qubit(site_a, SPIN_UP)
        a_down = mode_qubit(site_a, SPIN_DOWN)
        b_up = mode_qubit(site_b, SPIN_UP)
        b_down = mode_qubit(site_b, SPIN_DOWN)
        uu = pair_occupation(psi, z_by_qubit, a_up, b_up)
        ud = pair_occupation(psi, z_by_qubit, a_up, b_down)
        du = pair_occupation(psi, z_by_qubit, a_down, b_up)
        dd = pair_occupation(psi, z_by_qubit, a_down, b_down)
        rows.append(
            {
                "profile": profile,
                "orientation": bond["orientation"],
                "site_a": site_a,
                "x_a": int(bond["x_a"]),
                "y_a": int(bond["y_a"]),
                "site_b": site_b,
                "x_b": int(bond["x_b"]),
                "y_b": int(bond["y_b"]),
                "charge_correlation": float(uu + ud + du + dd),
                "spin_z_correlation": float(uu - ud - du + dd),
            }
        )
    return rows


def summarize_site_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    charges = np.asarray([float(row["charge"]) for row in rows])
    spins = np.asarray([float(row["spin_z"]) for row in rows])
    doubles = np.asarray([float(row["double_occupancy"]) for row in rows])
    return {
        "total_charge": float(np.sum(charges)),
        "total_spin_z": float(np.sum(spins)),
        "mean_charge": float(np.mean(charges)),
        "mean_abs_spin_z": float(np.mean(np.abs(spins))),
        "mean_double_occupancy": float(np.mean(doubles)),
        "min_charge": float(np.min(charges)),
        "max_charge": float(np.max(charges)),
    }


def occupation_rmse(a: list[dict[str, Any]], b: list[dict[str, Any]]) -> float:
    a_values: list[float] = []
    b_values: list[float] = []
    for row_a, row_b in zip(sorted(a, key=lambda row: int(row["site"])), sorted(b, key=lambda row: int(row["site"])), strict=True):
        a_values.extend([float(row_a["n_up"]), float(row_a["n_down"])])
        b_values.extend([float(row_b["n_up"]), float(row_b["n_down"])])
    return float(np.sqrt(np.mean((np.asarray(a_values) - np.asarray(b_values)) ** 2)))


def write_report(path: Path, summary: dict[str, Any]) -> None:
    lx = summary["config"]["lx"]
    ly = summary["config"]["ly"]
    lines = [
        f"# {lx}x{ly} Cuprate MPS Circuit Baseline",
        "",
        "This is a quimb MPS simulation of the same shallow circuit family used for the hardware route.",
        "It is not a full Hamiltonian TDVP/ITensor convergence result.",
        "",
        "## Target",
        "",
        f"- lattice/qubits: {summary['config']['lx']}x{summary['config']['ly']} / {summary['config']['qubits']}",
        f"- circuit_family: `{summary['circuit_family']}`",
        f"- steps/dt/time: {summary['config']['steps']}/{summary['config']['dt']}/{summary['config']['total_time']}",
        "",
        "## Convergence",
        "",
        "| max bond | observed max bond | elapsed s | occupation RMSE vs previous | total charge | total spin-z | mean doublon |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for profile in summary["profiles"]:
        mps = profile["mps"]
        final = profile["final_summary"]
        lines.append(
            f"| {mps['max_bond_requested']} | {mps['max_bond_observed']} | {mps['elapsed_seconds']:.3f} | "
            f"{profile['occupation_rmse_vs_previous']} | {final['total_charge']:.6f} | "
            f"{final['total_spin_z']:.6f} | {final['mean_double_occupancy']:.6f} |"
        )
    lines += [
        "",
        "Claim boundary: this validates the shallow circuit tensor baseline only. Hardware output remains diagnostic until compared against this and other local baselines.",
        "",
    ]
    path.write_text("\n".join(lines))


def run(args: argparse.Namespace) -> Path:
    cfg = replace(load_config(args.config), steps=int(args.steps))
    validate_config(cfg)
    if args.circuit_family not in SUPPORTED_CIRCUIT_FAMILIES:
        raise ValueError(f"Unsupported circuit_family: {args.circuit_family}")
    args.outdir.mkdir(parents=True, exist_ok=True)

    profiles = []
    previous_rows: list[dict[str, Any]] | None = None
    for max_bond in parse_int_list(args.max_bonds):
        started = time.perf_counter()
        psi, diagnostics, metadata = apply_circuit_mps(
            cfg,
            circuit_family=args.circuit_family,
            max_bond=max_bond,
            cutoff=float(args.cutoff),
        )
        elapsed = time.perf_counter() - started
        profile = f"mps_chi{max_bond}"
        sites = site_rows(cfg, psi, profile=profile)
        bonds = bond_rows(cfg, psi, profile=profile)
        suffix = f"_chi{max_bond}"
        write_csv(args.outdir / f"cuprate_2d_mps_site_observables{suffix}.csv", sites)
        write_csv(args.outdir / f"cuprate_2d_mps_bond_observables{suffix}.csv", bonds)
        profile_summary = {
            "profile": profile,
            "mps": {
                "library": "quimb",
                "max_bond_requested": int(max_bond),
                "max_bond_observed": metadata["max_bond_observed"],
                "cutoff": float(args.cutoff),
                "elapsed_seconds": float(elapsed),
                "barrier_diagnostics": diagnostics,
            },
            "circuit": metadata,
            "final_summary": summarize_site_rows(sites),
            "occupation_rmse_vs_previous": None if previous_rows is None else occupation_rmse(sites, previous_rows),
            "artifacts": {
                "site_observables_csv": (args.outdir / f"cuprate_2d_mps_site_observables{suffix}.csv").as_posix(),
                "bond_observables_csv": (args.outdir / f"cuprate_2d_mps_bond_observables{suffix}.csv").as_posix(),
            },
        }
        profiles.append(profile_summary)
        previous_rows = sites

    latest = profiles[-1]
    latest_chi = latest["mps"]["max_bond_requested"]
    latest_site = args.outdir / f"cuprate_2d_mps_site_observables_chi{latest_chi}.csv"
    latest_bond = args.outdir / f"cuprate_2d_mps_bond_observables_chi{latest_chi}.csv"
    summary = {
        "reference_kind": "quimb_mps_shallow_cuprate_2d_circuit",
        "reference_source": "cuprate_2d_mps_circuit_baseline.py",
        "claim_boundary": (
            "Tensor-network simulation of the submitted shallow circuit family. "
            "This is not a full Hamiltonian TDVP/ITensor convergence result."
        ),
        "config": {**asdict(cfg), "qubits": cfg.qubits, "sites": cfg.sites, "total_time": cfg.total_time},
        "circuit_family": args.circuit_family,
        "profiles": profiles,
        "latest_profile": latest["profile"],
        "artifacts": {
            "latest_site_observables_csv": latest_site.as_posix(),
            "latest_bond_observables_csv": latest_bond.as_posix(),
            "summary_json": (args.outdir / "cuprate_2d_mps_summary.json").as_posix(),
            "report_md": (args.outdir / "cuprate_2d_mps_report.md").as_posix(),
        },
    }
    write_json(args.outdir / "cuprate_2d_mps_summary.json", summary)
    write_report(args.outdir / "cuprate_2d_mps_report.md", summary)
    return args.outdir / "cuprate_2d_mps_report.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--steps", type=int, default=1)
    parser.add_argument("--circuit-family", choices=SUPPORTED_CIRCUIT_FAMILIES, default="number_preserving_t_only")
    parser.add_argument("--max-bonds", default="32,64")
    parser.add_argument("--cutoff", type=float, default=1e-10)
    return parser.parse_args()


def main() -> None:
    print(run(parse_args()))


if __name__ == "__main__":
    main()
