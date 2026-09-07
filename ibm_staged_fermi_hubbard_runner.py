#!/usr/bin/env python3
"""Staged IBM Runtime runner for the advantage-scale Fermi-Hubbard scaffold.

Default behavior is deliberately conservative:
  - Build and save a 20-qubit stage plan.
  - Do not submit hardware jobs unless --submit is passed.
  - Refuse multi-stage submission unless --allow-multiple-submit is passed.

The intended escalation is:
  20q -> 40q -> 60q -> 80q -> 100q -> 120q

This keeps the toy experiment separate from hardware staging and avoids jumping
straight to a 120-qubit job.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any

from qiskit import QuantumCircuit, transpile

from advantage_scale_fermi_hubbard_model import (
    AdvantageScaleConfig,
    SUPPORTED_CIRCUIT_FAMILIES,
    MitigationConfig,
    all_decay_recovery_echo_steps,
    build_decay_recovery_echo_circuit,
    build_main_circuit,
    build_readout_calibration_circuits,
    decay_recovery_echo_steps,
    qctrl_paper_native_resources,
    runtime_sampler_options,
    semantic_mapping_manifest,
    write_resource_artifacts,
)


DEFAULT_STAGE_QUBITS = [20, 40, 60, 80, 100, 120]
DEFAULT_STEPS_BY_QUBITS = {
    20: 4,
    40: 8,
    60: 12,
    80: 16,
    100: 20,
    120: 30,
}


def backend_name(backend: Any) -> str:
    name = getattr(backend, "name", backend.__class__.__name__)
    if callable(name):
        return str(name())
    return str(name)


def build_runtime_service(account_name: str | None = None) -> Any:
    try:
        from qiskit_ibm_runtime import QiskitRuntimeService
    except ImportError as exc:
        raise RuntimeError(
            "qiskit-ibm-runtime is missing. Install the Python requirements or run scripts/setup_python.sh."
        ) from exc

    if account_name:
        return QiskitRuntimeService(name=account_name)

    token = os.getenv("QCAPI_TOKEN") or os.getenv("QISKIT_IBM_TOKEN") or os.getenv("IBM_QUANTUM_TOKEN")
    instance = os.getenv("QISKIT_IBM_INSTANCE")
    if token:
        kwargs: dict[str, str] = {"token": token}
        if instance:
            kwargs["instance"] = instance
        try:
            return QiskitRuntimeService(channel="ibm_quantum", **kwargs)
        except TypeError:
            return QiskitRuntimeService(**kwargs)
    return QiskitRuntimeService()


def backend_pending_jobs(backend: Any) -> int | None:
    try:
        return int(backend.status().pending_jobs)
    except Exception:
        return None


def backend_operational(backend: Any) -> bool | None:
    try:
        return bool(backend.status().operational)
    except Exception:
        return None


def backend_quality_inventory_row(
    backend: Any,
    *,
    min_qubits: int,
    layout_beam_width: int,
    avoid_qubits: set[int] | None = None,
) -> dict[str, object]:
    pending = backend_pending_jobs(backend)
    operational = backend_operational(backend)
    row: dict[str, object] = {
        "name": backend_name(backend),
        "num_qubits": int(getattr(backend, "num_qubits", 0) or 0),
        "operational": operational,
        "pending_jobs": pending,
        "target_qubits": min_qubits,
    }
    try:
        layout = select_low_error_chain_layout(
            backend,
            min_qubits,
            beam_width=layout_beam_width,
            avoid_qubits=avoid_qubits,
        )
        row.update(
            {
                "quality_score": layout["score"],
                "selected_readout_error_mean": layout["selected_readout_error_mean"],
                "selected_readout_error_max": layout["selected_readout_error_max"],
                "selected_cz_error_mean": layout["selected_cz_error_mean"],
                "selected_cz_error_max": layout["selected_cz_error_max"],
                "logical_to_physical": layout["logical_to_physical"],
                "layout_method": layout["method"],
            }
        )
    except Exception as exc:
        row.update({"quality_score": None, "quality_error": str(exc)})
    return row


def select_backend(
    service: Any,
    requested_backend: str | None,
    min_qubits: int,
    *,
    backend_policy: str,
    layout_beam_width: int,
    avoid_qubits: set[int] | None = None,
) -> Any:
    if requested_backend:
        return service.backend(requested_backend)

    candidates = service.backends(simulator=False, operational=True, min_num_qubits=min_qubits)
    if not candidates:
        candidates = service.backends(simulator=False, min_num_qubits=min_qubits)
    if not candidates:
        raise RuntimeError(f"No IBM hardware backend found with at least {min_qubits} qubits")

    if backend_policy == "least-busy":
        scored = [
            (backend_pending_jobs(backend) if backend_pending_jobs(backend) is not None else 10**9, backend_name(backend), backend)
            for backend in candidates
        ]
        scored.sort(key=lambda item: (item[0], item[1]))
        return scored[0][2]

    rows = [
        backend_quality_inventory_row(
            backend,
            min_qubits=min_qubits,
            layout_beam_width=layout_beam_width,
            avoid_qubits=avoid_qubits,
        )
        for backend in candidates
    ]
    valid_rows = [row for row in rows if row.get("quality_score") is not None]
    if not valid_rows:
        scored = [
            (backend_pending_jobs(backend) if backend_pending_jobs(backend) is not None else 10**9, backend_name(backend), backend)
            for backend in candidates
        ]
        scored.sort(key=lambda item: (item[0], item[1]))
        return scored[0][2]

    pending_by_name = {backend_name(backend): backend_pending_jobs(backend) for backend in candidates}
    backend_by_name = {backend_name(backend): backend for backend in candidates}

    if backend_policy == "balanced":
        valid_rows.sort(
            key=lambda row: (
                float(row["quality_score"]) + 0.001 * float(pending_by_name.get(str(row["name"])) or 0),
                str(row["name"]),
            )
        )
    else:
        valid_rows.sort(
            key=lambda row: (
                float(row["quality_score"]),
                pending_by_name.get(str(row["name"])) if pending_by_name.get(str(row["name"])) is not None else 10**9,
                str(row["name"]),
            )
        )
    return backend_by_name[str(valid_rows[0]["name"])]


def list_backend_inventory(
    min_qubits: int,
    *,
    layout_beam_width: int,
    avoid_qubits: set[int] | None = None,
) -> list[dict[str, object]]:
    service = build_runtime_service()
    rows: list[dict[str, object]] = []
    for backend in service.backends(simulator=False, min_num_qubits=min_qubits):
        rows.append(
            backend_quality_inventory_row(
                backend,
                min_qubits=min_qubits,
                layout_beam_width=layout_beam_width,
                avoid_qubits=avoid_qubits,
            )
        )
    rows.sort(
        key=lambda row: (
            row["quality_score"] if row.get("quality_score") is not None else 10**9,
            row["pending_jobs"] if row["pending_jobs"] is not None else 10**9,
            row["name"],
        )
    )
    return rows


def backend_qubit_property(backend: Any, qubit: int, name: str, default: float) -> float:
    try:
        props = backend.properties()
        value = props.qubit_property(qubit).get(name)
        if value is None:
            return default
        raw_value = value[0] if isinstance(value, tuple) else value
        return float(raw_value)
    except Exception:
        return default


def backend_cz_error_map(backend: Any) -> dict[tuple[int, int], float]:
    errors: dict[tuple[int, int], float] = {}
    try:
        target = backend.target
        if "cz" in target.operation_names:
            for qargs, properties in target["cz"].items():
                if len(qargs) != 2:
                    continue
                a, b = int(qargs[0]), int(qargs[1])
                key = tuple(sorted((a, b)))
                error = getattr(properties, "error", None)
                if error is None:
                    continue
                error_value = float(error)
                errors[key] = min(errors.get(key, error_value), error_value)
    except Exception:
        pass
    return errors


def backend_coupling_adjacency(backend: Any) -> dict[int, set[int]]:
    num_qubits = int(getattr(backend, "num_qubits", 0) or 0)
    adjacency = {qubit: set() for qubit in range(num_qubits)}
    edges = []
    try:
        edges = list(backend.coupling_map.get_edges())
    except Exception:
        try:
            edges = list(backend.target.build_coupling_map().get_edges())
        except Exception:
            edges = []
    for a, b in edges:
        a_int, b_int = int(a), int(b)
        adjacency.setdefault(a_int, set()).add(b_int)
        adjacency.setdefault(b_int, set()).add(a_int)
    return adjacency


def backend_qubit_costs(backend: Any) -> dict[int, float]:
    num_qubits = int(getattr(backend, "num_qubits", 0) or 0)
    readout = [backend_qubit_property(backend, qubit, "readout_error", 0.02) for qubit in range(num_qubits)]
    t1 = [backend_qubit_property(backend, qubit, "T1", 1e-4) for qubit in range(num_qubits)]
    t2 = [backend_qubit_property(backend, qubit, "T2", 1e-4) for qubit in range(num_qubits)]
    median_t1 = max(median([value for value in t1 if value > 0.0] or [1e-4]), 1e-9)
    median_t2 = max(median([value for value in t2 if value > 0.0] or [1e-4]), 1e-9)

    costs = {}
    for qubit in range(num_qubits):
        t1_penalty = 0.002 * max(0.0, median_t1 / max(t1[qubit], 1e-9) - 1.0)
        t2_penalty = 0.002 * max(0.0, median_t2 / max(t2[qubit], 1e-9) - 1.0)
        costs[qubit] = float(readout[qubit] + t1_penalty + t2_penalty)
    return costs


def greedy_connected_layout(
    *,
    num_qubits: int,
    qubit_costs: dict[int, float],
    edge_errors: dict[tuple[int, int], float],
    adjacency: dict[int, set[int]],
    default_edge_error: float,
) -> tuple[list[int], str]:
    selected = [min(qubit_costs, key=lambda qubit: qubit_costs[qubit])]
    selected_set = set(selected)

    while len(selected) < num_qubits:
        candidates = []
        for qubit in set().union(*(adjacency.get(chosen, set()) for chosen in selected)):
            if qubit in selected_set:
                continue
            best_link = min(
                edge_errors.get(tuple(sorted((qubit, chosen))), default_edge_error)
                for chosen in selected
                if chosen in adjacency.get(qubit, set())
            )
            candidates.append((qubit_costs.get(qubit, 0.02) + best_link, qubit))
        if not candidates:
            remaining = [qubit for qubit in qubit_costs if qubit not in selected_set]
            if not remaining:
                break
            selected.append(min(remaining, key=lambda qubit: qubit_costs[qubit]))
            selected_set.add(selected[-1])
            continue
        _, chosen = min(candidates, key=lambda item: item[0])
        selected.append(chosen)
        selected_set.add(chosen)
    return selected[:num_qubits], "greedy_connected_fallback"


def summarize_chain_layout(
    backend: Any,
    layout: list[int],
    *,
    method: str,
    score: float,
    beam_width: int,
    rank: int | None = None,
    avoid_qubits: set[int] | None = None,
) -> dict[str, object]:
    edge_errors = backend_cz_error_map(backend)
    known_edges = list(edge_errors.values())
    default_edge_error = float(median(known_edges)) if known_edges else 0.01
    chain_edges = [tuple(sorted((a, b))) for a, b in zip(layout, layout[1:])]
    selected_edge_errors = [edge_errors.get(edge, default_edge_error) for edge in chain_edges]
    selected_readout_errors = [
        backend_qubit_property(backend, qubit, "readout_error", 0.02)
        for qubit in layout
    ]
    summary: dict[str, object] = {
        "enabled": True,
        "method": method,
        "backend": backend_name(backend),
        "logical_to_physical": layout,
        "score": float(score),
        "beam_width": beam_width,
        "selected_readout_error_mean": float(sum(selected_readout_errors) / len(selected_readout_errors)),
        "selected_readout_error_max": float(max(selected_readout_errors)),
        "selected_cz_error_mean": float(sum(selected_edge_errors) / len(selected_edge_errors))
        if selected_edge_errors
        else None,
        "selected_cz_error_max": float(max(selected_edge_errors)) if selected_edge_errors else None,
        "avoided_physical_qubits": sorted(avoid_qubits or set()),
        "warning": "Layout is chosen from current backend calibration data and can drift between jobs.",
    }
    if rank is not None:
        summary["rank"] = rank
    return summary


def select_low_error_chain_layouts(
    backend: Any,
    num_qubits: int,
    *,
    beam_width: int,
    limit: int,
    avoid_qubits: set[int] | None = None,
) -> list[dict[str, object]]:
    backend_qubits = int(getattr(backend, "num_qubits", 0) or 0)
    if num_qubits > backend_qubits:
        raise ValueError(f"Backend has fewer than {num_qubits} physical qubits")
    avoided = set(avoid_qubits or set())
    available_qubits = set(range(backend_qubits)) - avoided
    if len(available_qubits) < num_qubits:
        raise ValueError(
            f"Backend has only {len(available_qubits)} usable qubits after avoiding {sorted(avoided)}"
        )

    raw_adjacency = backend_coupling_adjacency(backend)
    adjacency = {
        qubit: {neighbor for neighbor in raw_adjacency.get(qubit, set()) if neighbor in available_qubits}
        for qubit in available_qubits
    }
    qubit_costs = {
        qubit: cost
        for qubit, cost in backend_qubit_costs(backend).items()
        if qubit in available_qubits
    }
    edge_errors = backend_cz_error_map(backend)
    known_edges = list(edge_errors.values())
    default_edge_error = float(median(known_edges)) if known_edges else 0.01

    beam = [(qubit_costs[qubit], (qubit,)) for qubit in sorted(qubit_costs, key=lambda q: qubit_costs[q])]
    beam = beam[: max(beam_width, 1)]
    best_partial = beam[0]

    for _ in range(1, num_qubits):
        candidates = []
        for score, path in beam:
            used = set(path)
            last = path[-1]
            for nxt in adjacency.get(last, set()):
                if nxt in used:
                    continue
                edge_key = tuple(sorted((last, nxt)))
                next_score = score + qubit_costs.get(nxt, 0.02) + edge_errors.get(edge_key, default_edge_error)
                candidates.append((next_score, path + (nxt,)))
        if not candidates:
            break
        candidates.sort(key=lambda item: item[0])
        beam = candidates[: max(beam_width, 1)]
        best_partial = beam[0]

    completed = [(score, path) for score, path in beam if len(path) >= num_qubits]
    if not completed:
        layout, method = greedy_connected_layout(
            num_qubits=num_qubits,
            qubit_costs=qubit_costs,
            edge_errors=edge_errors,
            adjacency=adjacency,
            default_edge_error=default_edge_error,
        )
        score = float(
            sum(qubit_costs.get(qubit, 0.02) for qubit in layout)
            + sum(
                edge_errors.get(tuple(sorted((a, b))), default_edge_error)
                for a, b in zip(layout, layout[1:])
            )
        )
        return [
            summarize_chain_layout(
                backend,
                layout,
                method=method,
                score=score,
                beam_width=beam_width,
                rank=1,
                avoid_qubits=avoided,
            )
        ]

    layouts = []
    seen: set[tuple[int, ...]] = set()
    for score, path in completed:
        layout_tuple = tuple(path[:num_qubits])
        if layout_tuple in seen:
            continue
        seen.add(layout_tuple)
        layouts.append(
            summarize_chain_layout(
                backend,
                list(layout_tuple),
                method="beam_search_low_error_chain",
                score=float(score),
                beam_width=beam_width,
                rank=len(layouts) + 1,
                avoid_qubits=avoided,
            )
        )
        if len(layouts) >= max(limit, 1):
            break
    return layouts


def select_low_error_chain_layout(
    backend: Any,
    num_qubits: int,
    *,
    beam_width: int,
    avoid_qubits: set[int] | None = None,
) -> dict[str, object]:
    return select_low_error_chain_layouts(
        backend,
        num_qubits,
        beam_width=beam_width,
        limit=1,
        avoid_qubits=avoid_qubits,
    )[0]


def parse_int_list(value: str) -> list[int]:
    items = [item.strip() for item in value.split(",") if item.strip()]
    if not items:
        raise ValueError("empty integer list")
    return [int(item) for item in items]


def parse_avoid_qubits(value: str | None) -> set[int]:
    if value is None:
        return set()
    stripped = value.strip()
    if not stripped or stripped.lower() in {"none", "false", "off"}:
        return set()
    return set(parse_int_list(stripped))


def parse_zne_noise_factors(value: str) -> tuple[int, ...]:
    factors = tuple(dict.fromkeys(parse_int_list(value)))
    if 1 not in factors:
        factors = (1, *factors)
    for factor in factors:
        if factor < 1 or factor % 2 != 1:
            raise ValueError("ZNE noise factors must be positive odd integers")
    return tuple(sorted(factors))


def parse_steps_by_qubits(value: str | None) -> dict[int, int]:
    if not value:
        return dict(DEFAULT_STEPS_BY_QUBITS)
    parsed: dict[int, int] = {}
    for item in value.split(","):
        if not item.strip():
            continue
        key, raw_steps = item.split(":", 1)
        parsed[int(key.strip())] = int(raw_steps.strip())
    return parsed


def build_stage_config(
    *,
    qubits: int,
    steps: int,
    args: argparse.Namespace,
) -> AdvantageScaleConfig:
    if qubits % 2:
        raise ValueError("Fermi-Hubbard site count needs an even qubit count")
    mitigation = MitigationConfig(
        layout_selection=not args.disable_layout_selection,
        dynamical_decoupling=not args.disable_dd,
        dd_sequence=args.dd_sequence,
        dd_scheduling_method=args.dd_scheduling_method,
        pauli_twirling=not args.disable_twirling,
        twirl_randomizations=args.twirls,
        twirl_strategy=args.twirl_strategy,
        zne_mitigation=args.zne,
        zne_noise_factors=parse_zne_noise_factors(args.zne_noise_factors),
        zne_extrapolator=args.zne_extrapolator,
        zne_fold_scope=args.zne_fold_scope,
        readout_correction=not args.disable_readout_correction,
        readout_calibration_shots_per_state=args.readout_cal_shots,
        decay_recovery=not args.disable_decay_recovery,
        decay_confidence=args.decay_confidence,
        symmetry_postselection=args.symmetry_postselection,
    )
    return AdvantageScaleConfig(
        sites=qubits // 2,
        steps=steps,
        dt=args.dt,
        hopping=args.hopping,
        interaction_u=args.U,
        chemical_potential=args.mu,
        shots=args.shots,
        twirls=args.twirls,
        vacancy_site=args.vacancy_site,
        measured=True,
        circuit_family=args.circuit_family,
        mitigation=mitigation,
    )


def stage_echo_steps(cfg: AdvantageScaleConfig, policy: str) -> list[int]:
    if not cfg.mitigation.decay_recovery or policy == "none":
        return []
    if policy == "final":
        return [cfg.steps]
    if policy == "even-all":
        return decay_recovery_echo_steps(cfg.steps)
    if policy == "all":
        return all_decay_recovery_echo_steps(cfg.steps)
    raise ValueError(f"unsupported echo policy: {policy}")


def stage_zne_noise_factors(cfg: AdvantageScaleConfig) -> list[int]:
    if not cfg.mitigation.zne_mitigation:
        return [1]
    factors = [int(factor) for factor in cfg.mitigation.zne_noise_factors]
    if 1 not in factors:
        factors.insert(0, 1)
    unique = sorted(dict.fromkeys(factors))
    for factor in unique:
        if factor < 1 or factor % 2 != 1:
            raise ValueError("ZNE noise factors must be positive odd integers")
    if cfg.mitigation.zne_fold_scope != "global":
        raise ValueError("Only global ZNE folding is implemented for Sampler counts")
    return unique


def globally_fold_measured_circuit(circuit: QuantumCircuit, noise_factor: int) -> QuantumCircuit:
    """Return a measured odd-factor global fold C(Cdag C)^m.

    The ideal output distribution is unchanged, but the executable circuit is
    longer. Barriers keep the fold boundaries visible to the transpiler.
    """
    if noise_factor == 1:
        return circuit.copy()
    if noise_factor < 1 or noise_factor % 2 != 1:
        raise ValueError("ZNE global folding needs a positive odd noise factor")
    base = circuit.remove_final_measurements(inplace=False)
    folded = base.copy()
    folded.name = f"{circuit.name or 'circuit'}_zne{noise_factor}"
    for _ in range((noise_factor - 1) // 2):
        folded.barrier()
        folded.compose(base.inverse(), inplace=True)
        folded.barrier()
        folded.compose(base, inplace=True)
    folded.measure_all()
    return folded


def build_stage_circuit_groups(cfg: AdvantageScaleConfig, echo_policy: str) -> dict[str, list[QuantumCircuit]]:
    noise_factors = stage_zne_noise_factors(cfg)
    main = build_main_circuit(cfg)
    groups = {
        "main": [globally_fold_measured_circuit(main, factor) for factor in noise_factors],
        "readout": [],
        "echo": [],
    }
    if cfg.mitigation.readout_correction:
        groups["readout"] = build_readout_calibration_circuits(cfg.qubits)
    for echo_step in stage_echo_steps(cfg, echo_policy):
        echo = build_decay_recovery_echo_circuit(cfg, echo_step)
        groups["echo"].extend(globally_fold_measured_circuit(echo, factor) for factor in noise_factors)
    return groups


def summarize_circuit(circuit: QuantumCircuit) -> dict[str, object]:
    two_qubit_count = 0
    for instruction in circuit.data:
        if len(instruction.qubits) == 2:
            two_qubit_count += 1
    try:
        two_qubit_depth = int(circuit.depth(filter_function=lambda instruction: len(instruction.qubits) == 2))
    except Exception:
        two_qubit_depth = None
    return {
        "qubits": circuit.num_qubits,
        "clbits": circuit.num_clbits,
        "depth": circuit.depth(),
        "two_qubit_depth": two_qubit_depth,
        "two_qubit_count": two_qubit_count,
        "size": circuit.size(),
        "operation_counts": dict(circuit.count_ops()),
    }


def stage_circuit_metadata(cfg: AdvantageScaleConfig, echo_policy: str) -> dict[str, list[dict[str, object]]]:
    echo_steps = stage_echo_steps(cfg, echo_policy)
    noise_factors = stage_zne_noise_factors(cfg)
    return {
        "main": [
            {
                "role": "main",
                "circuit_family": cfg.circuit_family,
                "resource_skeleton": cfg.circuit_family == "native-fswap-cz-skeleton",
                "logical_forward_steps": cfg.steps,
                "echo_steps": None,
                "echo_convention": None,
                "zne_noise_factor": factor,
                "zne_fold_scope": cfg.mitigation.zne_fold_scope,
                "zne_extrapolator": cfg.mitigation.zne_extrapolator,
            }
            for factor in noise_factors
        ],
        "readout": [
            {"role": "readout_all0", "calibration_state": "0" * cfg.qubits},
            {"role": "readout_all1", "calibration_state": "1" * cfg.qubits},
        ]
        if cfg.mitigation.readout_correction
        else [],
        "echo": [
            {
                "role": "echo",
                "circuit_family": cfg.circuit_family,
                "resource_skeleton": cfg.circuit_family == "native-fswap-cz-skeleton",
                "echo_steps": echo_step,
                "logical_forward_steps": echo_step,
                "logical_inverse_steps": echo_step,
                "echo_convention": "U_dagger(k) U(k) with a barrier at the echo boundary",
                "zne_noise_factor": factor,
                "zne_fold_scope": cfg.mitigation.zne_fold_scope,
                "zne_extrapolator": cfg.mitigation.zne_extrapolator,
            }
            for echo_step in echo_steps
            for factor in noise_factors
        ],
    }


def parse_optional_int_list(value: str) -> list[int | None]:
    items = [item.strip() for item in value.split(",") if item.strip()]
    if not items:
        raise ValueError("empty seed list")
    parsed: list[int | None] = []
    for item in items:
        parsed.append(None if item.lower() in {"none", "default"} else int(item))
    return parsed


def parse_string_set(value: str) -> set[str]:
    return {item.strip() for item in value.split(",") if item.strip()}


def qarg_index(circuit: QuantumCircuit, qarg: Any) -> int:
    return int(circuit.find_bit(qarg).index)


def estimate_transpiled_circuit(
    *,
    backend: Any,
    circuit: QuantumCircuit,
    depth_weight: float,
    cz_weight: float,
    hotspot_weight: float,
) -> dict[str, object]:
    edge_errors = backend_cz_error_map(backend)
    known_edges = list(edge_errors.values())
    default_edge_error = float(median(known_edges)) if known_edges else 0.01

    cz_edges: dict[str, int] = {}
    cz_edge_risks: dict[str, float] = {}
    cz_error_sum = 0.0
    readout_error_sum = 0.0
    measured_qubits = []
    for instruction in circuit.data:
        operation = instruction.operation
        qargs = instruction.qubits
        if operation.name == "cz" and len(qargs) == 2:
            a, b = sorted((qarg_index(circuit, qargs[0]), qarg_index(circuit, qargs[1])))
            edge = (a, b)
            edge_key = f"{a}-{b}"
            edge_error = edge_errors.get(edge, default_edge_error)
            cz_edges[edge_key] = cz_edges.get(edge_key, 0) + 1
            cz_edge_risks[edge_key] = cz_edge_risks.get(edge_key, 0.0) + float(edge_error)
            cz_error_sum += edge_error
        elif operation.name == "measure" and qargs:
            qubit = qarg_index(circuit, qargs[0])
            measured_qubits.append(qubit)
            readout_error_sum += backend_qubit_property(backend, qubit, "readout_error", 0.02)

    op_counts = dict(circuit.count_ops())
    cz_count = int(op_counts.get("cz", 0))
    two_qubit_count = sum(1 for instruction in circuit.data if len(instruction.qubits) == 2)
    try:
        two_qubit_depth = int(circuit.depth(filter_function=lambda instruction: len(instruction.qubits) == 2))
    except Exception:
        two_qubit_depth = None
    depth = int(circuit.depth())
    max_edge_uses = max(cz_edges.values(), default=0)
    max_edge_risk = max(cz_edge_risks.values(), default=0.0)
    hotspot_penalty = float(hotspot_weight * max_edge_risk)
    score = float(cz_error_sum + readout_error_sum + depth_weight * depth + cz_weight * cz_count + hotspot_penalty)
    return {
        "score": score,
        "cz_count": cz_count,
        "two_qubit_count": two_qubit_count,
        "two_qubit_depth": two_qubit_depth,
        "depth": depth,
        "size": int(circuit.size()),
        "cz_error_sum": float(cz_error_sum),
        "readout_error_sum": float(readout_error_sum),
        "depth_penalty": float(depth_weight * depth),
        "cz_count_penalty": float(cz_weight * cz_count),
        "cz_hotspot_penalty": hotspot_penalty,
        "cz_hotspot_weight": float(hotspot_weight),
        "max_edge_uses": int(max_edge_uses),
        "max_edge_risk": float(max_edge_risk),
        "measured_qubits": measured_qubits,
        "cz_edges": dict(sorted(cz_edges.items(), key=lambda item: item[0])),
        "cz_edge_risks": dict(sorted(cz_edge_risks.items(), key=lambda item: item[0])),
    }


def transpile_with_selection(
    *,
    backend: Any,
    circuits: list[QuantumCircuit],
    optimization_level: int,
    initial_layout: list[int] | None,
    seed_transpiler: int | None,
) -> list[QuantumCircuit]:
    transpile_kwargs: dict[str, object] = {
        "backend": backend,
        "optimization_level": optimization_level,
    }
    if initial_layout is not None:
        transpile_kwargs["initial_layout"] = initial_layout
    if seed_transpiler is not None:
        transpile_kwargs["seed_transpiler"] = seed_transpiler
    result = transpile(circuits, **transpile_kwargs)
    return result if isinstance(result, list) else [result]


def score_transpiled_group(
    *,
    backend: Any,
    circuits: list[QuantumCircuit],
    depth_weight: float,
    cz_weight: float,
    hotspot_weight: float,
) -> dict[str, object]:
    estimates = [
        estimate_transpiled_circuit(
            backend=backend,
            circuit=circuit,
            depth_weight=depth_weight,
            cz_weight=cz_weight,
            hotspot_weight=hotspot_weight,
        )
        for circuit in circuits
    ]
    return {
        "score": float(sum(float(item["score"]) for item in estimates)),
        "cz_count": int(sum(int(item["cz_count"]) for item in estimates)),
        "two_qubit_count": int(sum(int(item["two_qubit_count"]) for item in estimates)),
        "two_qubit_depth_max": int(max((int(item["two_qubit_depth"]) for item in estimates if item["two_qubit_depth"] is not None), default=0)),
        "depth_max": int(max((int(item["depth"]) for item in estimates), default=0)),
        "cz_error_sum": float(sum(float(item["cz_error_sum"]) for item in estimates)),
        "readout_error_sum": float(sum(float(item["readout_error_sum"]) for item in estimates)),
        "cz_hotspot_penalty": float(sum(float(item["cz_hotspot_penalty"]) for item in estimates)),
        "max_edge_uses": int(max((int(item["max_edge_uses"]) for item in estimates), default=0)),
        "max_edge_risk": float(max((float(item["max_edge_risk"]) for item in estimates), default=0.0)),
        "circuit_estimates": estimates,
    }


def compile_group_candidates(
    *,
    backend: Any,
    group_name: str,
    circuits: list[QuantumCircuit],
    layout_candidates: list[dict[str, object]],
    seeds: list[int | None],
    optimization_level: int,
    depth_weight: float,
    cz_weight: float,
    hotspot_weight: float,
) -> tuple[dict[str, object], list[QuantumCircuit], list[dict[str, object]]]:
    candidates = []
    best_record: dict[str, object] | None = None
    best_circuits: list[QuantumCircuit] | None = None

    if not circuits:
        empty_record = {
            "group": group_name,
            "score": 0.0,
            "seed_transpiler": None,
            "layout_rank": None,
            "layout": None,
            "transpiled_summaries": [],
            "score_terms": {},
        }
        return empty_record, [], []

    for layout in layout_candidates:
        initial_layout = list(layout["logical_to_physical"])
        for seed in seeds:
            transpiled = transpile_with_selection(
                backend=backend,
                circuits=circuits,
                optimization_level=optimization_level,
                initial_layout=initial_layout,
                seed_transpiler=seed,
            )
            score_terms = score_transpiled_group(
                backend=backend,
                circuits=transpiled,
                depth_weight=depth_weight,
                cz_weight=cz_weight,
                hotspot_weight=hotspot_weight,
            )
            record = {
                "group": group_name,
                "score": score_terms["score"],
                "seed_transpiler": seed,
                "layout_rank": layout.get("rank"),
                "layout": layout,
                "score_terms": score_terms,
                "transpiled_summaries": [summarize_circuit(circuit) for circuit in transpiled],
            }
            candidates.append(
                {
                    "group": group_name,
                    "score": score_terms["score"],
                    "seed_transpiler": seed,
                    "layout_rank": layout.get("rank"),
                    "cz_count": score_terms["cz_count"],
                    "two_qubit_count": score_terms["two_qubit_count"],
                    "two_qubit_depth_max": score_terms["two_qubit_depth_max"],
                    "depth_max": score_terms["depth_max"],
                    "cz_error_sum": score_terms["cz_error_sum"],
                    "readout_error_sum": score_terms["readout_error_sum"],
                    "cz_hotspot_penalty": score_terms["cz_hotspot_penalty"],
                    "max_edge_uses": score_terms["max_edge_uses"],
                    "max_edge_risk": score_terms["max_edge_risk"],
                }
            )
            if best_record is None or float(record["score"]) < float(best_record["score"]):
                best_record = record
                best_circuits = transpiled

    assert best_record is not None
    assert best_circuits is not None
    candidates.sort(key=lambda item: (float(item["score"]), int(item["layout_rank"] or 10**9), str(item["seed_transpiler"])))
    return best_record, best_circuits, candidates


def build_compile_selection(
    *,
    backend: Any,
    groups: dict[str, list[QuantumCircuit]],
    layout_candidates: list[dict[str, object]],
    seeds: list[int | None],
    optimization_level: int,
    sweep_groups: set[str],
    depth_weight: float,
    cz_weight: float,
    hotspot_weight: float,
) -> tuple[dict[str, object], dict[str, list[QuantumCircuit]]]:
    all_candidates: dict[str, list[dict[str, object]]] = {group_name: [] for group_name in groups}
    per_layout_records: dict[int, dict[str, object]] = {}
    per_layout_circuits: dict[int, dict[str, list[QuantumCircuit]]] = {}
    swept_layout_scores: dict[int, float] = {}

    for layout in layout_candidates:
        layout_rank = int(layout.get("rank") or len(per_layout_records) + 1)
        group_records: dict[str, dict[str, object]] = {}
        group_circuits: dict[str, list[QuantumCircuit]] = {}
        swept_score = 0.0
        for group_name, circuits in groups.items():
            best_record, best_circuits, candidates = compile_group_candidates(
                backend=backend,
                group_name=group_name,
                circuits=circuits,
                layout_candidates=[layout],
                seeds=seeds if group_name in sweep_groups else [seeds[0]],
                optimization_level=optimization_level,
                depth_weight=depth_weight,
                cz_weight=cz_weight,
                hotspot_weight=hotspot_weight,
            )
            group_records[group_name] = best_record
            group_circuits[group_name] = best_circuits
            all_candidates[group_name].extend(candidates)
            if group_name in sweep_groups:
                swept_score += float(best_record["score"])
        per_layout_records[layout_rank] = {
            "layout": layout,
            "groups": group_records,
            "swept_score": swept_score,
        }
        per_layout_circuits[layout_rank] = group_circuits
        swept_layout_scores[layout_rank] = swept_score

    selected_layout_rank = min(
        swept_layout_scores,
        key=lambda rank: (float(swept_layout_scores[rank]), rank),
    )
    selected_records = per_layout_records[selected_layout_rank]["groups"]
    selected_circuits_by_group = per_layout_circuits[selected_layout_rank]
    selected_layout = per_layout_records[selected_layout_rank]["layout"]
    for candidates in all_candidates.values():
        candidates.sort(key=lambda item: (float(item["score"]), int(item["layout_rank"] or 10**9), str(item["seed_transpiler"])))

    compile_plan = {
        "enabled": True,
        "backend": backend_name(backend),
        "optimization_level": optimization_level,
        "seeds": seeds,
        "sweep_groups": sorted(sweep_groups),
        "depth_weight": depth_weight,
        "cz_weight": cz_weight,
        "hotspot_weight": hotspot_weight,
        "layout_candidates": layout_candidates,
        "layout_scores_from_swept_groups": dict(sorted(swept_layout_scores.items())),
        "selected_layout_rank": selected_layout_rank,
        "selected_layout": selected_layout,
        "selected_layout_constraint": "main/readout/echo share one physical layout",
        "selected_groups": selected_records,
        "candidate_leaderboards": all_candidates,
        "warning": "Compile scores are calibration-derived heuristics; hardware validation still decides.",
    }
    return compile_plan, selected_circuits_by_group


def submit_group(
    *,
    backend: Any,
    circuits: list[QuantumCircuit],
    shots: int,
    optimization_level: int,
    sampler_options: dict[str, object],
    initial_layout: list[int] | None,
    layout_selection: dict[str, object] | None,
    precompiled_circuits: list[QuantumCircuit] | None = None,
    compile_selection: dict[str, object] | None = None,
    circuit_metadata: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    if not circuits:
        return {"submitted": False, "reason": "empty group"}

    from qiskit_ibm_runtime import SamplerV2

    if precompiled_circuits is None:
        transpiled = transpile_with_selection(
            backend=backend,
            circuits=circuits,
            optimization_level=optimization_level,
            initial_layout=initial_layout,
            seed_transpiler=None,
        )
    else:
        transpiled = precompiled_circuits
    sampler = SamplerV2(mode=backend, options=sampler_options) if sampler_options else SamplerV2(mode=backend)
    job = sampler.run(transpiled, shots=shots)
    return {
        "submitted": True,
        "job_id": str(job.job_id()),
        "backend": backend_name(backend),
        "shots": shots,
        "circuit_count": len(transpiled),
        "layout_selection": layout_selection,
        "compile_selection": compile_selection,
        "circuit_metadata": circuit_metadata or [],
        "transpiled_summaries": [summarize_circuit(circuit) for circuit in transpiled],
    }


def write_stage_plan(
    *,
    cfg: AdvantageScaleConfig,
    stage_dir: Path,
    echo_policy: str,
    include_circuit_summaries: bool,
    layout_selection: dict[str, object] | None,
    compile_plan: dict[str, object] | None,
) -> dict[str, object]:
    stage_dir.mkdir(parents=True, exist_ok=True)
    write_resource_artifacts(cfg, stage_dir)
    groups = build_stage_circuit_groups(cfg, echo_policy)
    echo_steps = stage_echo_steps(cfg, echo_policy)
    circuit_metadata = stage_circuit_metadata(cfg, echo_policy)
    resources = qctrl_paper_native_resources(cfg)
    resources_dict = asdict(resources)
    resources_dict.update(
        {
            "stage_echo_policy": echo_policy,
            "stage_echo_steps": echo_steps,
            "stage_echo_circuit_count": len(echo_steps),
        }
    )
    plan = {
        "config": asdict(cfg),
        "paper_native_resources": resources_dict,
        "runtime_sampler_options": runtime_sampler_options(cfg),
        "echo_policy": echo_policy,
        "echo_steps": echo_steps,
        "echo_convention": "U_dagger(k) U(k), where k is the listed echo step; barrier prevents boundary cancellation",
        "semantic_mapping": semantic_mapping_manifest(cfg),
        "layout_selection": layout_selection or {"enabled": cfg.mitigation.layout_selection, "status": "not evaluated"},
        "compile_selection": compile_plan or {"enabled": False, "status": "not evaluated"},
        "circuit_groups": {
            group_name: {
                "circuit_count": len(circuits),
                "shots": cfg.mitigation.readout_calibration_shots_per_state
                if group_name == "readout"
                else cfg.shots,
                "circuit_metadata": circuit_metadata[group_name],
                "summaries": [summarize_circuit(circuit) for circuit in circuits] if include_circuit_summaries else [],
            }
            for group_name, circuits in groups.items()
        },
    }
    plan["circuit_groups"]["echo"]["echo_steps"] = echo_steps
    plan["zne_noise_factors"] = stage_zne_noise_factors(cfg)
    (stage_dir / "stage_plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    return plan


def run_staged(args: argparse.Namespace) -> Path:
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    avoid_qubits = parse_avoid_qubits(args.avoid_qubits)

    stage_qubits = [q for q in parse_int_list(args.stage_qubits) if q <= args.max_qubits]
    if not stage_qubits:
        raise ValueError("No stages selected; check --stage-qubits and --max-qubits")
    if args.submit and len(stage_qubits) > 1 and not args.allow_multiple_submit:
        raise RuntimeError(
            "Refusing to submit multiple stages at once. Use --max-qubits 20 first, "
            "or pass --allow-multiple-submit deliberately."
        )

    steps_by_qubits = parse_steps_by_qubits(args.steps_by_qubits)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = outdir / f"staged_run_{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)

    service = None
    backend = None
    if args.submit or args.inspect_backend:
        service = build_runtime_service()
        backend = select_backend(
            service,
            args.backend,
            min_qubits=max(stage_qubits),
            backend_policy=args.backend_policy,
            layout_beam_width=args.layout_beam_width,
            avoid_qubits=avoid_qubits,
        )

    manifest: dict[str, object] = {
        "created_at_utc": run_id,
        "submit": bool(args.submit),
        "backend": backend_name(backend) if backend is not None else args.backend,
        "backend_policy": args.backend_policy,
        "avoided_physical_qubits": sorted(avoid_qubits),
        "circuit_family": args.circuit_family,
        "compile_sweep": {
            "enabled": not args.disable_compile_sweep,
            "layout_candidates": args.compile_layout_candidates,
            "transpiler_seeds": parse_optional_int_list(args.transpiler_seeds),
            "groups": sorted(parse_string_set(args.compile_sweep_groups)),
            "depth_weight": args.compile_depth_weight,
            "cz_weight": args.compile_cz_weight,
            "hotspot_weight": args.compile_hotspot_weight,
        },
        "selected_stage_qubits": stage_qubits,
        "stages": [],
    }

    for qubits in stage_qubits:
        steps = steps_by_qubits.get(qubits)
        if steps is None:
            steps = max(2, round(30 * qubits / 120))
            if steps % 2:
                steps += 1
        cfg = build_stage_config(qubits=qubits, steps=steps, args=args)
        groups = build_stage_circuit_groups(cfg, args.echo_policy)
        circuit_metadata = stage_circuit_metadata(cfg, args.echo_policy)
        layout_selection = None
        layout_candidates: list[dict[str, object]] = []
        initial_layout = None
        compile_plan = None
        compiled_groups: dict[str, list[QuantumCircuit]] = {}
        if backend is not None and cfg.mitigation.layout_selection:
            layout_candidates = select_low_error_chain_layouts(
                backend,
                cfg.qubits,
                beam_width=args.layout_beam_width,
                limit=args.compile_layout_candidates,
                avoid_qubits=avoid_qubits,
            )
            layout_selection = layout_candidates[0]
            initial_layout = list(layout_selection["logical_to_physical"])
            if not args.disable_compile_sweep:
                compile_plan, compiled_groups = build_compile_selection(
                    backend=backend,
                    groups=groups,
                    layout_candidates=layout_candidates,
                    seeds=parse_optional_int_list(args.transpiler_seeds),
                    optimization_level=args.optimization_level,
                    sweep_groups=parse_string_set(args.compile_sweep_groups),
                    depth_weight=args.compile_depth_weight,
                    cz_weight=args.compile_cz_weight,
                    hotspot_weight=args.compile_hotspot_weight,
                )
                selected_layout = compile_plan.get("selected_layout")
                if selected_layout:
                    layout_selection = selected_layout
                    initial_layout = list(selected_layout["logical_to_physical"])
        stage_dir = run_dir / f"q{qubits}_steps{steps}"
        plan = write_stage_plan(
            cfg=cfg,
            stage_dir=stage_dir,
            echo_policy=args.echo_policy,
            include_circuit_summaries=args.include_circuit_summaries,
            layout_selection=layout_selection,
            compile_plan=compile_plan,
        )

        stage_record: dict[str, object] = {
            "qubits": qubits,
            "sites": cfg.sites,
            "steps": steps,
            "stage_dir": str(stage_dir),
            "plan_path": str(stage_dir / "stage_plan.json"),
            "layout_selection": layout_selection or {"enabled": cfg.mitigation.layout_selection, "status": "not evaluated"},
            "layout_candidates": layout_candidates,
            "compile_selection": compile_plan or {"enabled": False, "status": "not evaluated"},
            "submit_results": {},
        }

        if args.submit:
            assert backend is not None
            sampler_options = runtime_sampler_options(cfg)
            submit_results = {
                "main": submit_group(
                    backend=backend,
                    circuits=groups["main"],
                    shots=cfg.shots,
                    optimization_level=args.optimization_level,
                    sampler_options=sampler_options,
                    initial_layout=initial_layout,
                    layout_selection=layout_selection,
                    precompiled_circuits=compiled_groups.get("main"),
                    compile_selection=(compile_plan or {}).get("selected_groups", {}).get("main") if compile_plan else None,
                    circuit_metadata=circuit_metadata["main"],
                ),
                "readout": submit_group(
                    backend=backend,
                    circuits=groups["readout"],
                    shots=cfg.mitigation.readout_calibration_shots_per_state,
                    optimization_level=args.optimization_level,
                    sampler_options={},
                    initial_layout=initial_layout,
                    layout_selection=layout_selection,
                    precompiled_circuits=compiled_groups.get("readout"),
                    compile_selection=(compile_plan or {}).get("selected_groups", {}).get("readout") if compile_plan else None,
                    circuit_metadata=circuit_metadata["readout"],
                ),
                "echo": submit_group(
                    backend=backend,
                    circuits=groups["echo"],
                    shots=cfg.shots,
                    optimization_level=args.optimization_level,
                    sampler_options=sampler_options,
                    initial_layout=initial_layout,
                    layout_selection=layout_selection,
                    precompiled_circuits=compiled_groups.get("echo"),
                    compile_selection=(compile_plan or {}).get("selected_groups", {}).get("echo") if compile_plan else None,
                    circuit_metadata=circuit_metadata["echo"],
                ),
            }
            (stage_dir / "submitted_jobs.json").write_text(json.dumps(submit_results, indent=2) + "\n")
            stage_record["submit_results"] = submit_results

        stage_record["planned_circuit_groups"] = plan["circuit_groups"]
        manifest["stages"].append(stage_record)

    manifest_path = run_dir / "staged_run_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-qubits", default="20,40,60,80,100,120")
    parser.add_argument("--max-qubits", type=int, default=20)
    parser.add_argument("--steps-by-qubits", default=None)
    parser.add_argument("--backend", default=None)
    parser.add_argument("--backend-policy", default="quality", choices=["quality", "balanced", "least-busy"])
    parser.add_argument(
        "--circuit-family",
        default="logical",
        choices=sorted(SUPPORTED_CIRCUIT_FAMILIES),
        help="Circuit family to stage: logical baseline, physical native fSWAP/CZ, or resource skeleton.",
    )
    parser.add_argument("--inspect-backend", action="store_true")
    parser.add_argument("--list-backends", action="store_true")
    parser.add_argument("--submit", action="store_true")
    parser.add_argument("--allow-multiple-submit", action="store_true")
    parser.add_argument("--include-circuit-summaries", action="store_true")
    parser.add_argument("--optimization-level", type=int, default=1)
    parser.add_argument("--disable-layout-selection", action="store_true")
    parser.add_argument(
        "--avoid-qubits",
        default="",
        help="Comma-separated physical qubit ids to exclude from backend/layout selection.",
    )
    parser.add_argument("--layout-beam-width", type=int, default=256)
    parser.add_argument("--disable-compile-sweep", action="store_true")
    parser.add_argument("--compile-layout-candidates", type=int, default=3)
    parser.add_argument("--transpiler-seeds", default="11,23,37")
    parser.add_argument("--compile-sweep-groups", default="main,echo")
    parser.add_argument("--compile-depth-weight", type=float, default=0.0001)
    parser.add_argument("--compile-cz-weight", type=float, default=0.0)
    parser.add_argument(
        "--compile-hotspot-weight",
        type=float,
        default=1.0,
        help="Penalty for repeatedly using the single riskiest CZ edge during compile/layout selection.",
    )
    parser.add_argument("--echo-policy", default="final", choices=["none", "final", "even-all", "all"])
    parser.add_argument("--shots", type=int, default=4096)
    parser.add_argument("--readout-cal-shots", type=int, default=4096)
    parser.add_argument("--twirls", type=int, default=8)
    parser.add_argument("--dt", type=float, default=0.2)
    parser.add_argument("--hopping", type=float, default=1.0)
    parser.add_argument("--U", type=float, default=-2.0)
    parser.add_argument("--mu", type=float, default=0.0)
    parser.add_argument("--vacancy-site", type=int, default=None)
    parser.add_argument("--disable-dd", action="store_true")
    parser.add_argument("--dd-sequence", default="XY4")
    parser.add_argument("--dd-scheduling-method", default="alap")
    parser.add_argument("--disable-twirling", action="store_true")
    parser.add_argument("--twirl-strategy", default="active-accum")
    parser.add_argument("--zne", action="store_true", help="Enable client-side global-folding ZNE circuit set.")
    parser.add_argument("--zne-noise-factors", default="1,3", help="Positive odd ZNE noise factors; 1 is added if omitted.")
    parser.add_argument("--zne-extrapolator", default="linear", choices=["linear"])
    parser.add_argument("--zne-fold-scope", default="global", choices=["global"])
    parser.add_argument("--disable-readout-correction", action="store_true")
    parser.add_argument("--disable-decay-recovery", action="store_true")
    parser.add_argument("--decay-confidence", type=float, default=0.5)
    parser.add_argument("--symmetry-postselection", action="store_true")
    parser.add_argument("--outdir", default="results_ibm_staged")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    avoid_qubits = parse_avoid_qubits(args.avoid_qubits)
    if args.list_backends:
        rows = list_backend_inventory(
            min_qubits=args.max_qubits,
            layout_beam_width=args.layout_beam_width,
            avoid_qubits=avoid_qubits,
        )
        print(json.dumps(rows, indent=2))
        return

    manifest_path = run_staged(args)
    print(f"Wrote {manifest_path}")
    if not args.submit:
        print("Dry-run only. Add --submit to send the selected stage to IBM Runtime.")


if __name__ == "__main__":
    main()
