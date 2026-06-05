#!/usr/bin/env python3
"""Refresh Discord/OpenClaw thread metadata into local PNH dispatch state.

Default mode uses a local fixture or dry-run planning only. Live Discord reads
require explicit approval because message content may be returned by OpenClaw.
This script stores only metadata counts/status, never message bodies.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE = ROOT / "companion" / "private" / "pnh_dispatch_state.json"
DEFAULT_OUT = ROOT / "ops" / "runs" / "PNH-DISCORD-THREAD-STATUS-REFRESH-20260605" / "discord_thread_status_refresh.json"
DEFAULT_OPENCLAW_ENV = Path.home() / ".config" / "openclaw" / "openclaw-gateway.env"


class DiscordThreadStatusRefreshError(ValueError):
    """Raised when thread status refresh cannot run safely."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh Discord thread metadata without storing message content.")
    parser.add_argument("--state-file", default=str(DEFAULT_STATE), help="Local dispatch state JSON.")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output JSON path.")
    parser.add_argument("--fixture-json", default="", help="Fixture OpenClaw read JSON for tests.")
    parser.add_argument("--openclaw-read", action="store_true", help="Read live Discord thread metadata through OpenClaw.")
    parser.add_argument("--approve-discord-read", action="store_true", help="Required with --openclaw-read.")
    parser.add_argument("--openclaw-env", default=str(DEFAULT_OPENCLAW_ENV), help="Approved OpenClaw env file for live read.")
    parser.add_argument("--apply", action="store_true", help="Update local dispatch state with metadata-only thread status.")
    parser.add_argument("--limit", type=int, default=10, help="Read limit per thread.")
    args = parser.parse_args()

    try:
        state_path = Path(args.state_file)
        state = load_state(state_path)
        fixture = load_json_object(Path(args.fixture_json), "fixture") if args.fixture_json else None
        result = build_refresh(args, state, fixture=fixture)
        if args.apply:
            apply_refresh(state_path, state, result)
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, DiscordThreadStatusRefreshError) as exc:
        print(f"pnh_discord_thread_status_refresh=false error={exc}", file=sys.stderr)
        return 2
    print(json.dumps(redact_stdout(result, out_path), ensure_ascii=False, sort_keys=True))
    return 0


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return load_json_object(path, "dispatch state")


