#!/usr/bin/env python3
"""Record redacted worker-result metadata for a PNH dispatch packet.

Dry-run is the default. Apply mode updates the ignored local dispatch state file
with external IDs and status metadata only; it does not contact OpenClaw,
Discord, GitHub, or any other external service.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE = ROOT / "companion" / "private" / "pnh_dispatch_state.json"
DEFAULT_DRY_RUN_OUT = ROOT / "ops" / "runs" / "PNH-WORKER-RESULT-RECORD-20260605" / "worker_result_plan.json"
ALLOWED_STATUS = {"queued", "running", "review", "qa", "blocked", "done", "failed"}


class WorkerResultRecordError(ValueError):
    """Raised when worker-result metadata is unsafe or incomplete."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Record PNH worker-result metadata without printing private values.")
    parser.add_argument("--packet-id", required=True, help="PNH capture/packet id to update.")
    parser.add_argument("--worker-session-id", required=True, help="External worker/session id or local rehearsal id.")
    parser.add_argument("--status", default="done", choices=sorted(ALLOWED_STATUS), help="Worker result status.")
    parser.add_argument("--evidence-ref", default="", help="Optional non-secret evidence reference, e.g. ops/runs/.../summary.json.")
    parser.add_argument("--state-file", default=str(DEFAULT_STATE), help="Local dispatch state JSON.")
    parser.add_argument("--out", default=str(DEFAULT_DRY_RUN_OUT), help="Dry-run plan output path.")
    parser.add_argument("--apply", action="store_true", help="Update local dispatch state.")
    args = parser.parse_args()

    try:
        packet_id = compact(args.packet_id, "packet id", max_len=160)
        worker_session_id = compact(args.worker_session_id, "worker session id", max_len=160)
        evidence_ref = compact(args.evidence_ref, "evidence ref", max_len=240) if args.evidence_ref else ""
        state_path = Path(args.state_file)
        state = load_state(state_path)
        existing = dict(state.get(packet_id, {}))
        planned_record = build_record(existing, worker_session_id, args.status, evidence_ref)
        result = {
            "workerResultRecord": True,
            "mode": "apply" if args.apply else "dry-run",
            "packetId": packet_id,
            "stateFile": safe_state_file_label(state_path),
            "writesPerformed": False,
            "privateValuesPrinted": False,
            "planned": redact_record(planned_record),
        }
        if args.apply:
            state[packet_id] = planned_record
            save_state(state_path, state)
            result["writesPerformed"] = True
        else:
            out_path = Path(args.out)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, WorkerResultRecordError) as exc:
        print(f"pnh_worker_result_record=false error={exc}", file=sys.stderr)
        return 2


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise WorkerResultRecordError(f"dispatch state JSON is invalid: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise WorkerResultRecordError("dispatch state must be an object")
    return value


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def build_record(existing: dict[str, Any], worker_session_id: str, status: str, evidence_ref: str) -> dict[str, Any]:
    record = dict(existing)
    now = utc_now()
    record.update(
        {
            "workerSessionId": worker_session_id,
            "workerStatus": status,
            "workerResultRecordedAt": now,
            "updatedAt": now,
        }
    )
    if evidence_ref:
        record["workerEvidenceRef"] = evidence_ref
    return record


def redact_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "githubIssueNumber": record.get("githubIssueNumber", ""),
        "githubIssueSet": bool(record.get("githubIssueUrl")),
        "discordThreadId": record.get("discordThreadId", ""),
        "discordThreadSet": bool(record.get("discordThreadId")),
        "workerSessionId": record.get("workerSessionId", ""),
        "workerStatus": record.get("workerStatus", ""),
        "workerEvidenceRefSet": bool(record.get("workerEvidenceRef")),
        "workerResultSet": bool(record.get("workerSessionId")),
        "workerResultRecordedAt": record.get("workerResultRecordedAt", ""),
        "updatedAt": record.get("updatedAt", ""),
    }


def compact(value: Any, label: str, *, max_len: int) -> str:
    text = " ".join(str(value or "").replace("\n", " ").split()).strip()
    if not text:
        raise WorkerResultRecordError(f"{label} is required")
    if len(text) > max_len:
        raise WorkerResultRecordError(f"{label} is too long")
    return text


def safe_state_file_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return "[external-state-file]"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


if __name__ == "__main__":
    raise SystemExit(main())
