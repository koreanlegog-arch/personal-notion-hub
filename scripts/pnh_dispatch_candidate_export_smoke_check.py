#!/usr/bin/env python3
"""Smoke check for metadata-only dispatch candidate export."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.private_store import insert_capture  # noqa: E402


PRIVATE_TITLE = "synthetic-candidate-private-title"
PRIVATE_BODY = "synthetic-candidate-private-body"


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        db_path = temp_root / "private" / "pnh_private_inbox.sqlite"
        out_path = temp_root / "candidate.json"
        inserted = insert_capture(
            db_path,
            {
                "source": "mobile_web",
                "kind": "task_request",
                "title": PRIVATE_TITLE,
                "body": PRIVATE_BODY,
                "sensitivity": "highly_sensitive",
            },
            allow_external=True,
        )
        blocked = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_dispatch_candidate_export.py"),
                "--db",
                str(db_path),
                "--out",
                str(out_path),
                "--allow-external-db",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert_true(blocked.returncode == 2, "plaintext_candidate_allowed_without_flag=true")

        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_dispatch_candidate_export.py"),
                "--db",
                str(db_path),
                "--capture-id",
                inserted["id"],
                "--allow-plaintext",
                "--allow-external-db",
                "--out",
                str(out_path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert_true(result.returncode == 0, f"candidate_export_failed={result.stderr.strip()}")
        combined = result.stdout + out_path.read_text(encoding="utf-8")
        assert_true(PRIVATE_TITLE not in combined, "private_title_leaked=true")
        assert_true(PRIVATE_BODY not in combined, "private_body_leaked=true")
        candidate = json.loads(out_path.read_text(encoding="utf-8"))
        assert_true(candidate["id"] == inserted["id"], "candidate_id_mismatch=true")
        assert_true(candidate["commandType"] == "task_request", "candidate_command_type_mismatch=true")
        assert_true(candidate["dispatchState"] == "not_dispatched", "candidate_dispatch_state_mismatch=true")

    print("pnh_dispatch_candidate_export_smoke_check_pass=true")
    print("private_values_printed=false")
    return 0


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())
