#!/usr/bin/env python3
"""Send metadata-only PNH automation status to an owner-only channel."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "ops" / "runs" / "PNH-REMOTE-STATUS-NOTIFY-20260606" / "remote_status_notify.json"
DEFAULT_OPENCLAW_ENV = Path.home() / ".config" / "openclaw" / "openclaw-gateway.env"


class RemoteStatusNotifyError(ValueError):
    """Raised when status notification cannot safely run."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Notify owner of PNH status without private content.")
    parser.add_argument("--owner-target", default=os.environ.get("PNH_OWNER_DISCORD_TARGET", ""), help="OpenClaw owner target, e.g. user:<discord-user-id>.")
    parser.add_argument("--delivery", default="discord-dm", choices=["discord-dm"], help="Notification channel.")
    parser.add_argument("--openclaw-env", default=str(DEFAULT_OPENCLAW_ENV), help="OpenClaw env file.")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Evidence JSON.")
    parser.add_argument("--allow-channel-target", action="store_true", help="Allow channel:<id> for a locked approval/status channel.")
    parser.add_argument("--apply", action="store_true", help="Send notification.")
    parser.add_argument("--approve-owner-dm", action="store_true", help="Required with --apply.")
    args = parser.parse_args()

    try:
        status = collect_status()
        result = build_or_apply(args, status)
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, RemoteStatusNotifyError) as exc:
        print(f"pnh_remote_status_notify=false error={exc}", file=sys.stderr)
        return 2
    print(json.dumps(redact_stdout(result, out_path), ensure_ascii=False, sort_keys=True))
    return 0


def collect_status() -> dict[str, Any]:
    return {
        "privateInbox": run_json(["python3", "scripts/private_inbox_status.py"]),
        "dispatchState": run_json(["python3", "scripts/pnh_dispatch_state_status.py"]),
        "evidence": run_json(["python3", "scripts/pnh_dispatch_evidence_summary.py"]),
        "completion": run_json(["python3", "scripts/pnh_assistant_mvp_completion_audit.py"]),
        "queue": run_json(["python3", "scripts/pnh_unattended_dispatch_queue_plan.py"]),
    }


def run_json(command: list[str]) -> dict[str, Any]:
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=60, check=False)
    if result.returncode != 0:
        return {"ok": False, "returnCode": result.returncode, "stderrBytes": len(result.stderr.encode("utf-8"))}
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"ok": False, "returnCode": result.returncode, "stdoutBytes": len(result.stdout.encode("utf-8"))}
    return payload if isinstance(payload, dict) else {}


def build_or_apply(args: argparse.Namespace, status: dict[str, Any]) -> dict[str, Any]:
    target = str(args.owner_target or "").strip()
    validate_target(target, allow_channel=args.allow_channel_target)
    message = build_message(status)
    result: dict[str, Any] = {
        "pnhRemoteStatusNotify": True,
        "mode": "apply" if args.apply else "dry-run",
        "ownerTargetSet": bool(target),
        "delivery": args.delivery,
        "messageLength": len(message),
        "notificationDelivered": False,
        "externalWritesPerformed": False,
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "messageContentStored": False,
        "status": status_summary(status),
    }
    if not args.apply:
        return result
    if not args.approve_owner_dm:
        raise RemoteStatusNotifyError("--apply requires --approve-owner-dm")
    completed = run_openclaw_message(target, message, Path(args.openclaw_env))
    result.update(
        {
            "notificationDelivered": completed.returncode == 0,
            "externalWritesPerformed": completed.returncode == 0,
            "returnCode": completed.returncode,
            "stdoutBytes": len(completed.stdout.encode("utf-8")),
            "stderrBytes": len(completed.stderr.encode("utf-8")),
        }
    )
    if completed.returncode != 0:
        raise RemoteStatusNotifyError(f"status DM delivery failed: {first_line(completed.stderr) or first_line(completed.stdout)}")
    return result


def build_message(status: dict[str, Any]) -> str:
    summary = status_summary(status)
    return "\n".join(
        [
            "PNH automation status",
            f"Private inbox: {summary['totalCaptures']} captures, plaintext rows {summary['plaintextRows']}",
            f"Dispatch: {summary['dispatchRecords']} records, worker results {summary['workerResults']}",
            f"Evidence: {summary['averageEvidenceCompleteness']}% average, blocked/failed {summary['blockedOrFailed']}",
            f"Queue: {summary['queuedCount']} queued",
            f"Completion: {summary['completionPercent']}% {summary['completionVerdict']}",
            "Raw private command bodies and secret values were not included.",
        ]
    )


def status_summary(status: dict[str, Any]) -> dict[str, Any]:
    inbox = status.get("privateInbox", {}).get("privateInbox", {})
    dispatch = status.get("dispatchState", {})
    evidence = status.get("evidence", {})
    completion = status.get("completion", {})
    queue = status.get("queue", {})
    storage = inbox.get("byStorageMode", {})
    return {
        "totalCaptures": int(inbox.get("totalCaptures", 0) or 0),
        "plaintextRows": int(storage.get("plaintext-inbox", 0) or 0),
        "dispatchRecords": int(dispatch.get("totalRecords", 0) or 0),
        "workerResults": int(dispatch.get("workerResults", 0) or 0),
        "averageEvidenceCompleteness": int(evidence.get("averageEvidenceCompleteness", 0) or 0),
        "blockedOrFailed": int(evidence.get("blockedOrFailed", 0) or 0),
        "queuedCount": int(queue.get("queuedCount", 0) or 0),
        "completionPercent": float(completion.get("completionPercent", 0) or 0),
        "completionVerdict": str(completion.get("verdict", "")),
    }


def validate_target(target: str, *, allow_channel: bool) -> None:
    if not target:
        raise RemoteStatusNotifyError("owner target is required")
    if target.startswith("user:"):
        return
    if allow_channel and target.startswith("channel:"):
        return
    raise RemoteStatusNotifyError("owner target must be user:<id> unless --allow-channel-target is used")


def run_openclaw_message(target: str, message: str, openclaw_env: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(read_env_file(openclaw_env))
    return subprocess.run(
        ["openclaw", "message", "send", "--channel", "discord", "--target", target, "--message", message, "--json"],
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
        "pnhRemoteStatusNotify": True,
        "mode": result["mode"],
        "out": safe_path_label(out_path),
        "ownerTargetSet": result["ownerTargetSet"],
        "notificationDelivered": result["notificationDelivered"],
        "externalWritesPerformed": result["externalWritesPerformed"],
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
