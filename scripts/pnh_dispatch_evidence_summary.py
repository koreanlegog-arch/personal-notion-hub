#!/usr/bin/env python3
"""Export a redacted PNH dispatch evidence summary."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.dispatch_summary import summarize_dispatch_record  # noqa: E402
from scripts.pnh_dispatch_state_status import load_state  # noqa: E402


DEFAULT_STATE = ROOT / "companion" / "private" / "pnh_dispatch_state.json"
DEFAULT_OUT = ROOT / "ops" / "runs" / "PNH-DISPATCH-EVIDENCE-SUMMARY-20260605" / "dispatch_evidence_summary.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Export redacted PNH dispatch evidence summary.")
    parser.add_argument("--state-file", default=str(DEFAULT_STATE), help="Local dispatch state JSON.")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Summary output JSON path.")
    parser.add_argument("--limit", type=int, default=50, help="Maximum records to include.")
    args = parser.parse_args()

    try:
        state_path = Path(args.state_file)
        state = load_state(state_path)
        summary = build_summary(state, limit=args.limit)
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, ValueError) as exc:
        print(f"pnh_dispatch_evidence_summary=false error={exc}", file=sys.stderr)
        return 2
    print(json.dumps({**summary, "records": summary["records"][:3], "out": safe_path_label(out_path)}, ensure_ascii=False, sort_keys=True))
    return 0


def build_summary(state: dict[str, Any], *, limit: int) -> dict[str, Any]:
    records = []
    for packet_id, value in sorted(state.items(), key=lambda item: str(item[1].get("updatedAt", "")), reverse=True):
        if isinstance(value, dict):
            records.append(summarize_dispatch_record(str(packet_id), value))
    bounded_limit = min(max(int(limit), 1), 200)
    included = records[:bounded_limit]
    return {
        "dispatchEvidenceSummary": True,
        "totalRecords": len(records),
        "includedRecords": len(included),
        "readyForSupervisorReview": sum(1 for item in records if item["taskStatus"] == "worker_done"),
        "blockedOrFailed": sum(1 for item in records if item["taskStatus"] in {"worker_blocked", "worker_failed"}),
        "averageEvidenceCompleteness": average([int(item["evidenceCompleteness"]) for item in records]),
        "privateValuesPrinted": False,
        "records": included,
    }


def average(values: list[int]) -> int:
    if not values:
        return 0
    return round(sum(values) / len(values))


def safe_path_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return "[external-path]"


if __name__ == "__main__":
    raise SystemExit(main())
