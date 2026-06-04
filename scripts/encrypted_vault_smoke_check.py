#!/usr/bin/env python3
"""Smoke self-test for the encrypted SQLite vault MVP."""

from __future__ import annotations

import contextlib
import io
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from http.client import HTTPResponse
from pathlib import Path
from unittest import mock
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.encrypted_vault import ALGORITHM, EncryptedVaultError, init_encrypted_vault, load_vault_from_env  # noqa: E402
from companion.private_store import create_token, init_private_store, insert_capture, list_captures, store_summary  # noqa: E402
from companion.server import create_server  # noqa: E402


FORBIDDEN_VALUES = (
    "synthetic-vault-secret-title-9d2a0d",
    "synthetic-vault-secret-body-6fb31b",
    "synthetic-vault-secret-payload-4d92aa",
)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def assert_no_secret_output(text: str) -> None:
    for value in FORBIDDEN_VALUES:
        assert_true(value not in text, "secret_value_printed=true")


def assert_no_forbidden_values(payload: dict[str, Any]) -> None:
    response_text = json.dumps(payload, ensure_ascii=False)
    for value in FORBIDDEN_VALUES:
        assert_true(value not in response_text, "private_value_leaked=true")


def read_capture_row(db_path: Path, capture_id: str) -> sqlite3.Row:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM encrypted_mobile_captures WHERE id = ?", (capture_id,)).fetchone()
    if row is None:
        raise SystemExit("encrypted_capture_missing=true")
    return row


def request_json(
    url: str,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    token: str | None = None,
) -> tuple[int, dict[str, Any]]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, _decode_json(response)
    except urllib.error.HTTPError as exc:
        return exc.code, _decode_json(exc)


def _decode_json(response: HTTPResponse | urllib.error.HTTPError) -> dict[str, Any]:
    raw_body = response.read().decode("utf-8")
    if not raw_body:
        return {}
    return json.loads(raw_body)


def count_unique_nonces(db_path: Path) -> int:
    with sqlite3.connect(db_path) as conn:
        return conn.execute("SELECT COUNT(DISTINCT nonce) FROM encrypted_mobile_captures").fetchone()[0]


def tamper_ciphertext(db_path: Path, capture_id: str) -> None:
    with sqlite3.connect(db_path) as conn:
        ciphertext = conn.execute(
            "SELECT ciphertext FROM encrypted_mobile_captures WHERE id = ?",
            (capture_id,),
        ).fetchone()[0]
        tampered = bytearray(ciphertext)
        tampered[-1] ^= 1
        conn.execute(
            "UPDATE encrypted_mobile_captures SET ciphertext = ? WHERE id = ?",
            (bytes(tampered), capture_id),
        )


def assert_missing_crypto_fails_closed(db_path: Path) -> None:
    real_import = __import__

    def guarded_import(name: str, *args: object, **kwargs: object) -> object:
        if name.startswith("cryptography"):
            raise ImportError("synthetic cryptography absence")
        return real_import(name, *args, **kwargs)

    with mock.patch("builtins.__import__", guarded_import):
        try:
            init_encrypted_vault(db_path, "synthetic-passphrase-without-crypto")
        except EncryptedVaultError:
            return
    raise SystemExit("missing_cryptography_fail_closed_failed=true")


