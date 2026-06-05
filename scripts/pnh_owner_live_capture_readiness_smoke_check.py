#!/usr/bin/env python3
"""Smoke check for owner live capture readiness output contracts."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        out_path = Path(temp_dir) / "readiness.json"
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_owner_live_capture_readiness.py"),
                "--out",
                str(out_path),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
        assert_true(result.returncode in {0, 2}, f"unexpected_return_code={result.returncode}")
        payload = json.loads(out_path.read_text(encoding="utf-8"))
        readiness = payload["ownerLiveCaptureReadiness"]
        stdout = json.loads(result.stdout)
        assert_true(stdout["ownerLiveCaptureReadiness"] is True, "stdout_flag_missing=true")
        assert_true(readiness["materialGateReached"] is True, "material_gate_missing=true")
        assert_true(readiness["privateValuesPrinted"] is False, "private_values_printed=true")
        assert_true(readiness["secretValuePrinted"] is False, "secret_value_printed=true")
        assert_true("commandsRun" in readiness and readiness["commandsRun"], "commands_missing=true")
        assert_true("pairing code" in readiness["materialGateReason"].lower(), "pairing_gate_reason_missing=true")

    print("pnh_owner_live_capture_readiness_smoke_check_pass=true")
    print("private_values_printed=false")
    print("secret_value_printed=false")
    return 0


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())
