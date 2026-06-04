#!/usr/bin/env python3
"""Restore encrypted captures from an encrypted vault backup."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.encrypted_vault import EncryptedVaultError, load_vault_from_env, restore_encrypted_backup  # noqa: E402
from companion.private_store import DEFAULT_DB_PATH, PrivateStoreError, init_private_store  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore an encrypted Personal Notion Hub vault backup.")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Target private inbox SQLite DB path.")
    parser.add_argument("--backup", required=True, help="Encrypted backup file path.")
    parser.add_argument("--vault-passphrase-env", default="PNH_VAULT_PASSPHRASE", help="Env var containing the target vault passphrase.")
    parser.add_argument("--backup-passphrase-env", default="PNH_BACKUP_PASSPHRASE", help="Env var containing the backup decryption passphrase.")
    parser.add_argument("--replace", action="store_true", help="Replace existing encrypted captures with matching IDs.")
    parser.add_argument("--allow-external-private-paths", action="store_true", help="Allow DB path outside companion/private for tests or explicit local operations.")
    args = parser.parse_args()

    try:
        db_path = init_private_store(Path(args.db), allow_external=args.allow_external_private_paths)
        backup_passphrase = os.environ.get(args.backup_passphrase_env)
        if not backup_passphrase:
            raise EncryptedVaultError("backup passphrase environment variable is missing")
        result = restore_encrypted_backup(
            load_vault_from_env(db_path, args.vault_passphrase_env),
            args.backup,
            backup_passphrase,
            replace=args.replace,
        )
    except (OSError, PrivateStoreError, EncryptedVaultError) as exc:
        print(f"encrypted_vault_restore=false error={exc}", file=sys.stderr)
        return 2

    print(json.dumps({"encryptedVaultRestore": result}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
