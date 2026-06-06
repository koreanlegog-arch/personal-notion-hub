#!/usr/bin/env python3
"""Batch import redacted worker progress snippets into dispatch state."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "ops" / "runs" / "PNH-WORKER-PROGRESS-BATCH-20260606" / "worker_progress_batch.json"


class ProgressBatchError(ValueError):
    """Raised when progress batch import cannot proceed."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch import redacted worker progress snippets.")
    parser.add_argument("--input-json", required=True, help="JSON list of {packetId,text} entries.")
    parser.add_argument("--state-file", default="", help="Dispatch state JSON override.")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Batch output JSON.")
    parser.add_argument("--apply", action="store_true", help="Apply semantic progress updates.")
    args = parser.parse_args()

    try:
        entries = load_entries(Path(args.input_json))
        results = []
        for idx, entry in enumerate(entries, start=1):
            result = run_parse(args, entry, idx)
            results.append(result)
        payload = {
            "pnhWorkerProgressBatchImport": True,
            "mode": "apply" if args.apply else "dry-run",
            "entriesProcessed": len(entries),
            "writesPerformed": bool(args.apply),
            "messageContentStored": False,
            "privateValuesPrinted": False,
            "tokenValuePrinted": False,
            "results": results,
        }
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, ProgressBatchError) as exc:
        print(f"pnh_worker_progress_batch_import=false error={exc}", file=sys.stderr)
        return 2
    print(json.dumps({**payload, "out": safe_path_label(Path(args.out))}, ensure_ascii=False, sort_keys=True))
    return 0


def load_entries(path: Path) -> list[dict[str, str]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProgressBatchError(f"input JSON is invalid: {exc.msg}") from exc
    if not isinstance(payload, list):
        raise ProgressBatchError("input JSON must be a list")
    entries = []
    for item in payload:
        if not isinstance(item, dict):
            raise ProgressBatchError("each progress item must be an object")
        packet_id = str(item.get("packetId") or item.get("packet_id") or "").strip()
        text = str(item.get("text") or "").strip()
        if not packet_id or not text:
            raise ProgressBatchError("each progress item requires packetId and text")
        entries.append({"packetId": packet_id, "text": text})
    return entries


def run_parse(args: argparse.Namespace, entry: dict[str, str], index: int) -> dict[str, Any]:
    out_path = Path(args.out).with_name(f"worker_progress_{index}.json")
    command = [
        sys.executable,
        str(ROOT / "scripts" / "pnh_worker_progress_parse.py"),
        "--packet-id",
        entry["packetId"],
        "--text",
        entry["text"],
        "--out",
        str(out_path),
    ]
    if args.state_file:
        command.extend(["--state-file", args.state_file])
    if args.apply:
        command.append("--apply")
    result = subprocess.run(command, capture_output=True, text=True, timeout=20, check=False)
    if result.returncode != 0:
        raise ProgressBatchError(first_line(result.stderr) or first_line(result.stdout) or "progress parse failed")
    parsed = json.loads(out_path.read_text(encoding="utf-8"))
    return {
        "packetId": entry["packetId"],
        "status": parsed.get("progress", {}).get("status", ""),
        "stage": parsed.get("progress", {}).get("stage", ""),
        "confidence": parsed.get("progress", {}).get("confidence", 0),
        "messageContentStored": False,
    }


def safe_path_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return "[external-path]"


def first_line(value: str) -> str:
    return value.strip().splitlines()[0] if value.strip() else ""


if __name__ == "__main__":
    raise SystemExit(main())
