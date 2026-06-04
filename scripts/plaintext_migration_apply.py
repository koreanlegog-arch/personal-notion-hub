#!/usr/bin/env python3
"""Migrate plaintext private inbox rows into the encrypted vault."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.encrypted_vault import (  # noqa: E402
    ALGORITHM,
    NONCE_BYTES,
    EncryptedVaultError,
    init_encrypted_vault,
    normalize_capture_for_vault,
)
from companion.passphrase_provider import PassphraseProviderError, resolve_passphrase  # noqa: E402
from companion.private_store import PrivateStoreError, require_existing_store, utc_now  # noqa: E402


CONFIRM_PHRASE = "MIGRATE_PLAINTEXT_TO_ENCRYPTED"


def plaintext_rows(db_path: Path) -> list[dict[str, object]]:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute("SELECT * FROM mobile_captures ORDER BY stored_at ASC, id ASC")]


def build_encrypted_row(vault: object, row: dict[str, object]) -> dict[str, object]:
    normalized = normalize_capture_for_vault(
        {
            "id": row["id"],
            "source": row["source"],
            "kind": row["kind"],
            "title": row["title"],
            "body": row["body"],
            "payload_json": row["payload_json"],
            "sensitivity": row["sensitivity"],
            "status": row["status"],
            "created_at": row["created_at"],
            "stored_at": row["stored_at"],
        }
    )
    metadata = dict(normalized["metadata"])
    metadata["key_id"] = vault.key_id
    metadata["algorithm"] = ALGORITHM
    nonce = os.urandom(NONCE_BYTES)
    ciphertext = vault._aesgcm_cls(vault._derive_key()).encrypt(
        nonce,
        json.dumps(normalized["private"], ensure_ascii=False, sort_keys=True).encode("utf-8"),
        vault._associated_data(metadata),
    )
    return {
        **metadata,
        "nonce": nonce,
        "ciphertext": ciphertext,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate plaintext private inbox rows to encrypted vault rows.")
    parser.add_argument("--db", default="companion/private/pnh_private_inbox.sqlite", help="Private inbox SQLite DB path.")
    parser.add_argument("--vault-passphrase-env", default="PNH_VAULT_PASSPHRASE", help="Env var containing vault passphrase.")
    parser.add_argument("--prompt-vault-passphrase", action="store_true", help="Prompt for vault passphrase without echo.")
    parser.add_argument("--vault-passphrase-provider", default="", help="Optional vault passphrase provider.")
    parser.add_argument("--vault-passphrase-name", default="vault-passphrase", help="Provider secret name.")
    parser.add_argument("--vault-passphrase-file", default="", help="Provider-specific secret file path.")
    parser.add_argument("--preflight-backup", default="", help="Existing local DB backup path required before mutation.")
    parser.add_argument("--confirm", default="", help=f"Must be exactly {CONFIRM_PHRASE} to mutate.")
    parser.add_argument("--dry-run", action="store_true", help="Report migratable row count without mutating the DB.")
    parser.add_argument("--allow-external-private-paths", action="store_true", help="Allow DB path outside companion/private for tests or explicit local operations.")
    args = parser.parse_args()

    if not args.dry_run:
        if args.confirm != CONFIRM_PHRASE:
            print("plaintext_migration_apply=false error=confirmation_required", file=sys.stderr)
            return 2
        if not args.preflight_backup or not Path(args.preflight_backup).expanduser().exists():
            print("plaintext_migration_apply=false error=preflight_backup_required", file=sys.stderr)
            return 2

    try:
        db_path = require_existing_store(Path(args.db), allow_external=args.allow_external_private_paths)
        rows = plaintext_rows(db_path)
        if args.dry_run:
            result = {
                "dryRun": True,
                "migrated": False,
                "migratableRowCount": len(rows),
                "deletedPlaintextRowCount": 0,
                "secretValuePrinted": False,
                "privateValuesPrinted": False,
                "dbMutated": False,
            }
        else:
            passphrase = resolve_passphrase(
                env_name=args.vault_passphrase_env,
                label="vault",
                prompt=args.prompt_vault_passphrase,
                provider=args.vault_passphrase_provider,
                secret_name=args.vault_passphrase_name,
                secret_path=args.vault_passphrase_file,
            ).value
            vault = init_encrypted_vault(db_path, passphrase)
            encrypted_rows = [build_encrypted_row(vault, row) for row in rows]
            migrated_ids = [row["id"] for row in encrypted_rows]
            with sqlite3.connect(db_path) as conn:
                conn.executemany(
                    """
                    INSERT INTO encrypted_mobile_captures (
                      id, source, kind, sensitivity, status, created_at, stored_at,
                      storage_mode, key_id, algorithm, nonce, ciphertext
                    ) VALUES (
                      :id, :source, :kind, :sensitivity, :status, :created_at, :stored_at,
                      :storage_mode, :key_id, :algorithm, :nonce, :ciphertext
                    )
                    """,
                    encrypted_rows,
                )
                conn.executemany("DELETE FROM mobile_captures WHERE id = ?", [(capture_id,) for capture_id in migrated_ids])
                conn.execute(
                    "INSERT INTO audit_events(event_type, capture_id, source, created_at) VALUES (?, ?, ?, ?)",
                    ("plaintext_mobile_captures_migrated", None, "local_migration", utc_now()),
                )
            vault.apply_private_mode()
            result = {
                "dryRun": False,
                "migrated": True,
                "migratedRowCount": len(migrated_ids),
                "deletedPlaintextRowCount": len(migrated_ids),
                "secretValuePrinted": False,
                "privateValuesPrinted": False,
                "dbMutated": True,
            }
    except (OSError, sqlite3.Error, PrivateStoreError, EncryptedVaultError, PassphraseProviderError) as exc:
        print(f"plaintext_migration_apply=false error={exc}", file=sys.stderr)
        return 2

    print(json.dumps({"plaintextMigrationApply": result}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
