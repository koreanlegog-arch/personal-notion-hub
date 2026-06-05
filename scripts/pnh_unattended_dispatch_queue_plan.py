#!/usr/bin/env python3
"""Build an unattended PNH dispatch queue plan without dispatching.

This script is intentionally dry-run only. It selects metadata-only candidates
from the private inbox, applies bounded rate-limit policy, and emits rollback
requirements for a future approved pilot runner. It does not create GitHub
Issues, Discord/OpenClaw threads, comments, labels, or worker runs.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.private_store import DEFAULT_DB_PATH, PrivateStoreError, list_captures  # noqa: E402


DEFAULT_STATE = ROOT / "companion" / "private" / "pnh_dispatch_state.json"
DEFAULT_HISTORY = ROOT / "companion" / "private" / "pnh_unattended_dispatch_history.json"
DEFAULT_COMMAND_ALIASES = ROOT / "companion" / "private" / "pnh_command_aliases.json"
DEFAULT_OUT = ROOT / "ops" / "runs" / "PNH-UNATTENDED-DISPATCH-READINESS-20260605" / "queue_plan.json"
COMMAND_KINDS = {"project_brief", "task_request", "daily_command", "urgent_approval"}


class QueuePlanError(ValueError):
    """Raised when unattended queue planning cannot proceed safely."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a safe dry-run queue plan for PNH unattended dispatch.")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Private inbox SQLite DB path.")
    parser.add_argument("--state-file", default=str(DEFAULT_STATE), help="Local dispatch state JSON.")
    parser.add_argument("--history-json", default=str(DEFAULT_HISTORY), help="Optional prior dispatch history JSON.")
    parser.add_argument("--command-aliases", default=str(DEFAULT_COMMAND_ALIASES), help="Metadata-only command alias JSON.")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output JSON path.")
    parser.add_argument("--limit", type=int, default=50, help="Recent captures to inspect.")
    parser.add_argument("--max-jobs-per-run", type=int, default=1, help="Maximum queued jobs per run.")
    parser.add_argument("--max-external-writes-per-hour", type=int, default=3, help="External write rate limit.")
    parser.add_argument("--cooldown-minutes", type=int, default=10, help="Minimum minutes between queue applies.")
    parser.add_argument("--allow-plaintext", action="store_true", help="Allow plaintext inbox rows in fixture tests only.")
    parser.add_argument("--allow-external-db", action="store_true", help="Allow a DB outside companion/private for fixture tests.")
    args = parser.parse_args()

    try:
        result = build_plan(args)
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, PrivateStoreError, QueuePlanError) as exc:
        print(f"pnh_unattended_dispatch_queue_plan=false error={exc}", file=sys.stderr)
        return 2
    print(json.dumps(redact_stdout(result, out_path), ensure_ascii=False, sort_keys=True))
    return 0


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    captures = list_captures(
        Path(args.db),
        limit=bounded(args.limit, 1, 200),
        include_body=False,
        create_if_missing=False,
        allow_external=args.allow_external_db,
    )
    state = load_json_object(Path(args.state_file), missing_ok=True, label="dispatch state")
    history = load_json_object(Path(args.history_json), missing_ok=True, label="dispatch history") if args.history_json else {}
    aliases = load_command_aliases(Path(args.command_aliases))
    policy = {
        "maxJobsPerRun": bounded(args.max_jobs_per_run, 1, 10),
        "maxExternalWritesPerHour": bounded(args.max_external_writes_per_hour, 1, 50),
        "cooldownMinutes": bounded(args.cooldown_minutes, 1, 1440),
    }
    now = utc_now()
    recent_writes = count_recent_external_writes(history, within_hours=1)
    cooldown_active = cooldown_is_active(history, cooldown_minutes=policy["cooldownMinutes"])
    skipped = []
    eligible = []
    for capture in captures:
        decision = classify_capture(capture, state, aliases, allow_plaintext=args.allow_plaintext)
        if decision["eligible"]:
            eligible.append(decision)
        else:
            skipped.append(decision)
    capacity = max(0, policy["maxExternalWritesPerHour"] - recent_writes)
    queue_limit = 0 if cooldown_active else min(policy["maxJobsPerRun"], capacity)
    queued = eligible[:queue_limit]
    for decision in eligible[queue_limit:]:
        decision["eligible"] = False
        decision["skipReason"] = "rate_or_run_limit_exceeded"
        skipped.append(decision)
    return {
        "pnhUnattendedDispatchQueuePlan": True,
        "generatedAt": now,
        "mode": "dry-run",
        "policy": policy,
        "capturesInspected": len(captures),
        "commandAliasesLoaded": len(aliases),
        "eligibleCount": len(eligible),
        "queuedCount": len(queued),
        "skippedCount": len(skipped),
        "recentExternalWriteCount1h": recent_writes,
        "remainingExternalWriteCapacity1h": capacity,
        "cooldownActive": cooldown_active,
        "queueActivationGateRequired": True,
        "queueActivationGateReason": "unattended dispatch can create GitHub Issues, Discord/OpenClaw threads, GitHub comments, and worker/model calls without an operator present.",
        "rollbackRequiredBeforeApply": True,
        "rollbackPlan": rollback_plan(),
        "lockPlan": lock_plan(args),
        "queued": [redacted_decision(item) for item in queued],
        "skipped": [redacted_decision(item) for item in skipped],
        "externalWritesPerformed": False,
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
    }


