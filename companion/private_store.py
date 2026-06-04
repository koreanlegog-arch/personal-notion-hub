"""Private local inbox storage for Personal Notion Hub.

This module uses Python stdlib only. It stores private mobile captures in an
ignored local SQLite file and never prints stored values.
"""

from __future__ import annotations

import json
import os
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .encrypted_vault import EncryptedVault
except ImportError:  # pragma: no cover - supports direct script execution through server import fallback.
    from encrypted_vault import EncryptedVault  # type: ignore


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRIVATE_DIR = ROOT / "companion" / "private"
DEFAULT_DB_PATH = DEFAULT_PRIVATE_DIR / "pnh_private_inbox.sqlite"
DEFAULT_TOKEN_PATH = DEFAULT_PRIVATE_DIR / "auth_token"
SCHEMA_VERSION = 1
MAX_CAPTURE_BYTES = 128 * 1024
ALLOWED_SOURCES = {
    "mobile",
    "mobile_web",
    "phone_note",
    "project_brief",
    "calendar",
    "routine",
    "call_note",
    "voice_note",
    "manual",
}
ALLOWED_SENSITIVITY = {"internal", "private", "highly_sensitive"}


class PrivateStoreError(ValueError):
    """Raised when private inbox input or storage setup is invalid."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ensure_private_dir(path: Path = DEFAULT_PRIVATE_DIR) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path, 0o700)
    except OSError:
        pass
    return path


def create_token(path: Path = DEFAULT_TOKEN_PATH, *, overwrite: bool = False, allow_external: bool = False) -> str:
    path = resolve_private_file(path, "auth token path", allow_external=allow_external)
    ensure_private_dir(path.parent)
    if path.exists() and not overwrite:
        apply_private_file_mode(path)
        return read_token(path, allow_external=allow_external)
    token = secrets.token_urlsafe(32)
    path.write_text(token + "\n", encoding="utf-8")
    apply_private_file_mode(path)
    return token


def read_token(path: Path = DEFAULT_TOKEN_PATH, *, allow_external: bool = False) -> str:
    path = resolve_private_file(path, "auth token path", allow_external=allow_external)
    token = path.read_text(encoding="utf-8").strip()
    if len(token) < 32:
        raise PrivateStoreError("auth token is missing or too short")
    return token


def init_private_store(db_path: Path = DEFAULT_DB_PATH, *, allow_external: bool = False) -> Path:
    db_path = resolve_private_file(db_path, "private DB path", allow_external=allow_external)
    ensure_private_dir(db_path.parent)
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA journal_mode=DELETE")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS meta (
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS mobile_captures (
              id TEXT PRIMARY KEY,
              source TEXT NOT NULL,
              kind TEXT NOT NULL,
              title TEXT NOT NULL,
              body TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              sensitivity TEXT NOT NULL,
              status TEXT NOT NULL,
              created_at TEXT NOT NULL,
              stored_at TEXT NOT NULL
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
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mobile_captures_status ON mobile_captures(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mobile_captures_stored_at ON mobile_captures(stored_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_encrypted_mobile_captures_status ON encrypted_mobile_captures(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_encrypted_mobile_captures_stored_at ON encrypted_mobile_captures(stored_at)")
        conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
            ("schema_version", str(SCHEMA_VERSION)),
        )
    try:
        apply_private_file_mode(db_path)
        apply_private_file_mode(db_path.with_suffix(db_path.suffix + "-journal"))
        apply_private_file_mode(db_path.with_suffix(db_path.suffix + "-wal"))
        apply_private_file_mode(db_path.with_suffix(db_path.suffix + "-shm"))
    except OSError:
        pass
    return db_path


def require_existing_store(db_path: Path = DEFAULT_DB_PATH, *, allow_external: bool = False) -> Path:
    db_path = resolve_private_file(db_path, "private DB path", allow_external=allow_external)
    if not db_path.exists():
        raise PrivateStoreError("private inbox database is not initialized")
    return db_path


def normalize_capture(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict) or isinstance(payload, list):
        raise PrivateStoreError("capture payload must be an object")
    encoded_size = len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    if encoded_size > MAX_CAPTURE_BYTES:
        raise PrivateStoreError("capture payload too large")

    title = compact(payload.get("title") or payload.get("summary") or "")
    body = normalize_body(payload.get("body") or payload.get("text") or payload.get("notes") or "")
    if not title:
        raise PrivateStoreError("title is required")
    if not body:
        raise PrivateStoreError("body/text/notes is required")

    source = compact(payload.get("source") or "mobile")
    if source not in ALLOWED_SOURCES:
        source = "mobile"

    kind = compact(payload.get("kind") or payload.get("type") or "project_brief")
    sensitivity = compact(payload.get("sensitivity") or "private")
    if sensitivity not in ALLOWED_SENSITIVITY:
        sensitivity = "private"

    created_at = compact(payload.get("createdAt") or payload.get("created_at") or utc_now())
    capture_id = compact(payload.get("id") or f"capture-{secrets.token_hex(12)}")

    sanitized_payload = dict(payload)
    sanitized_payload["title"] = title
    sanitized_payload["body"] = body
    sanitized_payload["source"] = source
    sanitized_payload["kind"] = kind
    sanitized_payload["sensitivity"] = sensitivity
    sanitized_payload["createdAt"] = created_at

    return {
        "id": capture_id,
        "source": source,
        "kind": kind,
        "title": title,
        "body": body,
        "payload_json": json.dumps(sanitized_payload, ensure_ascii=False, sort_keys=True),
        "sensitivity": sensitivity,
        "status": "inbox",
        "created_at": created_at,
        "stored_at": utc_now(),
    }


def insert_capture(
    db_path: Path,
    payload: Any,
    *,
    allow_external: bool = False,
    vault: EncryptedVault | None = None,
) -> dict[str, Any]:
    db_path = init_private_store(db_path, allow_external=allow_external)
    record = normalize_capture(payload)
    if vault is not None:
        if vault.db_path != db_path.resolve():
            raise PrivateStoreError("encrypted vault path does not match private DB path")
        capture = vault.encrypt_capture_record(record)
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "INSERT INTO audit_events(event_type, capture_id, source, created_at) VALUES (?, ?, ?, ?)",
                ("encrypted_mobile_capture_created", capture["id"], capture["source"], utc_now()),
            )
        return capture
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO mobile_captures (
              id, source, kind, title, body, payload_json, sensitivity, status, created_at, stored_at
            ) VALUES (
              :id, :source, :kind, :title, :body, :payload_json, :sensitivity, :status, :created_at, :stored_at
            )
            """,
            record,
        )
        conn.execute(
            "INSERT INTO audit_events(event_type, capture_id, source, created_at) VALUES (?, ?, ?, ?)",
            ("mobile_capture_created", record["id"], record["source"], utc_now()),
        )
    return {
        "id": record["id"],
        "source": record["source"],
        "kind": record["kind"],
        "sensitivity": record["sensitivity"],
        "status": record["status"],
        "storedAt": record["stored_at"],
        "storageMode": "plaintext-inbox",
        "encrypted": False,
    }


