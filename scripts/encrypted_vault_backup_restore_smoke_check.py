#!/usr/bin/env python3
"""Smoke self-test for encrypted vault backup and restore."""

from __future__ import annotations

import base64
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

from companion.encrypted_vault import EncryptedVaultError, init_encrypted_vault, load_vault_from_env  # noqa: E402
from companion.private_store import init_private_store, insert_capture, list_captures  # noqa: E402


FORBIDDEN_VALUES = (
    "synthetic-backup-secret-title-9d2a0d",
    "synthetic-backup-secret-body-6fb31b",
    "synthetic-backup-secret-payload-4d92aa",
)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def assert_no_forbidden_text(text: str) -> None:
    for value in FORBIDDEN_VALUES:
        assert_true(value not in text, "private_value_printed=true")


def assert_no_forbidden_file(path: Path) -> None:
    data = path.read_bytes()
    for value in FORBIDDEN_VALUES:
        assert_true(value.encode("utf-8") not in data, "private_value_found_in_backup=true")


def run_script(args: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert_no_forbidden_text(result.stdout + result.stderr)
    return result


def tampered_backup(source: Path, target: Path) -> None:
    envelope = json.loads(source.read_text(encoding="utf-8"))
    ciphertext = bytearray(base64.urlsafe_b64decode(envelope["ciphertext"].encode("ascii")))
    ciphertext[-1] ^= 1
    envelope["ciphertext"] = base64.urlsafe_b64encode(bytes(ciphertext)).decode("ascii")
    target.write_text(json.dumps(envelope, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def unsupported_backup(source: Path, target: Path) -> None:
    envelope = json.loads(source.read_text(encoding="utf-8"))
    envelope["algorithm"] = "AES-128-GCM"
    target.write_text(json.dumps(envelope, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def main() -> int:
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            source_db = temp_root / "source.sqlite"
            restore_db = temp_root / "restore.sqlite"
            wrong_db = temp_root / "wrong.sqlite"
            backup_path = temp_root / "backup.pnhbackup"
            tampered_path = temp_root / "tampered.pnhbackup"
            unsupported_path = temp_root / "unsupported.pnhbackup"
            vault_env = "PNH_SYNTHETIC_VAULT_PASSPHRASE"
            restore_env = "PNH_SYNTHETIC_RESTORE_VAULT_PASSPHRASE"
            backup_env = "PNH_SYNTHETIC_BACKUP_PASSPHRASE"
            wrong_backup_env = "PNH_SYNTHETIC_WRONG_BACKUP_PASSPHRASE"
            env = dict(os.environ)
            env[vault_env] = "synthetic-source-vault-passphrase"
            env[restore_env] = "synthetic-restore-vault-passphrase"
            env[backup_env] = "synthetic-backup-passphrase"
            env[wrong_backup_env] = "synthetic-wrong-backup-passphrase"

            init_private_store(source_db, allow_external=True)
            source_vault = init_encrypted_vault(source_db, env[vault_env])
            for index in range(2):
                insert_capture(
                    source_db,
                    {
                        "id": f"synthetic-backup-capture-{index}",
                        "source": "mobile",
                        "kind": "voice_note",
                        "title": f"{FORBIDDEN_VALUES[0]}-{index}",
                        "body": f"{FORBIDDEN_VALUES[1]}-{index}",
                        "sensitivity": "highly_sensitive",
                        "payload_marker": f"{FORBIDDEN_VALUES[2]}-{index}",
                    },
                    allow_external=True,
                    vault=source_vault,
                )

            backup_result = run_script(
                [
                    str(ROOT / "scripts" / "encrypted_vault_backup.py"),
                    "--db",
                    str(source_db),
                    "--out",
                    str(backup_path),
                    "--vault-passphrase-env",
                    vault_env,
                    "--backup-passphrase-env",
                    backup_env,
                    "--allow-external-private-paths",
                ],
                env,
            )
            assert_true(backup_result.returncode == 0, "encrypted_backup_failed=true")
            assert_true(backup_path.exists(), "encrypted_backup_missing=true")
            assert_no_forbidden_file(backup_path)
            envelope = json.loads(backup_path.read_text(encoding="utf-8"))
            assert_true(envelope.get("schemaVersion") == 1, "backup_schema_missing=true")
            assert_true(envelope.get("algorithm") == "AES-256-GCM", "backup_algorithm_missing=true")
            assert_true(envelope.get("kdf") == "PBKDF2-HMAC-SHA256", "backup_kdf_missing=true")

            restore_result = run_script(
                [
                    str(ROOT / "scripts" / "encrypted_vault_restore.py"),
                    "--db",
                    str(restore_db),
                    "--backup",
                    str(backup_path),
                    "--vault-passphrase-env",
                    restore_env,
                    "--backup-passphrase-env",
                    backup_env,
                    "--allow-external-private-paths",
                ],
                env,
            )
            assert_true(restore_result.returncode == 0, "encrypted_restore_failed=true")
            restored = list_captures(
                restore_db,
                include_body=True,
                allow_external=True,
                vault=init_encrypted_vault(restore_db, env[restore_env]),
            )
            assert_true(len(restored) == 2, "encrypted_restore_count_failed=true")
            assert_true(any(item.get("body") == f"{FORBIDDEN_VALUES[1]}-0" for item in restored), "encrypted_restore_body_failed=true")

            duplicate_restore = run_script(
                [
                    str(ROOT / "scripts" / "encrypted_vault_restore.py"),
                    "--db",
                    str(restore_db),
                    "--backup",
                    str(backup_path),
                    "--vault-passphrase-env",
                    restore_env,
                    "--backup-passphrase-env",
                    backup_env,
                    "--allow-external-private-paths",
                ],
                env,
            )
            assert_true(duplicate_restore.returncode == 0, "encrypted_duplicate_restore_failed=true")
            duplicate_payload = json.loads(duplicate_restore.stdout)
            assert_true(
                duplicate_payload["encryptedVaultRestore"]["skippedExistingCount"] == 2,
                "encrypted_duplicate_skip_failed=true",
            )

            wrong_result = run_script(
                [
                    str(ROOT / "scripts" / "encrypted_vault_restore.py"),
                    "--db",
                    str(wrong_db),
                    "--backup",
                    str(backup_path),
                    "--vault-passphrase-env",
                    restore_env,
                    "--backup-passphrase-env",
                    wrong_backup_env,
                    "--allow-external-private-paths",
                ],
                env,
            )
            assert_true(wrong_result.returncode == 2, "wrong_backup_passphrase_accepted=true")

            tampered_backup(backup_path, tampered_path)
            tampered_result = run_script(
                [
                    str(ROOT / "scripts" / "encrypted_vault_restore.py"),
                    "--db",
                    str(temp_root / "tampered.sqlite"),
                    "--backup",
                    str(tampered_path),
                    "--vault-passphrase-env",
                    restore_env,
                    "--backup-passphrase-env",
                    backup_env,
                    "--allow-external-private-paths",
                ],
                env,
            )
            assert_true(tampered_result.returncode == 2, "tampered_backup_accepted=true")

            unsupported_backup(backup_path, unsupported_path)
            unsupported_result = run_script(
                [
                    str(ROOT / "scripts" / "encrypted_vault_restore.py"),
                    "--db",
                    str(temp_root / "unsupported.sqlite"),
                    "--backup",
                    str(unsupported_path),
                    "--vault-passphrase-env",
                    restore_env,
                    "--backup-passphrase-env",
                    backup_env,
                    "--allow-external-private-paths",
                ],
                env,
            )
            assert_true(unsupported_result.returncode == 2, "unsupported_backup_accepted=true")

            try:
                init_encrypted_vault(restore_db, env[wrong_backup_env]).fetch_capture("synthetic-backup-capture-0")
            except EncryptedVaultError:
                pass
            else:
                raise SystemExit("wrong_restore_vault_passphrase_accepted=true")

    assert_no_forbidden_text(captured.getvalue())
    print("encrypted_vault_backup_restore_smoke_check_pass=true")
    print("secret_value_printed=false")
    print("plaintext_found_in_backup=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
