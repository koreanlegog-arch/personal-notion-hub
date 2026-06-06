#!/usr/bin/env python3
"""Smoke check for semantic worker progress parsing."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_MARKER = "progress-private-marker"


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        state = temp / "state.json"
        out = temp / "progress.json"
        state.write_text(json.dumps({"packet-1": {"privateNote": PRIVATE_MARKER}}, ensure_ascii=False), encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_worker_progress_parse.py"),
                "--packet-id",
                "packet-1",
                "--text",
                "Worker_done completed. QA tests passed, evidence recorded, GitHub issue updated, Discord thread updated.",
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
        payload = json.loads(state.read_text(encoding="utf-8"))
        progress = payload["packet-1"]["semanticProgress"]
        assert_true(progress["status"] == "done", "semantic_status_not_saved=true")
        assert_true(progress["evidenceStrength"] == "high", "semantic_evidence_strength_low=true")
        assert_true(progress["recommendedNextAction"] == "record_worker_result_and_close_dispatch", "semantic_next_action_wrong=true")
        assert_true(progress["messageContentStored"] is False, "message_content_storage_flag_wrong=true")
        assert_true(payload["packet-1"]["privateNote"] == PRIVATE_MARKER, "existing_private_metadata_lost=true")

        blocked = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_worker_progress_parse.py"),
                "--packet-id",
                "packet-1",
                "--text",
                "Worker is blocked and needs approval before external write.",
                "--state-file",
                str(state),
                "--out",
                str(temp / "blocked.json"),
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert_true(blocked.returncode == 0, blocked.stderr)
        blocked_payload = json.loads((temp / "blocked.json").read_text(encoding="utf-8"))
        assert_true(blocked_payload["progress"]["requiresSupervisorAction"] is True, "supervisor_action_not_detected=true")

        secret_like = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_worker_progress_parse.py"),
                "--packet-id",
                "packet-1",
                "--text",
                "token=synthetic-secret-like-value",
                "--state-file",
                str(state),
                "--out",
                str(temp / "secret.json"),
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert_true(secret_like.returncode == 2, "secret_like_progress_accepted=true")

    print("pnh_worker_progress_parse_smoke_check_pass=true")
    print("private_values_printed=false")
    return 0


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())
