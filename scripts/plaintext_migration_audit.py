#!/usr/bin/env python3
"""Audit plaintext private inbox rows without printing private values."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.private_store import DEFAULT_DB_PATH, PrivateStoreError, require_existing_store  # noqa: E402


SAFE_GROUP_FIELDS = ("source", "kind", "sensitivity", "status")


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)).fetchone()
    return row is not None


def count_table(conn: sqlite3.Connection, table: str) -> int:
    if not table_exists(conn, table):
        return 0
    return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def grouped_counts(conn: sqlite3.Connection, table: str, field: str) -> dict[str, int]:
    if not table_exists(conn, table):
        return {}
    return {
        str(row[0]): int(row[1])
        for row in conn.execute(f"SELECT {field}, COUNT(*) FROM {table} GROUP BY {field}").fetchall()
    }


def audit_plaintext_rows(db_path: Path, *, allow_external: bool = False) -> dict[str, Any]:
    db_path = require_existing_store(db_path, allow_external=allow_external)
    with sqlite3.connect(db_path) as conn:
        plaintext_rows = count_table(conn, "mobile_captures")
        encrypted_rows = count_table(conn, "encrypted_mobile_captures")
        plaintext_by_field = {
            field: grouped_counts(conn, "mobile_captures", field)
            for field in SAFE_GROUP_FIELDS
        }
    return {
        "plaintextRowsDetected": plaintext_rows > 0,
        "plaintextRowCount": plaintext_rows,
        "encryptedRowCount": encrypted_rows,
        "plaintextByField": plaintext_by_field,
        "valuesPrinted": False,
        "dbMutated": False,
        "recommendedNextAction": "review_and_migrate_with_separate_approval" if plaintext_rows else "none",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit plaintext private inbox rows without printing private values.")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Private inbox SQLite DB path.")
    parser.add_argument("--fail-on-plaintext", action="store_true", help="Exit 1 if plaintext rows are detected.")
    parser.add_argument("--allow-external-private-paths", action="store_true", help="Allow DB path outside companion/private for tests or explicit local operations.")
    args = parser.parse_args()

    try:
        result = audit_plaintext_rows(Path(args.db), allow_external=args.allow_external_private_paths)
    except (OSError, PrivateStoreError, sqlite3.Error) as exc:
        print(f"plaintext_migration_audit=false error={exc}", file=sys.stderr)
        return 2

    print(json.dumps({"plaintextMigrationAudit": result}, ensure_ascii=False, sort_keys=True))
    if args.fail_on_plaintext and result["plaintextRowsDetected"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