def list_captures(
    db_path: Path,
    *,
    limit: int = 20,
    include_body: bool = False,
    create_if_missing: bool = True,
    allow_external: bool = False,
    vault: EncryptedVault | None = None,
) -> list[dict[str, Any]]:
    if create_if_missing:
        db_path = init_private_store(db_path, allow_external=allow_external)
    else:
        db_path = require_existing_store(db_path, allow_external=allow_external)
    bounded_limit = min(max(int(limit), 1), 100)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        plaintext_rows = conn.execute(
            """
            SELECT id, source, kind, title, body, sensitivity, status, created_at, stored_at
            FROM mobile_captures
            ORDER BY stored_at DESC
            LIMIT ?
            """,
            (bounded_limit,),
        ).fetchall()
        encrypted_rows = conn.execute(
            """
            SELECT id, source, kind, sensitivity, status, created_at, stored_at,
                   storage_mode, key_id, algorithm, nonce, ciphertext
            FROM encrypted_mobile_captures
            ORDER BY stored_at DESC
            LIMIT ?
            """,
            (bounded_limit,),
        ).fetchall()
    result = []
    for row in plaintext_rows:
        item = {
            "id": row["id"],
            "source": row["source"],
            "kind": row["kind"],
            "title": row["title"] if include_body else redact_text(row["title"]),
            "sensitivity": row["sensitivity"],
            "status": row["status"],
            "createdAt": row["created_at"],
            "storedAt": row["stored_at"],
            "storageMode": "plaintext-inbox",
            "encrypted": False,
        }
        if include_body:
            item["body"] = row["body"]
        result.append(item)
    for row in encrypted_rows:
        if include_body and vault is not None:
            decrypted = vault.decrypt_capture_row(row)
            item = {
                "id": decrypted["id"],
                "source": decrypted["source"],
                "kind": decrypted["kind"],
                "title": decrypted["title"],
                "body": decrypted["body"],
                "sensitivity": decrypted["sensitivity"],
                "status": decrypted["status"],
                "createdAt": decrypted["created_at"],
                "storedAt": decrypted["stored_at"],
                "storageMode": "encrypted-vault",
                "encrypted": True,
            }
        else:
            item = {
                "id": row["id"],
                "source": row["source"],
                "kind": row["kind"],
                "title": "[encrypted]",
                "sensitivity": row["sensitivity"],
                "status": row["status"],
                "createdAt": row["created_at"],
                "storedAt": row["stored_at"],
                "storageMode": "encrypted-vault",
                "encrypted": True,
            }
        result.append(item)
    return sorted(result, key=lambda item: item["storedAt"], reverse=True)[:bounded_limit]


