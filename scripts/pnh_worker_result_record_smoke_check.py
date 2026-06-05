#!/usr/bin/env python3
"""Smoke check for redacted PNH worker result metadata recording."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_MARKER = "synthetic-worker-private-marker"


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        state = temp_path / "state.json"
        out = temp_path / "worker_result_plan.json"
        state.write_text(
            json.dumps(
                {
                    "capture-worker-smoke-001": {
                        "githubIssueNumber": 17,
                        "githubIssueUrl": "https://github.com/example/private/issues/17",
                        "discordThreadId": "1234567890",
                        "privateNote": PRIVATE_MARKER,
                        "updatedAt": "2026-06-05T00:00:00+00:00",
                    }
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        dry_run = run_record(state, out)
        assert_true(dry_run.returncode == 0, f"worker_result_dry_run_failed={dry_run.stderr.strip()}")
        combined = dry_run.stdout + out.read_text(encoding="utf-8")
        assert_true(PRIVATE_MARKER not in combined, "private_marker_leaked=true")
        plan = json.loads(out.read_text(encoding="utf-8"))
        assert_true(plan["writesPerformed"] is False, "dry_run_performed_write=true")
        assert_true(plan["privateValuesPrinted"] is False, "private_values_printed=true")
        assert_true(plan["planned"]["workerResultSet"] is True, "worker_result_plan_missing=true")

        apply = run_record(state, out, apply=True)
        assert_true(apply.returncode == 0, f"worker_result_apply_failed={apply.stderr.strip()}")
        assert_true(PRIVATE_MARKER not in apply.stdout, "private_marker_leaked_on_apply=true")
        payload = json.loads(state.read_text(encoding="utf-8"))
        record = payload["capture-worker-smoke-001"]
        assert_true(record["workerSessionId"] == "worker-session-smoke-001", "worker_session_not_saved=true")
        assert_true(record["workerStatus"] == "done", "worker_status_not_saved=true")
        assert_true(record["privateNote"] == PRIVATE_MARKER, "existing_private_metadata_lost=true")

    print("pnh_worker_result_record_smoke_check_pass=true")
    print("private_values_printed=false")
    return 0


def run_record(state: Path, out: Path, *, apply: bool = False) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(ROOT / "scripts" / "pnh_worker_result_record.py"),
        "--packet-id",
        "capture-worker-smoke-001",
        "--worker-session-id",
        "worker-session-smoke-001",
        "--status",
        "done",
        "--evidence-ref",
        "ops/runs/PNH-WORKER-SMOKE/summary.json",
        "--state-file",
        str(state),
        "--out",
        str(out),
    ]
    if apply:
        command.append("--apply")
    return subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())
