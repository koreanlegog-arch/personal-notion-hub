#!/usr/bin/env python3
"""Probe Discord/OpenClaw thread read-refresh capability safely.

Default mode inspects local CLI capability only. Optional live read is blocked
behind an explicit flag because it can read private Discord channel content.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "ops" / "runs" / "PNH-DISCORD-THREAD-READINESS-20260605" / "discord_thread_readiness_probe.json"


class DiscordThreadReadinessError(ValueError):
    """Raised when probe execution is invalid or unsafe."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe Discord/OpenClaw thread read-refresh readiness.")
    parser.add_argument("--thread-id", default="", help="Discord thread/channel id to read when live read is approved.")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output JSON path.")
    parser.add_argument("--openclaw-read", action="store_true", help="Perform a live read-only OpenClaw Discord read.")
    parser.add_argument("--approve-discord-read", action="store_true", help="Required with --openclaw-read.")
    parser.add_argument("--limit", type=int, default=5, help="Live read limit.")
    args = parser.parse_args()

    try:
        result = build_probe(args)
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, DiscordThreadReadinessError) as exc:
        print(f"pnh_discord_thread_readiness_probe=false error={exc}", file=sys.stderr)
        return 2
    print(json.dumps(redact_stdout(result, out_path), ensure_ascii=False, sort_keys=True))
    return 0


def build_probe(args: argparse.Namespace) -> dict[str, Any]:
    openclaw_path = shutil.which("openclaw") or ""
    commands = {
        "message_read": command_help(["openclaw", "message", "read", "--help"]) if openclaw_path else {"available": False},
        "message_search": command_help(["openclaw", "message", "search", "--help"]) if openclaw_path else {"available": False},
        "thread_list": command_help(["openclaw", "message", "thread", "list", "--help"]) if openclaw_path else {"available": False},
    }
    capability = {
        "openclawInstalled": bool(openclaw_path),
        "readCommandAvailable": commands["message_read"]["available"],
        "searchCommandAvailable": commands["message_search"]["available"],
        "threadListCommandAvailable": commands["thread_list"]["available"],
        "includeThreadSupported": "--include-thread" in commands["message_read"].get("helpText", ""),
        "jsonSupported": "--json" in commands["message_read"].get("helpText", ""),
        "threadListJsonSupported": "--json" in commands["thread_list"].get("helpText", ""),
    }
    live_read: dict[str, Any] = {
        "requested": bool(args.openclaw_read),
        "performed": False,
        "requiresApproval": True,
        "approvalReason": "Discord/OpenClaw read can expose private channel content even without writing.",
    }
    if args.openclaw_read:
        if not args.approve_discord_read:
            raise DiscordThreadReadinessError("--openclaw-read requires --approve-discord-read")
        if not args.thread_id.strip():
            raise DiscordThreadReadinessError("--thread-id is required for live read")
        live_read.update(run_live_read(args.thread_id.strip(), args.limit))
    return {
        "discordThreadReadinessProbe": True,
        "generatedAt": utc_now(),
        "mode": "live-read" if args.openclaw_read else "capability-only",
        "capability": capability,
        "commands": redact_help(commands),
        "recommendedNextStep": recommended_next_step(capability),
        "liveRead": live_read,
        "externalWritesPerformed": False,
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
    }


def command_help(command: list[str]) -> dict[str, Any]:
    result = subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)
    return {
        "available": result.returncode == 0,
        "returnCode": result.returncode,
        "helpText": result.stdout if result.returncode == 0 else "",
        "errorFirstLine": first_line(result.stderr),
    }


def redact_help(commands: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        name: {
            "available": value.get("available", False),
            "returnCode": value.get("returnCode", 1),
            "supportsJson": "--json" in value.get("helpText", ""),
            "supportsDryRun": "--dry-run" in value.get("helpText", ""),
        }
        for name, value in commands.items()
    }


def run_live_read(thread_id: str, limit: int) -> dict[str, Any]:
    bounded_limit = str(min(max(int(limit), 1), 25))
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
    )
    return {
        "performed": True,
        "returnCode": result.returncode,
        "stdoutBytes": len(result.stdout.encode("utf-8")),
        "stderrFirstLine": first_line(result.stderr),
        "contentPrintedInReport": False,
    }


def recommended_next_step(capability: dict[str, Any]) -> str:
    if not capability["openclawInstalled"]:
        return "install_or_restore_openclaw_before_discord_read_refresh"
    if capability["readCommandAvailable"] and capability["jsonSupported"]:
        return "implement_approval_gated_discord_thread_read_refresh"
    if capability["threadListCommandAvailable"] and capability["threadListJsonSupported"]:
        return "use_thread_list_as_metadata_only_fallback"
    return "keep_discord_thread_status_manual_until_stable_read_api_is_confirmed"


def redact_stdout(result: dict[str, Any], out_path: Path) -> dict[str, Any]:
    return {
        "discordThreadReadinessProbe": True,
        "mode": result["mode"],
        "out": safe_path_label(out_path),
        "readCommandAvailable": result["capability"]["readCommandAvailable"],
        "threadListCommandAvailable": result["capability"]["threadListCommandAvailable"],
        "recommendedNextStep": result["recommendedNextStep"],
        "liveReadPerformed": result["liveRead"]["performed"],
        "externalWritesPerformed": False,
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
    }


def safe_path_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return "[external-path]"


def first_line(value: str) -> str:
    return value.strip().splitlines()[0] if value.strip() else ""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


if __name__ == "__main__":
    raise SystemExit(main())
