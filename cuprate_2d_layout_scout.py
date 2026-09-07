#!/usr/bin/env python3
"""Dry-run layout scout for the 72-qubit 2D cuprate Hubbard target.

This script does not submit hardware jobs. It transpiles candidate layouts and
seeds against a live IBM backend calibration snapshot, scores them, and writes a
best-layout artifact that the hardware runner can consume.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from qiskit import QuantumCircuit, transpile

from cuprate_2d_ibm_hardware_runner import (
    backend_name,
    backend_operational,
    backend_pending_jobs,
    build_readout_calibration_circuits,
    select_hardware_backend,
    transpile_circuits,
)
from cuprate_2d_qiskit_circuit import SUPPORTED_CIRCUIT_FAMILIES, build_circuit, load_config
from ibm_staged_fermi_hubbard_runner import build_runtime_service, summarize_circuit


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("")
        return
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def two_qubit_depth(circuit: QuantumCircuit) -> int:
    try:
        return int(circuit.depth(filter_function=lambda instruction: len(instruction.qubits) == 2) or 0)
    except Exception:
        return 0


def operation_count(circuit: QuantumCircuit, names: set[str]) -> int:
    ops = circuit.count_ops()
    return int(sum(int(ops.get(name, 0)) for name in names))


def physical_qubits(circuit: QuantumCircuit, logical_qubits: int) -> list[int]:
    layout = getattr(circuit, "layout", None)
    initial_layout = getattr(layout, "initial_layout", None)
    if initial_layout is not None:
        try:
            mapping = initial_layout.get_virtual_bits()
            logical_to_physical: dict[int, int] = {}
            for virtual, physical in mapping.items():
                index = getattr(virtual, "_index", None)
                if index is not None and int(index) < logical_qubits:
                    logical_to_physical[int(index)] = int(physical)
            if len(logical_to_physical) == logical_qubits:
                return [logical_to_physical[index] for index in range(logical_qubits)]
        except Exception:
            pass
    return list(range(logical_qubits))


def measured_physical_qubits(circuit: QuantumCircuit) -> list[int]:
    measured: set[int] = set()
    for instruction in circuit.data:
        if instruction.operation.name != "measure" or not instruction.qubits:
            continue
        measured.add(int(circuit.find_bit(instruction.qubits[0]).index))
    return sorted(measured)


def coupling_edges(backend: Any) -> set[tuple[int, int]]:
    coupling_map = getattr(backend, "coupling_map", None)
    raw = []
    if coupling_map is not None:
        try:
            raw = list(coupling_map.get_edges())
        except Exception:
            try:
                raw = list(coupling_map)
            except Exception:
                raw = []
    edges: set[tuple[int, int]] = set()
    for edge in raw:
        if len(edge) == 2:
            a = int(edge[0])
            b = int(edge[1])
            edges.add((a, b))
            edges.add((b, a))
    return edges


def backend_error_maps(backend: Any) -> tuple[dict[int, float], dict[tuple[int, int], float], dict[int, float], dict[int, float]]:
    readout: dict[int, float] = {}
    gate: dict[tuple[int, int], float] = {}
    t1: dict[int, float] = {}
    t2: dict[int, float] = {}
    try:
        props = backend.properties()
    except Exception:
        return readout, gate, t1, t2

    for qubit_index, qubit_props in enumerate(getattr(props, "qubits", []) or []):
        for item in qubit_props:
            name = str(getattr(item, "name", ""))
            value = getattr(item, "value", None)
            if value is None:
                continue
            if name == "readout_error":
                readout[qubit_index] = float(value)
            elif name == "T1":
                t1[qubit_index] = float(value)
            elif name == "T2":
                t2[qubit_index] = float(value)

    for gate_prop in getattr(props, "gates", []) or []:
        qubits = list(getattr(gate_prop, "qubits", []) or [])
        if len(qubits) != 2:
            continue
        error = None
        for param in getattr(gate_prop, "parameters", []) or []:
            if str(getattr(param, "name", "")) == "gate_error":
                error = float(getattr(param, "value"))
                break
        if error is None:
            continue
        a, b = int(qubits[0]), int(qubits[1])
        gate[(a, b)] = error
        gate[(b, a)] = error
    return readout, gate, t1, t2


def circuit_edge_counts(circuit: QuantumCircuit) -> dict[tuple[int, int], int]:
    counts: dict[tuple[int, int], int] = {}
    for instruction in circuit.data:
        qubits = list(instruction.qubits)
        if len(qubits) != 2:
            continue
        a = getattr(qubits[0], "_index", None)
        b = getattr(qubits[1], "_index", None)
        if a is None or b is None:
            continue
        edge = tuple(sorted((int(a), int(b))))
        counts[edge] = counts.get(edge, 0) + 1
    return counts


def linear_chain_layout(edges: set[tuple[int, int]], start: int, length: int, num_qubits: int) -> list[int] | None:
    if start >= num_qubits:
        return None
    path = [start]
    seen = {start}
    while len(path) < length:
        current = path[-1]
        neighbors = sorted(b for a, b in edges if a == current and b not in seen and b < num_qubits)
        if not neighbors:
            return None
        nxt = neighbors[0]
        path.append(nxt)
        seen.add(nxt)
    return path


def score_candidate(
    circuit: QuantumCircuit,
    *,
    logical_qubits: int,
    readout_errors: dict[int, float],
    gate_errors: dict[tuple[int, int], float],
    t1: dict[int, float],
    t2: dict[int, float],
) -> dict[str, Any]:
    phys = physical_qubits(circuit, logical_qubits)
    edge_counts = circuit_edge_counts(circuit)
    edge_error_sum = 0.0
    edge_error_max = 0.0
    unknown_edges = 0
    for edge, count in edge_counts.items():
        err = gate_errors.get((edge[0], edge[1]))
        if err is None:
            unknown_edges += count
            err = 0.02
        edge_error_sum += float(count) * float(err)
        edge_error_max = max(edge_error_max, float(err))

    measured_phys = measured_physical_qubits(circuit)
    readout_phys = measured_phys if len(measured_phys) == logical_qubits else phys
    selected_readout = [readout_errors.get(q, 0.05) for q in readout_phys]
    readout_mean = sum(selected_readout) / len(selected_readout) if selected_readout else 0.0
    readout_max = max(selected_readout) if selected_readout else 0.0
    t1_values = [t1[q] for q in phys if q in t1]
    t2_values = [t2[q] for q in phys if q in t2]
    min_t1 = min(t1_values) if t1_values else 0.0
    min_t2 = min(t2_values) if t2_values else 0.0

    tq_count = operation_count(circuit, {"cx", "cz", "ecr", "rzz", "swap"})
    tq_depth = two_qubit_depth(circuit)
    score = (
        edge_error_sum
        + 30.0 * readout_mean
        + 10.0 * readout_max
        + 0.0005 * tq_count
        + 0.002 * tq_depth
        + 0.25 * unknown_edges
    )
    if min_t1 and min_t1 < 50e-6:
        score += (50e-6 - min_t1) / 50e-6
    if min_t2 and min_t2 < 50e-6:
        score += (50e-6 - min_t2) / 50e-6

    return {
        "score": score,
        "depth": int(circuit.depth() or 0),
        "two_qubit_depth": tq_depth,
        "two_qubit_count": tq_count,
        "edge_error_sum": edge_error_sum,
        "edge_error_max": edge_error_max,
        "unknown_two_qubit_edges": unknown_edges,
        "readout_error_mean": readout_mean,
        "readout_error_max": readout_max,
        "min_t1": min_t1,
        "min_t2": min_t2,
        "physical_qubits": " ".join(str(q) for q in phys),
        "measured_physical_qubits": " ".join(str(q) for q in readout_phys),
    }


def write_report(path: Path, payload: dict[str, Any], top_rows: list[dict[str, Any]]) -> None:
    lines = [
        "# 2D Cuprate Layout Scout",
        "",
        "Dry-run only. No IBM Runtime, Fire Opal, or hardware jobs were submitted.",
        "",
        "## Backend",
        "",
        f"- backend: `{payload['backend']}`",
        f"- pending_jobs: {payload['backend_pending_jobs']}",
        f"- operational: {payload['backend_operational']}",
        "",
        "## Best Candidate",
        "",
    ]
    best = payload["best_candidate"]
    for key in [
        "candidate",
        "seed_transpiler",
        "score",
        "depth",
        "two_qubit_depth",
        "two_qubit_count",
        "edge_error_sum",
        "readout_error_mean",
        "readout_error_max",
    ]:
        lines.append(f"- {key}: `{best[key]}`")
    lines += [
        f"- recommended runner seed: `{payload['recommended_runner_args']['seed_transpiler']}`",
        f"- force initial_layout by default: `{payload['recommended_runner_args']['force_initial_layout']}`",
        f"- runner note: {payload['recommended_runner_args']['note']}",
    ]
    lines += [
        "",
        "## Top Candidates",
        "",
        "| rank | candidate | seed | score | 2q count | 2q depth | readout mean | edge error sum |",
        "|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in top_rows:
        lines.append(
            f"| {row['rank']} | {row['candidate']} | {row['seed_transpiler']} | "
            f"{float(row['score']):.6f} | {row['two_qubit_count']} | {row['two_qubit_depth']} | "
            f"{float(row['readout_error_mean']):.6f} | {float(row['edge_error_sum']):.6f} |"
        )
    lines += [
        "",
        "Claim boundary: this ranks compilation/calibration diagnostics only. A selected layout still needs a gated hardware submission and baseline comparison.",
        "",
    ]
    path.write_text("\n".join(lines))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--backend", default="ibm_marrakesh")
    parser.add_argument("--account-name", default=None, help="Saved Qiskit Runtime account name.")
    parser.add_argument("--steps", type=int, default=1)
    parser.add_argument("--circuit-family", choices=SUPPORTED_CIRCUIT_FAMILIES, default="explicit_jw")
    parser.add_argument("--optimization-level", type=int, default=1)
    parser.add_argument("--seed-start", type=int, default=1)
    parser.add_argument("--seed-count", type=int, default=50)
    parser.add_argument("--chain-starts", default="", help="Comma-separated physical starts for simple chain layouts.")
    parser.add_argument("--include-readout", action="store_true", help="Also transpile all-0/all-1 readout circuits for the best seed.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)
    cfg = replace(load_config(args.config), steps=int(args.steps))
    service = build_runtime_service(args.account_name)
    backend = select_hardware_backend(service, args.backend, cfg.qubits)
    readout_errors, gate_errors, t1, t2 = backend_error_maps(backend)
    edges = coupling_edges(backend)
    main_circuit, _terms = build_circuit(cfg, measured=True, circuit_family=args.circuit_family)

    candidates: list[tuple[str, int, list[int] | None]] = []
    for seed in range(int(args.seed_start), int(args.seed_start) + int(args.seed_count)):
        candidates.append((f"sabre_seed_{seed}", seed, None))
    for raw_start in [item.strip() for item in str(args.chain_starts).split(",") if item.strip()]:
        start = int(raw_start)
        layout = linear_chain_layout(edges, start, cfg.qubits, int(getattr(backend, "num_qubits", cfg.qubits)))
        if layout is not None:
            candidates.append((f"chain_start_{start}", int(args.seed_start), layout))

    rows: list[dict[str, Any]] = []
    for candidate_name, seed, initial_layout in candidates:
        try:
            transpiled = transpile(
                main_circuit,
                backend=backend,
                optimization_level=int(args.optimization_level),
                seed_transpiler=seed,
                initial_layout=initial_layout,
            )
            metrics = score_candidate(
                transpiled,
                logical_qubits=cfg.qubits,
                readout_errors=readout_errors,
                gate_errors=gate_errors,
                t1=t1,
                t2=t2,
            )
            rows.append(
                {
                    "candidate": candidate_name,
                    "seed_transpiler": seed,
                    "initial_layout": "" if initial_layout is None else " ".join(str(q) for q in initial_layout),
                    **metrics,
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "candidate": candidate_name,
                    "seed_transpiler": seed,
                    "initial_layout": "" if initial_layout is None else " ".join(str(q) for q in initial_layout),
                    "score": math.inf,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    valid_rows = [row for row in rows if math.isfinite(float(row.get("score", math.inf)))]
    if not valid_rows:
        raise RuntimeError("No valid layout candidates were produced")
    valid_rows.sort(key=lambda row: (float(row["score"]), int(row["two_qubit_depth"]), int(row["two_qubit_count"])))
    best = valid_rows[0]
    best_layout = [int(item) for item in str(best["physical_qubits"]).split()]

    if args.include_readout:
        readout_circuits = build_readout_calibration_circuits(cfg.qubits)
        _ = transpile_circuits(
            readout_circuits,
            backend,
            optimization_level=int(args.optimization_level),
            seed_transpiler=int(best["seed_transpiler"]),
            initial_layout=best_layout,
        )

    payload = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "backend": backend_name(backend),
        "backend_num_qubits": int(getattr(backend, "num_qubits", 0) or 0),
        "backend_pending_jobs": backend_pending_jobs(backend),
        "backend_operational": backend_operational(backend),
        "config": asdict(cfg),
        "optimization_level": int(args.optimization_level),
        "circuit_family": args.circuit_family,
        "candidate_count": len(rows),
        "best_candidate": best,
        "initial_layout": best_layout,
        "layout_format": "logical_qubit_index_to_physical_qubit_index",
        "recommended_runner_args": {
            "seed_transpiler": int(best["seed_transpiler"]),
            "force_initial_layout": False,
            "note": (
                "For Qiskit SABRE candidates, reproducing the best seed is the first choice. "
                "Forcing the discovered physical map as initial_layout can change routing and should be rescored."
            ),
        },
        "artifacts": {
            "layout_candidates_csv": (args.outdir / "layout_candidates.csv").as_posix(),
            "best_layout_json": (args.outdir / "best_layout.json").as_posix(),
            "report_md": (args.outdir / "layout_scout_report.md").as_posix(),
        },
        "claim_boundary": "Dry-run layout/calibration ranking only; no hardware submission.",
    }
    write_csv(args.outdir / "layout_candidates.csv", rows)
    write_json(args.outdir / "best_layout.json", payload)
    top_rows = []
    for rank, row in enumerate(valid_rows[:10], start=1):
        top_rows.append({"rank": rank, **row})
    write_report(args.outdir / "layout_scout_report.md", payload, top_rows)
    print(args.outdir / "layout_scout_report.md")


if __name__ == "__main__":
    main()
