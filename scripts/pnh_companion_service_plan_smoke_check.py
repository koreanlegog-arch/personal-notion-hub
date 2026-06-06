#!/usr/bin/env python3
"""Smoke check for PNH companion service plan."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "pnh_companion_service_plan.py")],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert_true(result.returncode == 0, result.stderr)
    payload = json.loads(result.stdout)
    assert_true(payload["pnhCompanionServicePlan"] is True, "companion_service_plan_flag_missing=true")
    assert_true(payload["browserBridgeEnabled"] is False, "browser_bridge_enabled_in_headless_service=true")
    assert_true(payload["pairingCodePrinted"] is False, "pairing_code_printed=true")
    assert_true("pnh_companion_runtime_server.sh" in payload["serviceText"], "runtime_script_missing=true")
    assert_true("--enable-browser-bridge" not in payload["serviceText"], "browser_bridge_flag_in_service=true")
    assert_true("WindowsPowerShell" in payload["serviceText"], "powershell_path_missing=true")
    print("pnh_companion_service_plan_smoke_check_pass=true")
    print("private_values_printed=false")
    return 0


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())
