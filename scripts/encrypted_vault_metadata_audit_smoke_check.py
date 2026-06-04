#!/usr/bin/env python3
"""Smoke self-test for encrypted vault metadata audit."""

from __future__ import annotations

import contextlib
import io
import json
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.encrypted_vault import init_encrypted_vault  # noqa: E402
from companion.private_store import init_private_store, insert_capture  # noqa: E402


FORBIDDEN_VALUES = (
    "synthetic-metadata-secret-title-9d2a0d",
    "synthetic-metadata-secret-body-6fb31b",
    "synthetic-metadata-secret-payload-4d92aa",
)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def assert_no_forbidden_text(text: str) -> None:
    for value in FORBIDDEN_VALUES:
        assert_true(value not in text, "private_value_printed=true")


def run_audit(db_path: Path, *, fail_on_unsupported: bool = False) -> subprocess.CompletedProcess[str]:
    args = [
        sys.executable,
        str(ROOT / "scripts" / "encrypted_vault_metadata_audit.py"),
        "--db",
        str(db_path),
        "--allow-external-private-paths",
    ]
    if fail_on_unsupported:
        args.append("--fail-on-unsupported")
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
            db_path = Path(temp_dir) / "metadata.sqlite"
            init_private_store(db_path, allow_external=True)
            vault = init_encrypted_vault(db_path, "synthetic-metadata-vault-passphrase")
            insert_capture(
                db_path,
                {
                    "id": "synthetic-metadata-encrypted",
                    "source": "mobile",
                    "kind": "voice_note",
                    "title": FORBIDDEN_VALUES[0],
                    "body": FORBIDDEN_VALUES[1],
                    "sensitivity": "highly_sensitive",
                    "payload_marker": FORBIDDEN_VALUES[2],
                },
                allow_external=True,
                vault=vault,
            )
            insert_capture(
                db_path,
                {
                    "id": "synthetic-metadata-plaintext",
                    "source": "manual",
                    "kind": "project_brief",
                    "title": f"{FORBIDDEN_VALUES[0]}-plain",
                    "body": f"{FORBIDDEN_VALUES[1]}-plain",
                    "sensitivity": "private",
                    "payload_marker": f"{FORBIDDEN_VALUES[2]}-plain",
                },
                allow_external=True,
            )

            audit_result = run_audit(db_path)
            assert_true(audit_result.returncode == 0, "metadata_audit_failed=true")
            payload = json.loads(audit_result.stdout)
            audit = payload["encryptedVaultMetadataAudit"]
            assert_true(audit["encryptedVaultPresent"] is True, "metadata_vault_missing=true")
            assert_true(audit["algorithm"] == "AES-256-GCM", "metadata_algorithm_failed=true")
            assert_true(audit["kdf"] == "PBKDF2-HMAC-SHA256", "metadata_kdf_failed=true")
            assert_true(audit["encryptedCaptureCount"] == 1, "metadata_encrypted_count_failed=true")
            assert_true(audit["plaintextCaptureCount"] == 1, "metadata_plaintext_count_failed=true")
            assert_true(audit["valuesPrinted"] is False, "metadata_values_printed_flag_failed=true")
            assert_true(audit["dbMutated"] is False, "metadata_mutated_flag_failed=true")

            with sqlite3.connect(db_path) as conn:
                conn.execute(
                    "UPDATE encrypted_vault_meta SET value = ? WHERE key = ?",
                    (b"AES-128-GCM", "algorithm"),
                )
            unsupported = run_audit(db_path, fail_on_unsupported=True)
            assert_true(unsupported.returncode == 1, "metadata_unsupported_not_detected=true")
            unsupported_payload = json.loads(unsupported.stdout)
            assert_true(
                "algorithm" in unsupported_payload["encryptedVaultMetadataAudit"]["unsupportedFields"],
                "metadata_unsupported_field_missing=true",
            )

    assert_no_forbidden_text(captured.getvalue())
    print("encrypted_vault_metadata_audit_smoke_check_pass=true")
    print("private_values_printed=false")
    print("db_mutated=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
