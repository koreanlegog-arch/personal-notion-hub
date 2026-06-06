#!/usr/bin/env python3
"""Smoke check for the PNH worker completion auto lane."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_MARKER = "synthetic-worker-completion-private-marker"


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="pnh-worker-completion-auto-") as tmp:
        temp_path = Path(tmp)
        state = temp_path / "state.json"
        run_dir = temp_path / "run"
        state.write_text(
            json.dumps(
                {
                    "capture-ready-001": {
                        "githubIssueNumber": 123,
                        "githubIssueUrl": "https://github.com/example/private/issues/123",
                        "githubIssueState": "open",
                        "discordThreadId": "1510000000000000000",
                        "workerSessionId": "pnh:capture-ready-001:qa",
                        "workerStatus": "done",
                        "workerEvidenceRef": "ops/runs/PNH-WORKER-COMPLETION-SMOKE/worker.json",
                        "privateNote": PRIVATE_MARKER,
                        "updatedAt": "2026-06-06T00:00:00+00:00",
                    },
                    "capture-missing-evidence-001": {
                        "githubIssueNumber": 124,
                        "discordThreadId": "1510000000000000001",
                        "workerSessionId": "pnh:capture-missing-evidence-001:qa",
                        "workerStatus": "done",
                        "privateNote": PRIVATE_MARKER,
                        "updatedAt": "2026-06-06T00:00:01+00:00",
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_worker_completion_auto.py"),
                "--state-file",
                str(state),
                "--run-dir",
                str(run_dir),
                "--skip-github-read",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert_true(result.returncode == 0, result.stderr.strip() or result.stdout.strip())
        summary = json.loads((run_dir / "worker_completion_auto_summary.json").read_text(encoding="utf-8"))
        selected_state = (run_dir / "selected_dispatch_state.json").read_text(encoding="utf-8")
        combined = result.stdout + selected_state + (run_dir / "evidence_log.md").read_text(encoding="utf-8")
        assert_true(PRIVATE_MARKER not in combined, "private_marker_leaked=true")
        assert_true(summary["selectedCandidateCount"] == 1, "selected_candidate_count_mismatch=true")
        assert_true(summary["closurePlannedActionCount"] == 1, "closure_plan_count_mismatch=true")
        assert_true(summary["externalWritesPerformed"] is False, "dry_run_external_write=true")
        assert_true(summary["privateValuesPrinted"] is False, "private_values_printed=true")
        assert_true(summary["rawPrivateBodyRead"] is False, "raw_private_body_read=true")
    print("pnh_worker_completion_auto_smoke_check_pass=true")
    print("private_values_printed=false")
    return 0


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())
