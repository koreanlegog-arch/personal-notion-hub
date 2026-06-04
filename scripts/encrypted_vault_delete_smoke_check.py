#!/usr/bin/env python3
"""Smoke self-test for encrypted vault delete workflow."""

from __future__ import annotations

import contextlib
import io
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.encrypted_vault import init_encrypted_vault  # noqa: E402
from companion.private_store import init_private_store, insert_capture, list_captures, store_summary  # noqa: E402


FORBIDDEN_VALUES = (
    "synthetic-delete-secret-title-9d2a0d",
    "synthetic-delete-secret-body-6fb31b",
    "synthetic-delete-secret-payload-4d92aa",
)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def assert_no_forbidden_text(text: str) -> None:
    for value in FORBIDDEN_VALUES:
        assert_true(value not in text, "private_value_printed=true")


def run_delete(args: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "encrypted_vault_delete.py"), *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert_no_forbidden_text(result.stdout + result.stderr)
    return result


def encrypted_count(db_path: Path) -> int:
    with sqlite3.connect(db_path) as conn:
        return int(conn.execute("SELECT COUNT(*) FROM encrypted_mobile_captures").fetchone()[0])


def audit_events(db_path: Path) -> list[tuple[str, str | None, str | None]]:
    with sqlite3.connect(db_path) as conn:
        return conn.execute("SELECT event_type, capture_id, source FROM audit_events ORDER BY id").fetchall()


def main() -> int:
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "delete.sqlite"
            vault_env = "PNH_SYNTHETIC_DELETE_VAULT_PASSPHRASE"
            env = dict(os.environ)
            env[vault_env] = "synthetic-delete-vault-passphrase"
            init_private_store(db_path, allow_external=True)
            vault = init_encrypted_vault(db_path, env[vault_env])
            for index in range(2):
                insert_capture(
                    db_path,
                    {
                        "id": f"synthetic-delete-capture-{index}",
                        "source": "mobile",
                        "kind": "voice_note",
                        "title": f"{FORBIDDEN_VALUES[0]}-{index}",
                        "body": f"{FORBIDDEN_VALUES[1]}-{index}",
                        "sensitivity": "highly_sensitive",
                        "payload_marker": f"{FORBIDDEN_VALUES[2]}-{index}",
                    },
                    allow_external=True,
                    vault=vault,
                )
            assert_true(encrypted_count(db_path) == 2, "delete_setup_count_failed=true")

            missing_confirm = run_delete(
                [
                    "--db",
                    str(db_path),
                    "--capture-id",
                    "synthetic-delete-capture-0",
                    "--vault-passphrase-env",
                    vault_env,
                    "--confirm",
                    "WRONG",
                    "--allow-external-private-paths",
                ],
                env,
            )
            assert_true(missing_confirm.returncode == 2, "delete_confirmation_not_required=true")

            delete_result = run_delete(
                [
                    "--db",
                    str(db_path),
                    "--capture-id",
                    "synthetic-delete-capture-0",
                    "--vault-passphrase-env",
                    vault_env,
                    "--confirm",
                    "DELETE_CAPTURE",
                    "--vacuum",
                    "--allow-external-private-paths",
                ],
                env,
            )
            assert_true(delete_result.returncode == 0, "encrypted_delete_failed=true")
            delete_payload = json.loads(delete_result.stdout)
            assert_true(delete_payload["encryptedVaultDelete"]["deleted"] is True, "encrypted_delete_response_failed=true")
            assert_true(encrypted_count(db_path) == 1, "encrypted_delete_count_failed=true")

            listed = list_captures(db_path, include_body=False, allow_external=True)
            assert_true(all(item["id"] != "synthetic-delete-capture-0" for item in listed), "deleted_capture_still_listed=true")
            assert_true(any(item["id"] == "synthetic-delete-capture-1" for item in listed), "remaining_capture_missing=true")
            assert_no_forbidden_text(json.dumps({"items": listed}, ensure_ascii=False))
            summary = store_summary(db_path, allow_external=True)
            assert_true(summary["byStorageMode"]["encrypted-vault"] == 1, "delete_summary_count_failed=true")

            events = audit_events(db_path)
            event_text = json.dumps(events, ensure_ascii=False)
            assert_true("encrypted_mobile_capture_deleted" in event_text, "delete_audit_missing=true")
            assert_no_forbidden_text(event_text)

            missing_delete = run_delete(
                [
                    "--db",
                    str(db_path),
                    "--capture-id",
                    "synthetic-delete-missing",
                    "--vault-passphrase-env",
                    vault_env,
                    "--confirm",
                    "DELETE_CAPTURE",
                    "--allow-external-private-paths",
                ],
                env,
            )
            assert_true(missing_delete.returncode == 1, "missing_delete_exit_failed=true")

    assert_no_forbidden_text(captured.getvalue())
    print("encrypted_vault_delete_smoke_check_pass=true")
    print("secret_value_printed=false")
    print("private_response_values_printed=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
