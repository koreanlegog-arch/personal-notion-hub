#!/usr/bin/env python3
"""Smoke self-test for plaintext migration audit."""

from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.encrypted_vault import init_encrypted_vault  # noqa: E402
from companion.private_store import init_private_store, insert_capture, store_summary  # noqa: E402


FORBIDDEN_VALUES = (
    "synthetic-migration-secret-title-9d2a0d",
    "synthetic-migration-secret-body-6fb31b",
    "synthetic-migration-secret-payload-4d92aa",
)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def assert_no_forbidden_text(text: str) -> None:
    for value in FORBIDDEN_VALUES:
        assert_true(value not in text, "private_value_printed=true")


def run_audit(db_path: Path, *, fail_on_plaintext: bool = False) -> subprocess.CompletedProcess[str]:
    args = [
        sys.executable,
        str(ROOT / "scripts" / "plaintext_migration_audit.py"),
        "--db",
        str(db_path),
        "--allow-external-private-paths",
    ]
    if fail_on_plaintext:
        args.append("--fail-on-plaintext")
    result = subprocess.run(
        args,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert_no_forbidden_text(result.stdout + result.stderr)
    return result


def main() -> int:
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "migration.sqlite"
            init_private_store(db_path, allow_external=True)
            insert_capture(
                db_path,
                {
                    "id": "synthetic-plaintext-capture",
                    "source": "mobile",
                    "kind": "voice_note",
                    "title": FORBIDDEN_VALUES[0],
                    "body": FORBIDDEN_VALUES[1],
                    "sensitivity": "highly_sensitive",
                    "payload_marker": FORBIDDEN_VALUES[2],
                },
                allow_external=True,
            )
            vault = init_encrypted_vault(db_path, "synthetic-migration-vault-passphrase")
            insert_capture(
                db_path,
                {
                    "id": "synthetic-encrypted-capture",
                    "source": "mobile",
                    "kind": "voice_note",
                    "title": f"{FORBIDDEN_VALUES[0]}-encrypted",
                    "body": f"{FORBIDDEN_VALUES[1]}-encrypted",
                    "sensitivity": "highly_sensitive",
                    "payload_marker": f"{FORBIDDEN_VALUES[2]}-encrypted",
                },
                allow_external=True,
                vault=vault,
            )
            before = store_summary(db_path, allow_external=True)

            audit_result = run_audit(db_path)
            assert_true(audit_result.returncode == 0, "migration_audit_failed=true")
            payload = json.loads(audit_result.stdout)
            audit = payload["plaintextMigrationAudit"]
            assert_true(audit["plaintextRowsDetected"] is True, "plaintext_rows_not_detected=true")
            assert_true(audit["plaintextRowCount"] == 1, "plaintext_row_count_failed=true")
            assert_true(audit["encryptedRowCount"] == 1, "encrypted_row_count_failed=true")
            assert_true(audit["valuesPrinted"] is False, "migration_audit_values_printed=true")
            assert_true(audit["dbMutated"] is False, "migration_audit_mutated_flag_failed=true")

            failing_result = run_audit(db_path, fail_on_plaintext=True)
            assert_true(failing_result.returncode == 1, "migration_audit_fail_on_plaintext_failed=true")
            after = store_summary(db_path, allow_external=True)
            assert_true(before["totalCaptures"] == after["totalCaptures"], "migration_audit_mutated_db=true")
            assert_true(before["byStorageMode"] == after["byStorageMode"], "migration_audit_storage_mode_mutated=true")

    assert_no_forbidden_text(captured.getvalue())
    print("plaintext_migration_audit_smoke_check_pass=true")
    print("private_values_printed=false")
    print("db_mutated=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
