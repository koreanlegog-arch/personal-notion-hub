#!/usr/bin/env python3
"""Create an encrypted backup from the local encrypted vault."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.encrypted_vault import EncryptedVaultError, export_encrypted_backup, init_encrypted_vault  # noqa: E402
from companion.passphrase_provider import PassphraseProviderError, resolve_passphrase  # noqa: E402
from companion.private_store import DEFAULT_DB_PATH, PrivateStoreError, require_existing_store  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Create an encrypted-only Personal Notion Hub vault backup.")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Private inbox SQLite DB path.")
    parser.add_argument("--out", required=True, help="Encrypted backup output path. Use an ignored *.pnhbackup path.")
    parser.add_argument("--vault-passphrase-env", default="PNH_VAULT_PASSPHRASE", help="Env var containing the source vault passphrase.")
    parser.add_argument("--backup-passphrase-env", default="PNH_BACKUP_PASSPHRASE", help="Env var containing the backup encryption passphrase.")
    parser.add_argument("--prompt-vault-passphrase", action="store_true", help="Prompt for source vault passphrase without echo.")
    parser.add_argument("--prompt-backup-passphrase", action="store_true", help="Prompt for backup encryption passphrase without echo.")
    parser.add_argument("--confirm-backup-passphrase", action="store_true", help="Prompt twice and require matching backup passphrase.")
    parser.add_argument("--vault-passphrase-provider", default="", help="Optional source vault passphrase provider.")
    parser.add_argument("--vault-passphrase-name", default="vault-passphrase", help="Provider secret name.")
    parser.add_argument("--vault-passphrase-file", default="", help="Provider-specific secret file path.")
    parser.add_argument("--backup-passphrase-provider", default="", help="Optional backup passphrase provider.")
    parser.add_argument("--backup-passphrase-name", default="vault-passphrase", help="Provider backup secret name.")
    parser.add_argument("--backup-passphrase-file", default="", help="Provider-specific backup secret file path.")
    parser.add_argument("--allow-external-private-paths", action="store_true", help="Allow DB path outside companion/private for tests or explicit local operations.")
    args = parser.parse_args()

    try:
        db_path = require_existing_store(Path(args.db), allow_external=args.allow_external_private_paths)
        vault_passphrase = resolve_passphrase(
            env_name=args.vault_passphrase_env,
            label="vault",
            prompt=args.prompt_vault_passphrase,
            provider=args.vault_passphrase_provider,
            secret_name=args.vault_passphrase_name,
            secret_path=args.vault_passphrase_file,
        ).value
        backup_passphrase = resolve_passphrase(
            env_name=args.backup_passphrase_env,
            label="backup",
            prompt=args.prompt_backup_passphrase,
            confirm=args.confirm_backup_passphrase,
            provider=args.backup_passphrase_provider,
            secret_name=args.backup_passphrase_name,
            secret_path=args.backup_passphrase_file,
        ).value
        result = export_encrypted_backup(
            init_encrypted_vault(db_path, vault_passphrase),
            args.out,
            backup_passphrase,
        )
    except (OSError, PrivateStoreError, EncryptedVaultError, PassphraseProviderError) as exc:
        print(f"encrypted_vault_backup=false error={exc}", file=sys.stderr)
        return 2

    print(json.dumps({"encryptedVaultBackup": result}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
