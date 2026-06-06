#!/usr/bin/env python3
"""Archive stale or incomplete PNH dispatch-state records.

Dry-run is the default. Apply mode moves selected records into a local archive
file and removes them from the active state. It never reads private command
bodies and never contacts external services.
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
sys.path.insert(0, str(ROOT))

from companion.dispatch_summary import summarize_dispatch_record  # noqa: E402


DEFAULT_STATE = ROOT / "companion" / "private" / "pnh_dispatch_state.json"
DEFAULT_ARCHIVE = ROOT / "companion" / "private" / "pnh_dispatch_state_archive.json"
DEFAULT_OUT = ROOT / "ops" / "runs" / "PNH-DISPATCH-STATE-CLEANUP-20260606" / "cleanup_plan.json"


class CleanupError(ValueError):
    """Raised when cleanup cannot be performed safely."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Archive stale PNH dispatch-state records.")
    parser.add_argument("--state-file", default=str(DEFAULT_STATE), help="Dispatch state JSON.")
    parser.add_argument("--archive-file", default=str(DEFAULT_ARCHIVE), help="Dispatch state archive JSON.")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Plan/result output JSON.")
    parser.add_argument(
        "--mode",
        default="incomplete-worker-done",
        choices=["incomplete-worker-done", "missing-ledger-thread", "all-incomplete"],
        help="Cleanup selection mode.",
    )
    parser.add_argument("--packet-id", default="", help="Specific packet id to archive.")
    parser.add_argument("--apply", action="store_true", help="Move selected records to archive.")
    args = parser.parse_args()

    try:
        state_path = Path(args.state_file)
        archive_path = Path(args.archive_file)
        state = load_object(state_path)
        selected = select_records(state, args.mode, args.packet_id)
        result = {
            "pnhDispatchStateCleanup": True,
            "mode": "apply" if args.apply else "dry-run",
            "selectionMode": args.mode,
            "stateFile": safe_path_label(state_path),
            "archiveFile": safe_path_label(archive_path),
            "recordsInspected": len(state),
            "selectedCount": len(selected),
            "selected": [redacted_selection(packet_id, record) for packet_id, record in selected],
            "writesPerformed": False,
            "privateValuesPrinted": False,
        }
        if args.apply and selected:
            archive_records(state_path, archive_path, state, selected)
            result["writesPerformed"] = True
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, CleanupError) as exc:
        print(f"pnh_dispatch_state_cleanup=false error={exc}", file=sys.stderr)
        return 2
    print(json.dumps({**result, "out": safe_path_label(Path(args.out))}, ensure_ascii=False, sort_keys=True))
    return 0


def select_records(state: dict[str, Any], mode: str, packet_id: str) -> list[tuple[str, dict[str, Any]]]:
    selected: list[tuple[str, dict[str, Any]]] = []
    for key, value in state.items():
        if not isinstance(value, dict):
            continue
        if packet_id and key != packet_id:
            continue
        summary = summarize_dispatch_record(str(key), value)
        missing = set(summary.get("missingEvidence", []))
        if mode == "incomplete-worker-done":
            matched = summary.get("taskStatus") == "worker_done" and bool(missing)
        elif mode == "missing-ledger-thread":
            matched = bool({"github_issue", "discord_thread"} & missing)
        else:
            matched = bool(missing)
        if matched:
            selected.append((str(key), value))
    return selected


def archive_records(
    state_path: Path,
    archive_path: Path,
    state: dict[str, Any],
    selected: list[tuple[str, dict[str, Any]]],
) -> None:
    archive = load_object(archive_path, missing_ok=True)
    events = archive.setdefault("events", [])
    if not isinstance(events, list):
        raise CleanupError("archive events must be a list")
    now = utc_now()
    for packet_id, record in selected:
        events.append(
            {
                "archivedAt": now,
                "packetId": packet_id,
                "reason": "stale_or_incomplete_dispatch_state",
                "summary": summarize_dispatch_record(packet_id, record),
                "record": record,
            }
        )
        state.pop(packet_id, None)
    save_object(state_path, state)
    save_object(archive_path, archive)


def redacted_selection(packet_id: str, record: dict[str, Any]) -> dict[str, Any]:
    summary = summarize_dispatch_record(packet_id, record)
    return {
        "packetId": summary["packetId"],
        "taskStatus": summary["taskStatus"],
        "evidenceCompleteness": summary["evidenceCompleteness"],
        "missingEvidence": summary["missingEvidence"],
        "updatedAt": summary["updatedAt"],
    }


def load_object(path: Path, *, missing_ok: bool = False) -> dict[str, Any]:
    if not path.exists():
        if missing_ok:
            return {}
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CleanupError(f"invalid JSON: {path}: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise CleanupError(f"JSON must be an object: {path}")
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
