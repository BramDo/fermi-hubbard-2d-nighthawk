#!/usr/bin/env python3
"""Budget-gated IBM Estimator PEC/ZNE routes for the 6x6 2D Hubbard circuit."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import time
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import numpy as np
import qiskit.qpy as qpy
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import SparsePauliOp

from cuprate_2d_hubbard_pipeline import SPIN_DOWN, SPIN_UP, mode_qubit, site_coord, validate_config
from cuprate_2d_qiskit_circuit import build_circuit, load_config
from ibm_staged_fermi_hubbard_runner import backend_name, backend_pending_jobs, build_runtime_service, summarize_circuit


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def pauli_label(qubits: int, operators: dict[int, str]) -> str:
    label = ["I"] * qubits
    for qubit, pauli in operators.items():
        label[qubits - 1 - int(qubit)] = pauli
    return "".join(label)


def site_observables(cfg: Any) -> tuple[list[SparsePauliOp], list[dict[str, Any]]]:
    identity = "I" * cfg.qubits
    observables: list[SparsePauliOp] = []
    records: list[dict[str, Any]] = []
    for site in range(cfg.sites):
        x, y = site_coord(cfg, site)
        up = mode_qubit(site, SPIN_UP)
        down = mode_qubit(site, SPIN_DOWN)
        z_up = pauli_label(cfg.qubits, {up: "Z"})
        z_down = pauli_label(cfg.qubits, {down: "Z"})
        zz = pauli_label(cfg.qubits, {up: "Z", down: "Z"})
        definitions = (
            ("n_up", [(identity, 0.5), (z_up, -0.5)]),
            ("n_down", [(identity, 0.5), (z_down, -0.5)]),
            ("double_occupancy", [(identity, 0.25), (z_up, -0.25), (z_down, -0.25), (zz, 0.25)]),
        )
        for name, terms in definitions:
            observables.append(SparsePauliOp.from_list(terms))
            records.append({"site": site, "x": x, "y": y, "observable": name, "term_count": len(terms)})
    return observables, records


def instruction_sha256(circuit: QuantumCircuit) -> str:
    rows = []
    for instruction in circuit.data:
        rows.append(
            [
                instruction.operation.name,
                [circuit.find_bit(qubit).index for qubit in instruction.qubits],
                [circuit.find_bit(bit).index for bit in instruction.clbits],
                [round(float(value), 12) if hasattr(value, "__float__") else str(value) for value in instruction.operation.params],
            ]
        )
    payload = json.dumps(rows, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def qpy_sha256(circuit: QuantumCircuit) -> str:
    buffer = io.BytesIO()
    qpy.dump(circuit, buffer)
    return hashlib.sha256(buffer.getvalue()).hexdigest()


def estimator_options(args: argparse.Namespace) -> Any:
    from qiskit_ibm_runtime.options import EstimatorOptions

    options = EstimatorOptions()
    options.max_execution_time = int(args.max_execution_time)
    options.default_shots = int(args.shots)
    options.resilience_level = 0
    options.resilience.measure_mitigation = False
    options.environment.job_tags = ["2d-cuprate", "ibm-phoenix", args.method, "budgeted"]
    if args.method == "pec":
        options.resilience.zne_mitigation = False
        options.resilience.pec_mitigation = True
        options.resilience.pec.max_overhead = float(args.pec_max_overhead)
        options.resilience.pec.noise_gain = "auto"
        options.resilience.layer_noise_learning.max_layers_to_learn = 1
        options.resilience.layer_noise_learning.shots_per_randomization = 32
        options.resilience.layer_noise_learning.num_randomizations = 2
        options.resilience.layer_noise_learning.layer_pair_depths = (0, 1, 2)
    else:
        options.resilience.pec_mitigation = False
        options.resilience.zne_mitigation = True
        options.resilience.zne.amplifier = "gate_folding"
        options.resilience.zne.noise_factors = tuple(args.zne_noise_factors)
        options.resilience.zne.extrapolator = ("linear", "fallback")
        options.resilience.zne.extrapolated_noise_factors = (0.0,)
    return options


def status_name(job: Any) -> str:
    status = job.status()
    return str(getattr(status, "name", status))


def build_plan(args: argparse.Namespace) -> tuple[Any, QuantumCircuit, list[SparsePauliOp], list[dict[str, Any]], dict[str, Any]]:
    cfg = replace(load_config(args.config), steps=1)
    validate_config(cfg)
    service = build_runtime_service(args.account_name)
    backend = service.backend(args.backend)
    logical, _ = build_circuit(cfg, measured=False, circuit_family="number_preserving_t_only")
    isa = transpile(
        logical,
        backend=backend,
        optimization_level=int(args.optimization_level),
        seed_transpiler=int(args.seed_transpiler),
    )
    observables, records = site_observables(cfg)
    isa_observables = [observable.apply_layout(isa.layout) for observable in observables]
    if isa.num_clbits or any(instruction.operation.name == "measure" for instruction in isa.data):
        raise ValueError("Estimator ISA circuit must not contain measurements or classical bits")
    if any(observable.num_qubits != isa.num_qubits for observable in isa_observables):
        raise ValueError("ISA observable width does not match the transpiled circuit")
    unsupported = sorted(
        {
            instruction.operation.name
            for instruction in isa.data
            if instruction.operation.name not in backend.target.operation_names and instruction.operation.name != "barrier"
        }
    )
    if unsupported:
        raise ValueError(f"ISA circuit has unsupported operations: {unsupported}")

    options = estimator_options(args)
    if args.method == "pec":
        target_shots = int(np.ceil(args.shots * args.pec_max_overhead))
        learning_shots = 1 * 3 * 9 * 2 * 32
    else:
        target_shots = int(args.shots * len(args.zne_noise_factors))
        learning_shots = 0
    plan = {
        "created_at_unix": time.time(),
        "method": args.method,
        "backend": backend_name(backend),
        "backend_pending_jobs": backend_pending_jobs(backend),
        "account_name": args.account_name,
        "shots": int(args.shots),
        "max_execution_time": int(args.max_execution_time),
        "pec_max_overhead": float(args.pec_max_overhead) if args.method == "pec" else None,
        "zne_noise_factors": list(args.zne_noise_factors) if args.method == "zne" else None,
        "measurement_mitigation": False,
        "observable_count": len(isa_observables),
        "observable_records": records,
        "logical_summary": summarize_circuit(logical),
        "isa_summary": summarize_circuit(isa),
        "instruction_sha256": instruction_sha256(isa),
        "qpy_sha256": qpy_sha256(isa),
        "options": asdict(options),
        "shot_accounting": {
            "target_shots_bound": target_shots,
            "layer_learning_shots_upper_bound": learning_shots,
            "combined_shots_upper_bound": target_shots + learning_shots,
            "note": "Shot bounds are conservative counts, not a prediction of billed QPU seconds.",
        },
        "static_compatibility_passed": True,
        "submit_requested": bool(args.submit),
        "claim_boundary": "PEC/ZNE Estimator diagnostic for diagonal site observables; not a superconductivity or quantum-advantage claim.",
    }
    return backend, isa, isa_observables, records, plan


def extract_result(outdir: Path, job: Any, records: list[dict[str, Any]], method: str) -> None:
    primitive = job.result()
    pub = primitive[0]
    data = pub.data
    arrays: dict[str, Any] = {}
    for name in (
        "evs",
        "stds",
        "evs_noise_factors",
        "stds_noise_factors",
        "ensemble_stds_noise_factors",
        "evs_extrapolated",
        "stds_extrapolated",
    ):
        if hasattr(data, name):
            arrays[name] = np.asarray(getattr(data, name)).tolist()
    write_json(outdir / "estimator_result.json", {"method": method, "arrays": arrays, "metadata": getattr(pub, "metadata", {})})

    values = np.asarray(getattr(data, "evs"), dtype=float).reshape(-1)
    stds = np.asarray(getattr(data, "stds", np.full_like(values, np.nan)), dtype=float).reshape(-1)
    if len(values) != len(records):
        raise ValueError(f"Estimator returned {len(values)} values for {len(records)} observables")
    by_site: dict[int, dict[str, Any]] = {}
    for record, value, standard_error in zip(records, values, stds, strict=True):
        row = by_site.setdefault(
            int(record["site"]),
            {"source": method, "profile": method, "step": 1, "time": 0.1, "site": record["site"], "x": record["x"], "y": record["y"]},
        )
        row[str(record["observable"])] = float(value)
        row[f"{record['observable']}_standard_error"] = float(standard_error)
    rows = []
    for site in sorted(by_site):
        row = by_site[site]
        row["charge"] = row["n_up"] + row["n_down"]
        row["spin_z"] = row["n_up"] - row["n_down"]
        row["hole_density"] = 1.0 - row["charge"]
        rows.append(row)
    write_csv(outdir / "site_observables.csv", rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--method", choices=["pec", "zne"], required=True)
    parser.add_argument("--backend", default="ibm_phoenix")
    parser.add_argument("--account-name", default="qiskit-runtime-q9")
    parser.add_argument("--shots", type=int, default=128)
    parser.add_argument("--max-execution-time", type=int, default=5)
    parser.add_argument("--pec-max-overhead", type=float, default=2.0)
    parser.add_argument("--zne-noise-factors", type=float, nargs="+", default=[1.0, 3.0, 5.0])
    parser.add_argument("--optimization-level", type=int, default=1)
    parser.add_argument("--seed-transpiler", type=int, default=9)
    parser.add_argument("--submit", action="store_true")
    parser.add_argument("--retrieve", action="store_true")
    parser.add_argument("--wait-seconds", type=int, default=0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.submit and args.retrieve:
        raise ValueError("--submit and --retrieve are mutually exclusive")
    if args.shots <= 0 or args.max_execution_time <= 0:
        raise ValueError("shots and max execution time must be positive")
    if args.pec_max_overhead < 1:
        raise ValueError("PEC max overhead must be at least one")
    if len(args.zne_noise_factors) < 3 or args.zne_noise_factors[0] != 1.0:
        raise ValueError("ZNE requires at least three factors starting at 1.0")
    args.outdir.mkdir(parents=True, exist_ok=True)

    receipt_path = args.outdir / "submission_receipt.json"
    if args.retrieve:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        service = build_runtime_service(args.account_name)
        job = service.job(str(receipt["job_id"]))
        status = status_name(job)
        receipt["last_status"] = status
        receipt["last_checked_unix"] = time.time()
        if status == "DONE":
            metrics = job.metrics() or {}
            receipt["job_metrics"] = metrics
            usage = metrics.get("usage", {}) if isinstance(metrics, dict) else {}
            receipt["qpu_charge_time_seconds"] = usage.get("qpu_charge_time_seconds")
            plan = json.loads((args.outdir / "plan.json").read_text(encoding="utf-8"))
            extract_result(args.outdir, job, list(plan["observable_records"]), args.method)
        write_json(receipt_path, receipt)
        print(f"Job {receipt['job_id']} status: {status}")
        return

    backend, isa, isa_observables, _records, plan = build_plan(args)
    write_json(args.outdir / "plan.json", plan)
    print(args.outdir / "plan.json")
    if not args.submit:
        print("Dry-run only. Add --submit for one separately authorized Estimator job.")
        return
    if receipt_path.exists():
        raise FileExistsError(f"Refusing duplicate submission: {receipt_path}")

    from qiskit_ibm_runtime import EstimatorV2

    options = estimator_options(args)
    estimator = EstimatorV2(mode=backend, options=options)
    job = estimator.run([(isa, isa_observables)])
    receipt = {
        "submitted": True,
        "submitted_at_unix": time.time(),
        "job_id": str(job.job_id()),
        "method": args.method,
        "backend": backend_name(backend),
        "account_name": args.account_name,
        "shots": int(args.shots),
        "max_execution_time": int(args.max_execution_time),
        "last_status": status_name(job),
    }
    write_json(receipt_path, receipt)
    print(f"Submitted {args.method.upper()} job: {job.job_id()}")


if __name__ == "__main__":
    main()
