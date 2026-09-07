#!/usr/bin/env python3
"""Q-CTRL Fire Opal route for the 72-qubit 2D cuprate Hubbard target."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import warnings
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any, Mapping

from qiskit import QuantumCircuit, transpile

from advantage_scale_fermi_hubbard_model import AdvantageScaleConfig, MitigationConfig
from cuprate_2d_hubbard_pipeline import Cuprate2DConfig, validate_config
from cuprate_2d_ibm_hardware_runner import (
    build_readout_calibration_circuits,
    bond_observable_rows,
    plot_charge_spin,
    sector_survival,
    site_observable_rows,
    summarize_site_rows,
    write_csv,
    write_json,
)
from cuprate_2d_qiskit_circuit import SUPPORTED_CIRCUIT_FAMILIES, build_circuit, load_config
from fire_opal_fermi_hubbard_runner import (
    export_qasm2,
    fire_opal_payload_to_raw_results,
    ibm_credentials,
    qctrl_api_key,
)
from retrieve_fire_opal_results import action_status_map
from ibm_staged_fermi_hubbard_runner import build_runtime_service, summarize_circuit


def fire_opal_dummy_cfg(cfg: Cuprate2DConfig, *, shots: int, readout_shots: int) -> AdvantageScaleConfig:
    return AdvantageScaleConfig(
        sites=cfg.sites,
        steps=cfg.steps,
        dt=cfg.dt,
        hopping=cfg.hopping_t,
        interaction_u=cfg.interaction_u,
        chemical_potential=cfg.chemical_potential,
        shots=shots,
        twirls=1,
        vacancy_site=None,
        measured=True,
        circuit_family="cuprate-2d-explicit-row-major-jw",
        mitigation=MitigationConfig(
            layout_selection=False,
            dynamical_decoupling=False,
            pauli_twirling=False,
            zne_mitigation=False,
            readout_correction=True,
            readout_calibration_shots_per_state=readout_shots,
            decay_recovery=False,
        ),
    )


def build_groups(cfg: Cuprate2DConfig, *, circuit_family: str) -> dict[str, list[QuantumCircuit]]:
    main, _terms = build_circuit(cfg, measured=True, circuit_family=circuit_family)
    readout = build_readout_calibration_circuits(cfg.qubits)
    return {"main": [main], "readout": readout}


def load_layout_seed(path: Path | None) -> int | None:
    if path is None:
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    best = payload.get("best_candidate") if isinstance(payload, dict) else None
    if isinstance(best, dict) and best.get("seed_transpiler") is not None:
        return int(best["seed_transpiler"])
    return None


def maybe_backend_transpile_groups(
    groups: dict[str, list[QuantumCircuit]],
    args: argparse.Namespace,
) -> tuple[dict[str, list[QuantumCircuit]], dict[str, Any]]:
    if not args.backend_transpile:
        return groups, {"enabled": False}
    service = build_runtime_service()
    backend = service.backend(args.backend)
    seed = args.seed_transpiler
    if args.use_layout_seed:
        layout_seed = load_layout_seed(args.layout_scout)
        if layout_seed is not None:
            seed = layout_seed
    transpiled_groups: dict[str, list[QuantumCircuit]] = {}
    summaries: dict[str, list[dict[str, Any]]] = {}
    for group_name, circuits in groups.items():
        result = transpile(
            circuits,
            backend=backend,
            optimization_level=int(args.backend_optimization_level),
            seed_transpiler=seed,
        )
        transpiled = result if isinstance(result, list) else [result]
        transpiled_groups[group_name] = transpiled
        summaries[group_name] = [summarize_circuit(circuit) for circuit in transpiled]
    return transpiled_groups, {
        "enabled": True,
        "backend": args.backend,
        "seed_transpiler": seed,
        "optimization_level": int(args.backend_optimization_level),
        "layout_scout": None if args.layout_scout is None else str(args.layout_scout),
        "summaries": summaries,
        "note": "Circuits were backend-transpiled before Fire Opal QASM export.",
    }


def fire_opal_input_strategy(args: argparse.Namespace) -> dict[str, Any]:
    """Describe how abstract the Fire Opal input is before submission."""
    qasm_basis = str(args.qasm_basis)
    backend_transpile = bool(args.backend_transpile)
    abstract_for_fire_opal = qasm_basis == "native" and not backend_transpile
    warnings: list[str] = []
    if backend_transpile:
        warnings.append("backend_transpile_enabled_limits_fire_opal_layout_choice")
    if qasm_basis == "qelib":
        warnings.append("qelib_export_decomposes_to_cx_u_gates_before_fire_opal")
    if not warnings:
        warnings.append("none")
    return {
        "abstract_for_fire_opal": abstract_for_fire_opal,
        "qasm_basis": qasm_basis,
        "qasm_optimization_level": int(args.qasm_optimization_level),
        "backend_transpile": backend_transpile,
        "backend_optimization_level": int(args.backend_optimization_level),
        "recommendation": (
            "preferred_for_next_fire_opal_validation"
            if abstract_for_fire_opal
            else "use --abstract-input for the next Fire Opal validation dry-run"
        ),
        "warnings": warnings,
    }


def circuit_metadata(cfg: Cuprate2DConfig) -> dict[str, list[dict[str, Any]]]:
    return {
        "main": [
            {
                "role": "main",
                "model": "2d-cuprate-hubbard",
                "logical_forward_steps": cfg.steps,
                "observable_basis": "Z",
            }
        ],
        "readout": [
            {"role": "readout_all0", "calibration_state": "0" * cfg.qubits},
            {"role": "readout_all1", "calibration_state": "1" * cfg.qubits},
        ],
    }


def write_qasm_manifest(
    *,
    stage_dir: Path,
    groups: Mapping[str, list[QuantumCircuit]],
    metadata: Mapping[str, list[dict[str, Any]]],
    basis: str,
    optimization_level: int,
    parse_check: bool,
) -> tuple[Path, list[dict[str, Any]]]:
    qasm_dir = stage_dir / "qasm"
    qasm_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    for group_name, circuits in groups.items():
        for index, circuit in enumerate(circuits):
            role = metadata.get(group_name, [{}])[index].get("role", group_name)
            filename = f"{group_name}_{index:02d}_{role}.qasm"
            qasm, exported, qasm_meta = export_qasm2(
                circuit,
                basis=basis,
                optimization_level=optimization_level,
                parse_check=parse_check,
            )
            path = qasm_dir / filename
            path.write_text(qasm, encoding="utf-8")
            qasm_meta["sha256"] = hashlib.sha256(qasm.encode("utf-8")).hexdigest()
            records.append(
                {
                    "group": group_name,
                    "index": index,
                    "role": role,
                    "path": path.relative_to(stage_dir).as_posix(),
                    "circuit_metadata": metadata.get(group_name, [{}])[index],
                    "logical_summary": {
                        "qubits": circuit.num_qubits,
                        "clbits": circuit.num_clbits,
                        "depth": circuit.depth(),
                        "size": circuit.size(),
                        "operation_counts": dict(circuit.count_ops()),
                    },
                    "exported_summary": {
                        "qubits": exported.num_qubits,
                        "clbits": exported.num_clbits,
                        "depth": exported.depth(),
                        "size": exported.size(),
                        "operation_counts": dict(exported.count_ops()),
                    },
                    "qasm": qasm_meta,
                }
            )
    manifest_path = stage_dir / "fire_opal_qasm_manifest.json"
    write_json(manifest_path, {"records": records})
    return manifest_path, records


def safe_provider_call(label: str, function: Any, /, *args: Any, **kwargs: Any) -> Any:
    try:
        return function(*args, **kwargs)
    except Exception as exc:
        raise RuntimeError(f"{label} failed ({type(exc).__name__})") from None


def workflow_result(value: Any) -> dict[str, Any]:
    if hasattr(value, "result") and callable(value.result):
        value = safe_provider_call("Fire Opal workflow result", value.result)
    if not isinstance(value, Mapping):
        raise RuntimeError(f"Unexpected Fire Opal payload type: {type(value).__name__}")
    return dict(value)


def validate_fire_opal(stage_dir: Path, records: list[dict[str, Any]], args: argparse.Namespace) -> bool:
    import importlib.metadata
    import fireopal as fo

    api_key, qctrl_source = qctrl_api_key(args)
    if not api_key:
        raise RuntimeError("Q-CTRL authentication source is not ready")
    safe_provider_call("Q-CTRL authentication", fo.authenticate_qctrl_account, api_key=api_key)

    token, instance, credential_source = ibm_credentials(args)
    credentials = safe_provider_call(
        "Fire Opal IBM credential construction",
        fo.credentials.make_credentials_for_ibm_cloud,
        token=token,
        instance=instance,
    )
    instance_sha256 = hashlib.sha256(instance.encode("utf-8")).hexdigest()

    provider_calls = ["authenticate_qctrl_account", "show_supported_devices"]
    devices = workflow_result(
        safe_provider_call(
            "Fire Opal supported-device discovery",
            fo.show_supported_devices,
            credentials=credentials,
        )
    )
    supported = [str(value) for value in devices.get("supported_devices", [])]
    backend_supported = args.backend in supported
    report: dict[str, Any] = {
        "created_at_unix": time.time(),
        "backend": args.backend,
        "backend_supported": backend_supported,
        "supported_device_count": len(supported),
        "qctrl_auth_source": "notebook_in_memory" if qctrl_source else None,
        "credential_source": credential_source,
        "qiskit_account": args.qiskit_account,
        "ibm_instance_sha256": instance_sha256,
        "fire_opal_version": importlib.metadata.version("fire-opal"),
        "provider_calls": provider_calls,
        "circuit_count": len(records),
        "qasm_sha256": [record["qasm"]["sha256"] for record in records],
        "execution_attempted": False,
        "quantum_seconds_used": 0,
        "claim_boundary": "Validation establishes Fire Opal input compatibility only; it is not hardware execution or mitigation evidence.",
    }
    if not backend_supported:
        report["validation_passed"] = False
        report["errors"] = ["requested_backend_not_supported"]
        write_json(stage_dir / "fire_opal_validation_report.json", report)
        return False

    qasm_batch = [(stage_dir / str(record["path"])).read_text(encoding="utf-8") for record in records]
    provider_calls.append("validate")
    with warnings.catch_warnings(record=True) as surfaced:
        warnings.simplefilter("always", RuntimeWarning)
        validation_job = safe_provider_call(
            "Fire Opal validation",
            fo.validate,
            circuits=qasm_batch,
            credentials=credentials,
            backend_name=args.backend,
        )
        action_id = getattr(validation_job, "action_id", None)
        validation_payload = workflow_result(validation_job)

    raw_results = list(validation_payload.get("results", []) or [])
    metadata_keys = {"depth", "layout", "gate_count", "shot_count", "estimated_duration"}
    accepted_metadata = [
        dict(value)
        for value in raw_results
        if isinstance(value, Mapping) and metadata_keys.intersection(value)
    ]
    errors = [
        str(value)
        for value in raw_results
        if value and not (isinstance(value, Mapping) and metadata_keys.intersection(value))
    ]
    returned_warnings = [str(value) for value in validation_payload.get("warnings", []) or [] if value]
    surfaced_warnings = [str(item.message) for item in surfaced]
    report.update(
        {
            "validation_action_id": None if action_id is None else str(action_id),
            "validation_passed": not errors,
            "accepted_metadata": accepted_metadata,
            "errors": errors,
            "returned_warnings": returned_warnings,
            "surfaced_warnings": surfaced_warnings,
            "raw_validation_payload": validation_payload,
        }
    )
    write_json(stage_dir / "fire_opal_validation_report.json", report)
    return bool(report["validation_passed"])


def write_plan(
    *,
    stage_dir: Path,
    cfg: Cuprate2DConfig,
    records: list[dict[str, Any]],
    args: argparse.Namespace,
) -> dict[str, Any]:
    plan = {
        "route": "fire_opal_qasm",
        "model": "2d-cuprate-hubbard",
        "backend": args.backend,
        "circuit_family": args.circuit_family,
        "config": asdict(cfg),
        "shots": int(args.shots),
        "readout_shots": int(args.readout_shots),
        "qasm_manifest": "fire_opal_qasm_manifest.json",
        "qasm_basis": args.qasm_basis,
        "qasm_optimization_level": int(args.qasm_optimization_level),
        "backend_transpile": args.backend_transpile_metadata,
        "fire_opal_input_strategy": args.fire_opal_input_strategy,
        "groups": {
            "main": {"shots": int(args.shots), "circuit_count": 1},
            "readout": {"shots": int(args.readout_shots), "circuit_count": 2},
        },
        "records": records,
        "submit_requested": bool(args.submit),
        "claim_boundary": (
            "Fire Opal route for diagonal 72q 2D Hubbard observables. "
            "Pairing observables require separate circuits."
        ),
    }
    write_json(stage_dir / "fire_opal_plan.json", plan)
    return plan


def submit_fire_opal(stage_dir: Path, records: list[dict[str, Any]], args: argparse.Namespace) -> None:
    print("Importing Fire Opal...", flush=True)
    import fireopal as fo

    api_key, qctrl_source = qctrl_api_key(args)
    if api_key:
        print(f"Authenticating Q-CTRL from {qctrl_source}...", flush=True)
        fo.authenticate_qctrl_account(api_key=api_key)
    token, instance, credential_source = ibm_credentials(args)
    credentials = fo.credentials.make_credentials_for_ibm_cloud(token=token, instance=instance)

    records_by_group: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        records_by_group.setdefault(str(record["group"]), []).append(record)
    shots_by_group = {"main": int(args.shots), "readout": int(args.readout_shots)}
    only_groups = None if args.only_group is None else set(args.only_group.split(","))
    submitted_path = stage_dir / "fire_opal_submitted_jobs.json"
    submitted = {
        "backend": args.backend,
        "credential_source": credential_source,
        "qctrl_auth_source": qctrl_source,
        "submitted_at_unix": time.time(),
        "groups": {},
    }
    if submitted_path.exists():
        try:
            existing = json.loads(submitted_path.read_text(encoding="utf-8"))
            submitted["groups"] = dict(existing.get("groups", {}))
            submitted["resumed_from_existing_submission"] = True
        except json.JSONDecodeError:
            pass

    for group_name, group_records in records_by_group.items():
        if only_groups is not None and group_name not in only_groups:
            continue
        if group_name in submitted["groups"] and submitted["groups"][group_name].get("submitted"):
            print(f"Skipping Fire Opal group {group_name}; existing submission found.", flush=True)
            continue
        qasm_strings = [(stage_dir / str(record["path"])).read_text(encoding="utf-8") for record in group_records]
        print(
            f"Submitting Fire Opal group {group_name}: {len(qasm_strings)} circuit(s), "
            f"{shots_by_group[group_name]} shots, backend {args.backend}...",
            flush=True,
        )
        job = fo.execute(
            circuits=qasm_strings,
            shot_count=shots_by_group[group_name],
            credentials=credentials,
            backend_name=args.backend,
        )
        action_id = getattr(job, "action_id", None)
        job_id = getattr(job, "job_id", None) or getattr(job, "id", None) or getattr(job, "uid", None) or action_id
        submitted["groups"][group_name] = {
            "submitted": True,
            "action_id": None if action_id is None else str(action_id),
            "job_id": None if job_id is None else str(job_id),
            "job_repr": repr(job),
            "backend": args.backend,
            "shots": shots_by_group[group_name],
            "circuit_count": len(qasm_strings),
            "qasm_records": group_records,
        }
        write_json(submitted_path, submitted)
        print(f"Submitted Fire Opal group {group_name}; action_id={action_id}", flush=True)


def retrieve_fire_opal(stage_dir: Path, cfg: Cuprate2DConfig, args: argparse.Namespace) -> bool:
    submitted_path = stage_dir / "fire_opal_submitted_jobs.json"
    if not submitted_path.exists():
        raise FileNotFoundError(submitted_path)
    submitted = json.loads(submitted_path.read_text(encoding="utf-8"))
    groups = submitted.get("groups", {})
    only_groups = None if args.only_group is None else set(args.only_group.split(","))
    action_by_group = {
        group_name: str(group.get("action_id") or group.get("job_id"))
        for group_name, group in groups.items()
        if only_groups is None or group_name in only_groups
        if group.get("action_id") or group.get("job_id")
    }
    if not action_by_group:
        raise ValueError("No Fire Opal action ids found")

    import fireopal as fo

    api_key, qctrl_source = qctrl_api_key(args)
    if api_key:
        fo.authenticate_qctrl_account(api_key=api_key)
    statuses = action_status_map(fo, set(action_by_group.values()))
    status_payload = {
        "checked_at_unix": time.time(),
        "actions": {
            group_name: {"action_id": action_id, "metadata": statuses.get(action_id)}
            for group_name, action_id in action_by_group.items()
        },
    }
    write_json(stage_dir / "fire_opal_action_status.json", status_payload)
    for group_name, action_id in action_by_group.items():
        print(f"{group_name}: action_id={action_id} status={(statuses.get(action_id) or {}).get('status', 'UNKNOWN')}", flush=True)

    unfinished = [
        group_name
        for group_name, action_id in action_by_group.items()
        if (statuses.get(action_id) or {}).get("status") != "SUCCESS"
    ]
    if unfinished and not args.wait:
        print(f"Not all Fire Opal actions are ready: {', '.join(unfinished)}", flush=True)
        return False

    payload_by_group: dict[str, Mapping[str, Any]] = {}
    for group_name, action_id in action_by_group.items():
        print(f"Retrieving Fire Opal result for {group_name} action_id={action_id}...", flush=True)
        payload = dict(fo.get_result(action_id))
        payload["job_id"] = action_id
        payload_by_group[group_name] = payload
        groups[group_name]["result_available"] = True
    write_json(submitted_path, submitted)
    write_json(stage_dir / "fire_opal_result_payloads.json", payload_by_group)

    manifest = json.loads((stage_dir / "fire_opal_qasm_manifest.json").read_text(encoding="utf-8"))
    records_by_group: dict[str, list[dict[str, Any]]] = {}
    for record in manifest["records"]:
        records_by_group.setdefault(str(record["group"]), []).append(record)
    raw = fire_opal_payload_to_raw_results(
        payload_by_group=payload_by_group,
        records_by_group=records_by_group,
        shots_by_group={"main": int(args.shots), "readout": int(args.readout_shots)},
        n_qubits=cfg.qubits,
        backend_name=args.backend,
    )
    write_json(stage_dir / "fire_opal_raw_results.json", raw)
    summarize_observables(stage_dir, cfg, raw, args.backend)
    return True


def summarize_observables(stage_dir: Path, cfg: Cuprate2DConfig, raw: Mapping[str, Any], backend_name: str) -> None:
    main_pub = raw["main"]["pubs"][0]
    main_counts = main_pub["counts"]
    readout_pubs = raw.get("readout", {}).get("pubs", [])
    p01 = p10 = readout_meta = None
    if len(readout_pubs) >= 2:
        from advantage_scale_fermi_hubbard_model import estimate_local_readout_params

        p01, p10, readout_meta = estimate_local_readout_params(readout_pubs[0]["counts"], readout_pubs[1]["counts"], n_qubits=cfg.qubits)

    site_rows = site_observable_rows(cfg, main_counts, profile="raw", p01=None, p10=None, readout_corrected=False)
    bond_rows = bond_observable_rows(cfg, main_counts, profile="raw", p01=None, p10=None, readout_corrected=False)
    profiles = {"raw": summarize_site_rows(site_rows, "raw")}
    if p01 is not None and p10 is not None:
        corrected_sites = site_observable_rows(cfg, main_counts, profile="readout_corrected", p01=p01, p10=p10, readout_corrected=True)
        corrected_bonds = bond_observable_rows(cfg, main_counts, profile="readout_corrected", p01=p01, p10=p10, readout_corrected=True)
        site_rows.extend(corrected_sites)
        bond_rows.extend(corrected_bonds)
        profiles["readout_corrected"] = summarize_site_rows(site_rows, "readout_corrected")

    write_csv(stage_dir / "cuprate_2d_fire_opal_site_observables.csv", site_rows)
    write_csv(stage_dir / "cuprate_2d_fire_opal_bond_observables.csv", bond_rows)
    plot_path = plot_charge_spin(
        stage_dir / "cuprate_2d_fire_opal_readout_corrected_observables.png",
        cfg,
        site_rows,
        profile="readout_corrected" if "readout_corrected" in profiles else "raw",
    )
    summary = {
        "backend": backend_name,
        "config": asdict(cfg),
        "profiles": profiles,
        "particle_sector": sector_survival(main_counts, cfg),
        "readout_calibration": readout_meta,
        "artifacts": {
            "site_observables_csv": (stage_dir / "cuprate_2d_fire_opal_site_observables.csv").as_posix(),
            "bond_observables_csv": (stage_dir / "cuprate_2d_fire_opal_bond_observables.csv").as_posix(),
            "plot": None if plot_path is None else plot_path.as_posix(),
        },
    }
    write_json(stage_dir / "cuprate_2d_fire_opal_observable_summary.json", summary)
    write_summary_md(stage_dir / "cuprate_2d_fire_opal_summary.md", summary)


def write_summary_md(path: Path, summary: Mapping[str, Any]) -> None:
    lines = [
        "# Fire Opal 72q 2D Cuprate Hubbard Observables",
        "",
        f"- backend: `{summary['backend']}`",
        f"- lattice/qubits: {summary['config']['lx']}x{summary['config']['ly']} / {2 * summary['config']['lx'] * summary['config']['ly']}",
        f"- steps/dt: {summary['config']['steps']}/{summary['config']['dt']}",
        "",
        "| profile | total charge | total spin-z | mean |spin-z| | mean doublon | min charge | max charge |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for profile, metrics in summary["profiles"].items():
        lines.append(
            f"| {profile} | {metrics['total_charge']:.6f} | {metrics['total_spin_z']:.6f} | "
            f"{metrics['mean_abs_spin_z']:.6f} | {metrics['mean_double_occupancy']:.6f} | "
            f"{metrics['min_charge']:.6f} | {metrics['max_charge']:.6f} |"
        )
    sector = summary["particle_sector"]
    lines += [
        "",
        "## Particle Sector",
        "",
        f"- expected N_up/N_down: {sector['expected_n_up']}/{sector['expected_n_down']}",
        f"- exact sector fraction: {sector['exact_sector_fraction']:.6f}",
        "",
        "Claim boundary: diagonal Fire Opal hardware observables only, not d-wave superconductivity.",
        "",
    ]
    path.write_text("\n".join(lines))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    parser.add_argument("--backend", default="ibm_marrakesh")
    parser.add_argument("--qiskit-account", default="default-ibm-cloud")
    parser.add_argument("--qctrl-notebook", type=Path, default=None)
    parser.add_argument("--steps", type=int, default=1)
    parser.add_argument("--shots", type=int, default=512)
    parser.add_argument("--readout-shots", type=int, default=512)
    parser.add_argument("--circuit-family", choices=SUPPORTED_CIRCUIT_FAMILIES, default="explicit_jw")
    parser.add_argument("--qasm-basis", default="qelib", choices=["qelib", "native"])
    parser.add_argument("--qasm-optimization-level", type=int, default=1)
    parser.add_argument(
        "--abstract-input",
        action="store_true",
        help="Prefer native, non-backend-transpiled QASM so Fire Opal has more optimization freedom.",
    )
    parser.add_argument("--backend-transpile", action="store_true", help="Transpile circuits to the target IBM backend before QASM export.")
    parser.add_argument("--backend-optimization-level", type=int, default=1)
    parser.add_argument("--seed-transpiler", type=int, default=72)
    parser.add_argument("--layout-scout", type=Path, default=None, help="best_layout.json from cuprate_2d_layout_scout.py.")
    parser.add_argument("--use-layout-seed", action="store_true", help="Use best_candidate.seed_transpiler from --layout-scout when present.")
    parser.add_argument("--no-qasm-parse-check", action="store_true")
    parser.add_argument("--submit", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--retrieve", action="store_true")
    parser.add_argument("--wait", action="store_true")
    parser.add_argument("--only-group", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.submit and args.validate_only:
        raise ValueError("--submit and --validate-only are mutually exclusive")
    if args.abstract_input:
        args.qasm_basis = "native"
        args.qasm_optimization_level = 0
        args.backend_transpile = False
    cfg = replace(load_config(args.config), steps=int(args.steps))
    validate_config(cfg)
    args.outdir.mkdir(parents=True, exist_ok=True)

    if args.retrieve:
        done = retrieve_fire_opal(args.outdir, cfg, args)
        if done:
            print(args.outdir / "cuprate_2d_fire_opal_summary.md")
        return

    groups = build_groups(cfg, circuit_family=args.circuit_family)
    groups, args.backend_transpile_metadata = maybe_backend_transpile_groups(groups, args)
    args.fire_opal_input_strategy = fire_opal_input_strategy(args)
    metadata = circuit_metadata(cfg)
    manifest_path, records = write_qasm_manifest(
        stage_dir=args.outdir,
        groups=groups,
        metadata=metadata,
        basis=args.qasm_basis,
        optimization_level=args.qasm_optimization_level,
        parse_check=not args.no_qasm_parse_check,
    )
    write_plan(stage_dir=args.outdir, cfg=cfg, records=records, args=args)
    print(f"Wrote {manifest_path}", flush=True)
    if args.validate_only:
        passed = validate_fire_opal(args.outdir, records, args)
        print(args.outdir / "fire_opal_validation_report.json", flush=True)
        print(f"Fire Opal validation passed: {passed}", flush=True)
    elif args.submit:
        submit_fire_opal(args.outdir, records, args)
    else:
        print("Dry run only. Add --submit to call fireopal.execute.", flush=True)


if __name__ == "__main__":
    main()
