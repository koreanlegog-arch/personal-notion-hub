#!/usr/bin/env python3
"""Create an encrypted backup from the local encrypted vault."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.encrypted_vault import EncryptedVaultError, export_encrypted_backup, load_vault_from_env  # noqa: E402
from companion.private_store import DEFAULT_DB_PATH, PrivateStoreError, require_existing_store  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an encrypted-only Personal Notion Hub vault backup.")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Private inbox SQLite DB path.")
    parser.add_argument("--out", required=True, help="Encrypted backup output path. Use an ignored *.pnhbackup path.")
    parser.add_argument("--vault-passphrase-env", default="PNH_VAULT_PASSPHRASE", help="Env var containing the source vault passphrase.")
    parser.add_argument("--backup-passphrase-env", default="PNH_BACKUP_PASSPHRASE", help="Env var containing the backup encryption passphrase.")
    parser.add_argument("--allow-external-private-paths", action="store_true", help="Allow DB path outside companion/private for tests or explicit local operations.")
    args = parser.parse_args()

    try:
        db_path = require_existing_store(Path(args.db), allow_external=args.allow_external_private_paths)
        backup_passphrase = os.environ.get(args.backup_passphrase_env)
        if not backup_passphrase:
            raise EncryptedVaultError("backup passphrase environment variable is missing")
        result = export_encrypted_backup(
            load_vault_from_env(db_path, args.vault_passphrase_env),
            args.out,
            backup_passphrase,
        )
    except (OSError, PrivateStoreError, EncryptedVaultError) as exc:
        print(f"encrypted_vault_backup=false error={exc}", file=sys.stderr)
        return 2

    print(json.dumps({"encryptedVaultBackup": result}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