def classify_capture(
    capture: dict[str, Any],
    state: dict[str, Any],
    aliases: dict[str, dict[str, Any]],
    *,
    allow_plaintext: bool,
) -> dict[str, Any]:
    capture_id = compact(capture.get("id"))
    original_kind = compact(capture.get("kind"))
    alias = aliases.get(capture_id, {})
    kind = compact(alias.get("commandType") or original_kind)
    storage_mode = compact(capture.get("storageMode"))
    encrypted = bool(capture.get("encrypted"))
    aliased = bool(alias)
    eligible = True
    reason = ""
    if alias and kind not in COMMAND_KINDS:
        eligible = False
        reason = "invalid_command_alias"
    elif kind not in COMMAND_KINDS:
        eligible = False
        reason = "not_dispatch_command_kind"
    elif capture.get("status") != "inbox":
        eligible = False
        reason = "capture_not_in_inbox"
    elif capture_id in state:
        eligible = False
        reason = "already_in_dispatch_state"
    elif storage_mode == "plaintext-inbox" and not allow_plaintext:
        eligible = False
        reason = "plaintext_candidate_blocked"
    return {
        "captureId": capture_id,
        "commandType": kind,
        "originalKind": original_kind,
        "commandAliasApplied": aliased,
        "storageMode": storage_mode,
        "encrypted": encrypted,
        "sensitivity": compact(capture.get("sensitivity")),
        "storedAt": compact(capture.get("storedAt")),
        "eligible": eligible,
        "skipReason": reason,
    }


def count_recent_external_writes(history: dict[str, Any], *, within_hours: int) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=within_hours)
    count = 0
    for item in history.get("events", []):
        if not isinstance(item, dict) or not item.get("externalWrite"):
            continue
        try:
            timestamp = datetime.fromisoformat(str(item.get("at")).replace("Z", "+00:00"))
        except ValueError:
            continue
        if timestamp >= cutoff:
            count += 1
    return count


def cooldown_is_active(history: dict[str, Any], *, cooldown_minutes: int) -> bool:
    newest = newest_external_write_at(history)
    if newest is None:
        return False
    return newest + timedelta(minutes=cooldown_minutes) > datetime.now(timezone.utc)


def newest_external_write_at(history: dict[str, Any]) -> datetime | None:
    newest: datetime | None = None
    for item in history.get("events", []):
        if not isinstance(item, dict) or not item.get("externalWrite"):
            continue
        try:
            timestamp = datetime.fromisoformat(str(item.get("at")).replace("Z", "+00:00"))
        except ValueError:
            continue
        if newest is None or timestamp > newest:
            newest = timestamp
    return newest


def rollback_plan() -> dict[str, Any]:
    return {
        "beforeApply": [
            "snapshot companion/private/pnh_dispatch_state.json",
            "write run-local candidate and dispatch plan before external apply",
            "record GitHub issue labels before mutation",
            "record Discord thread id only after creation succeeds",
        ],
        "rollbackActions": [
            "restore local dispatch state snapshot if local state is inconsistent",
            "manually close or relabel GitHub issue created by failed run",
            "post no additional Discord messages until supervisor review",
            "rerun reconciliation plan before retry",
        ],
    }


def lock_plan(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "lockFile": "companion/private/pnh_unattended_dispatch.lock",
        "staleAfterMinutes": max(2 * bounded(args.cooldown_minutes, 1, 1440), 15),
        "singleWriter": True,
        "stateWritesMustBeSequential": True,
    }


def load_json_object(path: Path, *, missing_ok: bool, label: str) -> dict[str, Any]:
    if not path or str(path) == ".":
        return {}
    if not path.exists():
        if missing_ok:
            return {}
        raise QueuePlanError(f"{label} file is missing")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise QueuePlanError(f"{label} JSON is invalid: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise QueuePlanError(f"{label} JSON must be an object")
    return payload


def load_command_aliases(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    payload = load_json_object(path, missing_ok=False, label="command aliases")
    aliases = payload.get("aliases", payload)
    if not isinstance(aliases, dict):
        raise QueuePlanError("command aliases JSON must contain an object")
    result: dict[str, dict[str, Any]] = {}
    for capture_id, alias in aliases.items():
        capture_id_text = compact(capture_id)
        if not capture_id_text or not isinstance(alias, dict):
            continue
        command_type = compact(alias.get("commandType"))
        if command_type:
            result[capture_id_text] = {**alias, "commandType": command_type}
    return result


def redacted_decision(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "captureId": item["captureId"],
        "commandType": item["commandType"],
        "originalKind": item["originalKind"],
        "commandAliasApplied": item["commandAliasApplied"],
        "storageMode": item["storageMode"],
        "encrypted": item["encrypted"],
        "sensitivity": item["sensitivity"],
        "eligible": item["eligible"],
        "skipReason": item["skipReason"],
    }


def redact_stdout(result: dict[str, Any], out_path: Path) -> dict[str, Any]:
    return {
        "pnhUnattendedDispatchQueuePlan": True,
        "mode": result["mode"],
        "out": safe_path_label(out_path),
        "capturesInspected": result["capturesInspected"],
        "queuedCount": result["queuedCount"],
        "skippedCount": result["skippedCount"],
        "queueActivationGateRequired": result["queueActivationGateRequired"],
        "externalWritesPerformed": False,
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
    }


def bounded(value: int, lower: int, upper: int) -> int:
    return min(max(int(value), lower), upper)


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
