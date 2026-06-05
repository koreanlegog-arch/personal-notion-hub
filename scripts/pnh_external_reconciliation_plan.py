#!/usr/bin/env python3
"""Plan external ledger/thread reconciliation without performing writes.

This script reads local dispatch-state metadata and optional GitHub status
refresh output. It emits a redacted plan for the next operator-approved
external writes, such as replacing stale GitHub dispatch labels.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE = ROOT / "companion" / "private" / "pnh_dispatch_state.json"
DEFAULT_REFRESH = ROOT / "ops" / "runs" / "PNH-DISPATCH-STATUS-REFRESH-20260605" / "dispatch_status_refresh.json"
DEFAULT_OUT = ROOT / "ops" / "runs" / "PNH-EXTERNAL-RECONCILIATION-PLAN-20260605" / "external_reconciliation_plan.json"


class ReconciliationPlanError(ValueError):
    """Raised when reconciliation inputs are malformed."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a redacted PNH external reconciliation plan.")
    parser.add_argument("--state-file", default=str(DEFAULT_STATE), help="Local dispatch state JSON.")
    parser.add_argument("--refresh-json", default=str(DEFAULT_REFRESH), help="Optional GitHub status refresh JSON.")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output JSON path.")
    parser.add_argument("--limit", type=int, default=50, help="Maximum dispatch records to inspect.")
    args = parser.parse_args()

    try:
        state = load_json_object(Path(args.state_file), missing_ok=True, label="dispatch state")
        refresh = load_json_object(Path(args.refresh_json), missing_ok=True, label="refresh output")
        result = build_plan(state, refresh, limit=args.limit)
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, ReconciliationPlanError) as exc:
        print(f"pnh_external_reconciliation_plan=false error={exc}", file=sys.stderr)
        return 2
    print(json.dumps(redact_stdout(result, out_path), ensure_ascii=False, sort_keys=True))
    return 0


def load_json_object(path: Path, *, missing_ok: bool, label: str) -> dict[str, Any]:
    if not path.exists():
        if missing_ok:
            return {}
        raise ReconciliationPlanError(f"{label} file is missing")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ReconciliationPlanError(f"{label} JSON is invalid: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ReconciliationPlanError(f"{label} JSON must be an object")
    return payload


def build_plan(state: dict[str, Any], refresh: dict[str, Any], *, limit: int) -> dict[str, Any]:
    refresh_by_packet = {
        str(item.get("packetId")): item
        for item in refresh.get("records", [])
        if isinstance(item, dict) and item.get("packetId")
    }
    records = []
    for packet_id, record in sorted(state.items(), key=lambda item: str(item[1].get("updatedAt", "")), reverse=True):
        if len(records) >= min(max(int(limit), 1), 200):
            break
        if isinstance(record, dict):
            records.append(plan_record(str(packet_id), record, refresh_by_packet.get(str(packet_id), {})))
    external_writes = [action for item in records for action in item["externalWritePlan"]]
    local_followups = [action for item in records for action in item["localFollowUpPlan"]]
    return {
        "externalReconciliationPlan": True,
        "generatedAt": utc_now(),
        "mode": "dry-run",
        "recordsInspected": len(records),
        "externalWritesPerformed": False,
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "approvalRequiredBeforeExternalWrite": bool(external_writes),
        "approvalReason": "GitHub label/state/comment mutation or Discord/OpenClaw message/thread mutation would write to external systems.",
        "plannedExternalWrites": external_writes,
        "plannedLocalFollowUps": local_followups,
        "records": records,
    }


def plan_record(packet_id: str, record: dict[str, Any], refresh: dict[str, Any]) -> dict[str, Any]:
    github_labels = list_from_first_nonempty(refresh.get("githubIssueLabels"), record.get("githubIssueLabels"))
    worker_status = str(record.get("workerStatus") or "")
    github_issue_number = compact(record.get("githubIssueNumber") or refresh.get("githubIssueNumber"))
    discord_thread_id = compact(record.get("discordThreadId"))
    external_plan = []
    local_plan = []
    desired_dispatch_label = desired_dispatch_status_label(github_issue_number, discord_thread_id, worker_status)
    if desired_dispatch_label:
        dispatch_labels = ["dispatch:not-dispatched", "dispatch:dispatched-to-worker", "dispatch:worker-done"]
        desired_labels = [desired_dispatch_label]
        remove_labels = [label for label in dispatch_labels if label in github_labels and label != desired_dispatch_label]
        if remove_labels or desired_dispatch_label not in github_labels:
            external_plan.append(
                {
                    "system": "github",
                    "operation": "replace_dispatch_status_labels",
                    "githubIssueNumber": github_issue_number,
                    "addLabels": [label for label in desired_labels if label not in github_labels],
                    "removeLabels": remove_labels,
                    "requiresApproval": True,
                }
            )
    if github_issue_number and discord_thread_id:
        local_plan.append(
            {
                "operation": "keep_local_dispatch_state_as_source_of_mapping",
                "packetId": packet_id,
                "reason": "ledger and thread ids are already linked locally",
            }
        )
    if worker_status == "done" and not compact(record.get("workerEvidenceRef")):
        local_plan.append(
            {
                "operation": "record_worker_evidence_ref",
                "packetId": packet_id,
                "reason": "worker status is done but evidence reference is missing",
            }
        )
    if not github_issue_number:
        local_plan.append(
            {
                "operation": "create_or_link_github_ledger_before_delivery",
                "packetId": packet_id,
                "reason": "worker result exists without durable GitHub ledger linkage",
            }
        )
    if not discord_thread_id:
        local_plan.append(
            {
                "operation": "create_or_link_discord_thread_before_delivery",
                "packetId": packet_id,
                "reason": "worker result exists without Discord/OpenClaw thread linkage",
            }
        )
    return {
        "packetId": packet_id,
        "githubIssueSet": bool(github_issue_number),
        "githubIssueNumber": github_issue_number,
        "githubIssueState": compact(refresh.get("githubIssueState") or record.get("githubIssueState")),
        "githubLabelsKnown": bool(github_labels),
        "githubIssueLabels": github_labels,
        "discordThreadSet": bool(discord_thread_id),
        "discordThreadId": discord_thread_id,
        "workerStatus": worker_status,
        "externalWritePlan": external_plan,
        "localFollowUpPlan": local_plan,
    }


def desired_dispatch_status_label(github_issue_number: str, discord_thread_id: str, worker_status: str) -> str:
    if not github_issue_number:
        return ""
    if worker_status == "done":
        return "dispatch:worker-done"
    if discord_thread_id:
        return "dispatch:dispatched-to-worker"
    return ""


def list_from_first_nonempty(*values: Any) -> list[str]:
    for value in values:
        if isinstance(value, list) and value:
            return [compact(item) for item in value if compact(item)]
    return []


def redact_stdout(result: dict[str, Any], out_path: Path) -> dict[str, Any]:
    return {
        "externalReconciliationPlan": True,
        "mode": result["mode"],
        "out": safe_path_label(out_path),
        "recordsInspected": result["recordsInspected"],
        "plannedExternalWriteCount": len(result["plannedExternalWrites"]),
        "plannedLocalFollowUpCount": len(result["plannedLocalFollowUps"]),
        "approvalRequiredBeforeExternalWrite": result["approvalRequiredBeforeExternalWrite"],
        "externalWritesPerformed": False,
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
    }


def compact(value: Any) -> str:
    return " ".join(str(value or "").replace("\n", " ").split()).strip()


def safe_path_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return "[external-path]"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


if __name__ == "__main__":
    raise SystemExit(main())
