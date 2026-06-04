#!/usr/bin/env python3
"""Smoke self-test for encrypted vault passphrase rotation."""

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

from companion.encrypted_vault import EncryptedVaultError, export_encrypted_backup, init_encrypted_vault  # noqa: E402
from companion.private_store import init_private_store, insert_capture, list_captures  # noqa: E402


FORBIDDEN_VALUES = (
    "synthetic-rotation-secret-title-58df",
    "synthetic-rotation-secret-body-0a46",
    "synthetic-rotation-secret-payload-22ea",
)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def assert_no_secret_output(text: str) -> None:
    for value in FORBIDDEN_VALUES:
        assert_true(value not in text, "secret_value_printed=true")


def key_ids(db_path: Path) -> set[str]:
    with sqlite3.connect(db_path) as conn:
        return {row[0] for row in conn.execute("SELECT DISTINCT key_id FROM encrypted_mobile_captures").fetchall()}


def audit_event_types(db_path: Path) -> list[str]:
    with sqlite3.connect(db_path) as conn:
        return [row[0] for row in conn.execute("SELECT event_type FROM audit_events ORDER BY id").fetchall()]


def run_rotation(args: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "encrypted_vault_rotate_passphrase.py"), *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )


def main() -> int:
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            db_path = root / "private" / "pnh_private_inbox.sqlite"
            backup_path = root / "backup.pnhbackup"
            init_private_store(db_path, allow_external=True)

            old_passphrase = "synthetic-old-rotation-passphrase"
            new_passphrase = "synthetic-new-rotation-passphrase"
            backup_passphrase = "synthetic-backup-rotation-passphrase"
            vault = init_encrypted_vault(db_path, old_passphrase)
            for index in range(2):
                insert_capture(
                    db_path,
                    {
                        "id": f"synthetic-rotation-capture-{index}",
                        "source": "mobile",
                        "kind": "voice_note",
                        "title": f"{FORBIDDEN_VALUES[0]}-{index}",
                        "body": f"{FORBIDDEN_VALUES[1]}-{index}",
                        "payload_marker": f"{FORBIDDEN_VALUES[2]}-{index}",
                    },
                    allow_external=True,
                    vault=vault,
                )
            old_key_ids = key_ids(db_path)
            export_encrypted_backup(vault, backup_path, backup_passphrase)

            env = os.environ.copy()
            env["PNH_ROTATION_OLD"] = old_passphrase
            env["PNH_ROTATION_NEW"] = new_passphrase

            no_backup = run_rotation(
                [
                    "--db",
                    str(db_path),
                    "--vault-passphrase-env",
                    "PNH_ROTATION_OLD",
                    "--new-vault-passphrase-env",
                    "PNH_ROTATION_NEW",
                    "--confirm",
                    "ROTATE_VAULT_PASSPHRASE",
                    "--allow-external-private-paths",
                ],
                env,
            )
            assert_true(no_backup.returncode == 2, "rotation_without_backup_allowed=true")

            dry_run = run_rotation(
                [
                    "--db",
                    str(db_path),
                    "--vault-passphrase-env",
                    "PNH_ROTATION_OLD",
                    "--new-vault-passphrase-env",
                    "PNH_ROTATION_NEW",
                    "--confirm",
                    "ROTATE_VAULT_PASSPHRASE",
                    "--dry-run",
                    "--allow-external-private-paths",
                ],
                env,
            )
            assert_true(dry_run.returncode == 0, "rotation_dry_run_failed=true")
            assert_true(key_ids(db_path) == old_key_ids, "rotation_dry_run_mutated=true")

            same_env = env.copy()
            same_env["PNH_ROTATION_NEW"] = old_passphrase
            same_pass = run_rotation(
                [
                    "--db",
                    str(db_path),
                    "--vault-passphrase-env",
                    "PNH_ROTATION_OLD",
                    "--new-vault-passphrase-env",
                    "PNH_ROTATION_NEW",
                    "--preflight-backup",
                    str(backup_path),
                    "--confirm",
                    "ROTATE_VAULT_PASSPHRASE",
                    "--allow-external-private-paths",
                ],
                same_env,
            )
            assert_true(same_pass.returncode == 2, "same_passphrase_rotation_allowed=true")

            rotated = run_rotation(
                [
                    "--db",
                    str(db_path),
                    "--vault-passphrase-env",
                    "PNH_ROTATION_OLD",
                    "--new-vault-passphrase-env",
                    "PNH_ROTATION_NEW",
                    "--preflight-backup",
                    str(backup_path),
                    "--confirm",
                    "ROTATE_VAULT_PASSPHRASE",
                    "--allow-external-private-paths",
                ],
                env,
            )
            assert_true(rotated.returncode == 0, "rotation_failed=true")
            rotation_payload = json.loads(rotated.stdout)
            result = rotation_payload["encryptedVaultPassphraseRotation"]
            assert_true(result["rotated"] is True, "rotation_result_flag_failed=true")
            assert_true(result["captureCount"] == 2, "rotation_capture_count_failed=true")
            assert_true(result["keyChanged"] is True, "rotation_key_id_not_changed=true")
            assert_true(key_ids(db_path) != old_key_ids, "rotation_rows_key_id_not_changed=true")

            try:
                init_encrypted_vault(db_path, old_passphrase).fetch_capture("synthetic-rotation-capture-0")
            except EncryptedVaultError:
                pass
            else:
                raise SystemExit("old_passphrase_still_decrypts=true")

            new_vault = init_encrypted_vault(db_path, new_passphrase)
            decrypted = new_vault.fetch_capture("synthetic-rotation-capture-0")
            assert_true(FORBIDDEN_VALUES[0] in decrypted["title"], "new_passphrase_decrypt_failed=true")
            redacted = list_captures(db_path, include_body=False, allow_external=True)
            assert_true(len(redacted) == 2, "rotated_redacted_list_failed=true")
            assert_true("encrypted_vault_passphrase_rotated" in audit_event_types(db_path), "rotation_audit_missing=true")

            db_bytes = db_path.read_bytes()
            for value in FORBIDDEN_VALUES:
                assert_true(value.encode("utf-8") not in db_bytes, "plaintext_found_after_rotation=true")

            combined = no_backup.stdout + no_backup.stderr + dry_run.stdout + dry_run.stderr + same_pass.stdout + same_pass.stderr + rotated.stdout + rotated.stderr
            assert_no_secret_output(combined)

    assert_no_secret_output(captured.getvalue())
    print("encrypted_vault_rotation_smoke_check_pass=true")
    print("secret_value_printed=false")
    print("plaintext_found_after_rotation=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
