#!/usr/bin/env python3
"""Run one approved PNH unattended dispatch pilot batch.

Dry-run is the default. Apply mode requires `--approve-unattended-pilot` and
uses the existing bounded queue plan. It creates external records only through
the already-gated dispatch job path and records rollback evidence.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE = ROOT / "ops" / "runs" / "PNH-UNATTENDED-DISPATCH-READINESS-20260605" / "queue_plan.json"
DEFAULT_RUN_DIR = ROOT / "ops" / "runs" / "PNH-UNATTENDED-DISPATCH-PILOT-20260605"
DEFAULT_STATE = ROOT / "companion" / "private" / "pnh_dispatch_state.json"
DEFAULT_HISTORY = ROOT / "companion" / "private" / "pnh_unattended_dispatch_history.json"
DEFAULT_LOCK = ROOT / "companion" / "private" / "pnh_unattended_dispatch.lock"
DEFAULT_REPO = "koreanlegog-arch/personal-notion-hub"
DEFAULT_DISCORD_TARGET = "channel:1511691320136306718"
SECRET_SCAN_PATTERN = re.compile(
    r"OPENCLAW_GATEWAY_TOKEN|DISCORD_BOT_TOKEN|GITHUB_TOKEN=|Bearer [A-Za-z0-9_.-]{12,}|"
    r"gh[opsu]_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9]|password\s*[=:]|secret\s*[=:]",
    re.IGNORECASE,
)


class PilotError(ValueError):
    """Raised when unattended pilot execution is unsafe or failed."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one approved PNH unattended dispatch pilot batch.")
    parser.add_argument("--queue-plan", default=str(DEFAULT_QUEUE), help="Queue plan JSON.")
    parser.add_argument("--run-dir", default=str(DEFAULT_RUN_DIR), help="Evidence directory.")
    parser.add_argument("--state-file", default=str(DEFAULT_STATE), help="Dispatch state JSON.")
    parser.add_argument("--history-json", default=str(DEFAULT_HISTORY), help="Unattended dispatch history JSON.")
    parser.add_argument("--lock-file", default=str(DEFAULT_LOCK), help="Single-writer lock file.")
    parser.add_argument("--repo", default=DEFAULT_REPO, help="GitHub owner/repo.")
    parser.add_argument("--discord-target", default=DEFAULT_DISCORD_TARGET, help="Discord target channel.")
    parser.add_argument("--apply", action="store_true", help="Run approved live pilot.")
    parser.add_argument("--approve-unattended-pilot", action="store_true", help="Required with --apply.")
    parser.add_argument("--detect-existing-github", action="store_true", help="Enable duplicate detection before issue creation.")
    args = parser.parse_args()

    lock_path = Path(args.lock_file)
    try:
        run_dir = Path(args.run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)
        queue = load_json_object(Path(args.queue_plan), "queue plan")
        validate_queue(queue)
        queued = queue.get("queued", [])
        if not queued:
            result = empty_result(args, run_dir, queue)
        elif args.apply:
            if not args.approve_unattended_pilot:
                raise PilotError("--apply requires --approve-unattended-pilot")
            acquire_lock(lock_path)
            result = apply_first(args, run_dir, queue, queued[0])
        else:
            result = dry_run_result(args, run_dir, queue, queued[0])
        out_path = run_dir / "pilot_result.json"
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, PilotError) as exc:
        print(f"pnh_unattended_dispatch_pilot=false error={exc}", file=sys.stderr)
        return 2
    finally:
        if args.apply:
            release_lock(lock_path)
    print(json.dumps(redact_stdout(result, run_dir / "pilot_result.json"), ensure_ascii=False, sort_keys=True))
    return 0


def validate_queue(queue: dict[str, Any]) -> None:
    if not queue.get("pnhUnattendedDispatchQueuePlan"):
        raise PilotError("queue plan is missing pnhUnattendedDispatchQueuePlan")
    if queue.get("mode") != "dry-run":
        raise PilotError("queue plan must be dry-run")
    if queue.get("externalWritesPerformed"):
        raise PilotError("queue plan unexpectedly performed external writes")


