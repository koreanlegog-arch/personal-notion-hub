#!/usr/bin/env python3
"""Export a redacted PNH dispatch candidate from the private inbox.

The output is suitable for `scripts/pnh_dispatch_job.py`. It uses metadata only
by default and does not decrypt or print private command bodies.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.private_store import DEFAULT_DB_PATH, PrivateStoreError, list_captures  # noqa: E402


COMMAND_KINDS = {"project_brief", "task_request", "daily_command", "urgent_approval"}
DEFAULT_OUT = ROOT / "ops" / "runs" / "PNH-DISPATCH-CANDIDATE-EXPORT-20260605" / "dispatch_candidate.json"
DEFAULT_STATE = ROOT / "companion" / "private" / "pnh_dispatch_state.json"
DEFAULT_COMMAND_ALIASES = ROOT / "companion" / "private" / "pnh_command_aliases.json"


class CandidateExportError(ValueError):
    """Raised when no safe dispatch candidate can be exported."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Export a metadata-only PNH dispatch candidate.")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Private inbox SQLite DB path.")
    parser.add_argument("--limit", type=int, default=20, help="Recent captures to inspect.")
    parser.add_argument("--capture-id", default="", help="Specific capture id to export.")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output JSON path.")
    parser.add_argument("--state-file", default=str(DEFAULT_STATE), help="Local dispatch state JSON used to skip already dispatched captures.")
    parser.add_argument("--command-aliases", default=str(DEFAULT_COMMAND_ALIASES), help="Metadata-only command alias JSON.")
    parser.add_argument("--allow-plaintext", action="store_true", help="Allow plaintext inbox candidates. Values are still not printed.")
    parser.add_argument("--allow-external-db", action="store_true", help="Allow a DB outside companion/private for fixture tests.")
    parser.add_argument("--allow-dispatched", action="store_true", help="Allow captures already present in dispatch state.")
    args = parser.parse_args()

    try:
        captures = list_captures(
            Path(args.db),
            limit=args.limit,
            include_body=False,
            create_if_missing=False,
            allow_external=args.allow_external_db,
        )
        dispatch_state = load_dispatch_state(Path(args.state_file))
        aliases = load_command_aliases(Path(args.command_aliases))
        capture = select_capture(
            captures,
            args.capture_id,
            allow_plaintext=args.allow_plaintext,
            dispatch_state=dispatch_state,
            allow_dispatched=args.allow_dispatched,
            aliases=aliases,
        )
        candidate = build_candidate(capture, aliases)
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(candidate, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(
            json.dumps(
                {
                    "dispatchCandidateExported": True,
                    "captureId": candidate["id"],
                    "commandType": candidate["commandType"],
                    "storageMode": candidate["storageMode"],
                    "privateValuesPrinted": False,
                    "out": str(out_path),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0
    except (OSError, PrivateStoreError, CandidateExportError) as exc:
        print(f"pnh_dispatch_candidate_export=false error={exc}", file=sys.stderr)
        return 2


def load_dispatch_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CandidateExportError(f"dispatch state JSON is invalid: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise CandidateExportError("dispatch state must be an object")
    return value


def select_capture(
    captures: list[dict[str, Any]],
    capture_id: str,
    *,
    allow_plaintext: bool,
    dispatch_state: dict[str, Any],
    allow_dispatched: bool,
    aliases: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    candidates = [
        item
        for item in captures
        if is_command_candidate(
            item,
            allow_plaintext=allow_plaintext,
            dispatch_state=dispatch_state,
            allow_dispatched=allow_dispatched,
            aliases=aliases,
        )
    ]
    if capture_id:
        for item in candidates:
            if item.get("id") == capture_id:
                return item
        if capture_id in dispatch_state and not allow_dispatched:
            raise CandidateExportError("requested capture id is already present in dispatch state")
        raise CandidateExportError("requested capture id is not an exportable command candidate")
    if not candidates:
        raise CandidateExportError("no exportable command candidate found")
    return candidates[0]


def is_command_candidate(
    item: dict[str, Any],
    *,
    allow_plaintext: bool,
    dispatch_state: dict[str, Any],
    allow_dispatched: bool,
    aliases: dict[str, dict[str, Any]],
) -> bool:
    if command_type_for(item, aliases) not in COMMAND_KINDS:
        return False
    if item.get("status") != "inbox":
        return False
    if item.get("storageMode") == "plaintext-inbox" and not allow_plaintext:
        return False
    if not allow_dispatched and str(item.get("id") or "") in dispatch_state:
        return False
    return True


def build_candidate(capture: dict[str, Any], aliases: dict[str, dict[str, Any]]) -> dict[str, Any]:
    capture_id = str(capture.get("id") or "").strip()
    if not capture_id:
        raise CandidateExportError("capture id is missing")
    command_type = command_type_for(capture, aliases) or "project_brief"
    sensitivity = str(capture.get("sensitivity") or "private").strip()
    return {
        "id": capture_id,
        "captureId": capture_id,
        "payloadType": "pnh_mobile_command_packet",
        "commandType": command_type,
        "originalKind": str(capture.get("kind") or "").strip(),
        "commandAliasApplied": capture_id in aliases,
        "commandStatus": "stored",
        "dispatchState": "not_dispatched",
        "priority": "normal",
        "sensitivity": sensitivity,
        "source": str(capture.get("source") or "mobile").strip(),
        "storageMode": str(capture.get("storageMode") or "unknown").strip(),
        "encrypted": bool(capture.get("encrypted")),
        "storedAt": str(capture.get("storedAt") or ""),
        "title": f"PNH {command_type} command packet ({capture_id})",
        "body": "Private command body remains in the local vault and is intentionally not exported.",
    }


def command_type_for(capture: dict[str, Any], aliases: dict[str, dict[str, Any]]) -> str:
    capture_id = str(capture.get("id") or "").strip()
    alias = aliases.get(capture_id, {})
    return str(alias.get("commandType") or capture.get("kind") or "").strip()


def load_command_aliases(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    payload = load_dispatch_state(path)
    aliases = payload.get("aliases", payload)
    if not isinstance(aliases, dict):
        raise CandidateExportError("command aliases JSON must contain an object")
    result: dict[str, dict[str, Any]] = {}
    for capture_id, alias in aliases.items():
        capture_id_text = str(capture_id or "").strip()
        if not capture_id_text or not isinstance(alias, dict):
            continue
        command_type = str(alias.get("commandType") or "").strip()
        if command_type:
            result[capture_id_text] = {**alias, "commandType": command_type}
    return result


if __name__ == "__main__":
    raise SystemExit(main())
