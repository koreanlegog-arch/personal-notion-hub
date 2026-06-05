#!/usr/bin/env python3
"""Smoke check for redacted PNH supervisor review summary export."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_MARKER = "synthetic-supervisor-review-private-marker"


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        evidence = temp_path / "dispatch_evidence_summary.json"
        out = temp_path / "supervisor_review_summary.md"
        evidence.write_text(
            json.dumps(
                {
                    "dispatchEvidenceSummary": True,
                    "totalRecords": 2,
                    "includedRecords": 2,
                    "readyForSupervisorReview": 1,
                    "blockedOrFailed": 1,
                    "averageEvidenceCompleteness": 67,
                    "privateValuesPrinted": False,
                    "records": [
                        {
                            "packetId": "capture-review-smoke-001",
                            "githubIssueNumber": 7,
                            "githubIssueSet": True,
                            "discordThreadId": "1234567890",
                            "discordThreadSet": True,
                            "workerSessionId": "worker-review-smoke-001",
                            "workerStatus": "done",
                            "workerResultSet": True,
                            "workerEvidenceRefSet": True,
                            "taskStatus": "worker_done",
                            "evidenceCompleteness": 100,
                            "missingEvidence": [],
                            "nextAction": "summarize_worker_result_for_supervisor_review",
                            "updatedAt": "2026-06-05T00:00:00+00:00",
                            "privateNote": PRIVATE_MARKER,
                        },
                        {
                            "packetId": "capture-review-smoke-002",
                            "taskStatus": "worker_failed",
                            "evidenceCompleteness": 33,
                            "missingEvidence": ["github_issue", "discord_thread"],
                            "nextAction": "review_worker_evidence_and_retry_or_mark_blocked",
                            "privateNote": PRIVATE_MARKER,
                        },
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_supervisor_review_summary.py"),
                "--evidence",
                str(evidence),
                "--out",
                str(out),
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert_true(result.returncode == 0, f"supervisor_review_summary_failed={result.stderr.strip()}")
        combined = result.stdout + out.read_text(encoding="utf-8")
        assert_true(PRIVATE_MARKER not in combined, "private_marker_leaked=true")
        assert_true("pnhSupervisorReviewSummary" in result.stdout, "summary_flag_missing=true")
        assert_true("worker done records: 1" in combined, "worker_done_count_missing=true")
        assert_true("complete review ready: 1" in combined, "complete_review_ready_missing=true")
        assert_true("needs follow-up: 1" in combined, "needs_follow_up_missing=true")
        assert_true("capture-review-smoke-001" in combined, "record_missing=true")
        assert_true("Confirm the linked GitHub Issue" in combined, "supervisor_check_missing=true")

    print("pnh_supervisor_review_summary_smoke_check_pass=true")
    print("private_values_printed=false")
    return 0


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())
