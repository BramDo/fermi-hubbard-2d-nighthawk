#!/usr/bin/env python3
"""Scout shallower 3x3 2D cuprate circuit candidates.

This is local/offline engineering. It compares the current explicit row-major
Jordan-Wigner circuit with shallower number-preserving hopping ansatz circuits.
The ansatz circuits are resource candidates, not validated replacements for
the explicit JW Hamiltonian.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import XXPlusYYGate
from qiskit.quantum_info import Statevector

from advantage_scale_fermi_hubbard_model import bit_from_qiskit_bitstring
from compare_cuprate_2d_observables import SITE_FIELDS, normalize_site_row, rmse_rows, summary_rows
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
from cuprate_2d_ibm_hardware_runner import select_hardware_backend, site_observable_rows
from cuprate_2d_layout_scout import backend_error_maps, score_candidate
from cuprate_2d_qiskit_circuit import build_circuit, load_config, prepare_initial_state
from ibm_staged_fermi_hubbard_runner import backend_name, backend_pending_jobs, build_runtime_service, summarize_circuit


FAMILY_EXPLICIT_JW = "explicit_jw"
FAMILY_ONSITE_ONLY = "onsite_only"
FAMILY_T_ONLY = "number_preserving_t_only"
FAMILY_T_TPRIME = "number_preserving_t_tprime"
DEFAULT_FAMILIES = [FAMILY_EXPLICIT_JW, FAMILY_ONSITE_ONLY, FAMILY_T_ONLY, FAMILY_T_TPRIME]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    if fields is None:
        ordered: list[str] = []
        for row in rows:
            for key in row:
                if key not in ordered:
                    ordered.append(key)
        fields = ordered
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def add_onsite_terms(qc: QuantumCircuit, cfg: Cuprate2DConfig) -> None:
    onsite_z = -0.25 * cfg.interaction_u + 0.5 * cfg.chemical_potential
    onsite_zz = 0.25 * cfg.interaction_u
    for site in range(cfg.sites):
        up = mode_qubit(site, SPIN_UP)
        down = mode_qubit(site, SPIN_DOWN)
        qc.rz(2.0 * onsite_z * cfg.dt, up)
        qc.rz(2.0 * onsite_z * cfg.dt, down)
        qc.rzz(2.0 * onsite_zz * cfg.dt, up, down)


def greedy_edge_layers(pairs: list[tuple[int, int, str]]) -> list[list[tuple[int, int, str]]]:
    layers: list[list[tuple[int, int, str]]] = []
    occupied: list[set[int]] = []
    for a, b, label in pairs:
        for index, used in enumerate(occupied):
            if a not in used and b not in used:
                layers[index].append((a, b, label))
                used.update({a, b})
                break
        else:
            layers.append([(a, b, label)])
            occupied.append({a, b})
    return layers


def hopping_pairs(cfg: Cuprate2DConfig, *, include_tprime: bool) -> list[tuple[int, int, str, float]]:
    pairs = []
    for bond in all_hopping_bonds(cfg):
        if str(bond["family"]) == "next_nearest_t_prime" and not include_tprime:
            continue
        site_a = int(bond["site_a"])
        site_b = int(bond["site_b"])
        coefficient = float(bond["coefficient"])
        family = str(bond["family"])
        orientation = str(bond["orientation"])
        for spin in SPINS:
            pairs.append(
                (
                    mode_qubit(site_a, spin),
                    mode_qubit(site_b, spin),
                    f"{family}_{orientation}_{spin}_{site_a}_{site_b}",
                    coefficient,
                )
            )
    return pairs


def add_number_preserving_hops(qc: QuantumCircuit, cfg: Cuprate2DConfig, *, include_tprime: bool) -> int:
    pairs = hopping_pairs(cfg, include_tprime=include_tprime)
    labeled = [(a, b, label) for a, b, label, _coefficient in pairs]
    coefficient_by_label = {label: coefficient for _a, _b, label, coefficient in pairs}
    layer_count = 0
    for layer in greedy_edge_layers(labeled):
        layer_count += 1
        for a, b, label in layer:
            coefficient = coefficient_by_label[label]
            qc.append(XXPlusYYGate(2.0 * coefficient * cfg.dt), [a, b])
        qc.barrier()
    return layer_count


def build_shallow_candidate(cfg: Cuprate2DConfig, family: str, *, measured: bool) -> tuple[QuantumCircuit, dict[str, Any]]:
    if family == FAMILY_EXPLICIT_JW:
        circuit, terms = build_circuit(cfg, measured=measured)
        return circuit, {
            "family": family,
            "exact_jw_hamiltonian": True,
            "particle_number_preserving_by_construction": True,
            "claim_boundary": "Current explicit row-major JW first-order Trotter circuit.",
            "pauli_terms_per_step": len(terms),
        }

    qc = QuantumCircuit(cfg.qubits)
    prepare_initial_state(qc, cfg)
    hopping_layer_count = 0
    for _ in range(cfg.steps):
        add_onsite_terms(qc, cfg)
        if family == FAMILY_T_ONLY:
            hopping_layer_count += add_number_preserving_hops(qc, cfg, include_tprime=False)
        elif family == FAMILY_T_TPRIME:
            hopping_layer_count += add_number_preserving_hops(qc, cfg, include_tprime=True)
        elif family != FAMILY_ONSITE_ONLY:
            raise ValueError(f"Unknown shallow circuit family: {family}")
    if measured:
        qc.measure_all()
    return qc, {
        "family": family,
        "exact_jw_hamiltonian": False,
        "particle_number_preserving_by_construction": True,
        "claim_boundary": (
            "Number-preserving shallow ansatz for resource/sector diagnostics. "
            "It omits nonlocal row-major JW parity strings and is not a validated 2D Hubbard replacement."
        ),
        "hopping_layers": hopping_layer_count,
    }


def normalize_probabilities(probabilities: Mapping[str, float], n_qubits: int, threshold: float) -> dict[str, float]:
    normalized: dict[str, float] = {}
    for key, value in probabilities.items():
        prob = float(value)
        if prob <= threshold:
            continue
        bitstring = str(key).replace(" ", "").zfill(n_qubits)
        normalized[bitstring] = normalized.get(bitstring, 0.0) + prob
    return normalized


def ideal_sector_summary(probs: Mapping[str, float], cfg: Cuprate2DConfig) -> dict[str, Any]:
    expected_up = 0
    expected_down = 0
    for row in initial_site_rows(cfg):
        expected_up += int(row["n_up_initial"])
        expected_down += int(row["n_down_initial"])
    exact = 0.0
    total = 0.0
    abs_up = 0.0
    abs_down = 0.0
    for bitstring, probability in probs.items():
        prob = float(probability)
        total += prob
        n_up = 0
        n_down = 0
        for site in range(cfg.sites):
            n_up += bit_from_qiskit_bitstring(bitstring, mode_qubit(site, SPIN_UP), cfg.qubits)
            n_down += bit_from_qiskit_bitstring(bitstring, mode_qubit(site, SPIN_DOWN), cfg.qubits)
        if (n_up, n_down) == (expected_up, expected_down):
            exact += prob
        abs_up += prob * abs(n_up - expected_up)
        abs_down += prob * abs(n_down - expected_down)
    return {
        "expected_n_up": expected_up,
        "expected_n_down": expected_down,
        "exact_sector_fraction": 0.0 if total <= 0.0 else exact / total,
        "mean_abs_n_up_error": 0.0 if total <= 0.0 else abs_up / total,
        "mean_abs_n_down_error": 0.0 if total <= 0.0 else abs_down / total,
    }


def read_time_series_baseline(source: str, path: Path, profile: str, step: int) -> list[dict[str, Any]]:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    selected = [row for row in rows if int(float(row["step"])) == step]
    return [normalize_site_row(source, profile, row, step=step) for row in selected]


def ideal_observables(cfg: Cuprate2DConfig, circuit: QuantumCircuit, family: str, *, threshold: float) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    state = Statevector.from_instruction(circuit)
    probs = normalize_probabilities(state.probabilities_dict(), cfg.qubits, threshold)
    site_rows = site_observable_rows(cfg, probs, profile=f"{family}_ideal", p01=None, p10=None, readout_corrected=False)
    normalized = []
    for row in site_rows:
        normalized.append(
            {
                "source": "shallow_scout",
                "profile": row["profile"],
                "step": cfg.steps,
                "time": cfg.total_time,
                "site": int(row["site"]),
                "x": int(row["x"]),
                "y": int(row["y"]),
                "n_up": float(row["n_up"]),
                "n_down": float(row["n_down"]),
                "charge": float(row["charge"]),
                "spin_z": float(row["spin_z"]),
                "hole_density": float(row["hole_density"]),
                "double_occupancy": float(row["double_occupancy"]),
            }
        )
    return normalized, ideal_sector_summary(probs, cfg)


def backend_best_summary(
    circuit: QuantumCircuit,
    *,
    backend: Any,
    logical_qubits: int,
    seed_start: int,
    seed_count: int,
    optimization_level: int,
    readout_errors: dict[int, float],
    gate_errors: dict[tuple[int, int], float],
    t1: dict[int, float],
    t2: dict[int, float],
) -> dict[str, Any]:
    rows = []
    for seed in range(seed_start, seed_start + seed_count):
        try:
            transpiled = transpile(circuit, backend=backend, optimization_level=optimization_level, seed_transpiler=seed)
            metrics = score_candidate(
                transpiled,
                logical_qubits=logical_qubits,
                readout_errors=readout_errors,
                gate_errors=gate_errors,
                t1=t1,
                t2=t2,
            )
            rows.append({"seed_transpiler": seed, **metrics})
        except Exception as exc:
            rows.append({"seed_transpiler": seed, "score": math.inf, "error": f"{type(exc).__name__}: {exc}"})
    valid = [row for row in rows if math.isfinite(float(row.get("score", math.inf)))]
    if not valid:
        return {"backend_candidate_rows": rows}
    valid.sort(key=lambda row: (float(row["score"]), int(row["two_qubit_depth"]), int(row["two_qubit_count"])))
    return {"backend_candidate_rows": rows, "backend_best": valid[0]}


def write_report(path: Path, rows: list[dict[str, Any]], rmse_rows_out: list[dict[str, Any]], artifacts: dict[str, str]) -> None:
    lines = [
        "# 3x3 2D Cuprate Shallow Circuit Scout",
        "",
        "Local dry-run only. No IBM Runtime, Fire Opal, or hardware job was submitted.",
        "",
        "The number-preserving ansatz rows are resource candidates. They preserve N_up/N_down ideally, but they omit row-major JW parity strings and are not validated Hubbard physics replacements yet.",
        "",
        "## Resource Summary",
        "",
        "| family | exact JW | logical 2q count | logical 2q depth | backend 2q count | backend 2q depth | ideal exact sector | charge RMSE | spin-z RMSE | doublon RMSE |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    rmse_by_profile = {str(row["profile"]): row for row in rmse_rows_out}
    for row in rows:
        profile = f"{row['family']}_ideal"
        rmse = rmse_by_profile.get(profile, {})
        lines.append(
            f"| {row['family']} | {row['exact_jw_hamiltonian']} | "
            f"{row['logical_two_qubit_count']} | {row['logical_two_qubit_depth']} | "
            f"{row.get('backend_two_qubit_count', '')} | {row.get('backend_two_qubit_depth', '')} | "
            f"{float(row.get('ideal_exact_sector_fraction', 0.0)):.6f} | "
            f"{float(rmse.get('charge_rmse', 0.0)):.6f} | {float(rmse.get('spin_z_rmse', 0.0)):.6f} | "
            f"{float(rmse.get('double_occupancy_rmse', 0.0)):.6f} |"
        )
    lines += [
        "",
        "## Artifacts",
        "",
    ]
    for label, artifact in artifacts.items():
        lines.append(f"- {label}: `{artifact}`")
    lines += [
        "",
        "Gate for next hardware submit: prefer a candidate only if backend two-qubit depth/count are materially lower and local/ideal observable drift is understood against TDHF.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--tdhf-path", type=Path, required=True)
    parser.add_argument("--gaussian-path", type=Path, default=None)
    parser.add_argument("--family", action="append", choices=DEFAULT_FAMILIES)
    parser.add_argument("--backend", default=None)
    parser.add_argument("--optimization-level", type=int, default=1)
    parser.add_argument("--seed-start", type=int, default=1)
    parser.add_argument("--seed-count", type=int, default=10)
    parser.add_argument("--probability-threshold", type=float, default=1e-14)
    parser.add_argument("--skip-statevector", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)
    validate_config(cfg)
    args.outdir.mkdir(parents=True, exist_ok=True)
    families = args.family or DEFAULT_FAMILIES

    backend = None
    backend_payload: dict[str, Any] = {}
    readout_errors: dict[int, float] = {}
    gate_errors: dict[tuple[int, int], float] = {}
    t1: dict[int, float] = {}
    t2: dict[int, float] = {}
    if args.backend:
        service = build_runtime_service()
        backend = select_hardware_backend(service, args.backend, cfg.qubits)
        readout_errors, gate_errors, t1, t2 = backend_error_maps(backend)
        backend_payload = {
            "backend": backend_name(backend),
            "backend_pending_jobs": backend_pending_jobs(backend),
            "optimization_level": int(args.optimization_level),
            "seed_start": int(args.seed_start),
            "seed_count": int(args.seed_count),
        }

    baseline_rows = read_time_series_baseline("tdhf", args.tdhf_path, "mean_field", cfg.steps)
    if args.gaussian_path and args.gaussian_path.exists():
        baseline_rows.extend(read_time_series_baseline("gaussian_u0", args.gaussian_path, "free_fermion", cfg.steps))

    resource_rows: list[dict[str, Any]] = []
    ideal_rows = list(baseline_rows)
    backend_candidate_rows: list[dict[str, Any]] = []
    metadata: dict[str, Any] = {"config": asdict(cfg), "backend": backend_payload, "families": {}}

    for family in families:
        measured_circuit, family_meta = build_shallow_candidate(cfg, family, measured=True)
        ideal_circuit, _ = build_shallow_candidate(cfg, family, measured=False)
        logical_summary = summarize_circuit(measured_circuit)
        row: dict[str, Any] = {
            **family_meta,
            "logical_depth": logical_summary["depth"],
            "logical_two_qubit_depth": logical_summary["two_qubit_depth"],
            "logical_two_qubit_count": logical_summary["two_qubit_count"],
            "logical_operation_counts": json.dumps(logical_summary["operation_counts"], sort_keys=True),
        }
        if not args.skip_statevector:
            family_ideal_rows, sector = ideal_observables(cfg, ideal_circuit, family, threshold=float(args.probability_threshold))
            ideal_rows.extend(family_ideal_rows)
            row.update(
                {
                    "ideal_exact_sector_fraction": sector["exact_sector_fraction"],
                    "ideal_mean_abs_n_up_error": sector["mean_abs_n_up_error"],
                    "ideal_mean_abs_n_down_error": sector["mean_abs_n_down_error"],
                }
            )
        if backend is not None:
            backend_summary = backend_best_summary(
                measured_circuit,
                backend=backend,
                logical_qubits=cfg.qubits,
                seed_start=int(args.seed_start),
                seed_count=int(args.seed_count),
                optimization_level=int(args.optimization_level),
                readout_errors=readout_errors,
                gate_errors=gate_errors,
                t1=t1,
                t2=t2,
            )
            for candidate in backend_summary.get("backend_candidate_rows", []):
                backend_candidate_rows.append({"family": family, **candidate})
            best = backend_summary.get("backend_best")
            if best:
                row.update(
                    {
                        "backend_seed_transpiler": best["seed_transpiler"],
                        "backend_score": best["score"],
                        "backend_depth": best["depth"],
                        "backend_two_qubit_depth": best["two_qubit_depth"],
                        "backend_two_qubit_count": best["two_qubit_count"],
                        "backend_readout_error_mean": best["readout_error_mean"],
                        "backend_readout_error_max": best["readout_error_max"],
                        "backend_edge_error_sum": best["edge_error_sum"],
                    }
                )
        resource_rows.append(row)
        metadata["families"][family] = family_meta

    summaries = summary_rows(ideal_rows)
    rmses = rmse_rows(ideal_rows, "tdhf")

    resource_path = args.outdir / "shallow_circuit_resource_summary.csv"
    ideal_site_path = args.outdir / "shallow_circuit_ideal_site_observables.csv"
    ideal_summary_path = args.outdir / "shallow_circuit_ideal_observable_summary.csv"
    ideal_rmse_path = args.outdir / "shallow_circuit_ideal_observable_rmse.csv"
    backend_candidates_path = args.outdir / "shallow_circuit_backend_candidates.csv"
    metadata_path = args.outdir / "shallow_circuit_scout_metadata.json"
    report_path = args.outdir / "shallow_circuit_scout_report.md"

    write_csv(resource_path, resource_rows)
    write_csv(ideal_site_path, ideal_rows, SITE_FIELDS)
    write_csv(ideal_summary_path, summaries, list(summaries[0].keys()))
    write_csv(ideal_rmse_path, rmses, list(rmses[0].keys()))
    if backend_candidate_rows:
        write_csv(backend_candidates_path, backend_candidate_rows)
    write_json(metadata_path, metadata)
    artifacts = {
        "resource summary": resource_path.as_posix(),
        "ideal site observables": ideal_site_path.as_posix(),
        "ideal observable summary": ideal_summary_path.as_posix(),
        "ideal RMSE": ideal_rmse_path.as_posix(),
        "metadata": metadata_path.as_posix(),
    }
    if backend_candidate_rows:
        artifacts["backend candidates"] = backend_candidates_path.as_posix()
    write_report(report_path, resource_rows, rmses, artifacts)
    print(report_path)


if __name__ == "__main__":
    main()
