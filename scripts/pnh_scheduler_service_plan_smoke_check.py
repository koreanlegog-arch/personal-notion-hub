#!/usr/bin/env python3
"""Smoke check for PNH scheduler service planning."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "pnh_scheduler_service_plan.py"), "--interval-minutes", "5"],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert_true(result.returncode == 0, result.stderr)
    payload = json.loads(result.stdout)
    assert_true(payload["pnhSchedulerServicePlan"] is True, "service_plan_flag_missing=true")
    assert_true(payload["intervalMinutes"] == 5, "interval_minutes_failed=true")
    assert_true("pnh_scheduler_runtime_tick.sh" in payload["serviceText"], "runtime_tick_missing=true")
    assert_true("companion/private/scheduler/scheduler_tick.json" in payload["serviceText"], "runtime_out_missing=true")
    assert_true("companion/private/scheduler/jobs" in payload["serviceText"], "runtime_dir_missing=true")
    assert_true("OnUnitActiveSec=5min" in payload["timerText"], "timer_interval_missing=true")
    assert_true(payload["externalWritesPerformed"] is False, "external_write_performed=true")
    print("pnh_scheduler_service_plan_smoke_check_pass=true")
    print("private_values_printed=false")
    return 0


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())
