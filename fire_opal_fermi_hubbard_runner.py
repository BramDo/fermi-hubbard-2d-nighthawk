#!/usr/bin/env python3
"""Prepare or submit the 60q Fermi-Hubbard route through Q-CTRL Fire Opal.

Default mode is a dry run: build the same staged circuit groups as the IBM
Runtime route, export OpenQASM 2 files, and write a Fire Opal manifest. Passing
``--submit`` uses ``fireopal.execute`` with IBM Cloud credentials loaded from
environment variables or the local ``~/.qiskit/qiskit-ibm.json`` account file.

Credentials are never written to the repo. Result payloads are converted into
the existing ``ibm_staged_raw_results.json`` shape when ``--wait`` is used, so
the current summarizer can process Fire Opal counts without changing the old
IBM/DD/twirling artifacts.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping

from qiskit import qasm2, transpile
from qiskit import QuantumCircuit

from advantage_scale_fermi_hubbard_model import AdvantageScaleConfig, MitigationConfig
from ibm_staged_fermi_hubbard_runner import (
    build_stage_circuit_groups,
    stage_circuit_metadata,
    stage_zne_noise_factors,
    summarize_circuit,
    write_stage_plan,
)


QELIB_BASIS = ["u1", "u2", "u3", "cx", "measure"]
NATIVE_RZZ_ALIAS = "fo_rzz"


def clean_bitstring(bitstring: Any, n_qubits: int) -> str:
    if isinstance(bitstring, int):
        return format(bitstring, f"0{n_qubits}b")
    return str(bitstring).replace(" ", "").zfill(n_qubits)


def normalize_counts(counts: Mapping[Any, Any], n_qubits: int) -> dict[str, int]:
    normalized: dict[str, int] = {}
    for key, value in counts.items():
        bitstring = clean_bitstring(key, n_qubits)
        normalized[bitstring] = normalized.get(bitstring, 0) + int(round(float(value)))
    return dict(sorted(normalized.items()))


def build_fire_opal_config(args: argparse.Namespace) -> AdvantageScaleConfig:
    if args.qubits % 2:
        raise ValueError("Fermi-Hubbard site count needs an even qubit count")
    mitigation = MitigationConfig(
        layout_selection=False,
        dynamical_decoupling=False,
        pauli_twirling=False,
        zne_mitigation=args.zne,
        zne_noise_factors=[int(value) for value in args.zne_noise_factors.split(",") if value.strip()],
        zne_extrapolator=args.zne_extrapolator,
        zne_fold_scope=args.zne_fold_scope,
        readout_correction=not args.disable_readout_correction,
        readout_calibration_shots_per_state=args.readout_cal_shots,
        decay_recovery=not args.disable_decay_recovery,
        decay_confidence=args.decay_confidence,
        symmetry_postselection=False,
    )
    return AdvantageScaleConfig(
        sites=args.qubits // 2,
        steps=args.steps,
        dt=args.dt,
        hopping=args.hopping,
        interaction_u=args.U,
        chemical_potential=args.mu,
        shots=args.shots,
        twirls=1,
        vacancy_site=args.vacancy_site,
        measured=True,
        circuit_family=args.circuit_family,
        mitigation=mitigation,
    )


def export_qasm2(
    circuit: QuantumCircuit,
    *,
    basis: str,
    optimization_level: int,
    parse_check: bool,
) -> tuple[str, QuantumCircuit, dict[str, Any]]:
    if basis == "qelib":
        exported = transpile(circuit, basis_gates=QELIB_BASIS, optimization_level=optimization_level)
    elif basis == "native":
        exported = circuit
    else:
        raise ValueError("qasm basis must be 'qelib' or 'native'")

    qasm = qasm2.dumps(exported)
    native_aliases: dict[str, str] = {}
    if basis == "native":
        qasm, native_aliases = add_native_qasm2_gate_definitions(qasm)
    contains_reserved_rzz = contains_qasm_gate_or_call(qasm, "rzz")
    metadata: dict[str, Any] = {
        "basis": basis,
        "optimization_level": optimization_level,
        "contains_custom_xx_plus_yy": "xx_plus_yy" in qasm,
        "contains_rzz": contains_reserved_rzz,
        "contains_reserved_rzz": contains_reserved_rzz,
        "contains_native_rzz_alias": contains_qasm_gate_or_call(qasm, NATIVE_RZZ_ALIAS),
        "native_gate_aliases": native_aliases,
        "contains_swap": "swap " in qasm,
        "qasm_characters": len(qasm),
        "parse_check": parse_check,
        "parse_ok": None,
    }
    if parse_check:
        try:
            parsed = qasm2.loads(qasm)
            metadata["parse_ok"] = True
            metadata["parsed_summary"] = summarize_circuit(parsed)
        except Exception as exc:
            metadata["parse_ok"] = False
            metadata["parse_error"] = f"{type(exc).__name__}: {exc}"
    return qasm, exported, metadata


def contains_qasm_gate_or_call(qasm: str, name: str) -> bool:
    return re.search(rf"(?<![A-Za-z0-9_]){re.escape(name)}\s*(?:\(|[A-Za-z_])", qasm) is not None


def add_native_qasm2_gate_definitions(qasm: str) -> tuple[str, dict[str, str]]:
    """Define Qiskit-native gates that qasm2.dumps may emit before using custom gates."""
    prelude: list[str] = []
    aliases: dict[str, str] = {}
    if "sx " in qasm:
        prelude.append("gate sx q { u2(-pi/2,pi/2) q; }")
    if "sxdg " in qasm:
        prelude.append("gate sxdg q { u2(pi/2,-pi/2) q; }")
    if "rzz(" in qasm:
        qasm = re.sub(r"(?<![A-Za-z0-9_])rzz(?=\s*\()", NATIVE_RZZ_ALIAS, qasm)
        aliases["rzz"] = NATIVE_RZZ_ALIAS
        prelude.append(f"gate {NATIVE_RZZ_ALIAS}(theta) a,b {{ cx a,b; rz(theta) b; cx a,b; }}")
    if not prelude:
        return qasm, aliases
    include = 'include "qelib1.inc";'
    if include not in qasm:
        return "\n".join(prelude) + "\n" + qasm, aliases
    return qasm.replace(include, include + "\n" + "\n".join(prelude), 1), aliases


def write_qasm_manifest(
    *,
    stage_dir: Path,
    groups: Mapping[str, list[QuantumCircuit]],
    circuit_metadata: Mapping[str, list[dict[str, object]]],
    basis: str,
    optimization_level: int,
    parse_check: bool,
) -> tuple[Path, list[dict[str, Any]]]:
    qasm_dir = stage_dir / "qasm"
    qasm_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    for group_name, circuits in groups.items():
        for index, circuit in enumerate(circuits):
            role = circuit_metadata.get(group_name, [{}])[index].get("role", group_name)
            filename = f"{group_name}_{index:02d}_{role}.qasm"
            qasm, exported, qasm_meta = export_qasm2(
                circuit,
                basis=basis,
                optimization_level=optimization_level,
                parse_check=parse_check,
            )
            path = qasm_dir / filename
            path.write_text(qasm, encoding="utf-8")
            records.append(
                {
                    "group": group_name,
                    "index": index,
                    "role": role,
                    "path": path.relative_to(stage_dir).as_posix(),
                    "shots": None,
                    "circuit_metadata": circuit_metadata.get(group_name, [{}])[index],
                    "logical_summary": summarize_circuit(circuit),
                    "exported_summary": summarize_circuit(exported),
                    "qasm": qasm_meta,
                }
            )
    manifest_path = stage_dir / "fire_opal_qasm_manifest.json"
    manifest_path.write_text(json.dumps({"records": records}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest_path, records


def load_qiskit_ibm_cloud_account(account_name: str | None) -> tuple[str, str, str]:
    path = Path.home() / ".qiskit" / "qiskit-ibm.json"
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}; set IBM_CLOUD_API_KEY and IBM_QUANTUM_CRN instead.")
    accounts = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(accounts, dict):
        raise ValueError(f"{path} does not contain a JSON account mapping")
    selected_name = account_name
    if selected_name is None:
        selected_name = "default-ibm-cloud" if "default-ibm-cloud" in accounts else next(iter(accounts))
    account = accounts.get(selected_name)
    if not isinstance(account, dict):
        raise KeyError(f"Qiskit IBM account not found: {selected_name}")
    token = account.get("token")
    instance = account.get("instance")
    if not token or not instance:
        raise ValueError(f"Qiskit IBM account {selected_name!r} does not contain token and instance")
    return str(token), str(instance), str(selected_name)


def ibm_credentials(args: argparse.Namespace) -> tuple[str, str, dict[str, Any]]:
    token = os.environ.get("IBM_CLOUD_API_KEY")
    instance = os.environ.get("IBM_QUANTUM_CRN")
    source: dict[str, Any] = {"source": "environment", "account": None}
    if not token or not instance:
        token, instance, account_name = load_qiskit_ibm_cloud_account(args.qiskit_account)
        source = {"source": "~/.qiskit/qiskit-ibm.json", "account": account_name}
    return token, instance, source


def extract_qctrl_api_key_from_notebook(path: Path) -> str:
    notebook = json.loads(path.read_text(encoding="utf-8"))
    text = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))
    patterns = [
        r"authenticate_qctrl_account\s*\(\s*api_key\s*=\s*(['\"])(.+?)\1",
        r"qctrl_api_key\s*=\s*(['\"])(.+?)\1",
        r"api_key\s*=\s*(['\"])(.+?)\1",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE | re.DOTALL):
            candidate = str(match.group(2)).strip()
            if candidate and "YOUR" not in candidate.upper():
                return candidate
    raise ValueError(f"No Q-CTRL API key candidate found in {path}")


def qctrl_api_key(args: argparse.Namespace) -> tuple[str | None, str | None]:
    key = os.environ.get("QCTRL_API_KEY")
    if key:
        return key, "QCTRL_API_KEY"
    if args.qctrl_notebook:
        path = Path(args.qctrl_notebook).expanduser()
        if not path.exists():
            raise FileNotFoundError(f"Q-CTRL notebook not found: {path}")
        return extract_qctrl_api_key_from_notebook(path), str(path)
    return None, None


def normalize_fire_opal_result_item(item: Mapping[str, Any], shots: int, n_qubits: int) -> dict[str, int]:
    counts: dict[str, int] = {}
    total_value = float(sum(float(value) for value in item.values()))
    values_are_probabilities = total_value <= 1.5
    for bitstring, value in item.items():
        clean = clean_bitstring(bitstring, n_qubits)
        count = int(round(float(value) * shots)) if values_are_probabilities else int(round(float(value)))
        counts[clean] = counts.get(clean, 0) + count
    return normalize_counts(counts, n_qubits)


def fire_opal_payload_to_raw_results(
    *,
    payload_by_group: Mapping[str, Mapping[str, Any]],
    records_by_group: Mapping[str, list[dict[str, Any]]],
    shots_by_group: Mapping[str, int],
    n_qubits: int,
    backend_name: str,
) -> dict[str, Any]:
    raw: dict[str, Any] = {}
    for group_name, payload in payload_by_group.items():
        results = payload.get("results", [])
        if not isinstance(results, list):
            raise ValueError(f"Fire Opal payload for {group_name} has no results list")
        pubs = []
        for index, item in enumerate(results):
            if not isinstance(item, Mapping):
                raise ValueError(f"Fire Opal result item {group_name}[{index}] is not a mapping")
            counts = normalize_fire_opal_result_item(item, shots_by_group[group_name], n_qubits)
            pubs.append(
                {
                    "index": index,
                    "shots": int(sum(counts.values())),
                    "unique_bitstrings": len(counts),
                    "counts": counts,
                }
            )
        raw[group_name] = {
            "backend": backend_name,
            "job_id": str(payload.get("job_id", "")),
            "status": str(payload.get("status", "result_available")),
            "pubs": pubs,
            "fire_opal_execution_metadata": payload.get("execution_metadata"),
            "fire_opal_qasm_records": records_by_group.get(group_name, []),
        }
    return raw


def maybe_submit_fire_opal(
    *,
    args: argparse.Namespace,
    cfg: AdvantageScaleConfig,
    stage_dir: Path,
    records: list[dict[str, Any]],
) -> None:
    if not args.submit:
        return
    print("Importing Fire Opal...", flush=True)
    try:
        import fireopal as fo
    except Exception as exc:
        raise RuntimeError("fire-opal is not installed; install optional requirements-fire-opal.txt") from exc

    api_key, qctrl_source = qctrl_api_key(args)
    if api_key:
        print(f"Authenticating Q-CTRL from {qctrl_source}...", flush=True)
        fo.authenticate_qctrl_account(api_key=api_key)

    token, instance, credential_source = ibm_credentials(args)
    print(f"Preparing IBM credentials from {credential_source['source']} account {credential_source['account']}...", flush=True)
    credentials = fo.credentials.make_credentials_for_ibm_cloud(token=token, instance=instance)
    print("IBM credentials prepared.", flush=True)

    records_by_group: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        records_by_group.setdefault(str(record["group"]), []).append(record)

    shots_by_group = {
        "main": cfg.shots,
        "readout": cfg.mitigation.readout_calibration_shots_per_state,
        "echo": cfg.shots,
    }
    submitted_path = stage_dir / "fire_opal_submitted_jobs.json"
    submitted: dict[str, Any] = {
        "backend": args.backend,
        "credential_source": credential_source,
        "qctrl_auth_source": qctrl_source,
        "submitted_at_unix": time.time(),
        "waited_for_results": bool(args.wait),
        "groups": {},
    }
    if submitted_path.exists():
        try:
            existing = json.loads(submitted_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}
        if isinstance(existing, dict):
            submitted["groups"] = dict(existing.get("groups", {}))
            submitted["resumed_from_existing_submission"] = True

    def write_submitted_jobs() -> None:
        submitted_path.write_text(
            json.dumps(submitted, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    payload_by_group: dict[str, Mapping[str, Any]] = {}
    jobs_to_wait: dict[str, tuple[Any, dict[str, Any]]] = {}
    for group_name, group_records in records_by_group.items():
        if args.only_group and group_name not in set(args.only_group.split(",")):
            continue
        if group_name in submitted["groups"] and submitted["groups"][group_name].get("submitted"):
            print(f"Skipping Fire Opal group {group_name}; existing submission found.", flush=True)
            continue
        qasm_strings = [(stage_dir / str(record["path"])).read_text(encoding="utf-8") for record in group_records]
        if not qasm_strings:
            continue
        print(
            f"Submitting Fire Opal group {group_name}: {len(qasm_strings)} circuit(s), "
            f"{int(shots_by_group[group_name])} shots, backend {args.backend}...",
            flush=True,
        )
        job = fo.execute(
            circuits=qasm_strings,
            shot_count=int(shots_by_group[group_name]),
            credentials=credentials,
            backend_name=args.backend,
        )
        action_id = getattr(job, "action_id", None)
        job_id = getattr(job, "job_id", None) or getattr(job, "id", None) or getattr(job, "uid", None) or action_id
        print(f"Submitted Fire Opal group {group_name}; action_id={action_id}", flush=True)
        group_entry = {
            "submitted": True,
            "action_id": None if action_id is None else str(action_id),
            "job_id": None if job_id is None else str(job_id),
            "job_repr": repr(job),
            "backend": args.backend,
            "shots": int(shots_by_group[group_name]),
            "circuit_count": len(qasm_strings),
            "circuit_metadata": [record.get("circuit_metadata", {}) for record in group_records],
            "qasm_records": group_records,
        }
        submitted["groups"][group_name] = group_entry
        jobs_to_wait[group_name] = (job, group_entry)
        write_submitted_jobs()

    if args.wait:
        for group_name, (job, group_entry) in jobs_to_wait.items():
            print(f"Waiting for Fire Opal group {group_name} result...", flush=True)
            result = job.result()
            print(f"Received Fire Opal group {group_name} result.", flush=True)
            payload = dict(result)
            payload["job_id"] = group_entry["job_id"]
            payload_by_group[group_name] = payload
            group_entry["result_available"] = True
            write_submitted_jobs()

    if payload_by_group:
        raw = fire_opal_payload_to_raw_results(
            payload_by_group=payload_by_group,
            records_by_group=records_by_group,
            shots_by_group=shots_by_group,
            n_qubits=cfg.qubits,
            backend_name=args.backend,
        )
        (stage_dir / "ibm_staged_raw_results.json").write_text(
            json.dumps(raw, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", type=Path, default=Path("results_fire_opal"))
    parser.add_argument("--run-name", default="fire_opal_60q_steps8")
    parser.add_argument("--backend", default="ibm_fez")
    parser.add_argument("--qiskit-account", default="default-ibm-cloud")
    parser.add_argument("--qubits", type=int, default=60)
    parser.add_argument("--steps", type=int, default=8)
    parser.add_argument("--dt", type=float, default=0.2)
    parser.add_argument("--hopping", type=float, default=1.0)
    parser.add_argument("--U", type=float, default=-2.0)
    parser.add_argument("--mu", type=float, default=0.0)
    parser.add_argument("--vacancy-site", type=int, default=None)
    parser.add_argument("--shots", type=int, default=4096)
    parser.add_argument("--readout-cal-shots", type=int, default=4096)
    parser.add_argument("--circuit-family", default="native-fswap-cz")
    parser.add_argument("--echo-policy", default="final", choices=["none", "final", "even-all", "all"])
    parser.add_argument("--disable-readout-correction", action="store_true")
    parser.add_argument("--disable-decay-recovery", action="store_true")
    parser.add_argument("--decay-confidence", type=float, default=0.5)
    parser.add_argument("--zne", action="store_true")
    parser.add_argument("--zne-noise-factors", default="1,3")
    parser.add_argument("--zne-extrapolator", default="linear")
    parser.add_argument("--zne-fold-scope", default="global")
    parser.add_argument("--qasm-basis", default="qelib", choices=["qelib", "native"])
    parser.add_argument("--qasm-optimization-level", type=int, default=1)
    parser.add_argument("--no-qasm-parse-check", action="store_true")
    parser.add_argument("--submit", action="store_true")
    parser.add_argument("--wait", action="store_true", help="Wait for submitted Fire Opal jobs and write ibm_staged_raw_results.json")
    parser.add_argument("--only-group", default=None, help="Comma-separated subset of main,readout,echo for submission smoke tests.")
    parser.add_argument("--qctrl-notebook", type=Path, default=None, help="Optional notebook to read a Q-CTRL API key from in memory.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cfg = build_fire_opal_config(args)
    stage_dir = args.outdir / args.run_name
    stage_dir.mkdir(parents=True, exist_ok=True)
    groups = build_stage_circuit_groups(cfg, args.echo_policy)
    metadata = stage_circuit_metadata(cfg, args.echo_policy)
    write_stage_plan(
        cfg=cfg,
        stage_dir=stage_dir,
        echo_policy=args.echo_policy,
        include_circuit_summaries=True,
        layout_selection={
            "enabled": False,
            "status": "delegated_to_fire_opal",
            "backend": args.backend,
        },
        compile_plan={
            "enabled": False,
            "status": "delegated_to_fire_opal",
            "backend": args.backend,
            "qasm_basis": args.qasm_basis,
        },
    )
    manifest_path, records = write_qasm_manifest(
        stage_dir=stage_dir,
        groups=groups,
        circuit_metadata=metadata,
        basis=args.qasm_basis,
        optimization_level=args.qasm_optimization_level,
        parse_check=not args.no_qasm_parse_check,
    )
    shots_by_group = {
        "main": cfg.shots,
        "readout": cfg.mitigation.readout_calibration_shots_per_state,
        "echo": cfg.shots,
    }
    for record in records:
        record["shots"] = shots_by_group[str(record["group"])]
    manifest_path.write_text(json.dumps({"records": records}, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    fire_opal_plan = {
        "schema_version": 1,
        "route": "fire_opal_qasm",
        "claim_boundary": "Fire Opal route is an opt-in hardware execution path; old IBM/DD/twirling artifacts are unchanged.",
        "config": asdict(cfg),
        "backend": args.backend,
        "qiskit_account": args.qiskit_account,
        "qasm_manifest": manifest_path.relative_to(stage_dir).as_posix(),
        "qasm_basis": args.qasm_basis,
        "qasm_optimization_level": args.qasm_optimization_level,
        "zne_noise_factors": stage_zne_noise_factors(cfg),
        "groups": {
            group_name: {
                "circuit_count": len(circuits),
                "shots": shots_by_group[group_name],
            }
            for group_name, circuits in groups.items()
        },
        "submit_requested": bool(args.submit),
        "wait_requested": bool(args.wait),
        "credential_policy": "IBM credentials are read from env or ~/.qiskit/qiskit-ibm.json and are not written to artifacts.",
        "qctrl_auth_policy": "Q-CTRL key is read from env or --qctrl-notebook in memory and is not written to artifacts.",
    }
    (stage_dir / "fire_opal_plan.json").write_text(
        json.dumps(fire_opal_plan, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    maybe_submit_fire_opal(args=args, cfg=cfg, stage_dir=stage_dir, records=records)
    print(f"Wrote {stage_dir / 'stage_plan.json'}")
    print(f"Wrote {manifest_path}")
    print(f"Wrote {stage_dir / 'fire_opal_plan.json'}")
    if not args.submit:
        print("Dry run only. Re-run with --submit to call fireopal.execute.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
