#!/usr/bin/env python3
"""Run the bounded PNH unattended command flow from a capture trigger.

This wrapper exists so the browser companion can request dispatch without the
owner typing follow-up terminal commands. It delegates actual dispatch and
worker capture to `pnh_single_command_packet.py` and records metadata-only
evidence. Raw private command bodies are never read by this script.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN_DIR = ROOT / "companion" / "private" / "scheduler" / "jobs" / "unattended_orchestrator"
DEFAULT_OPENCLAW_ENV = Path.home() / ".config" / "openclaw" / "openclaw-gateway.env"
SECRET_SCAN_RE = re.compile(
    r"OPENCLAW_GATEWAY_TOKEN|DISCORD_BOT_TOKEN|GITHUB_TOKEN=|Bearer [A-Za-z0-9_\-]+|"
    r"gho_[A-Za-z0-9_]+|sk-[A-Za-z0-9]|pnh_odc_[A-Za-z0-9_\-]+|password\s*[=:]|secret\s*[=:]",
    re.IGNORECASE,
)


class UnattendedOrchestratorError(ValueError):
    """Raised when unattended orchestration cannot safely continue."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one metadata-safe PNH unattended dispatch cycle.")
    parser.add_argument("--trigger-capture-id", default="", help="Capture ID that triggered this cycle.")
    parser.add_argument("--run-dir", default=str(DEFAULT_RUN_DIR), help="Evidence directory.")
    parser.add_argument("--db", default="", help="Private inbox DB override.")
    parser.add_argument("--state-file", default="", help="Dispatch state override.")
    parser.add_argument("--history-json", default="", help="Dispatch history override.")
    parser.add_argument("--openclaw-env", default=str(DEFAULT_OPENCLAW_ENV), help="OpenClaw env file.")
    parser.add_argument("--max-jobs-per-run", type=int, default=1, help="Max queued jobs this cycle.")
    parser.add_argument("--max-external-writes-per-hour", type=int, default=3, help="Hourly external write guardrail.")
    parser.add_argument("--cooldown-minutes", type=int, default=10, help="Dispatch cooldown guardrail.")
    parser.add_argument("--notify-owner", action="store_true", help="Send metadata-only owner status after the cycle.")
    parser.add_argument("--owner-target", default=os.environ.get("PNH_OWNER_DISCORD_TARGET", ""), help="OpenClaw target such as user:<id>.")
    parser.add_argument("--apply", action="store_true", help="Run the bounded dispatch/worker workflow.")
    parser.add_argument("--approve-unattended-orchestrator", action="store_true", help="Required with --apply.")
    args = parser.parse_args()

    run_dir = safe_run_dir(Path(args.run_dir), compact(args.trigger_capture_id))
    commands_run: list[dict[str, Any]] = []
    try:
        if args.apply and not args.approve_unattended_orchestrator:
            raise UnattendedOrchestratorError("--apply requires --approve-unattended-orchestrator")
        run_dir.mkdir(parents=True, exist_ok=True)
        result = run_cycle(args, run_dir, commands_run)
        write_outputs(run_dir, result, commands_run)
    except (OSError, UnattendedOrchestratorError) as exc:
        result = failure_result(args, run_dir, commands_run, str(exc))
        write_outputs(run_dir, result, commands_run)
        print(f"pnh_unattended_orchestrator=false error={redact_text(str(exc))}", file=sys.stderr)
        return 2
    print(json.dumps(redact_stdout(result), ensure_ascii=False, sort_keys=True))
    return 0


def run_cycle(args: argparse.Namespace, run_dir: Path, commands_run: list[dict[str, Any]]) -> dict[str, Any]:
    packet_dir = run_dir / "single_command_packet"
    command = [
        sys.executable,
        str(ROOT / "scripts" / "pnh_single_command_packet.py"),
        "--run-dir",
        str(packet_dir),
        "--openclaw-env",
        args.openclaw_env,
        "--max-jobs-per-run",
        str(args.max_jobs_per_run),
        "--max-external-writes-per-hour",
        str(args.max_external_writes_per_hour),
        "--cooldown-minutes",
        str(args.cooldown_minutes),
    ]
    if args.db:
        command.extend(["--db", args.db, "--allow-plaintext", "--allow-external-db"])
    if args.state_file:
        command.extend(["--state-file", args.state_file])
    if args.history_json:
        command.extend(["--history-json", args.history_json])
    if args.apply:
        command.append("--apply")
    run_command(command, "single_command_packet", commands_run, timeout=1200)
    summary = load_json_object(packet_dir / "single_command_packet_summary.json", "single command packet summary")

    notification: dict[str, Any] = {
        "requested": bool(args.notify_owner),
        "delivered": False,
        "reason": "owner_notification_not_requested",
    }
    if args.notify_owner:
        if not compact(args.owner_target):
            notification["reason"] = "owner_target_missing"
        else:
            notify_out = run_dir / "remote_status_notify.json"
            notify_command = [
                sys.executable,
                str(ROOT / "scripts" / "pnh_remote_status_notify.py"),
                "--owner-target",
                args.owner_target,
                "--out",
                str(notify_out),
            ]
            if args.apply:
                notify_command.extend(["--apply", "--approve-owner-dm"])
            run_command(notify_command, "remote_status_notify", commands_run, timeout=90)
            notify_result = load_json_object(notify_out, "remote status notify")
            notification = {
                "requested": True,
                "delivered": bool(notify_result.get("notificationDelivered")),
                "out": safe_path_label(notify_out),
            }

    return {
        "pnhUnattendedOrchestrator": True,
        "generatedAt": utc_now(),
        "mode": "apply" if args.apply else "dry-run",
        "triggerCaptureId": compact(args.trigger_capture_id),
        "runDir": safe_path_label(run_dir),
        "singleCommandPacket": {
            "out": safe_path_label(packet_dir / "single_command_packet_summary.json"),
            "selectedCaptureId": compact(summary.get("selectedCaptureId")),
            "queuedCount": int(summary.get("queuedCount", 0) or 0),
            "externalWritesPerformed": bool(summary.get("externalWritesPerformed")),
            "workerRunPerformed": bool(summary.get("workerRunPerformed")),
        },
        "ownerNotification": notification,
        "commandsRun": commands_run,
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "rawPrivateBodyRead": False,
    }


