#!/usr/bin/env python3
"""Smoke check for unattended dispatch readiness assessment."""

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
        reconciliation = temp_path / "reconcile.json"
        discord = temp_path / "discord.json"
        out = temp_path / "readiness.json"
        queue.write_text(
            json.dumps(
                {
                    "pnhUnattendedDispatchQueuePlan": True,
                    "mode": "dry-run",
                    "policy": {"maxJobsPerRun": 1, "maxExternalWritesPerHour": 3, "cooldownMinutes": 10},
                }
            ),
            encoding="utf-8",
        )
        reconciliation.write_text(json.dumps({"plannedExternalWrites": []}), encoding="utf-8")
        discord.write_text(
            json.dumps({"discordThreadStatusRefresh": True, "messageContentStored": False}), encoding="utf-8"
        )
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_unattended_dispatch_readiness.py"),
                "--queue-plan",
                str(queue),
                "--reconciliation-json",
                str(reconciliation),
                "--discord-refresh-json",
                str(discord),
                "--out",
                str(out),
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert_true(result.returncode == 0, f"readiness_failed={result.stderr.strip()}")
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert_true(payload["pnhUnattendedDispatchReadiness"] is True, "readiness_flag_missing=true")
        assert_true(payload["activationGate"]["required"] is False, "delegated_gate_not_reflected=true")
        assert_true(payload["activationGate"]["name"] == "project_AGENTS_bounded_dispatch_delegation", "delegation_scope_missing=true")
        assert_true(payload["externalWritesPerformed"] is False, "external_write_performed=true")

        reconciliation.write_text(
            json.dumps({"plannedExternalWrites": [{"system": "github", "operation": "replace_dispatch_status_labels"}]}),
            encoding="utf-8",
        )
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_unattended_dispatch_readiness.py"),
                "--queue-plan",
                str(queue),
                "--reconciliation-json",
                str(reconciliation),
                "--discord-refresh-json",
                str(discord),
                "--out",
                str(out),
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert_true(result.returncode == 0, f"readiness_pending_write_run_failed={result.stderr.strip()}")
        payload = json.loads(out.read_text(encoding="utf-8"))
        failed_names = {item["name"] for item in payload["failedChecks"]}
        assert_true("no_pending_external_reconciliation" in failed_names, "pending_external_write_not_detected=true")

    print("pnh_unattended_dispatch_readiness_smoke_check_pass=true")
    print("external_writes_performed=false")
    print("private_values_printed=false")
    return 0


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())
