#!/usr/bin/env python3
"""Audit encrypted vault metadata without decrypting or printing private values."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.encrypted_vault import ALGORITHM, KDF_ITERATIONS, KDF_NAME  # noqa: E402
from companion.private_store import DEFAULT_DB_PATH, PrivateStoreError, require_existing_store  # noqa: E402


META_KEYS = ("schema_version", "kdf_name", "kdf_iterations", "algorithm", "key_id")


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)).fetchone()
    return row is not None


def count_table(conn: sqlite3.Connection, table: str) -> int:
    if not table_exists(conn, table):
        return 0
    return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def read_meta(conn: sqlite3.Connection) -> dict[str, str]:
    if not table_exists(conn, "encrypted_vault_meta"):
        return {}
    rows = conn.execute(
        "SELECT key, value FROM encrypted_vault_meta WHERE key IN ({})".format(
            ",".join("?" for _ in META_KEYS)
        ),
        META_KEYS,
    ).fetchall()
    result: dict[str, str] = {}
    for key, value in rows:
        if key == "salt":
            continue
        if isinstance(value, bytes):
            result[str(key)] = value.decode("ascii", errors="replace")
        else:
            result[str(key)] = str(value)
    return result


def grouped_counts(conn: sqlite3.Connection, table: str, field: str) -> dict[str, int]:
    if not table_exists(conn, table):
        return {}
    return {
        str(row[0]): int(row[1])
        for row in conn.execute(f"SELECT {field}, COUNT(*) FROM {table} GROUP BY {field}").fetchall()
    }


def audit_vault_metadata(db_path: Path, *, allow_external: bool = False) -> dict[str, Any]:
    db_path = require_existing_store(db_path, allow_external=allow_external)
    with sqlite3.connect(db_path) as conn:
        meta = read_meta(conn)
        encrypted_count = count_table(conn, "encrypted_mobile_captures")
        plaintext_count = count_table(conn, "mobile_captures")
        encrypted_by_status = grouped_counts(conn, "encrypted_mobile_captures", "status")
        encrypted_by_sensitivity = grouped_counts(conn, "encrypted_mobile_captures", "sensitivity")
    unsupported: list[str] = []
    if meta.get("algorithm") not in ("", ALGORITHM):
        unsupported.append("algorithm")
    if meta.get("kdf_name") not in ("", KDF_NAME):
        unsupported.append("kdf_name")
    if meta.get("kdf_iterations") not in ("", str(KDF_ITERATIONS)):
        unsupported.append("kdf_iterations")
    return {
        "dbPath": safe_path_label(db_path),
        "encryptedVaultPresent": bool(meta),
        "schemaVersion": meta.get("schema_version", ""),
        "algorithm": meta.get("algorithm", ""),
        "kdf": meta.get("kdf_name", ""),
        "kdfIterations": meta.get("kdf_iterations", ""),
        "keyIdPresent": bool(meta.get("key_id")),
        "encryptedCaptureCount": encrypted_count,
        "plaintextCaptureCount": plaintext_count,
        "encryptedByStatus": encrypted_by_status,
        "encryptedBySensitivity": encrypted_by_sensitivity,
        "unsupportedFields": unsupported,
        "valuesPrinted": False,
        "dbMutated": False,
    }


def safe_path_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return "[outside-project-private-store]"


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit encrypted vault metadata without decrypting private values.")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Private inbox SQLite DB path.")
    parser.add_argument("--allow-external-private-paths", action="store_true", help="Allow DB path outside companion/private for tests or explicit local operations.")
    parser.add_argument("--fail-on-unsupported", action="store_true", help="Exit 1 when unsupported metadata is found.")
    args = parser.parse_args()

    try:
        result = audit_vault_metadata(Path(args.db), allow_external=args.allow_external_private_paths)
    except (OSError, PrivateStoreError, sqlite3.Error) as exc:
        print(f"encrypted_vault_metadata_audit=false error={exc}", file=sys.stderr)
        return 2

    print(json.dumps({"encryptedVaultMetadataAudit": result}, ensure_ascii=False, sort_keys=True))
    if args.fail_on_unsupported and result["unsupportedFields"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
