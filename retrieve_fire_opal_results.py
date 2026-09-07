#!/usr/bin/env python3
"""Retrieve Fire Opal action results and write repo-compatible raw results."""

from __future__ import annotations

import argparse
import dataclasses
import json
import time
from pathlib import Path
from typing import Any, Mapping

from fire_opal_fermi_hubbard_runner import (
    fire_opal_payload_to_raw_results,
    qctrl_api_key,
)


def metadata_to_dict(item: Any) -> dict[str, Any]:
    if dataclasses.is_dataclass(item):
        return dataclasses.asdict(item)
    if isinstance(item, Mapping):
        return dict(item)
    return dict(vars(item))


def action_status_map(fo: Any, action_ids: set[str]) -> dict[str, dict[str, Any]]:
    statuses: dict[str, dict[str, Any]] = {}
    offset = 0
    while action_ids - set(statuses):
        items = fo.get_action_metadata(limit=50, offset=offset)
        if not items:
            break
        for item in items:
            data = metadata_to_dict(item)
            action_id = str(data.get("action_id") or data.get("model_id") or data.get("id") or "")
            if action_id in action_ids:
                statuses[action_id] = data
        offset += len(items)
        if len(items) < 50:
            break
    return statuses


def load_records_by_group(stage_dir: Path) -> dict[str, list[dict[str, Any]]]:
    manifest = json.loads((stage_dir / "fire_opal_qasm_manifest.json").read_text(encoding="utf-8"))
    records_by_group: dict[str, list[dict[str, Any]]] = {}
    for record in manifest["records"]:
        records_by_group.setdefault(str(record["group"]), []).append(record)
    return records_by_group


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--qctrl-notebook", type=Path, default=None)
    parser.add_argument("--wait", action="store_true", help="Block with fireopal.get_result for unfinished actions.")
    parser.add_argument(
        "--only-group",
        default=None,
        help="Comma-separated subset of submitted groups to retrieve, for partial runs.",
    )
    args = parser.parse_args()

    stage_dir = args.run_dir
    submitted_path = stage_dir / "fire_opal_submitted_jobs.json"
    plan_path = stage_dir / "fire_opal_plan.json"
    submitted = json.loads(submitted_path.read_text(encoding="utf-8"))
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    groups = submitted.get("groups", {})
    only_groups = None if args.only_group is None else set(args.only_group.split(","))
    action_by_group = {
        group_name: str(group_entry.get("action_id") or group_entry.get("job_id"))
        for group_name, group_entry in groups.items()
        if only_groups is None or group_name in only_groups
        if group_entry.get("action_id") or group_entry.get("job_id")
    }
    if not action_by_group:
        raise ValueError(f"No Fire Opal action IDs found in {submitted_path}")

    print("Importing Fire Opal...", flush=True)
    import fireopal as fo

    api_key, qctrl_source = qctrl_api_key(args)
    if api_key:
        print(f"Authenticating Q-CTRL from {qctrl_source}...", flush=True)
        fo.authenticate_qctrl_account(api_key=api_key)

    statuses = action_status_map(fo, set(action_by_group.values()))
    status_payload = {
        "checked_at_unix": time.time(),
        "actions": {
            group_name: {
                "action_id": action_id,
                "metadata": statuses.get(action_id),
            }
            for group_name, action_id in action_by_group.items()
        },
    }
    (stage_dir / "fire_opal_action_status.json").write_text(
        json.dumps(status_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    for group_name, action_id in action_by_group.items():
        status = (statuses.get(action_id) or {}).get("status", "UNKNOWN")
        print(f"{group_name}: action_id={action_id} status={status}", flush=True)

    unfinished = [
        group_name
        for group_name, action_id in action_by_group.items()
        if (statuses.get(action_id) or {}).get("status") != "SUCCESS"
    ]
    if unfinished and not args.wait:
        print(f"Not all Fire Opal actions are ready: {', '.join(unfinished)}", flush=True)
        return 2

    payload_by_group: dict[str, Mapping[str, Any]] = {}
    for group_name, action_id in action_by_group.items():
        print(f"Retrieving Fire Opal result for {group_name} action_id={action_id}...", flush=True)
        payload = dict(fo.get_result(action_id))
        payload["job_id"] = action_id
        payload_by_group[group_name] = payload
        groups[group_name]["result_available"] = True
    submitted["waited_for_results"] = True
    submitted_path.write_text(json.dumps(submitted, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (stage_dir / "fire_opal_result_payloads.json").write_text(
        json.dumps(payload_by_group, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    shots_by_group = {
        group_name: int(group_plan["shots"])
        for group_name, group_plan in plan["groups"].items()
    }
    n_qubits = int(plan["config"]["sites"]) * 2
    raw = fire_opal_payload_to_raw_results(
        payload_by_group=payload_by_group,
        records_by_group=load_records_by_group(stage_dir),
        shots_by_group=shots_by_group,
        n_qubits=n_qubits,
        backend_name=str(plan["backend"]),
    )
    (stage_dir / "ibm_staged_raw_results.json").write_text(
        json.dumps(raw, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {stage_dir / 'ibm_staged_raw_results.json'}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