def store_summary(
    db_path: Path = DEFAULT_DB_PATH,
    *,
    create_if_missing: bool = True,
    allow_external: bool = False,
) -> dict[str, Any]:
    if create_if_missing:
        db_path = init_private_store(db_path, allow_external=allow_external)
    else:
        db_path = require_existing_store(db_path, allow_external=allow_external)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        plaintext_total = conn.execute("SELECT COUNT(*) AS count FROM mobile_captures").fetchone()["count"]
        encrypted_total = conn.execute("SELECT COUNT(*) AS count FROM encrypted_mobile_captures").fetchone()["count"]
        by_status = merge_count_maps(
            count_by(conn, "mobile_captures", "status"),
            count_by(conn, "encrypted_mobile_captures", "status"),
        )
        by_sensitivity = merge_count_maps(
            count_by(conn, "mobile_captures", "sensitivity"),
            count_by(conn, "encrypted_mobile_captures", "sensitivity"),
        )
    return {
        "dbPath": safe_path_label(db_path),
        "totalCaptures": plaintext_total + encrypted_total,
        "byStatus": by_status,
        "bySensitivity": by_sensitivity,
        "byStorageMode": {
            "plaintext-inbox": plaintext_total,
            "encrypted-vault": encrypted_total,
        },
        "encryptedVaultEnabled": encrypted_total > 0,
    }


def compact(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def normalize_body(value: Any) -> str:
    return str(value or "").replace("\r\n", "\n").strip()


def redact_text(value: str) -> str:
    text = compact(value)
    if not text:
        return ""
    return f"[redacted:{len(text)}]"


def safe_path_label(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError:
        return "[outside-project-private-store]"


def resolve_private_file(path: Path, label: str, *, allow_external: bool = False) -> Path:
    resolved = path.expanduser().resolve()
    if allow_external:
        return resolved

    private_root = DEFAULT_PRIVATE_DIR.resolve()
    try:
        resolved.relative_to(private_root)
    except ValueError as exc:
        raise PrivateStoreError(f"{label} must be under companion/private") from exc
    return resolved


def count_by(conn: sqlite3.Connection, table: str, field: str) -> dict[str, int]:
    return {
        row[field]: row["count"]
        for row in conn.execute(f"SELECT {field}, COUNT(*) AS count FROM {table} GROUP BY {field}").fetchall()
    }


def merge_count_maps(*maps: dict[str, int]) -> dict[str, int]:
    result: dict[str, int] = {}
    for count_map in maps:
        for key, value in count_map.items():
            result[key] = result.get(key, 0) + int(value)
    return result


def apply_private_file_mode(path: Path) -> None:
    if not path.exists():
        return
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
