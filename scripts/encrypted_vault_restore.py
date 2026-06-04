#!/usr/bin/env python3
"""Restore encrypted captures from an encrypted vault backup."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.encrypted_vault import EncryptedVaultError, init_encrypted_vault, restore_encrypted_backup  # noqa: E402
from companion.passphrase_provider import PassphraseProviderError, resolve_passphrase  # noqa: E402
from companion.private_store import DEFAULT_DB_PATH, PrivateStoreError, init_private_store  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore an encrypted Personal Notion Hub vault backup.")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Target private inbox SQLite DB path.")
    parser.add_argument("--backup", required=True, help="Encrypted backup file path.")
    parser.add_argument("--vault-passphrase-env", default="PNH_VAULT_PASSPHRASE", help="Env var containing the target vault passphrase.")
    parser.add_argument("--backup-passphrase-env", default="PNH_BACKUP_PASSPHRASE", help="Env var containing the backup decryption passphrase.")
    parser.add_argument("--prompt-vault-passphrase", action="store_true", help="Prompt for target vault passphrase without echo.")
    parser.add_argument("--prompt-backup-passphrase", action="store_true", help="Prompt for backup decryption passphrase without echo.")
    parser.add_argument("--vault-passphrase-provider", default="", help="Optional target vault passphrase provider.")
    parser.add_argument("--vault-passphrase-name", default="vault-passphrase", help="Provider secret name.")
    parser.add_argument("--vault-passphrase-file", default="", help="Provider-specific secret file path.")
    parser.add_argument("--replace", action="store_true", help="Replace existing encrypted captures with matching IDs.")
    parser.add_argument("--allow-external-private-paths", action="store_true", help="Allow DB path outside companion/private for tests or explicit local operations.")
    args = parser.parse_args()

    try:
        db_path = init_private_store(Path(args.db), allow_external=args.allow_external_private_paths)
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
        ).value
        result = restore_encrypted_backup(
            init_encrypted_vault(db_path, vault_passphrase),
            args.backup,
            backup_passphrase,
            replace=args.replace,
        )
    except (OSError, PrivateStoreError, EncryptedVaultError, PassphraseProviderError) as exc:
        print(f"encrypted_vault_restore=false error={exc}", file=sys.stderr)
        return 2

    print(json.dumps({"encryptedVaultRestore": result}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
