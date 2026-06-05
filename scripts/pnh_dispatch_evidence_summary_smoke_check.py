#!/usr/bin/env python3
"""Smoke check for redacted PNH dispatch evidence summary export."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_MARKER = "synthetic-evidence-summary-private-marker"


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        state = temp_path / "state.json"
        out = temp_path / "summary.json"
        state.write_text(
            json.dumps(
                {
                    "capture-summary-smoke-001": {
                        "githubIssueNumber": 19,
                        "githubIssueUrl": "https://github.com/example/private/issues/19",
                        "discordThreadId": "1234567890",
                        "workerSessionId": "worker-summary-smoke-001",
                        "workerStatus": "done",
                        "workerEvidenceRef": "ops/runs/PNH-WORKER-SUMMARY/summary.json",
                        "privateNote": PRIVATE_MARKER,
                        "updatedAt": "2026-06-05T00:00:00+00:00",
                    },
                    "capture-summary-smoke-002": {
                        "workerSessionId": "worker-summary-smoke-002",
                        "workerStatus": "failed",
                        "privateNote": PRIVATE_MARKER,
                        "updatedAt": "2026-06-05T00:00:01+00:00",
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_dispatch_evidence_summary.py"),
                "--state-file",
                str(state),
                "--out",
                str(out),
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert_true(result.returncode == 0, f"evidence_summary_failed={result.stderr.strip()}")
        combined = result.stdout + out.read_text(encoding="utf-8")
        assert_true(PRIVATE_MARKER not in combined, "private_marker_leaked=true")
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert_true(payload["dispatchEvidenceSummary"] is True, "summary_flag_missing=true")
        assert_true(payload["readyForSupervisorReview"] == 1, "ready_count_mismatch=true")
        assert_true(payload["blockedOrFailed"] == 1, "blocked_failed_count_mismatch=true")
        assert_true(payload["privateValuesPrinted"] is False, "private_values_printed=true")
        assert_true(payload["records"][0]["taskStatus"] == "worker_failed", "task_status_sort_or_mapping_failed=true")
        assert_true("missingEvidence" in payload["records"][0], "missing_evidence_missing=true")

    print("pnh_dispatch_evidence_summary_smoke_check_pass=true")
    print("private_values_printed=false")
    return 0


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())
