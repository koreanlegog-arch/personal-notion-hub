#!/usr/bin/env python3
"""Smoke check for PNH external reconciliation planning."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_MARKER = "synthetic-reconcile-private-marker"


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        state = temp_path / "state.json"
        refresh = temp_path / "refresh.json"
        out = temp_path / "plan.json"
        state.write_text(
            json.dumps(
                {
                    "capture-reconcile-smoke-001": {
                        "githubIssueNumber": 2,
                        "githubIssueState": "open",
                        "discordThreadId": "1512295718054793419",
                        "workerStatus": "done",
                        "workerEvidenceRef": "ops/runs/example/worker.json",
                        "privateNote": PRIVATE_MARKER,
                    }
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        refresh.write_text(
            json.dumps(
                {
                    "records": [
                        {
                            "packetId": "capture-reconcile-smoke-001",
                            "githubIssueNumber": "2",
                            "githubIssueState": "open",
                            "githubIssueLabels": ["pnh", "dispatch:not-dispatched"],
                        }
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_external_reconciliation_plan.py"),
                "--state-file",
                str(state),
                "--refresh-json",
                str(refresh),
                "--out",
                str(out),
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert_true(result.returncode == 0, f"reconciliation_plan_failed={result.stderr.strip()}")
        combined = result.stdout + out.read_text(encoding="utf-8")
        assert_true(PRIVATE_MARKER not in combined, "private_marker_leaked=true")
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert_true(payload["externalReconciliationPlan"] is True, "plan_flag_missing=true")
        assert_true(payload["externalWritesPerformed"] is False, "external_write_performed=true")
        assert_true(payload["approvalRequiredBeforeExternalWrite"] is True, "approval_gate_missing=true")
        assert_true(payload["plannedExternalWrites"][0]["operation"] == "replace_dispatch_status_labels", "label_plan_missing=true")

    print("pnh_external_reconciliation_plan_smoke_check_pass=true")
    print("private_values_printed=false")
    print("external_writes_performed=false")
    return 0


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())