def assert_server_startup_gates(temp_root: Path, db_path: Path, token_path: Path) -> None:
    no_private = subprocess.run(
        [
            sys.executable,
            str(ROOT / "companion" / "server.py"),
            "--enable-encrypted-vault",
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert_true(no_private.returncode == 2, "encrypted_vault_without_private_inbox_started=true")

    missing_env = subprocess.run(
        [
            sys.executable,
            str(ROOT / "companion" / "server.py"),
            "--enable-private-inbox",
            "--enable-encrypted-vault",
            "--private-db",
            str(db_path),
            "--token-file",
            str(token_path),
            "--vault-passphrase-env",
            "PNH_SYNTHETIC_MISSING_VAULT_ENV",
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert_true(missing_env.returncode == 2, "encrypted_vault_missing_passphrase_started=true")
    assert_no_secret_output(missing_env.stdout + missing_env.stderr)


def assert_db_does_not_contain_forbidden_values(db_path: Path) -> None:
    db_bytes = db_path.read_bytes()
    for value in FORBIDDEN_VALUES:
        assert_true(value.encode("utf-8") not in db_bytes, "plaintext_found_in_db=true")


def main() -> int:
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "encrypted_vault.sqlite"
            assert_missing_crypto_fails_closed(Path(temp_dir) / "missing_crypto.sqlite")
            passphrase = "synthetic-passphrase-for-smoke-check"
            wrong_passphrase = "synthetic-wrong-passphrase-check"
            record = {
                "id": "synthetic-capture-001",
                "source": "mobile",
                "kind": "voice_note",
                "title": FORBIDDEN_VALUES[0],
                "body": FORBIDDEN_VALUES[1],
                "sensitivity": "highly_sensitive",
                "payload_marker": FORBIDDEN_VALUES[2],
            }

            vault = init_encrypted_vault(db_path, passphrase)
            metadata = vault.encrypt_capture_record(record)
            row = read_capture_row(db_path, metadata["id"])
            assert_true(metadata.get("encrypted") is True, "encrypted_metadata_missing=true")
            assert_true(metadata.get("storageMode") == "encrypted-vault", "storage_mode_contract_failed=true")
            assert_true(metadata.get("algorithm") == ALGORITHM, "algorithm_contract_failed=true")

            assert_db_does_not_contain_forbidden_values(db_path)
            assert_true(b"title" not in row["ciphertext"], "field_name_found_in_ciphertext=true")

            decrypted = vault.decrypt_capture_row(row)
            assert_true(decrypted["title"] == FORBIDDEN_VALUES[0], "decrypted_title_mismatch=true")
            assert_true(decrypted["body"] == FORBIDDEN_VALUES[1], "decrypted_body_mismatch=true")
            assert_true(FORBIDDEN_VALUES[2] in decrypted["payload_json"], "decrypted_payload_mismatch=true")

            wrong_vault = init_encrypted_vault(db_path, wrong_passphrase)
            try:
                wrong_vault.decrypt_capture_row(row)
            except EncryptedVaultError:
                pass
            else:
                raise SystemExit("wrong_passphrase_accepted=true")

            second_record = dict(record)
            second_record["id"] = "synthetic-capture-002"
            second_record["title"] = FORBIDDEN_VALUES[0] + "-second"
            second_metadata = vault.encrypt_capture_record(second_record)
            assert_true(second_metadata["id"] == "synthetic-capture-002", "second_encrypted_write_failed=true")
            assert_true(count_unique_nonces(db_path) == 2, "nonce_reuse_detected=true")

            tamper_ciphertext(db_path, metadata["id"])
            tampered_row = read_capture_row(db_path, metadata["id"])
            try:
                vault.decrypt_capture_row(tampered_row)
            except EncryptedVaultError:
                pass
            else:
                raise SystemExit("tampered_ciphertext_accepted=true")

            integration_db = Path(temp_dir) / "private" / "pnh_private_inbox.sqlite"
            token_path = Path(temp_dir) / "private" / "auth_token"
            init_private_store(integration_db, allow_external=True)
            token = create_token(token_path, allow_external=True)
            assert_server_startup_gates(Path(temp_dir), integration_db, token_path)

            env_name = "PNH_SYNTHETIC_VAULT_PASSPHRASE"
            os.environ[env_name] = passphrase
            try:
                integration_vault = load_vault_from_env(integration_db, env_name)
                direct_capture = insert_capture(
                    integration_db,
                    record,
                    allow_external=True,
                    vault=integration_vault,
                )
                assert_true(direct_capture.get("encrypted") is True, "direct_encrypted_insert_failed=true")
                assert_db_does_not_contain_forbidden_values(integration_db)

                server = create_server(
                    "127.0.0.1",
                    0,
                    private_db_path=integration_db,
                    auth_token=token,
                    allow_external_private_paths=True,
                    private_vault=integration_vault,
                )
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                host, port = server.server_address[:2]
                base_url = f"http://{host}:{port}"
                try:
                    status, health = request_json(f"{base_url}/api/health")
                    assert_true(status == 200, "encrypted_health_failed=true")
                    assert_true(health.get("storageMode") == "encrypted-vault", "encrypted_health_mode_failed=true")
                    assert_true(health.get("encryptedVault", {}).get("enabled") is True, "encrypted_health_flag_failed=true")

                    status, missing_auth = request_json(f"{base_url}/api/private/mobile-captures", "POST", record)
                    assert_true(status == 401, "encrypted_missing_auth_rejection_failed=true")
                    assert_no_forbidden_values(missing_auth)

                    server_record = dict(record)
                    server_record["id"] = "synthetic-server-capture-003"
                    status, stored = request_json(
                        f"{base_url}/api/private/mobile-captures",
                        "POST",
                        server_record,
                        token=token,
                    )
                    assert_true(status == 201 and stored.get("writesPerformed") is True, "encrypted_server_write_failed=true")
                    assert_true(stored.get("capture", {}).get("encrypted") is True, "encrypted_server_metadata_failed=true")
                    assert_no_forbidden_values(stored)

                    status, summary = request_json(f"{base_url}/api/private/summary", token=token)
                    assert_true(status == 200, "encrypted_summary_failed=true")
                    assert_true(summary.get("summary", {}).get("totalCaptures") == 2, "encrypted_summary_count_failed=true")
                    assert_true(summary.get("summary", {}).get("byStorageMode", {}).get("encrypted-vault") == 2, "encrypted_summary_mode_failed=true")
                    assert_no_forbidden_values(summary)

                    status, listed = request_json(f"{base_url}/api/private/mobile-captures", token=token)
                    assert_true(status == 200 and len(listed.get("items", [])) == 2, "encrypted_list_failed=true")
                    assert_no_forbidden_values(listed)
                    assert_db_does_not_contain_forbidden_values(integration_db)

                    decrypted_recent = list_captures(
                        integration_db,
                        include_body=True,
                        allow_external=True,
                        vault=integration_vault,
                    )
                    assert_true(
                        any(item.get("body") == FORBIDDEN_VALUES[1] for item in decrypted_recent),
                        "encrypted_private_store_decrypt_failed=true",
                    )
                    redacted_recent = list_captures(integration_db, include_body=False, allow_external=True)
                    assert_no_forbidden_values({"items": redacted_recent})
                    local_summary = store_summary(integration_db, allow_external=True)
                    assert_true(local_summary["byStorageMode"]["encrypted-vault"] == 2, "encrypted_local_summary_failed=true")
                finally:
                    server.shutdown()
                    server.server_close()
                    thread.join(timeout=5)
            finally:
                os.environ.pop(env_name, None)

    assert_no_secret_output(captured.getvalue())
    print("encrypted_vault_smoke_check_pass=true")
    print("secret_value_printed=false")
    print("plaintext_found_in_db=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
