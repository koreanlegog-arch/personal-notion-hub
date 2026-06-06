#!/usr/bin/env python3
"""Report PNH scheduler user-systemd service status without secret output."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SERVICE_NAME = "pnh-scheduler.service"
TIMER_NAME = "pnh-scheduler.timer"
RUNTIME_OUT = ROOT / "companion" / "private" / "scheduler" / "scheduler_tick.json"


def main() -> int:
    payload = {
        "pnhSchedulerServiceStatus": True,
        "systemctlUserAvailable": command_ok(["systemctl", "--user", "show-environment"]),
        "service": systemctl_state(SERVICE_NAME),
        "timer": systemctl_state(TIMER_NAME),
        "runtimeOut": safe_path_label(RUNTIME_OUT),
        "runtimeOutExists": RUNTIME_OUT.exists(),
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def systemctl_state(unit: str) -> dict[str, Any]:
    if not command_ok(["systemctl", "--user", "show-environment"]):
        return {"unit": unit, "available": False, "active": "unknown", "enabled": "unknown"}
    return {
        "unit": unit,
        "available": True,
        "active": command_output(["systemctl", "--user", "is-active", unit]),
        "enabled": command_output(["systemctl", "--user", "is-enabled", unit]),
    }


def command_ok(command: list[str]) -> bool:
    return subprocess.run(command, capture_output=True, text=True, check=False).returncode == 0


def command_output(command: list[str]) -> str:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    return (result.stdout or result.stderr).strip().splitlines()[0] if (result.stdout or result.stderr).strip() else "unknown"


def safe_path_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return "[external-path]"


if __name__ == "__main__":
    raise SystemExit(main())