def load_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DiscordThreadStatusRefreshError(f"{label} JSON is invalid: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise DiscordThreadStatusRefreshError(f"{label} JSON must be an object")
    return payload


def build_refresh(args: argparse.Namespace, state: dict[str, Any], *, fixture: dict[str, Any] | None) -> dict[str, Any]:
    if args.openclaw_read and not args.approve_discord_read:
        raise DiscordThreadStatusRefreshError("--openclaw-read requires --approve-discord-read")
    records = []
    for packet_id, record in sorted(state.items(), key=lambda item: str(item[1].get("updatedAt", "")), reverse=True):
        if not isinstance(record, dict) or not compact(record.get("discordThreadId")):
            continue
        records.append(refresh_record(str(packet_id), record, args, fixture=fixture))
    return {
        "discordThreadStatusRefresh": True,
        "generatedAt": utc_now(),
        "mode": "apply" if args.apply else "dry-run",
        "openclawReadRequested": bool(args.openclaw_read),
        "fixtureUsed": fixture is not None,
        "recordsInspected": len(records),
        "recordsRefreshed": sum(1 for item in records if item["discordStatusRefreshed"]),
        "recordsWithErrors": sum(1 for item in records if item["error"]),
        "localWritesPerformed": bool(args.apply),
        "externalWritesPerformed": False,
        "messageContentStored": False,
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "records": records,
    }


def refresh_record(
    packet_id: str,
    record: dict[str, Any],
    args: argparse.Namespace,
    *,
    fixture: dict[str, Any] | None,
) -> dict[str, Any]:
    thread_id = compact(record.get("discordThreadId"))
    status: dict[str, Any] = {}
    error = ""
    if fixture is not None:
        status = summarize_openclaw_read_payload(fixture)
    elif args.openclaw_read:
        try:
            status = live_read_status(thread_id, args.limit, Path(args.openclaw_env))
        except DiscordThreadStatusRefreshError as exc:
            error = str(exc)
    return {
        "packetId": packet_id,
        "discordThreadId": thread_id,
        "discordThreadSet": bool(thread_id),
        "discordStatusRefreshed": bool(status) and status.get("returnCode") == 0,
        "discordReadReturnCode": status.get("returnCode", ""),
        "discordMessagesObserved": status.get("messageCount", 0),
        "discordReadStdoutBytes": status.get("stdoutBytes", 0),
        "discordReadCheckedAt": utc_now() if status else "",
        "error": error or status.get("errorFirstLine", ""),
    }


def live_read_status(thread_id: str, limit: int, openclaw_env: Path) -> dict[str, Any]:
    bounded_limit = str(min(max(int(limit), 1), 25))
    env = None
    if openclaw_env.exists():
        import os

        env = os.environ.copy()
        env.update(read_env_file(openclaw_env))
    result = subprocess.run(
        [
            "openclaw",
            "message",
            "read",
            "--channel",
            "discord",
            "--target",
            f"channel:{thread_id}",
            "--limit",
            bounded_limit,
            "--json",
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        env=env,
    )
    if result.returncode != 0:
        return {
            "returnCode": result.returncode,
            "messageCount": 0,
            "stdoutBytes": len(result.stdout.encode("utf-8")),
            "errorFirstLine": first_line(result.stderr),
        }
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        payload = {}
    summary = summarize_openclaw_read_payload(payload)
    summary["returnCode"] = result.returncode
    summary["stdoutBytes"] = len(result.stdout.encode("utf-8"))
    return summary


def read_env_file(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def summarize_openclaw_read_payload(payload: dict[str, Any]) -> dict[str, Any]:
    messages = find_message_list(payload)
    return {
        "returnCode": int(payload.get("returnCode", 0)) if str(payload.get("returnCode", "0")).isdigit() else 0,
        "messageCount": len(messages),
        "stdoutBytes": int(payload.get("stdoutBytes", 0)) if str(payload.get("stdoutBytes", "0")).isdigit() else 0,
    }


def find_message_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if not isinstance(value, dict):
        return []
    for key in ["messages", "items", "results"]:
        candidate = value.get(key)
        if isinstance(candidate, list):
            return candidate
    for candidate in value.values():
        nested = find_message_list(candidate)
        if nested:
            return nested
    return []


def apply_refresh(state_path: Path, state: dict[str, Any], result: dict[str, Any]) -> None:
    checked_at = utc_now()
    for item in result["records"]:
        if not item["discordStatusRefreshed"]:
            continue
        record = state.get(item["packetId"])
        if not isinstance(record, dict):
            continue
        record.update(
            {
                "discordReadCheckedAt": item["discordReadCheckedAt"] or checked_at,
                "discordMessagesObserved": item["discordMessagesObserved"],
                "discordReadReturnCode": item["discordReadReturnCode"],
                "updatedAt": checked_at,
            }
        )
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def redact_stdout(result: dict[str, Any], out_path: Path) -> dict[str, Any]:
    return {
        "discordThreadStatusRefresh": True,
        "mode": result["mode"],
        "out": safe_path_label(out_path),
        "openclawReadRequested": result["openclawReadRequested"],
        "fixtureUsed": result["fixtureUsed"],
        "recordsInspected": result["recordsInspected"],
        "recordsRefreshed": result["recordsRefreshed"],
        "recordsWithErrors": result["recordsWithErrors"],
        "localWritesPerformed": result["localWritesPerformed"],
        "externalWritesPerformed": False,
        "messageContentStored": False,
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
    }


def compact(value: Any) -> str:
    return " ".join(str(value or "").replace("\n", " ").split()).strip()


def first_line(value: str) -> str:
    return value.strip().splitlines()[0] if value.strip() else ""


def safe_path_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return "[external-path]"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


if __name__ == "__main__":
    raise SystemExit(main())
