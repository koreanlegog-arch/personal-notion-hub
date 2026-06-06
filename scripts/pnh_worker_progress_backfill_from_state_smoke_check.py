#!/usr/bin/env python3
"""Smoke check for semantic progress backfill from dispatch-state metadata."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_MARKER = "backfill-private-marker"


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        state = temp / "state.json"
        out = temp / "backfill.json"
        state.write_text(
            json.dumps(
                {
                    "packet-1": {
                        "workerStatus": "done",
                        "workerEvidenceRef": "ops/runs/example/evidence.json",
                        "githubIssueNumber": 9,
                        "githubIssueState": "closed",
                        "discordThreadId": "1234567890",
                        "privateNote": PRIVATE_MARKER,
                    },
                    "packet-2": {
                        "workerStatus": "done",
                        "semanticProgress": {"status": "done"},
                        "privateNote": PRIVATE_MARKER,
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_worker_progress_backfill_from_state.py"),
                "--state-file",
                str(state),
                "--out",
                str(out),
                "--apply",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert_true(result.returncode == 0, result.stderr)
        combined = result.stdout + out.read_text(encoding="utf-8")
        assert_true(PRIVATE_MARKER not in combined, "private_marker_leaked=true")
        summary = json.loads(out.read_text(encoding="utf-8"))
        assert_true(summary["recordsBackfilled"] == 2, "backfill_count_mismatch=true")
        state_payload = json.loads(state.read_text(encoding="utf-8"))
        progress = state_payload["packet-1"]["semanticProgress"]
        assert_true(progress["status"] == "done", "semantic_status_not_backfilled=true")
        assert_true(progress["evidenceStrength"] == "high", "semantic_evidence_strength_low=true")
        assert_true(progress["messageContentStored"] is False, "message_content_storage_flag_wrong=true")
        upgraded = state_payload["packet-2"]["semanticProgress"]
        assert_true(upgraded["parserVersion"] == 2, "legacy_semantic_not_upgraded=true")
        assert_true(state_payload["packet-1"]["privateNote"] == PRIVATE_MARKER, "private_metadata_lost=true")

    print("pnh_worker_progress_backfill_from_state_smoke_check_pass=true")
    print("private_values_printed=false")
    return 0


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())
