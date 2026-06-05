#!/usr/bin/env python3
"""Smoke check for metadata-only command packet status summaries."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.command_packet_status import build_command_packet_status  # noqa: E402


PRIVATE_TITLE = "synthetic-command-packet-status-private-title"
PRIVATE_BODY = "synthetic-command-packet-status-private-body"


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        runs_dir = temp_path / "ops" / "runs"
        run_dir = runs_dir / "PNH-COMMAND-PACKET-SMOKE"
        run_dir.mkdir(parents=True)
        (run_dir / "single_command_packet_summary.json").write_text(
            json.dumps(
                {
                    "pnhSingleCommandPacket": True,
                    "generatedAt": "2026-06-05T00:00:00+00:00",
                    "mode": "apply",
                    "runId": "PNH-COMMAND-PACKET-SMOKE",
                    "runDir": "ops/runs/PNH-COMMAND-PACKET-SMOKE",
                    "selectedCaptureId": "capture-status-smoke-001",
                    "queuedCount": 1,
                    "externalWritesPerformed": True,
                    "workerRunPerformed": True,
                    "pendingExternalWriteCount": 0,
                    "workerStatus": "done",
                    "workerSessionId": "pnh:capture-status-smoke-001:qa",
                    "privateValuesPrinted": False,
                    "rawPrivateBodyRead": False,
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        dispatch_state = {
            "capture-status-smoke-001": {
                "githubIssueNumber": 4,
                "githubIssueUrl": "https://github.example/issues/4",
                "githubIssueState": "open",
                "discordThreadId": "1512323845514596373",
                "workerSessionId": "pnh:capture-status-smoke-001:qa",
                "workerStatus": "done",
                "workerEvidenceRef": "ops/runs/worker/evidence.json",
                "updatedAt": "2026-06-05T00:00:01+00:00",
                "title": PRIVATE_TITLE,
                "body": PRIVATE_BODY,
            }
        }

        status = build_command_packet_status(dispatch_state, runs_dir=runs_dir)
        combined = json.dumps(status, ensure_ascii=False, sort_keys=True)
        assert_true(status["queueCount"] == 1, "queue_count_mismatch=true")
        assert_true(status["lastIssue"] == 4, "last_issue_mismatch=true")
        assert_true(status["lastWorkerStatus"] == "done", "last_worker_status_mismatch=true")
        assert_true(status["nextAction"] == "summarize_worker_result_for_supervisor_review", "next_action_mismatch=true")
        assert_true(status["stage"] == "review_ready", "stage_mismatch=true")
        assert_true(status["stageLabel"] == "Review ready", "stage_label_mismatch=true")
        assert_true([step["state"] for step in status["stageSteps"]] == ["done", "done", "done", "done", "done"], "stage_steps_mismatch=true")
        assert_true(status["readyForSupervisorReview"] == 1, "ready_review_mismatch=true")
        assert_true(status["privateValuesPrinted"] is False, "private_values_printed=true")
        assert_true(status["rawPrivateBodyRead"] is False, "raw_private_body_read=true")
        assert_true(PRIVATE_TITLE not in combined, "private_title_leaked=true")
        assert_true(PRIVATE_BODY not in combined, "private_body_leaked=true")

    print("pnh_command_packet_status_smoke_check_pass=true")
    print("private_values_printed=false")
    return 0


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())