def dry_run_result(args: argparse.Namespace, run_dir: Path, queue: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    return {
        "pnhUnattendedDispatchPilot": True,
        "generatedAt": utc_now(),
        "mode": "dry-run",
        "selectedCaptureId": item.get("captureId", ""),
        "selectedCommandType": item.get("commandType", ""),
        "wouldApply": True,
        "approvalRequiredForApply": True,
        "externalWritesPerformed": False,
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "outputs": {"runDir": safe_path_label(run_dir)},
        "pilotLimits": queue.get("policy", {}),
    }


def empty_result(args: argparse.Namespace, run_dir: Path, queue: dict[str, Any]) -> dict[str, Any]:
    return {
        "pnhUnattendedDispatchPilot": True,
        "generatedAt": utc_now(),
        "mode": "apply" if args.apply else "dry-run",
        "selectedCaptureId": "",
        "externalWritesPerformed": False,
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "outputs": {"runDir": safe_path_label(run_dir)},
        "pilotLimits": queue.get("policy", {}),
        "message": "queue_empty",
    }


def apply_first(args: argparse.Namespace, run_dir: Path, queue: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    capture_id = str(item.get("captureId") or "").strip()
    if not capture_id:
        raise PilotError("queued capture id is missing")
    rollback_dir = run_dir / "rollback"
    rollback_dir.mkdir(parents=True, exist_ok=True)
    state_path = Path(args.state_file)
    snapshot_path = rollback_dir / "dispatch_state_before.json"
    snapshot_state(state_path, snapshot_path)
    dispatch_run_dir = run_dir / "dispatch"
    command = [
        sys.executable,
        str(ROOT / "scripts" / "pnh_auto_dispatch_from_inbox.py"),
        "--capture-id",
        capture_id,
        "--repo",
        args.repo,
        "--discord-target",
        args.discord_target,
        "--state-file",
        str(state_path),
        "--run-dir",
        str(dispatch_run_dir),
        "--apply",
        "--approve-live-dispatch",
        "--approve-external-write",
        "--approve-discord-dispatch",
    ]
    if args.detect_existing_github:
        command.append("--detect-existing-github")
    result = subprocess.run(command, capture_output=True, text=True, timeout=120, check=False)
    if result.returncode != 0:
        write_dispatch_failure(dispatch_run_dir, command, result)
        raise PilotError(f"pilot dispatch failed: {first_line(result.stderr) or first_line(result.stdout)}")
    summary = load_json_object(dispatch_run_dir / "auto_dispatch_summary.json", "auto dispatch summary")
    history_path = Path(args.history_json)
    history = load_json_object(history_path, "dispatch history", missing_ok=True)
    history.setdefault("events", []).append(
        {
            "at": utc_now(),
            "captureId": capture_id,
            "externalWrite": bool(summary.get("externalWritePerformed")),
            "writesPerformed": bool(summary.get("writesPerformed")),
            "runDir": safe_path_label(run_dir),
        }
    )
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.write_text(json.dumps(history, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "pnhUnattendedDispatchPilot": True,
        "generatedAt": utc_now(),
        "mode": "apply",
        "selectedCaptureId": capture_id,
        "selectedCommandType": item.get("commandType", ""),
        "externalWritesPerformed": bool(summary.get("externalWritePerformed")),
        "writesPerformed": bool(summary.get("writesPerformed")),
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "rollbackSnapshot": safe_path_label(snapshot_path),
        "dispatchSummary": summary,
        "outputs": {
            "runDir": safe_path_label(run_dir),
            "dispatchRunDir": safe_path_label(dispatch_run_dir),
            "history": safe_path_label(history_path),
        },
        "pilotLimits": queue.get("policy", {}),
    }


def acquire_lock(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise PilotError("unattended dispatch lock already exists") from exc
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(json.dumps({"pid": os.getpid(), "createdAt": utc_now()}, sort_keys=True) + "\n")


def release_lock(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def snapshot_state(source: Path, target: Path) -> None:
    if source.exists():
        shutil.copy2(source, target)
    else:
        target.write_text("{}\n", encoding="utf-8")


def write_dispatch_failure(run_dir: Path, command: list[str], result: subprocess.CompletedProcess[str]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "pnhUnattendedDispatchFailure": True,
        "generatedAt": utc_now(),
        "command": redact_command(command),
        "returnCode": result.returncode,
        "stdoutFirstLines": safe_output_excerpt(result.stdout),
        "stderrFirstLines": safe_output_excerpt(result.stderr),
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
    }
    (run_dir / "dispatch_failure.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def redact_command(command: list[str]) -> list[str]:
    return [safe_command_arg(item) for item in command]


def safe_command_arg(value: str) -> str:
    text = str(value)
    if text == sys.executable:
        return "python3"
    root_text = str(ROOT)
    if text.startswith(root_text + os.sep):
        return text[len(root_text) + 1 :]
    return text


def safe_output_excerpt(value: str) -> list[str]:
    lines = []
    for line in value.splitlines()[:12]:
        lines.append(SECRET_SCAN_PATTERN.sub("[redacted]", line)[:500])
    return lines


def load_json_object(path: Path, label: str, *, missing_ok: bool = False) -> dict[str, Any]:
    if not path.exists():
        if missing_ok:
            return {}
        raise PilotError(f"{label} is missing")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PilotError(f"{label} JSON is invalid: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise PilotError(f"{label} JSON must be an object")
    return payload


def redact_stdout(result: dict[str, Any], out_path: Path) -> dict[str, Any]:
    return {
        "pnhUnattendedDispatchPilot": True,
        "mode": result["mode"],
        "out": safe_path_label(out_path),
        "selectedCaptureId": result.get("selectedCaptureId", ""),
        "externalWritesPerformed": bool(result.get("externalWritesPerformed")),
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
