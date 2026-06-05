#!/usr/bin/env python3
"""Smoke check for unattended dispatch pilot dry-run and gate behavior."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        queue = temp_path / "queue.json"
        out_dir = temp_path / "run"
        queue.write_text(
            json.dumps(
                {
                    "pnhUnattendedDispatchQueuePlan": True,
                    "mode": "dry-run",
                    "externalWritesPerformed": False,
                    "policy": {"maxJobsPerRun": 1, "maxExternalWritesPerHour": 3, "cooldownMinutes": 10},
                    "queued": [{"captureId": "capture-smoke-001", "commandType": "project_brief"}],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        dry_run = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_unattended_dispatch_pilot.py"),
                "--queue-plan",
                str(queue),
                "--run-dir",
                str(out_dir),
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert_true(dry_run.returncode == 0, f"pilot_dry_run_failed={dry_run.stderr.strip()}")
        payload = json.loads((out_dir / "pilot_result.json").read_text(encoding="utf-8"))
        assert_true(payload["mode"] == "dry-run", "dry_run_mode_missing=true")
        assert_true(payload["externalWritesPerformed"] is False, "dry_run_performed_write=true")

        blocked = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_unattended_dispatch_pilot.py"),
                "--queue-plan",
                str(queue),
                "--run-dir",
                str(out_dir / "blocked"),
                "--apply",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert_true(blocked.returncode == 2, "apply_without_approval_allowed=true")
        assert_true("approve-unattended-pilot" in blocked.stderr, "approval_gate_message_missing=true")

    print("pnh_unattended_dispatch_pilot_smoke_check_pass=true")
    print("external_writes_performed=false")
    print("private_values_printed=false")
    return 0


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())
