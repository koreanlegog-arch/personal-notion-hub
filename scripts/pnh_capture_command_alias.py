#!/usr/bin/env python3
"""Create a metadata-only dispatch command alias for an existing capture.

This script does not decrypt, print, or modify private capture content. It
creates an ignored local overlay that lets dispatch scripts treat an encrypted
assistant capture as an explicit command packet.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.private_store import DEFAULT_DB_PATH, PrivateStoreError, list_captures  # noqa: E402


DEFAULT_STATE = ROOT / "companion" / "private" / "pnh_dispatch_state.json"
DEFAULT_COMMAND_ALIASES = ROOT / "companion" / "private" / "pnh_command_aliases.json"
DEFAULT_OUT = ROOT / "ops" / "runs" / "PNH-CAPTURE-COMMAND-ALIAS-20260605" / "command_alias_result.json"
COMMAND_KINDS = {"project_brief", "task_request", "daily_command", "urgent_approval"}


class CommandAliasError(ValueError):
    """Raised when a command alias cannot be created safely."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a metadata-only PNH capture command alias.")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Private inbox SQLite DB path.")
    parser.add_argument("--capture-id", default="", help="Specific capture id. Defaults to latest matching capture.")
    parser.add_argument("--command-type", default="task_request", choices=sorted(COMMAND_KINDS))
    parser.add_argument("--from-kind", default="assistant_capture", help="Required original kind unless --allow-any-kind.")
    parser.add_argument("--alias-file", default=str(DEFAULT_COMMAND_ALIASES), help="Ignored local command alias JSON.")
    parser.add_argument("--state-file", default=str(DEFAULT_STATE), help="Local dispatch state JSON.")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Redacted evidence output JSON.")
    parser.add_argument("--limit", type=int, default=50, help="Recent captures to inspect.")
    parser.add_argument("--reason", default="owner_requested_dispatch", help="Metadata-only alias reason.")
    parser.add_argument("--allow-any-kind", action="store_true", help="Allow aliasing captures with any original kind.")
    parser.add_argument("--allow-plaintext", action="store_true", help="Allow plaintext fixture captures.")
    parser.add_argument("--allow-external-db", action="store_true", help="Allow a DB outside companion/private for fixture tests.")
    args = parser.parse_args()

    try:
        result = create_alias(args)
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(redact_stdout(result, out_path), ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, PrivateStoreError, CommandAliasError) as exc:
        print(f"pnh_capture_command_alias=false error={exc}", file=sys.stderr)
        return 2


def create_alias(args: argparse.Namespace) -> dict[str, Any]:
    captures = list_captures(
        Path(args.db),
        limit=min(max(int(args.limit), 1), 200),
        include_body=False,
        create_if_missing=False,
        allow_external=args.allow_external_db,
    )
    capture = select_capture(captures, args)
    dispatch_state = load_json_object(Path(args.state_file), missing_ok=True, label="dispatch state")
    capture_id = compact(capture.get("id"))
    if capture_id in dispatch_state:
        raise CommandAliasError("capture is already present in dispatch state")

    alias_path = Path(args.alias_file)
    aliases_payload = load_alias_payload(alias_path)
    aliases = aliases_payload.setdefault("aliases", {})
    if not isinstance(aliases, dict):
        raise CommandAliasError("alias file aliases must be an object")
    aliases[capture_id] = {
        "captureId": capture_id,
        "commandType": args.command_type,
        "originalKind": compact(capture.get("kind")),
        "storageMode": compact(capture.get("storageMode")),
        "encrypted": bool(capture.get("encrypted")),
        "sensitivity": compact(capture.get("sensitivity")),
        "reason": compact(args.reason),
        "createdAt": utc_now(),
        "rawPrivateBodyRead": False,
    }
    alias_path.parent.mkdir(parents=True, exist_ok=True)
    alias_path.write_text(json.dumps(aliases_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "pnhCaptureCommandAlias": True,
        "captureId": capture_id,
        "commandType": args.command_type,
        "originalKind": compact(capture.get("kind")),
        "storageMode": compact(capture.get("storageMode")),
        "encrypted": bool(capture.get("encrypted")),
        "aliasFile": safe_path_label(alias_path),
        "dbContentModified": False,
        "privateValuesPrinted": False,
        "rawPrivateBodyRead": False,
        "out": "",
    }


def select_capture(captures: list[dict[str, Any]], args: argparse.Namespace) -> dict[str, Any]:
    for capture in captures:
        if args.capture_id and compact(capture.get("id")) != args.capture_id:
            continue
        if not args.allow_plaintext and capture.get("storageMode") == "plaintext-inbox":
            continue
        if not args.allow_any_kind and compact(capture.get("kind")) != compact(args.from_kind):
            continue
        if capture.get("status") != "inbox":
            continue
        return capture
    if args.capture_id:
        raise CommandAliasError("requested capture is not aliasable")
    raise CommandAliasError("no aliasable capture found")


def load_alias_payload(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "pnhCommandAliases": True,
            "schemaVersion": 1,
            "aliases": {},
        }
    payload = load_json_object(path, missing_ok=False, label="command aliases")
    if "aliases" not in payload:
        payload = {
            "pnhCommandAliases": True,
            "schemaVersion": 1,
            "aliases": payload,
        }
    return payload


def load_json_object(path: Path, *, missing_ok: bool, label: str) -> dict[str, Any]:
    if not path.exists():
        if missing_ok:
            return {}
        raise CommandAliasError(f"{label} is missing")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CommandAliasError(f"{label} JSON is invalid: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise CommandAliasError(f"{label} JSON must be an object")
    return payload


def redact_stdout(result: dict[str, Any], out_path: Path) -> dict[str, Any]:
    return {
        "pnhCaptureCommandAlias": True,
        "captureId": result["captureId"],
        "commandType": result["commandType"],
        "originalKind": result["originalKind"],
        "storageMode": result["storageMode"],
        "encrypted": result["encrypted"],
        "dbContentModified": False,
        "rawPrivateBodyRead": False,
        "privateValuesPrinted": False,
        "out": safe_path_label(out_path),
    }


def compact(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def safe_path_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return "[external-path]"


if __name__ == "__main__":
    raise SystemExit(main())
