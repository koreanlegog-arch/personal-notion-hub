#!/usr/bin/env python3
"""Print redacted PNH dispatch state status.

This reads local private dispatch state metadata only. It does not contact
GitHub, Discord, or OpenClaw.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE = ROOT / "companion" / "private" / "pnh_dispatch_state.json"


class DispatchStateStatusError(ValueError):
    """Raised when dispatch state cannot be safely summarized."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect PNH dispatch state without printing private values.")
    parser.add_argument("--state-file", default=str(DEFAULT_STATE), help="Local dispatch state JSON.")
    parser.add_argument("--limit", type=int, default=20, help="Maximum records to print.")
    parser.add_argument("--include-urls", action="store_true", help="Include external issue URLs. IDs are shown either way.")
    args = parser.parse_args()

    try:
        state_path = Path(args.state_file)
        state = load_state(state_path)
        result = summarize_state(state, state_path, limit=args.limit, include_urls=args.include_urls)
    except (OSError, DispatchStateStatusError) as exc:
        print(f"pnh_dispatch_state_status=false error={exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DispatchStateStatusError(f"dispatch state JSON is invalid: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise DispatchStateStatusError("dispatch state must be an object")
    return value


def summarize_state(state: dict[str, Any], state_path: Path, *, limit: int, include_urls: bool) -> dict[str, Any]:
    bounded_limit = min(max(int(limit), 1), 100)
    records = []
    for packet_id, value in sorted(state.items(), key=lambda item: str(item[1].get("updatedAt", "")), reverse=True):
        if not isinstance(value, dict):
            continue
        record = {
            "packetId": str(packet_id),
            "githubIssueNumber": value.get("githubIssueNumber", ""),
            "githubIssueSet": bool(value.get("githubIssueUrl")),
            "discordThreadId": value.get("discordThreadId", ""),
            "discordThreadSet": bool(value.get("discordThreadId")),
            "updatedAt": value.get("updatedAt", ""),
        }
        if include_urls:
            record["githubIssueUrl"] = value.get("githubIssueUrl", "")
        records.append(record)
    return {
        "dispatchStateStatus": True,
        "stateFile": safe_state_file_label(state_path),
        "totalRecords": len(records),
        "githubLinked": sum(1 for item in records if item["githubIssueSet"]),
        "discordLinked": sum(1 for item in records if item["discordThreadSet"]),
        "privateValuesPrinted": False,
        "records": records[:bounded_limit],
    }


def safe_state_file_label(path: Path) -> str:
    try:
        rel = path.resolve().relative_to(ROOT)
        return str(rel)
    except ValueError:
        return "[external-state-file]"


if __name__ == "__main__":
    raise SystemExit(main())
