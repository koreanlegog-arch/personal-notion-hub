#!/usr/bin/env python3
"""Plan retry/backoff actions for bounded PNH unattended dispatch."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE = ROOT / "companion" / "private" / "pnh_dispatch_state.json"
DEFAULT_HISTORY = ROOT / "companion" / "private" / "pnh_unattended_retry_history.json"
DEFAULT_OUT = ROOT / "ops" / "runs" / "PNH-UNATTENDED-RETRY-BACKOFF-20260606" / "retry_backoff_plan.json"
RETRYABLE_STATUSES = {"worker_failed", "worker_blocked"}


class RetryBackoffError(ValueError):
    """Raised when retry planning cannot proceed."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan retry/backoff for PNH unattended dispatch records.")
    parser.add_argument("--state-file", default=str(DEFAULT_STATE), help="Dispatch state JSON.")
    parser.add_argument("--history-json", default=str(DEFAULT_HISTORY), help="Retry history JSON.")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output JSON.")
    parser.add_argument("--base-delay-minutes", type=int, default=15, help="Base retry delay.")
    parser.add_argument("--max-delay-minutes", type=int, default=240, help="Maximum retry delay.")
    parser.add_argument("--max-attempts", type=int, default=3, help="Maximum retry attempts.")
    parser.add_argument("--apply", action="store_true", help="Persist retry planning state.")
    args = parser.parse_args()

    try:
        state = load_object(Path(args.state_file))
        history_path = Path(args.history_json)
        history = load_object(history_path)
        plan = build_plan(args, state, history)
        payload = {
            "pnhUnattendedRetryBackoff": True,
            "mode": "apply" if args.apply else "dry-run",
            "recordsInspected": len(state),
            "retryCandidates": plan,
            "writesPerformed": False,
            "externalWritesPerformed": False,
            "privateValuesPrinted": False,
            "tokenValuePrinted": False,
        }
        if args.apply:
            history["retryPlan"] = plan
            history["updatedAt"] = utc_now()
            save_object(history_path, history)
            payload["writesPerformed"] = True
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, RetryBackoffError) as exc:
        print(f"pnh_unattended_retry_backoff=false error={exc}", file=sys.stderr)
        return 2
    print(json.dumps({**payload, "out": safe_path_label(Path(args.out))}, ensure_ascii=False, sort_keys=True))
    return 0


def build_plan(args: argparse.Namespace, state: dict[str, Any], history: dict[str, Any]) -> list[dict[str, Any]]:
    prior = history.get("attempts", {})
    if not isinstance(prior, dict):
        prior = {}
    result = []
    for packet_id, record in sorted(state.items()):
        if not isinstance(record, dict):
            continue
        status = task_status(record)
        if status not in RETRYABLE_STATUSES:
            continue
        attempts = int(prior.get(packet_id, 0) or 0)
        if attempts >= args.max_attempts:
            action = "manual_review_required"
            next_retry = ""
        else:
            delay = min(args.max_delay_minutes, args.base_delay_minutes * (2**attempts))
            action = "retry_after_backoff"
            next_retry = (datetime.now(timezone.utc) + timedelta(minutes=delay)).isoformat(timespec="seconds")
        result.append(
            {
                "packetId": str(packet_id),
                "taskStatus": status,
                "attempts": attempts,
                "maxAttempts": args.max_attempts,
                "nextAction": action,
                "nextRetryAt": next_retry,
            }
        )
    return result


def task_status(record: dict[str, Any]) -> str:
    worker_status = str(record.get("workerStatus") or "")
    semantic = record.get("semanticProgress") if isinstance(record.get("semanticProgress"), dict) else {}
    semantic_status = str(semantic.get("status") or "") if isinstance(semantic, dict) else ""
    if worker_status == "failed" or semantic_status == "failed":
        return "worker_failed"
    if worker_status == "blocked" or semantic_status == "blocked":
        return "worker_blocked"
    return "not_retryable"


def load_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RetryBackoffError(f"invalid JSON: {path}: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise RetryBackoffError(f"JSON must be an object: {path}")
    return payload


def save_object(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def safe_path_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return "[external-path]"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


if __name__ == "__main__":
    raise SystemExit(main())
