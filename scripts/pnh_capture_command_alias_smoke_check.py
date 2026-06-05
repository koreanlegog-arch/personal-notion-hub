#!/usr/bin/env python3
"""Smoke check for metadata-only PNH capture command aliases."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.private_store import insert_capture  # noqa: E402


PRIVATE_TITLE = "synthetic-alias-private-title"
PRIVATE_BODY = "synthetic-alias-private-body"


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        db_path = temp_path / "private" / "pnh_private_inbox.sqlite"
        state_path = temp_path / "state.json"
        alias_path = temp_path / "aliases.json"
        alias_out = temp_path / "alias_result.json"
        queue_out = temp_path / "queue_plan.json"
        candidate_out = temp_path / "candidate.json"
        history_path = temp_path / "history.json"
        inserted = insert_capture(
            db_path,
            {
                "source": "mobile_web",
                "kind": "assistant_capture",
                "title": PRIVATE_TITLE,
                "body": PRIVATE_BODY,
                "sensitivity": "private",
            },
            allow_external=True,
        )
        state_path.write_text("{}\n", encoding="utf-8")
        history_path.write_text(json.dumps({"events": []}), encoding="utf-8")

        alias = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_capture_command_alias.py"),
                "--db",
                str(db_path),
                "--capture-id",
                inserted["id"],
                "--command-type",
                "task_request",
                "--alias-file",
                str(alias_path),
                "--state-file",
                str(state_path),
                "--out",
                str(alias_out),
                "--allow-plaintext",
                "--allow-external-db",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert_true(alias.returncode == 0, f"alias_failed={alias.stderr.strip()}")

        queue = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_unattended_dispatch_queue_plan.py"),
                "--db",
                str(db_path),
                "--state-file",
                str(state_path),
                "--history-json",
                str(history_path),
                "--command-aliases",
                str(alias_path),
                "--out",
                str(queue_out),
                "--allow-plaintext",
                "--allow-external-db",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert_true(queue.returncode == 0, f"queue_failed={queue.stderr.strip()}")

        export = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_dispatch_candidate_export.py"),
                "--db",
                str(db_path),
                "--capture-id",
                inserted["id"],
                "--allow-plaintext",
                "--allow-external-db",
                "--command-aliases",
                str(alias_path),
                "--state-file",
                str(state_path),
                "--out",
                str(candidate_out),
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert_true(export.returncode == 0, f"export_failed={export.stderr.strip()}")

        combined = "\n".join(
            [
                alias.stdout,
                queue.stdout,
                export.stdout,
                alias_out.read_text(encoding="utf-8"),
                queue_out.read_text(encoding="utf-8"),
                candidate_out.read_text(encoding="utf-8"),
            ]
        )
        assert_true(PRIVATE_TITLE not in combined, "private_title_leaked=true")
        assert_true(PRIVATE_BODY not in combined, "private_body_leaked=true")
        queue_payload = json.loads(queue_out.read_text(encoding="utf-8"))
        candidate = json.loads(candidate_out.read_text(encoding="utf-8"))
        assert_true(queue_payload["queuedCount"] == 1, "alias_queue_count_mismatch=true")
        assert_true(queue_payload["queued"][0]["commandType"] == "task_request", "alias_queue_command_type_mismatch=true")
        assert_true(queue_payload["queued"][0]["commandAliasApplied"] is True, "alias_not_applied_to_queue=true")
        assert_true(candidate["commandType"] == "task_request", "alias_export_command_type_mismatch=true")
        assert_true(candidate["originalKind"] == "assistant_capture", "alias_export_original_kind_mismatch=true")
        assert_true(candidate["commandAliasApplied"] is True, "alias_not_applied_to_export=true")

    print("pnh_capture_command_alias_smoke_check_pass=true")
    print("private_values_printed=false")
    print("raw_private_body_read=false")
    return 0


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())
