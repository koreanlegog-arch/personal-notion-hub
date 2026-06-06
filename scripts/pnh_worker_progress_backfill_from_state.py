#!/usr/bin/env python3
"""Backfill semantic worker progress from redacted dispatch-state metadata.

This script does not read private command bodies, Discord messages, GitHub issue
bodies, or worker transcripts. It derives semantic progress from existing
metadata-only fields such as worker status, evidence-ref presence, and linked
ledger/thread IDs.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.pnh_worker_progress_parse import parse_progress  # noqa: E402


DEFAULT_STATE = ROOT / "companion" / "private" / "pnh_dispatch_state.json"
DEFAULT_OUT = ROOT / "ops" / "runs" / "PNH-WORKER-PROGRESS-BACKFILL-20260606" / "worker_progress_backfill.json"


class BackfillError(ValueError):
    """Raised when semantic progress backfill cannot proceed safely."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill semantic progress from redacted dispatch metadata.")
    parser.add_argument("--state-file", default=str(DEFAULT_STATE), help="Dispatch state JSON.")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output JSON.")
    parser.add_argument("--apply", action="store_true", help="Persist backfilled semantic progress.")
    args = parser.parse_args()

    try:
        state_path = Path(args.state_file)
        state = load_state(state_path)
        candidates = build_candidates(state)
        result = {
            "pnhWorkerProgressBackfillFromState": True,
            "mode": "apply" if args.apply else "dry-run",
            "stateFile": safe_path_label(state_path),
            "recordsInspected": len(state),
            "recordsBackfilled": len(candidates),
            "writesPerformed": False,
            "messageContentStored": False,
            "privateValuesPrinted": False,
            "tokenValuePrinted": False,
            "backfilled": [redacted_item(packet_id, progress) for packet_id, progress in candidates],
        }
        if args.apply and candidates:
            for packet_id, progress in candidates:
                record = dict(state.get(packet_id, {}))
                record["semanticProgress"] = progress
                record["updatedAt"] = progress["updatedAt"]
                state[packet_id] = record
            save_state(state_path, state)
            result["writesPerformed"] = True
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, BackfillError) as exc:
        print(f"pnh_worker_progress_backfill_from_state=false error={exc}", file=sys.stderr)
        return 2
    print(json.dumps({**result, "out": safe_path_label(Path(args.out))}, ensure_ascii=False, sort_keys=True))
    return 0


def build_candidates(state: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    candidates = []
    for packet_id, record in sorted(state.items()):
        if not isinstance(record, dict):
            continue
        if is_current_semantic_progress(record.get("semanticProgress")):
            continue
        text = semantic_text_from_record(record)
        if not text:
            continue
        candidates.append((str(packet_id), parse_progress(text)))
    return candidates


def semantic_text_from_record(record: dict[str, Any]) -> str:
    worker_status = str(record.get("workerStatus") or "").strip()
    if not worker_status:
        return ""
    parts = []
    if worker_status == "done":
        parts.append("Worker_done completed.")
    elif worker_status == "failed":
        parts.append("Worker failed.")
    elif worker_status == "blocked":
        parts.append("Worker is blocked and needs input.")
    elif worker_status in {"running", "review", "qa"}:
        parts.append(f"Worker is {worker_status}.")
    else:
        return ""
    if record.get("workerEvidenceRef"):
        parts.append("Evidence recorded.")
    if record.get("githubIssueNumber") or record.get("githubIssueUrl"):
        parts.append("GitHub issue linked.")
    if record.get("githubIssueState") == "closed":
        parts.append("GitHub issue closed.")
    if record.get("discordThreadId"):
        parts.append("Discord thread linked.")
    return " ".join(parts)


def is_current_semantic_progress(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    try:
        parser_version = int(value.get("parserVersion") or 0)
    except (TypeError, ValueError):
        parser_version = 0
    required = ["evidenceStrength", "recommendedNextAction", "messageContentStored", "signals"]
    return parser_version >= 2 and all(key in value for key in required)


def redacted_item(packet_id: str, progress: dict[str, Any]) -> dict[str, Any]:
    return {
        "packetId": packet_id,
        "status": progress.get("status", ""),
        "stage": progress.get("stage", ""),
        "confidence": progress.get("confidence", 0),
        "evidenceStrength": progress.get("evidenceStrength", ""),
        "recommendedNextAction": progress.get("recommendedNextAction", ""),
    }


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BackfillError(f"dispatch state JSON is invalid: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise BackfillError("dispatch state must be an object")
    return payload


def save_state(path: Path, payload: dict[str, Any]) -> None:
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


if __name__ == "__main__":
    raise SystemExit(main())
