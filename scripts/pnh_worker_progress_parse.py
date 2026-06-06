#!/usr/bin/env python3
"""Parse redacted worker progress text into dispatch-state metadata.

This script accepts operator-provided or fixture text. It stores only semantic
status, stage, confidence, and redacted signal labels. It does not store message
content and does not contact Discord/OpenClaw.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE = ROOT / "companion" / "private" / "pnh_dispatch_state.json"
DEFAULT_OUT = ROOT / "ops" / "runs" / "PNH-WORKER-PROGRESS-PARSE-20260606" / "worker_progress_parse.json"

SECRET_PATTERN = re.compile(
    r"(Bearer\s+[A-Za-z0-9_.-]{8,}|gh[opsu]_[A-Za-z0-9_]{12,}|sk-[A-Za-z0-9_-]{8,}|"
    r"password\s*[=:]|secret\s*[=:]|token\s*[=:])",
    re.IGNORECASE,
)

SIGNALS = [
    ("blocked", "blocked", "blocked", re.compile(r"\b(blocked|waiting|cannot proceed|needs approval)\b", re.I)),
    ("failed", "failed", "failed", re.compile(r"\b(failed|error|exception|traceback|cannot complete)\b", re.I)),
    ("done", "done", "done", re.compile(r"\b(done|completed|complete|worker_done|finished|passed)\b", re.I)),
    ("qa", "qa", "qa", re.compile(r"\b(qa|test|verified|verification|playwright|smoke)\b", re.I)),
    ("review", "review", "review", re.compile(r"\b(review|diff|finding|regression)\b", re.I)),
    ("running", "running", "implementation", re.compile(r"\b(running|working|implementing|in progress)\b", re.I)),
]


class ProgressParseError(ValueError):
    """Raised when progress input is invalid or unsafe."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse redacted worker progress into PNH dispatch state.")
    parser.add_argument("--packet-id", required=True, help="Dispatch packet id to update.")
    parser.add_argument("--text", default="", help="Short redacted progress text.")
    parser.add_argument("--text-file", default="", help="Text file to parse.")
    parser.add_argument("--state-file", default=str(DEFAULT_STATE), help="Dispatch state JSON.")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Dry-run output JSON.")
    parser.add_argument("--apply", action="store_true", help="Update dispatch state with semantic progress metadata.")
    args = parser.parse_args()

    try:
        packet_id = compact(args.packet_id, "packet id", 160)
        text = load_text(args.text, args.text_file)
        progress = parse_progress(text)
        state_path = Path(args.state_file)
        state = load_object(state_path)
        record = dict(state.get(packet_id, {}))
        planned = attach_progress(record, progress)
        result = {
            "pnhWorkerProgressParse": True,
            "mode": "apply" if args.apply else "dry-run",
            "packetId": packet_id,
            "stateFile": safe_path_label(state_path),
            "progress": progress,
            "writesPerformed": False,
            "messageContentStored": False,
            "privateValuesPrinted": False,
            "tokenValuePrinted": False,
        }
        if args.apply:
            state[packet_id] = planned
            save_object(state_path, state)
            result["writesPerformed"] = True
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, ProgressParseError) as exc:
        print(f"pnh_worker_progress_parse=false error={exc}", file=sys.stderr)
        return 2
    print(json.dumps({**result, "out": safe_path_label(Path(args.out))}, ensure_ascii=False, sort_keys=True))
    return 0


def parse_progress(text: str) -> dict[str, Any]:
    if SECRET_PATTERN.search(text):
        raise ProgressParseError("progress input appears to contain a secret-like value")
    compacted = " ".join(text.split())
    if not compacted:
        raise ProgressParseError("progress text is required")
    if len(compacted) > 5000:
        raise ProgressParseError("progress text is too long")
    matched = []
    for label, status, stage, pattern in SIGNALS:
        if pattern.search(compacted):
            matched.append((label, status, stage))
    if not matched:
        status, stage, confidence = "running", "unknown", 30
        labels = ["generic-progress"]
    else:
        label, status, stage = matched[0]
        confidence = min(95, 55 + 10 * len(matched))
        labels = [item[0] for item in matched]
    return {
        "status": status,
        "stage": stage,
        "confidence": confidence,
        "signals": labels[:6],
        "updatedAt": utc_now(),
    }


def attach_progress(record: dict[str, Any], progress: dict[str, Any]) -> dict[str, Any]:
    updated = dict(record)
    updated["semanticProgress"] = progress
    updated["updatedAt"] = progress["updatedAt"]
    return updated


def load_text(text: str, text_file: str) -> str:
    if text_file:
        return Path(text_file).read_text(encoding="utf-8")
    return text


def load_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProgressParseError(f"dispatch state JSON is invalid: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ProgressParseError("dispatch state must be an object")
    return payload


def save_object(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def compact(value: Any, label: str, max_len: int) -> str:
    text = " ".join(str(value or "").split()).strip()
    if not text:
        raise ProgressParseError(f"{label} is required")
    if len(text) > max_len:
        raise ProgressParseError(f"{label} is too long")
    return text


def safe_path_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return "[external-path]"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


if __name__ == "__main__":
    raise SystemExit(main())
