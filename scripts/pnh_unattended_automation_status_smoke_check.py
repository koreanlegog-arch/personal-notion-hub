#!/usr/bin/env python3
"""Smoke check for bounded unattended automation status summary."""

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
        queue = temp / "queue.json"
        readiness = temp / "readiness.json"
        retry = temp / "retry.json"
        out = temp / "status.json"
        queue.write_text(
            json.dumps(
                {
                    "pnhUnattendedDispatchQueuePlan": True,
                    "queuedCount": 1,
                    "skippedCount": 2,
                    "cooldownActive": False,
                    "remainingExternalWriteCapacity1h": 3,
                    "queueActivationGateRequired": False,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        readiness.write_text(
            json.dumps(
                {
                    "pnhUnattendedDispatchReadiness": True,
                    "verdict": "ready_for_delegated_bounded_pilot",
                    "failedChecks": [],
                    "activationGate": {"required": False},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        retry.write_text(
            json.dumps({"pnhUnattendedRetryBackoff": True, "retryCandidates": []}, ensure_ascii=False),
            encoding="utf-8",
        )
        result = run_status(queue, readiness, retry, out)
        assert_true(result.returncode == 0, result.stderr)
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert_true(payload["decision"] == "ready_to_run_bounded_pilot", "queued_decision_wrong=true")
        assert_true(payload["safety"]["messageContentStored"] is False, "message_content_flag_wrong=true")

        queue.write_text(json.dumps({**json.loads(queue.read_text(encoding="utf-8")), "queuedCount": 0}), encoding="utf-8")
        result = run_status(queue, readiness, retry, out)
        assert_true(result.returncode == 0, result.stderr)
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert_true(payload["decision"] == "idle_ready", "idle_decision_wrong=true")

        readiness.write_text(
            json.dumps({"verdict": "not_ready", "failedChecks": [{"name": "x"}], "activationGate": {"required": False}}),
            encoding="utf-8",
        )
        result = run_status(queue, readiness, retry, out)
        assert_true(result.returncode == 0, result.stderr)
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert_true(payload["decision"] == "hold_for_readiness", "hold_decision_wrong=true")

    print("pnh_unattended_automation_status_smoke_check_pass=true")
    print("private_values_printed=false")
    return 0


def run_status(queue: Path, readiness: Path, retry: Path, out: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "pnh_unattended_automation_status.py"),
            "--queue-plan",
            str(queue),
            "--readiness-json",
            str(readiness),
            "--retry-json",
            str(retry),
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())
