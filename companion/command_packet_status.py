"""Metadata-only command packet status helpers for Personal Notion Hub."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from .dispatch_summary import summarize_dispatch_record
except ImportError:  # pragma: no cover - supports direct script execution.
    from dispatch_summary import summarize_dispatch_record  # type: ignore


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNS_DIR = ROOT / "ops" / "runs"
SUMMARY_FILENAME = "single_command_packet_summary.json"
RUN_PREFIXES = ("PNH-COMMAND-PACKET", "PNH-SINGLE-COMMAND-PACKET")


def build_command_packet_status(
    dispatch_state: dict[str, Any],
    *,
    runs_dir: Path = DEFAULT_RUNS_DIR,
    limit: int = 20,
) -> dict[str, Any]:
    """Return a redacted status snapshot for UI/companion consumers."""
    dispatch_records = _dispatch_records(dispatch_state, limit=limit)
    latest_dispatch = dispatch_records[0] if dispatch_records else {}
    latest_run = latest_single_command_packet_run(runs_dir)
    queue_count = _int_value(latest_run.get("queuedCount")) if latest_run else 0
    worker_status = str(latest_dispatch.get("workerStatus") or latest_run.get("workerStatus") or "")
    next_action = str(latest_dispatch.get("nextAction") or _next_action_for_run(latest_run, queue_count))
    stage = _status_stage(latest_dispatch, latest_run, queue_count)

    return {
        "queueCount": queue_count,
        "latestRun": latest_run,
        "latestDispatch": latest_dispatch,
        "stage": stage,
        "stageLabel": _stage_label(stage),
        "stageSteps": _stage_steps(latest_dispatch, latest_run, queue_count),
        "lastIssue": latest_dispatch.get("githubIssueNumber", ""),
        "lastWorkerStatus": worker_status,
        "nextAction": next_action,
        "readyForSupervisorReview": sum(1 for item in dispatch_records if item.get("nextAction") == "summarize_worker_result_for_supervisor_review"),
        "workerDone": sum(1 for item in dispatch_records if item.get("taskStatus") == "worker_done"),
        "pendingWorkerSession": sum(1 for item in dispatch_records if item.get("taskStatus") == "dispatched_to_worker_thread"),
        "totalRecords": len(dispatch_records),
        "privateValuesPrinted": False,
        "rawPrivateBodyRead": False,
        "responsePolicy": "metadata-only",
    }


def latest_single_command_packet_run(runs_dir: Path = DEFAULT_RUNS_DIR) -> dict[str, Any]:
    if not runs_dir.exists():
        return {}

    candidates: list[tuple[float, Path]] = []
    for path in runs_dir.iterdir():
        if not path.is_dir() or not path.name.startswith(RUN_PREFIXES):
            continue
        summary = path / SUMMARY_FILENAME
        if summary.is_file():
            candidates.append((summary.stat().st_mtime, summary))

    if not candidates:
        return {}

    _mtime, latest = max(candidates, key=lambda item: item[0])
    try:
        payload = json.loads(latest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "runDir": _safe_path_label(latest.parent),
            "readable": False,
            "privateValuesPrinted": False,
            "rawPrivateBodyRead": False,
        }
    if not isinstance(payload, dict):
        return {}
    return _summarize_run(payload, latest.parent)


def _dispatch_records(state: dict[str, Any], *, limit: int) -> list[dict[str, Any]]:
    records = []
    for packet_id, value in sorted(state.items(), key=lambda item: str(item[1].get("updatedAt", "")), reverse=True):
        if isinstance(value, dict):
            records.append(summarize_dispatch_record(str(packet_id), value))
    return records[:limit]


def _summarize_run(payload: dict[str, Any], run_dir: Path) -> dict[str, Any]:
    return {
        "runDir": str(payload.get("runDir") or _safe_path_label(run_dir)),
        "runId": str(payload.get("runId") or run_dir.name),
        "mode": str(payload.get("mode") or ""),
        "generatedAt": str(payload.get("generatedAt") or ""),
        "message": str(payload.get("message") or ""),
        "selectedCaptureId": str(payload.get("selectedCaptureId") or ""),
        "queuedCount": _int_value(payload.get("queuedCount")),
        "externalWritesPerformed": bool(payload.get("externalWritesPerformed")),
        "workerRunPerformed": bool(payload.get("workerRunPerformed")),
        "pendingExternalWriteCount": _int_value(payload.get("pendingExternalWriteCount")),
        "workerStatus": str(payload.get("workerStatus") or ""),
        "workerSessionId": str(payload.get("workerSessionId") or ""),
        "githubIssueSet": bool(payload.get("githubIssueSet")),
        "discordThreadSet": bool(payload.get("discordThreadSet")),
        "privateValuesPrinted": False,
        "rawPrivateBodyRead": False,
        "readable": True,
    }


def _next_action_for_run(run: dict[str, Any], queue_count: int) -> str:
    if not run:
        return "run_single_command_packet_wrapper"
    if queue_count > 0 and not run.get("externalWritesPerformed"):
        return "apply_or_review_pending_command_packet"
    if run.get("message") == "queue_empty" or queue_count == 0:
        return "wait_for_next_mobile_command_packet"
    if run.get("workerRunPerformed"):
        return "refresh_dispatch_evidence_and_supervisor_summary"
    return "review_command_packet_wrapper_result"


def _status_stage(dispatch: dict[str, Any], run: dict[str, Any], queue_count: int) -> str:
    if dispatch.get("taskStatus") == "worker_done":
        return "review_ready"
    if dispatch.get("workerResultSet") or dispatch.get("workerStatus"):
        return "worker_result"
    if dispatch.get("discordThreadSet"):
        return "worker_thread"
    if dispatch.get("githubIssueSet"):
        return "ledger_ready"
    if queue_count > 0:
        return "queued"
    if run.get("message") == "queue_empty" or queue_count == 0:
        return "idle"
    return "unknown"


def _stage_label(stage: str) -> str:
    labels = {
        "idle": "Idle",
        "queued": "Queued",
        "ledger_ready": "Ledger ready",
        "worker_thread": "Worker thread",
        "worker_result": "Worker result",
        "review_ready": "Review ready",
        "unknown": "Unknown",
    }
    return labels.get(stage, "Unknown")


def _stage_steps(dispatch: dict[str, Any], run: dict[str, Any], queue_count: int) -> list[dict[str, Any]]:
    return [
        {
            "key": "queued",
            "label": "Inbox",
            "state": _step_state(queue_count > 0 or bool(dispatch) or bool(run), True),
        },
        {
            "key": "github",
            "label": "Ledger",
            "state": _step_state(bool(dispatch.get("githubIssueSet")), bool(dispatch) or queue_count > 0),
        },
        {
            "key": "discord",
            "label": "Thread",
            "state": _step_state(bool(dispatch.get("discordThreadSet")), bool(dispatch.get("githubIssueSet"))),
        },
        {
            "key": "worker",
            "label": "Worker",
            "state": _step_state(bool(dispatch.get("workerResultSet") or dispatch.get("workerStatus")), bool(dispatch.get("discordThreadSet"))),
        },
        {
            "key": "review",
            "label": "Review",
            "state": _step_state(dispatch.get("taskStatus") == "worker_done", bool(dispatch.get("workerResultSet") or dispatch.get("workerStatus"))),
        },
    ]


def _step_state(done: bool, available: bool) -> str:
    if done:
        return "done"
    if available:
        return "current"
    return "waiting"


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _safe_path_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return path.name
