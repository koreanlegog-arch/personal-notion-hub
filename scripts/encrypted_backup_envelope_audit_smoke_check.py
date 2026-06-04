#!/usr/bin/env python3
"""Smoke self-test for encrypted backup envelope audit."""

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
from companion.private_store import init_private_store, insert_capture  # noqa: E402


FORBIDDEN_VALUES = (
    "synthetic-envelope-secret-title-c4fd9a",
    "synthetic-envelope-secret-body-81ab72",
    "synthetic-envelope-secret-payload-59ef31",
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
            backup_path = temp_root / "backup.pnhbackup"
            unsupported_path = temp_root / "unsupported.pnhbackup"
            vault_env = "PNH_SYNTHETIC_AUDIT_VAULT_PASSPHRASE"
            backup_env = "PNH_SYNTHETIC_AUDIT_BACKUP_PASSPHRASE"
            env = dict(os.environ)
            env[vault_env] = "synthetic-audit-vault-passphrase"
            env[backup_env] = "synthetic-audit-backup-passphrase"

            init_private_store(source_db, allow_external=True)
            source_vault = init_encrypted_vault(source_db, env[vault_env])
            insert_capture(
                source_db,
                {
                    "id": "synthetic-envelope-audit-capture",
                    "source": "mobile",
                    "kind": "voice_note",
                    "title": FORBIDDEN_VALUES[0],
                    "body": FORBIDDEN_VALUES[1],
                    "sensitivity": "highly_sensitive",
                    "payload_marker": FORBIDDEN_VALUES[2],
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

            audit_result = run_script(
                [str(ROOT / "scripts" / "encrypted_backup_envelope_audit.py"), "--backup", str(backup_path)],
                env,
            )
            assert_true(audit_result.returncode == 0, "envelope_audit_failed=true")
            audit_payload = json.loads(audit_result.stdout)
            metadata = audit_payload["encryptedBackupEnvelopeAudit"]
            assert_true(metadata["schemaVersion"] == 1, "audit_schema_failed=true")
            assert_true(metadata["kind"] == "pnh.encrypted-vault-backup", "audit_kind_failed=true")
            assert_true(metadata["algorithm"] == "AES-256-GCM", "audit_algorithm_failed=true")
            assert_true(metadata["kdf"] == "PBKDF2-HMAC-SHA256", "audit_kdf_failed=true")
            assert_true(metadata["kdfIterations"] == 390_000, "audit_kdf_iterations_failed=true")
            assert_true(isinstance(metadata["ciphertextBytes"], int), "audit_ciphertext_bytes_failed=true")
            assert_true(metadata["ciphertextBytes"] > 0, "audit_ciphertext_empty=true")
            assert_true(metadata["valuesPrinted"] is False, "audit_values_printed_failed=true")
            assert_true(
                sorted(metadata.keys())
                == [
                    "algorithm",
                    "ciphertextBytes",
                    "kdf",
                    "kdfIterations",
                    "kind",
                    "schemaVersion",
                    "valuesPrinted",
                ],
                "audit_unsafe_metadata_keys=true",
            )

            unsupported_backup(backup_path, unsupported_path)
            assert_no_forbidden_file(unsupported_path)
            unsupported_result = run_script(
                [
                    str(ROOT / "scripts" / "encrypted_backup_envelope_audit.py"),
                    "--backup",
                    str(unsupported_path),
                    "--fail-on-unsupported",
                ],
                env,
            )
            assert_true(unsupported_result.returncode == 2, "unsupported_envelope_not_detected=true")

    assert_no_forbidden_text(captured.getvalue())
    print("encrypted_backup_envelope_audit_smoke_check_pass=true")
    print("secret_value_printed=false")
    print("plaintext_found_in_backup=false")
    print("unsupported_algorithm_detected=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
