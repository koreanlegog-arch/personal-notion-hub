#!/usr/bin/env python3
"""Summarize bounded PNH unattended automation status.

This script performs no external writes. It combines queue, readiness, and
retry/backoff outputs into one metadata-only decision so the scheduler and
operator can tell whether the system is idle, ready to run a bounded pilot, or
held by a blocker.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE = ROOT / "ops" / "runs" / "PNH-UNATTENDED-DISPATCH-READINESS-20260605" / "queue_plan.json"
DEFAULT_READINESS = ROOT / "ops" / "runs" / "PNH-UNATTENDED-DISPATCH-READINESS-20260605" / "readiness.json"
DEFAULT_RETRY = ROOT / "ops" / "runs" / "PNH-UNATTENDED-RETRY-BACKOFF-20260606" / "retry_backoff_plan.json"
DEFAULT_OUT = ROOT / "ops" / "runs" / "PNH-UNATTENDED-AUTOMATION-STATUS-20260606" / "unattended_status.json"


class UnattendedStatusError(ValueError):
    """Raised when unattended status cannot be summarized."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize PNH unattended automation status.")
    parser.add_argument("--queue-plan", default=str(DEFAULT_QUEUE), help="Queue plan JSON.")
    parser.add_argument("--readiness-json", default=str(DEFAULT_READINESS), help="Readiness JSON.")
    parser.add_argument("--retry-json", default=str(DEFAULT_RETRY), help="Retry/backoff JSON.")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output JSON.")
    args = parser.parse_args()

    try:
        queue = load_json(Path(args.queue_plan), "queue plan")
        readiness = load_json(Path(args.readiness_json), "readiness")
        retry = load_json(Path(args.retry_json), "retry/backoff")
        payload = build_status(queue, readiness, retry)
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, UnattendedStatusError) as exc:
        print(f"pnh_unattended_automation_status=false error={exc}", file=sys.stderr)
        return 2
    print(json.dumps(redact_stdout(payload, Path(args.out)), ensure_ascii=False, sort_keys=True))
    return 0


def build_status(queue: dict[str, Any], readiness: dict[str, Any], retry: dict[str, Any]) -> dict[str, Any]:
    queued_count = int(queue.get("queuedCount") or 0)
    retry_candidates = retry.get("retryCandidates") if isinstance(retry.get("retryCandidates"), list) else []
    failed_checks = readiness.get("failedChecks") if isinstance(readiness.get("failedChecks"), list) else []
    readiness_verdict = str(readiness.get("verdict") or "")
    if readiness_verdict != "ready_for_delegated_bounded_pilot" or failed_checks:
        decision = "hold_for_readiness"
        autonomous_next = "repair_readiness_before_dispatch"
    elif queued_count > 0:
        decision = "ready_to_run_bounded_pilot"
        autonomous_next = "run_one_bounded_unattended_pilot_with_rollback"
    elif retry_candidates:
        decision = "retry_candidates_waiting"
        autonomous_next = "respect_backoff_or_route_manual_review"
    else:
        decision = "idle_ready"
        autonomous_next = "wait_for_new_command_capture"
    return {
        "pnhUnattendedAutomationStatus": True,
        "generatedAt": utc_now(),
        "decision": decision,
        "autonomousNextAction": autonomous_next,
        "queue": {
            "queuedCount": queued_count,
            "skippedCount": int(queue.get("skippedCount") or 0),
            "cooldownActive": bool(queue.get("cooldownActive")),
            "remainingExternalWriteCapacity1h": int(queue.get("remainingExternalWriteCapacity1h") or 0),
            "queueActivationGateRequired": bool(queue.get("queueActivationGateRequired")),
        },
        "readiness": {
            "verdict": readiness_verdict,
            "failedCheckCount": len(failed_checks),
            "activationGateRequired": bool(readiness.get("activationGate", {}).get("required")),
        },
        "retry": {
            "candidateCount": len(retry_candidates),
            "manualReviewRequiredCount": sum(1 for item in retry_candidates if item.get("nextAction") == "manual_review_required"),
        },
        "safety": {
            "boundedOnly": True,
            "rollbackRequired": True,
            "externalWritesPerformed": False,
            "messageContentStored": False,
            "privateValuesPrinted": False,
            "tokenValuePrinted": False,
        },
    }


def load_json(path: Path, label: str) -> dict[str, Any]:
    if not path.exists():
        raise UnattendedStatusError(f"{label} is missing: {safe_path_label(path)}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise UnattendedStatusError(f"{label} JSON is invalid: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise UnattendedStatusError(f"{label} JSON must be an object")
    return payload


def redact_stdout(payload: dict[str, Any], out_path: Path) -> dict[str, Any]:
    return {
        "pnhUnattendedAutomationStatus": True,
        "decision": payload["decision"],
        "autonomousNextAction": payload["autonomousNextAction"],
        "out": safe_path_label(out_path),
        "externalWritesPerformed": False,
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
    }


def safe_path_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return "[external-path]"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


if __name__ == "__main__":
    raise SystemExit(main())
