"""Guarded runner for the PNH single command packet wrapper."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
APPLY_CONFIRMATION = "RUN_EXTERNAL_WRITES_AND_WORKER"
APPLY_ENV = "PNH_BROWSER_SINGLE_PACKET_APPLY_ENABLED"


class SingleCommandPacketRunError(ValueError):
    """Raised when a browser-triggered wrapper run is not allowed or fails."""

    def __init__(self, code: str, *, status_code: int = 400) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code


def run_single_command_packet_from_browser(
    *,
    mode: str,
    confirm_apply: str = "",
    timeout: int | None = None,
    extra_args: list[str] | None = None,
) -> dict[str, Any]:
    normalized_mode = str(mode or "dry-run").strip().lower()
    if normalized_mode not in {"dry-run", "apply"}:
        raise SingleCommandPacketRunError("invalid_single_command_packet_mode")
    if normalized_mode == "apply" and not browser_apply_enabled(confirm_apply):
        raise SingleCommandPacketRunError("browser_apply_not_enabled", status_code=403)

    run_id = f"PNH-COMMAND-PACKET-BROWSER-{normalized_mode.upper().replace('-', '')}-{utc_stamp()}"
    command = [
        sys.executable,
        str(ROOT / "scripts" / "pnh_single_command_packet.py"),
        "--run-id",
        run_id,
    ]
    if extra_args:
        command.extend(extra_args)
    if normalized_mode == "apply":
        command.append("--apply")

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout or (720 if normalized_mode == "apply" else 180),
            check=False,
            cwd=ROOT,
        )
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "mode": normalized_mode,
            "runId": run_id,
            "returnCode": -1,
            "error": "single_command_packet_run_timeout",
            "stdoutBytes": 0,
            "stderrBytes": 0,
            "externalWritesPerformed": False,
            "workerRunPerformed": False,
            "privateValuesPrinted": False,
            "rawPrivateBodyRead": False,
        }
    payload = parse_redacted_stdout(result.stdout)
    if result.returncode != 0:
        return {
            "ok": False,
            "mode": normalized_mode,
            "runId": run_id,
            "returnCode": result.returncode,
            "error": "single_command_packet_run_failed",
            "message": first_line(result.stderr) or first_line(result.stdout),
            "stdoutBytes": len(result.stdout.encode("utf-8")),
            "stderrBytes": len(result.stderr.encode("utf-8")),
            "externalWritesPerformed": False,
            "workerRunPerformed": False,
            "privateValuesPrinted": False,
            "rawPrivateBodyRead": False,
        }

    return {
        "ok": True,
        "mode": normalized_mode,
        "runId": run_id,
        "returnCode": result.returncode,
        "summary": payload,
        "stdoutBytes": len(result.stdout.encode("utf-8")),
        "stderrBytes": len(result.stderr.encode("utf-8")),
        "externalWritesPerformed": bool(payload.get("externalWritesPerformed")),
        "workerRunPerformed": bool(payload.get("workerRunPerformed")),
        "privateValuesPrinted": False,
        "rawPrivateBodyRead": False,
    }


def browser_apply_enabled(confirm_apply: str) -> bool:
    return os.environ.get(APPLY_ENV) == "1" and confirm_apply == APPLY_CONFIRMATION


def parse_redacted_stdout(stdout: str) -> dict[str, Any]:
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return {}


def first_line(value: str) -> str:
    return next((line.strip() for line in value.splitlines() if line.strip()), "")


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
