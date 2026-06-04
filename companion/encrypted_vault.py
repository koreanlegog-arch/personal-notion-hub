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
KDF_ITERATIONS = 390_000
SALT_BYTES = 16
NONCE_BYTES = 12
MAX_CAPTURE_BYTES = 128 * 1024
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
            "stored_at": utc_now(),
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
