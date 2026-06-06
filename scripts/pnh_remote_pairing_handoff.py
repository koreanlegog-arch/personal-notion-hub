#!/usr/bin/env python3
"""Deliver the current browser pairing code through an owner-only channel.

The event file is expected to live under ignored local storage. The pairing code
is delivered only to the requested owner target and is never printed or written
to tracked evidence.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVENT = ROOT / "companion" / "private" / "pairing_handoff.json"
DEFAULT_OUT = ROOT / "ops" / "runs" / "PNH-REMOTE-PAIRING-HANDOFF-20260606" / "pairing_handoff.json"
DEFAULT_OPENCLAW_ENV = Path.home() / ".config" / "openclaw" / "openclaw-gateway.env"


class PairingHandoffError(ValueError):
    """Raised when pairing handoff is unavailable or unsafe."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Send a one-time PNH pairing code to an owner-only target.")
    parser.add_argument("--event-file", default=str(DEFAULT_EVENT), help="Ignored local pairing handoff event JSON.")
    parser.add_argument("--delivery", default="dry-run", choices=["dry-run", "discord-dm"], help="Delivery channel.")
    parser.add_argument("--owner-target", default=os.environ.get("PNH_OWNER_DISCORD_TARGET", ""), help="OpenClaw owner target, e.g. user:<discord-user-id>.")
    parser.add_argument("--openclaw-env", default=str(DEFAULT_OPENCLAW_ENV), help="OpenClaw env file.")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Redacted evidence output JSON.")
    parser.add_argument("--allow-channel-target", action="store_true", help="Allow channel:<id> instead of owner DM.")
    parser.add_argument("--apply", action="store_true", help="Send the handoff message.")
    parser.add_argument("--approve-owner-dm", action="store_true", help="Required with --apply.")
    args = parser.parse_args()

    try:
        event = load_event(Path(args.event_file))
        result = build_or_apply(args, event)
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, PairingHandoffError) as exc:
        print(f"pnh_remote_pairing_handoff=false error={exc}", file=sys.stderr)
        return 2
    print(json.dumps(redact_stdout(result, out_path), ensure_ascii=False, sort_keys=True))
    return 0


def load_event(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise PairingHandoffError("pairing handoff event file is missing")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PairingHandoffError("pairing handoff event JSON is invalid") from exc
    if not isinstance(payload, dict) or not payload.get("pnhPairingHandoff"):
        raise PairingHandoffError("pairing handoff event is invalid")
    if payload.get("status") != "issued":
        raise PairingHandoffError("pairing code is not in issued state")
    code = str(payload.get("pairingCode") or "")
    if len(code) < 12:
        raise PairingHandoffError("pairing code is missing or too short")
    return payload


def build_or_apply(args: argparse.Namespace, event: dict[str, Any]) -> dict[str, Any]:
    target = str(args.owner_target or "").strip()
    validate_target(target, allow_channel=args.allow_channel_target)
    message = build_message(event)
    result: dict[str, Any] = {
        "pnhRemotePairingHandoff": True,
        "mode": "apply" if args.apply else "dry-run",
        "delivery": args.delivery,
        "ownerTargetSet": bool(target),
        "ownerTargetKind": target.split(":", 1)[0] if ":" in target else "",
        "pairingCodeDelivered": False,
        "pairingCodePrinted": False,
        "pairingCodeStoredInEvidence": False,
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "eventStatus": event.get("status", ""),
        "ttlSeconds": int(event.get("ttlSeconds", 0) or 0),
        "messageLength": len(message),
    }
    if not args.apply:
        return result
    if args.delivery != "discord-dm":
        raise PairingHandoffError("apply currently supports discord-dm delivery only")
    if not args.approve_owner_dm:
        raise PairingHandoffError("--apply requires --approve-owner-dm")
    completed = run_openclaw_message(target, message, Path(args.openclaw_env))
    result.update(
        {
            "pairingCodeDelivered": completed.returncode == 0,
            "returnCode": completed.returncode,
            "stdoutBytes": len(completed.stdout.encode("utf-8")),
            "stderrBytes": len(completed.stderr.encode("utf-8")),
        }
    )
    if completed.returncode != 0:
        raise PairingHandoffError(f"owner DM delivery failed: {first_line(completed.stderr) or first_line(completed.stdout)}")
    return result


def validate_target(target: str, *, allow_channel: bool) -> None:
    if not target:
        raise PairingHandoffError("owner target is required")
    if target.startswith("user:"):
        return
    if allow_channel and target.startswith("channel:"):
        return
    raise PairingHandoffError("owner target must be user:<id> unless --allow-channel-target is used")


def build_message(event: dict[str, Any]) -> str:
    code = str(event.get("pairingCode") or "")
    ttl = int(event.get("ttlSeconds", 0) or 0)
    return (
        "PNH owner browser pairing code\n"
        f"Code: {code}\n"
        f"TTL seconds: {ttl}\n"
        "Use this only in the owner phone browser. Do not paste it into chat, docs, screenshots, or Git."
    )


def run_openclaw_message(target: str, message: str, openclaw_env: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(read_env_file(openclaw_env))
    return subprocess.run(
        [
            "openclaw",
            "message",
            "send",
            "--channel",
            "discord",
            "--target",
            target,
            "--message",
            message,
            "--json",
        ],
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
        env=env,
    )


def read_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    env: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def redact_stdout(result: dict[str, Any], out_path: Path) -> dict[str, Any]:
    return {
        "pnhRemotePairingHandoff": True,
        "mode": result["mode"],
        "delivery": result["delivery"],
        "out": safe_path_label(out_path),
        "ownerTargetSet": result["ownerTargetSet"],
        "pairingCodeDelivered": result["pairingCodeDelivered"],
        "pairingCodePrinted": False,
        "pairingCodeStoredInEvidence": False,
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
    }


def first_line(value: str) -> str:
    return value.strip().splitlines()[0] if value.strip() else ""


def safe_path_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return "[external-path]"


if __name__ == "__main__":
    raise SystemExit(main())
