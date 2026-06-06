#!/usr/bin/env python3
"""Smoke check for bounded PNH scheduler loop."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_scheduler_loop.py"),
                "--iterations",
                "1",
                "--interval-seconds",
                "1",
                "--jobs",
                "adapter-status,live-adapter-status,retry-backoff",
                "--run-dir",
                str(temp / "runs"),
                "--lock-file",
                str(temp / "scheduler.lock"),
                "--runtime-dir",
                str(temp / "runtime"),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert_true(result.returncode == 0, result.stderr)
        payload = json.loads(result.stdout)
        assert_true(payload["pnhSchedulerLoop"] is True, "scheduler_loop_flag_missing=true")
        assert_true(payload["iterations"] == 1, "iteration_count_mismatch=true")
        assert_true(payload["externalWritesPerformed"] is False, "external_write_performed=true")

    print("pnh_scheduler_smoke_check_pass=true")
    print("private_values_printed=false")
    return 0


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())
