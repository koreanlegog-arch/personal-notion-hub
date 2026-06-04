"""Encrypted SQLite vault MVP for local mobile captures.

This module intentionally fails closed when ``cryptography`` is unavailable.
It uses AES-GCM through ``cryptography`` and stores only non-sensitive metadata
as plaintext. Private title/body/payload content is encrypted before SQLite
writes.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
KDF_NAME = "PBKDF2-HMAC-SHA256"
ALGORITHM = "AES-256-GCM"
BACKUP_KIND = "pnh.encrypted-vault-backup"
BACKUP_SCHEMA_VERSION = 1
KDF_ITERATIONS = 390_000
SALT_BYTES = 16
NONCE_BYTES = 12
MAX_CAPTURE_BYTES = 128 * 1024
MAX_BACKUP_BYTES = 10 * 1024 * 1024
MIN_PASSPHRASE_LENGTH = 16


class EncryptedVaultError(ValueError):
    """Raised when encrypted vault setup, input, or decryption fails."""


def _load_crypto() -> tuple[Any, Any, Any, Any]:
    try:
        from cryptography.exceptions import InvalidTag
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    except ImportError as exc:
        raise EncryptedVaultError("encrypted vault requires installed cryptography") from exc
    return AESGCM, PBKDF2HMAC, hashes, InvalidTag


def cryptography_available() -> bool:
    try:
        _load_crypto()
    except EncryptedVaultError:
        return False
    return True


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def compact(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def normalize_body(value: Any) -> str:
    return str(value or "").replace("\r\n", "\n").strip()


def require_passphrase(passphrase: str) -> str:
    if not isinstance(passphrase, str) or len(passphrase) < MIN_PASSPHRASE_LENGTH:
        raise EncryptedVaultError("vault passphrase is missing or too short")
    return passphrase


def normalize_capture_for_vault(record: Any) -> dict[str, Any]:
    if not isinstance(record, dict) or isinstance(record, list):
        raise EncryptedVaultError("capture record must be an object")
    encoded_size = len(json.dumps(record, ensure_ascii=False).encode("utf-8"))
    if encoded_size > MAX_CAPTURE_BYTES:
        raise EncryptedVaultError("capture record too large")

    title = compact(record.get("title") or record.get("summary") or "")
    body = normalize_body(record.get("body") or record.get("text") or record.get("notes") or "")
    if not title:
        raise EncryptedVaultError("title is required")
    if not body:
        raise EncryptedVaultError("body/text/notes is required")

    source = compact(record.get("source") or "mobile")
    kind = compact(record.get("kind") or record.get("type") or "capture")
    sensitivity = compact(record.get("sensitivity") or "private")
    status = compact(record.get("status") or "inbox")
    created_at = compact(record.get("created_at") or record.get("createdAt") or utc_now())
    stored_at = compact(record.get("stored_at") or record.get("storedAt") or utc_now())
    capture_id = compact(record.get("id") or f"capture-{secrets.token_hex(12)}")

    sanitized_payload = dict(record)
    sanitized_payload["title"] = title
    sanitized_payload["body"] = body
    sanitized_payload["source"] = source
    sanitized_payload["kind"] = kind
    sanitized_payload["sensitivity"] = sensitivity
    sanitized_payload["createdAt"] = created_at

    return {
        "metadata": {
            "id": capture_id,
            "source": source,
            "kind": kind,
            "sensitivity": sensitivity,
            "status": status,
            "created_at": created_at,
            "stored_at": stored_at,
            "storage_mode": "encrypted-vault",
        },
        "private": {
            "title": title,
            "body": body,
            "payload_json": json.dumps(sanitized_payload, ensure_ascii=False, sort_keys=True),
        },
    }


class EncryptedVault:
    """AES-GCM encrypted SQLite vault for mobile capture records."""

    def __init__(self, db_path: str | Path, passphrase: str) -> None:
        self.db_path = Path(db_path).expanduser().resolve()
        self.passphrase = require_passphrase(passphrase)
        AESGCM, _, _, _ = _load_crypto()
        self._aesgcm_cls = AESGCM

    def init(self) -> "EncryptedVault":
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        _apply_dir_mode(self.db_path.parent)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=DELETE")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS encrypted_vault_meta (
                  key TEXT PRIMARY KEY,
                  value BLOB NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS encrypted_mobile_captures (
                  id TEXT PRIMARY KEY,
                  source TEXT NOT NULL,
                  kind TEXT NOT NULL,
                  sensitivity TEXT NOT NULL,
                  status TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  stored_at TEXT NOT NULL,
                  storage_mode TEXT NOT NULL,
                  key_id TEXT NOT NULL,
                  algorithm TEXT NOT NULL,
                  nonce BLOB NOT NULL,
                  ciphertext BLOB NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  event_type TEXT NOT NULL,
                  capture_id TEXT,
                  source TEXT,
                  created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_encrypted_mobile_captures_status "
                "ON encrypted_mobile_captures(status)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_encrypted_mobile_captures_stored_at "
                "ON encrypted_mobile_captures(stored_at)"
            )
            conn.execute(
                "INSERT OR IGNORE INTO encrypted_vault_meta(key, value) VALUES (?, ?)",
                ("schema_version", str(SCHEMA_VERSION).encode("ascii")),
            )
            conn.execute(
                "INSERT OR IGNORE INTO encrypted_vault_meta(key, value) VALUES (?, ?)",
                ("kdf_name", KDF_NAME.encode("ascii")),
            )
            conn.execute(
                "INSERT OR IGNORE INTO encrypted_vault_meta(key, value) VALUES (?, ?)",
                ("kdf_iterations", str(KDF_ITERATIONS).encode("ascii")),
            )
            conn.execute(
                "INSERT OR IGNORE INTO encrypted_vault_meta(key, value) VALUES (?, ?)",
                ("algorithm", ALGORITHM.encode("ascii")),
            )
            conn.execute(
                "INSERT OR IGNORE INTO encrypted_vault_meta(key, value) VALUES (?, ?)",
                ("salt", os.urandom(SALT_BYTES)),
            )
            salt = _read_meta_from_conn(conn, "salt")
            key_id = _key_id(salt)
            conn.execute(
                "INSERT OR REPLACE INTO encrypted_vault_meta(key, value) VALUES (?, ?)",
                ("key_id", key_id.encode("ascii")),
            )
        self.apply_private_mode()
        return self

    @property
    def key_id(self) -> str:
        self.init()
        return self._read_meta_text("key_id")

    @property
    def algorithm(self) -> str:
        return ALGORITHM

    def encrypt_capture_record(self, record: dict[str, Any]) -> dict[str, Any]:
        self.init()
        normalized = normalize_capture_for_vault(record)
        metadata = dict(normalized["metadata"])
        metadata["key_id"] = self.key_id
        metadata["algorithm"] = ALGORITHM
        nonce = os.urandom(NONCE_BYTES)
        ciphertext = self._aesgcm_cls(self._derive_key()).encrypt(
            nonce,
            json.dumps(normalized["private"], ensure_ascii=False, sort_keys=True).encode("utf-8"),
            self._associated_data(metadata),
        )
        row = {
            **metadata,
            "nonce": nonce,
            "ciphertext": ciphertext,
        }
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO encrypted_mobile_captures (
                  id, source, kind, sensitivity, status, created_at, stored_at,
                  storage_mode, key_id, algorithm, nonce, ciphertext
                ) VALUES (
                  :id, :source, :kind, :sensitivity, :status, :created_at, :stored_at,
                  :storage_mode, :key_id, :algorithm, :nonce, :ciphertext
                )
                """,
                row,
            )
        self.apply_private_mode()
        return metadata_response(metadata)

    def decrypt_capture_row(self, row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
        data = dict(row)
        metadata = {
            "id": data["id"],
            "source": data["source"],
            "kind": data["kind"],
            "sensitivity": data["sensitivity"],
            "status": data["status"],
            "created_at": data["created_at"],
            "stored_at": data["stored_at"],
            "storage_mode": data.get("storage_mode", "encrypted-vault"),
            "key_id": data["key_id"],
            "algorithm": data["algorithm"],
        }
        if metadata["algorithm"] != ALGORITHM:
            raise EncryptedVaultError("unsupported encrypted vault algorithm")
        _, _, _, InvalidTag = _load_crypto()
        try:
            plaintext = self._aesgcm_cls(self._derive_key()).decrypt(
                data["nonce"],
                data["ciphertext"],
                self._associated_data(metadata),
            )
        except InvalidTag as exc:
            raise EncryptedVaultError("capture decryption failed") from exc
        try:
            private_payload = json.loads(plaintext.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise EncryptedVaultError("capture plaintext is invalid") from exc
        return {**metadata, **private_payload}

    def fetch_capture(self, capture_id: str) -> dict[str, Any]:
        self.init()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM encrypted_mobile_captures WHERE id = ?",
                (capture_id,),
            ).fetchone()
        if row is None:
            raise EncryptedVaultError("capture not found")
        return self.decrypt_capture_row(row)

    def list_decrypted_captures(self) -> list[dict[str, Any]]:
        self.init()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT id, source, kind, sensitivity, status, created_at, stored_at,
                       storage_mode, key_id, algorithm, nonce, ciphertext
                FROM encrypted_mobile_captures
                ORDER BY stored_at ASC, id ASC
                """
            ).fetchall()
        return [self.decrypt_capture_row(row) for row in rows]

    def _derive_key(self) -> bytes:
        _, PBKDF2HMAC, hashes, _ = _load_crypto()
        salt = self._read_meta("salt")
        iterations = int(self._read_meta_text("kdf_iterations"))
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=iterations,
        )
        return kdf.derive(self.passphrase.encode("utf-8"))

    def _associated_data(self, metadata: dict[str, Any]) -> bytes:
        return json.dumps(
            {
                "id": metadata["id"],
                "source": metadata["source"],
                "kind": metadata["kind"],
                "sensitivity": metadata["sensitivity"],
                "status": metadata["status"],
                "created_at": metadata["created_at"],
                "stored_at": metadata["stored_at"],
                "storage_mode": metadata["storage_mode"],
                "key_id": metadata["key_id"],
                "algorithm": metadata["algorithm"],
                "schema_version": SCHEMA_VERSION,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

    def _read_meta(self, key: str) -> bytes:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT value FROM encrypted_vault_meta WHERE key = ?", (key,)).fetchone()
        if row is None:
            raise EncryptedVaultError("encrypted vault metadata is missing")
        return bytes(row[0])

    def _read_meta_text(self, key: str) -> str:
        return self._read_meta(key).decode("ascii")

    def apply_private_mode(self) -> None:
        for path in (
            self.db_path,
            self.db_path.with_suffix(self.db_path.suffix + "-journal"),
            self.db_path.with_suffix(self.db_path.suffix + "-wal"),
            self.db_path.with_suffix(self.db_path.suffix + "-shm"),
        ):
            _apply_file_mode(path)


def init_encrypted_vault(db_path: str | Path, passphrase: str) -> EncryptedVault:
    return EncryptedVault(db_path, passphrase).init()


def load_vault_from_env(db_path: str | Path, env_name: str) -> EncryptedVault:
    passphrase = os.environ.get(env_name)
    if not passphrase:
        raise EncryptedVaultError("vault passphrase environment variable is missing")
    return init_encrypted_vault(db_path, passphrase)


def encrypt_capture_record(
    record: dict[str, Any],
    *,
    vault: EncryptedVault | None = None,
    db_path: str | Path | None = None,
    passphrase: str | None = None,
) -> dict[str, Any]:
    active_vault = vault or _vault_from_args(db_path, passphrase)
    return active_vault.encrypt_capture_record(record)


def decrypt_capture_row(
    row: sqlite3.Row | dict[str, Any],
    *,
    vault: EncryptedVault | None = None,
    db_path: str | Path | None = None,
    passphrase: str | None = None,
) -> dict[str, Any]:
    active_vault = vault or _vault_from_args(db_path, passphrase)
    return active_vault.decrypt_capture_row(row)


def export_encrypted_backup(
    vault: EncryptedVault,
    backup_path: str | Path,
    backup_passphrase: str,
) -> dict[str, Any]:
    vault.init()
    backup_passphrase = require_passphrase(backup_passphrase)
    captures = [_backup_capture_payload(capture) for capture in vault.list_decrypted_captures()]
    payload = {
        "schemaVersion": BACKUP_SCHEMA_VERSION,
        "kind": BACKUP_KIND,
        "exportedAt": utc_now(),
        "captureCount": len(captures),
        "captures": captures,
    }
    plaintext = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if len(plaintext) > MAX_BACKUP_BYTES:
        raise EncryptedVaultError("encrypted vault backup payload too large")

    salt = os.urandom(SALT_BYTES)
    nonce = os.urandom(NONCE_BYTES)
    envelope_header = {
        "schemaVersion": BACKUP_SCHEMA_VERSION,
        "kind": BACKUP_KIND,
        "algorithm": ALGORITHM,
        "kdf": KDF_NAME,
        "kdfIterations": KDF_ITERATIONS,
        "salt": _b64encode(salt),
        "nonce": _b64encode(nonce),
        "createdAt": utc_now(),
    }
    ciphertext = _load_crypto()[0](_derive_key_from_passphrase(backup_passphrase, salt)).encrypt(
        nonce,
        plaintext,
        _backup_associated_data(envelope_header),
    )
    envelope = {**envelope_header, "ciphertext": _b64encode(ciphertext)}

    path = Path(backup_path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(envelope, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _apply_dir_mode(path.parent)
    _apply_file_mode(path)
    return {
        "backupPath": _safe_path_label(path),
        "captureCount": len(captures),
        "encrypted": True,
        "algorithm": ALGORITHM,
        "secretValuePrinted": False,
    }


def restore_encrypted_backup(
    vault: EncryptedVault,
    backup_path: str | Path,
    backup_passphrase: str,
    *,
    replace: bool = False,
) -> dict[str, Any]:
    vault.init()
    payload = decrypt_backup_payload(backup_path, backup_passphrase)
    captures = payload.get("captures")
    if not isinstance(captures, list):
        raise EncryptedVaultError("encrypted backup captures are invalid")

    restored = 0
    skipped_existing = 0
    with sqlite3.connect(vault.db_path) as conn:
        existing_ids = {
            row[0]
            for row in conn.execute("SELECT id FROM encrypted_mobile_captures").fetchall()
        }
    for capture in captures:
        record = _restore_capture_record(capture)
        capture_id = record["id"]
        if capture_id in existing_ids:
            if not replace:
                skipped_existing += 1
                continue
            delete_encrypted_capture(vault, capture_id)
        vault.encrypt_capture_record(record)
        restored += 1
    return {
        "backupPath": _safe_path_label(Path(backup_path).expanduser().resolve()),
        "restoredCount": restored,
        "skippedExistingCount": skipped_existing,
        "replace": replace,
        "secretValuePrinted": False,
    }


def decrypt_backup_payload(backup_path: str | Path, backup_passphrase: str) -> dict[str, Any]:
    backup_passphrase = require_passphrase(backup_passphrase)
    path = Path(backup_path).expanduser().resolve()
    if not path.exists():
        raise EncryptedVaultError("encrypted backup file is missing")
    raw_text = path.read_text(encoding="utf-8")
    if len(raw_text.encode("utf-8")) > MAX_BACKUP_BYTES:
        raise EncryptedVaultError("encrypted backup file too large")
    try:
        envelope = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise EncryptedVaultError("encrypted backup is invalid JSON") from exc
    if not isinstance(envelope, dict):
        raise EncryptedVaultError("encrypted backup envelope must be an object")
    _validate_backup_envelope(envelope)
    salt = _b64decode(envelope["salt"])
    nonce = _b64decode(envelope["nonce"])
    ciphertext = _b64decode(envelope["ciphertext"])
    _, _, _, InvalidTag = _load_crypto()
    try:
        plaintext = _load_crypto()[0](_derive_key_from_passphrase(backup_passphrase, salt)).decrypt(
            nonce,
            ciphertext,
            _backup_associated_data(envelope),
        )
    except InvalidTag as exc:
        raise EncryptedVaultError("encrypted backup decryption failed") from exc
    try:
        payload = json.loads(plaintext.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EncryptedVaultError("encrypted backup payload is invalid") from exc
    if payload.get("schemaVersion") != BACKUP_SCHEMA_VERSION or payload.get("kind") != BACKUP_KIND:
        raise EncryptedVaultError("encrypted backup payload version is unsupported")
    return payload


def delete_encrypted_capture(vault: EncryptedVault, capture_id: str, *, vacuum: bool = False) -> dict[str, Any]:
    vault.init()
    normalized_id = compact(capture_id)
    if not normalized_id:
        raise EncryptedVaultError("capture id is required")
    with sqlite3.connect(vault.db_path) as conn:
        cursor = conn.execute("DELETE FROM encrypted_mobile_captures WHERE id = ?", (normalized_id,))
        deleted = cursor.rowcount
        if deleted:
            conn.execute(
                "INSERT INTO audit_events(event_type, capture_id, source, created_at) VALUES (?, ?, ?, ?)",
                ("encrypted_mobile_capture_deleted", normalized_id, "local_vault", utc_now()),
            )
        if vacuum and deleted:
            conn.commit()
            conn.execute("VACUUM")
    vault.apply_private_mode()
    return {
        "id": normalized_id,
        "deleted": bool(deleted),
        "deletedCount": int(deleted),
        "vacuumRequested": vacuum,
        "secretValuePrinted": False,
    }


def rotate_vault_passphrase(
    db_path: str | Path,
    current_passphrase: str,
    new_passphrase: str,
) -> dict[str, Any]:
    """Re-encrypt all encrypted capture rows with a new vault passphrase.

    Rotation is intentionally all-or-nothing: existing rows are decrypted before
    mutation, then metadata and rows are updated in one SQLite transaction.
    """

    current_passphrase = require_passphrase(current_passphrase)
    new_passphrase = require_passphrase(new_passphrase)
    if current_passphrase == new_passphrase:
        raise EncryptedVaultError("new vault passphrase must differ from current passphrase")

    old_vault = init_encrypted_vault(db_path, current_passphrase)
    captures = old_vault.list_decrypted_captures()
    old_key_id = old_vault.key_id
    new_salt = os.urandom(SALT_BYTES)
    new_key_id = _key_id(new_salt)
    new_key = _derive_key_from_passphrase(new_passphrase, new_salt)
    AESGCM, _, _, _ = _load_crypto()
    aesgcm = AESGCM(new_key)

    rotated_rows = []
    for capture in captures:
        metadata = {
            "id": capture["id"],
            "source": capture["source"],
            "kind": capture["kind"],
            "sensitivity": capture["sensitivity"],
            "status": capture["status"],
            "created_at": capture["created_at"],
            "stored_at": capture["stored_at"],
            "storage_mode": capture.get("storage_mode", "encrypted-vault"),
            "key_id": new_key_id,
            "algorithm": ALGORITHM,
        }
        private_payload = {
            "title": capture["title"],
            "body": capture["body"],
            "payload_json": capture["payload_json"],
        }
        nonce = os.urandom(NONCE_BYTES)
        ciphertext = aesgcm.encrypt(
            nonce,
            json.dumps(private_payload, ensure_ascii=False, sort_keys=True).encode("utf-8"),
            old_vault._associated_data(metadata),
        )
        rotated_rows.append({**metadata, "nonce": nonce, "ciphertext": ciphertext})

    with sqlite3.connect(old_vault.db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO encrypted_vault_meta(key, value) VALUES (?, ?)",
            ("salt", new_salt),
        )
        conn.execute(
            "INSERT OR REPLACE INTO encrypted_vault_meta(key, value) VALUES (?, ?)",
            ("key_id", new_key_id.encode("ascii")),
        )
        conn.executemany(
            """
            UPDATE encrypted_mobile_captures
            SET key_id = :key_id,
                algorithm = :algorithm,
                nonce = :nonce,
                ciphertext = :ciphertext
            WHERE id = :id
            """,
            rotated_rows,
        )
        conn.execute(
            "INSERT INTO audit_events(event_type, capture_id, source, created_at) VALUES (?, ?, ?, ?)",
            ("encrypted_vault_passphrase_rotated", None, "local_vault", utc_now()),
        )
    old_vault.apply_private_mode()
    return {
        "rotated": True,
        "captureCount": len(rotated_rows),
        "oldKeyId": old_key_id,
        "newKeyId": new_key_id,
        "keyChanged": old_key_id != new_key_id,
        "secretValuePrinted": False,
    }


def metadata_response(metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": metadata["id"],
        "source": metadata["source"],
        "kind": metadata["kind"],
        "sensitivity": metadata["sensitivity"],
        "status": metadata["status"],
        "storedAt": metadata["stored_at"],
        "storageMode": metadata.get("storage_mode", "encrypted-vault"),
        "encrypted": True,
        "algorithm": metadata.get("algorithm", ALGORITHM),
    }


def _backup_capture_payload(capture: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": capture["id"],
        "source": capture["source"],
        "kind": capture["kind"],
        "sensitivity": capture["sensitivity"],
        "status": capture["status"],
        "createdAt": capture["created_at"],
        "storedAt": capture["stored_at"],
        "title": capture["title"],
        "body": capture["body"],
        "payloadJson": capture["payload_json"],
    }


def _restore_capture_record(capture: Any) -> dict[str, Any]:
    if not isinstance(capture, dict):
        raise EncryptedVaultError("encrypted backup capture must be an object")
    payload_json = capture.get("payloadJson")
    if not isinstance(payload_json, str):
        raise EncryptedVaultError("encrypted backup capture payload is invalid")
    try:
        payload = json.loads(payload_json)
    except json.JSONDecodeError as exc:
        raise EncryptedVaultError("encrypted backup capture payload JSON is invalid") from exc
    if not isinstance(payload, dict):
        raise EncryptedVaultError("encrypted backup capture payload must be an object")
    payload["id"] = capture.get("id")
    payload["title"] = capture.get("title")
    payload["body"] = capture.get("body")
    payload["source"] = capture.get("source")
    payload["kind"] = capture.get("kind")
    payload["sensitivity"] = capture.get("sensitivity")
    payload["status"] = capture.get("status")
    payload["created_at"] = capture.get("createdAt")
    payload["stored_at"] = capture.get("storedAt")
    return payload


def _validate_backup_envelope(envelope: dict[str, Any]) -> None:
    expected = {
        "schemaVersion": BACKUP_SCHEMA_VERSION,
        "kind": BACKUP_KIND,
        "algorithm": ALGORITHM,
        "kdf": KDF_NAME,
        "kdfIterations": KDF_ITERATIONS,
    }
    for key, value in expected.items():
        if envelope.get(key) != value:
            raise EncryptedVaultError("encrypted backup envelope version is unsupported")
    for key in ("salt", "nonce", "ciphertext", "createdAt"):
        if not isinstance(envelope.get(key), str) or not envelope[key]:
            raise EncryptedVaultError("encrypted backup envelope is incomplete")


def _derive_key_from_passphrase(passphrase: str, salt: bytes) -> bytes:
    _, PBKDF2HMAC, hashes, _ = _load_crypto()
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=KDF_ITERATIONS,
    )
    return kdf.derive(passphrase.encode("utf-8"))


def _backup_associated_data(envelope: dict[str, Any]) -> bytes:
    return json.dumps(
        {
            "schemaVersion": envelope["schemaVersion"],
            "kind": envelope["kind"],
            "algorithm": envelope["algorithm"],
            "kdf": envelope["kdf"],
            "kdfIterations": envelope["kdfIterations"],
            "salt": envelope["salt"],
            "nonce": envelope["nonce"],
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _vault_from_args(db_path: str | Path | None, passphrase: str | None) -> EncryptedVault:
    if db_path is None or passphrase is None:
        raise EncryptedVaultError("vault, db_path, or passphrase is required")
    return init_encrypted_vault(db_path, passphrase)


def _read_meta_from_conn(conn: sqlite3.Connection, key: str) -> bytes:
    row = conn.execute("SELECT value FROM encrypted_vault_meta WHERE key = ?", (key,)).fetchone()
    if row is None:
        raise EncryptedVaultError("encrypted vault metadata is missing")
    return bytes(row[0])


def _key_id(salt: bytes) -> str:
    digest = hashlib.sha256(
        b"|".join(
            [
                ALGORITHM.encode("ascii"),
                KDF_NAME.encode("ascii"),
                str(KDF_ITERATIONS).encode("ascii"),
                salt,
            ]
        )
    ).digest()[:12]
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii")


def _b64decode(value: str) -> bytes:
    try:
        return base64.urlsafe_b64decode(value.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise EncryptedVaultError("encrypted backup base64 value is invalid") from exc


def _safe_path_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path(__file__).resolve().parents[1]))
    except ValueError:
        return "[outside-project-private-file]"


def _apply_dir_mode(path: Path) -> None:
    if not path.exists():
        return
    try:
        os.chmod(path, 0o700)
    except OSError:
        pass


def _apply_file_mode(path: Path) -> None:
    if not path.exists():
        return
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
