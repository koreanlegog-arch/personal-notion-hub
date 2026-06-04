#!/usr/bin/env python3
"""Smoke self-test for plaintext-to-encrypted migration apply gate."""

from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.encrypted_vault import init_encrypted_vault  # noqa: E402
from companion.private_store import init_private_store, insert_capture, store_summary  # noqa: E402


FORBIDDEN_VALUES = (
    "synthetic-apply-secret-title-91de",
    "synthetic-apply-secret-body-b8fc",
    "synthetic-apply-secret-payload-24ca",
)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def assert_no_secret_output(text: str) -> None:
    for value in FORBIDDEN_VALUES:
        assert_true(value not in text, "migration_apply_private_value_printed=true")


def run_apply(db_path: Path, env: dict[str, str], args: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "plaintext_migration_apply.py"), "--db", str(db_path), "--allow-external-private-paths", *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert_no_secret_output(result.stdout + result.stderr)
    return result


def main() -> int:
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            db_path = temp_root / "migration-apply.sqlite"
            backup_path = temp_root / "preflight.sqlite.backup"
            passphrase = "synthetic-apply-vault-passphrase"
            env = os.environ.copy()
            env["PNH_APPLY_VAULT_PASSPHRASE"] = passphrase
            init_private_store(db_path, allow_external=True)
            insert_capture(
                db_path,
                {
                    "id": "synthetic-plaintext-apply-capture",
                    "source": "mobile",
                    "kind": "voice_note",
                    "title": FORBIDDEN_VALUES[0],
                    "body": FORBIDDEN_VALUES[1],
                    "sensitivity": "highly_sensitive",
                    "payload_marker": FORBIDDEN_VALUES[2],
                },
                allow_external=True,
            )
            before = store_summary(db_path, allow_external=True)
            assert_true(before["byStorageMode"]["plaintext-inbox"] == 1, "apply_smoke_plaintext_setup_failed=true")

            dry = run_apply(db_path, env, ["--dry-run"])
            assert_true(dry.returncode == 0, "migration_apply_dry_run_failed=true")
            dry_payload = json.loads(dry.stdout)["plaintextMigrationApply"]
            assert_true(dry_payload["migratableRowCount"] == 1, "migration_apply_dry_count_failed=true")
            assert_true(store_summary(db_path, allow_external=True)["byStorageMode"]["plaintext-inbox"] == 1, "migration_apply_dry_mutated=true")

            no_backup = run_apply(
                db_path,
                env,
                ["--vault-passphrase-env", "PNH_APPLY_VAULT_PASSPHRASE", "--confirm", "MIGRATE_PLAINTEXT_TO_ENCRYPTED"],
            )
            assert_true(no_backup.returncode == 2, "migration_apply_without_backup_allowed=true")

            backup_path.write_bytes(db_path.read_bytes())
            applied = run_apply(
                db_path,
                env,
                [
                    "--vault-passphrase-env",
                    "PNH_APPLY_VAULT_PASSPHRASE",
                    "--preflight-backup",
                    str(backup_path),
                    "--confirm",
                    "MIGRATE_PLAINTEXT_TO_ENCRYPTED",
                ],
            )
            assert_true(applied.returncode == 0, "migration_apply_failed=true")
            applied_payload = json.loads(applied.stdout)["plaintextMigrationApply"]
            assert_true(applied_payload["migratedRowCount"] == 1, "migration_apply_count_failed=true")
            after = store_summary(db_path, allow_external=True)
            assert_true(after["byStorageMode"].get("plaintext-inbox", 0) == 0, "migration_apply_plaintext_remains=true")
            assert_true(after["byStorageMode"].get("encrypted-vault", 0) == 1, "migration_apply_encrypted_missing=true")
            decrypted = init_encrypted_vault(db_path, passphrase).fetch_capture("synthetic-plaintext-apply-capture")
            assert_true(decrypted["title"] == FORBIDDEN_VALUES[0], "migration_apply_decrypt_failed=true")
            for value in FORBIDDEN_VALUES:
                assert_true(value.encode("utf-8") not in db_path.read_bytes(), "migration_apply_plaintext_found=true")

    assert_no_secret_output(captured.getvalue())
    print("plaintext_migration_apply_smoke_check_pass=true")
    print("private_values_printed=false")
    print("plaintext_found_after_apply=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