def run_command(command: list[str], step: str, commands_run: list[dict[str, Any]], *, timeout: int) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=timeout, check=False)
    entry = {
        "step": step,
        "command": redact_command(command),
        "returnCode": result.returncode,
        "stdoutBytes": len(result.stdout.encode("utf-8")),
        "stderrBytes": len(result.stderr.encode("utf-8")),
        "stdoutFirstLines": safe_output_excerpt(result.stdout),
        "stderrFirstLines": safe_output_excerpt(result.stderr),
    }
    commands_run.append(entry)
    if result.returncode != 0:
        raise UnattendedOrchestratorError(f"{step} failed: {first_line(result.stderr) or first_line(result.stdout)}")
    return result


def failure_result(args: argparse.Namespace, run_dir: Path, commands_run: list[dict[str, Any]], error: str) -> dict[str, Any]:
    return {
        "pnhUnattendedOrchestrator": True,
        "failed": True,
        "generatedAt": utc_now(),
        "mode": "apply" if args.apply else "dry-run",
        "triggerCaptureId": compact(args.trigger_capture_id),
        "runDir": safe_path_label(run_dir),
        "error": redact_text(error)[:500],
        "commandsRun": commands_run,
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "rawPrivateBodyRead": False,
    }


def write_outputs(run_dir: Path, result: dict[str, Any], commands_run: list[dict[str, Any]]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "unattended_orchestrator_summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Evidence Log: PNH Unattended Orchestrator",
        "",
        f"Date: {utc_now()}",
        f"Mode: `{result.get('mode', '')}`",
        f"Trigger capture: `{result.get('triggerCaptureId', '')}`",
        "",
        "## Result",
        "",
        f"- selected capture: `{result.get('singleCommandPacket', {}).get('selectedCaptureId', '')}`",
        f"- queued count: `{result.get('singleCommandPacket', {}).get('queuedCount', 0)}`",
        f"- external writes performed: `{str(bool(result.get('singleCommandPacket', {}).get('externalWritesPerformed'))).lower()}`",
        f"- worker run performed: `{str(bool(result.get('singleCommandPacket', {}).get('workerRunPerformed'))).lower()}`",
        f"- private values printed: `false`",
        f"- raw private body read: `false`",
        "",
        "## Commands",
        "",
    ]
    for item in commands_run:
        lines.append(f"- `{item['step']}` returnCode=`{item['returnCode']}`")
    (run_dir / "evidence_log.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_json_object(path: Path, label: str) -> dict[str, Any]:
    if not path.exists():
        raise UnattendedOrchestratorError(f"{label} missing")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise UnattendedOrchestratorError(f"{label} invalid JSON") from exc
    if not isinstance(payload, dict):
        raise UnattendedOrchestratorError(f"{label} must be an object")
    return payload


def safe_run_dir(base: Path, trigger_capture_id: str) -> Path:
    path = base if base.is_absolute() else ROOT / base
    if trigger_capture_id and path == DEFAULT_RUN_DIR:
        path = path / trigger_capture_id
    return unique_dir(path)


def unique_dir(base: Path) -> Path:
    if not base.exists():
        return base
    for index in range(2, 100):
        candidate = Path(f"{base}-{index}")
        if not candidate.exists():
            return candidate
    raise UnattendedOrchestratorError("could not allocate run directory")


def redact_command(command: list[str]) -> list[str]:
    redacted: list[str] = []
    for index, value in enumerate(command):
        previous = command[index - 1] if index else ""
        if previous in {"--owner-target", "--openclaw-env"}:
            redacted.append("[redacted]")
        else:
            redacted.append(redact_text(value))
    return redacted


def safe_output_excerpt(value: str, *, limit: int = 3) -> list[str]:
    lines = []
    for line in value.splitlines()[:limit]:
        lines.append(redact_text(line)[:300])
    return lines


def redact_stdout(result: dict[str, Any]) -> dict[str, Any]:
    packet = result.get("singleCommandPacket", {})
    return {
        "pnhUnattendedOrchestrator": True,
        "mode": result.get("mode", ""),
        "runDir": result.get("runDir", ""),
        "triggerCaptureId": result.get("triggerCaptureId", ""),
        "selectedCaptureId": packet.get("selectedCaptureId", ""),
        "queuedCount": packet.get("queuedCount", 0),
        "externalWritesPerformed": bool(packet.get("externalWritesPerformed")),
        "workerRunPerformed": bool(packet.get("workerRunPerformed")),
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "rawPrivateBodyRead": False,
    }


def redact_text(value: Any) -> str:
    return SECRET_SCAN_RE.sub("[redacted]", str(value))


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
