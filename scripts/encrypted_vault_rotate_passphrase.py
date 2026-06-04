#!/usr/bin/env python3
"""Rotate the encrypted vault passphrase without printing secret values."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.encrypted_vault import EncryptedVaultError, rotate_vault_passphrase  # noqa: E402
from companion.passphrase_provider import PassphraseProviderError, resolve_passphrase  # noqa: E402
from companion.private_store import DEFAULT_DB_PATH, PrivateStoreError, require_existing_store  # noqa: E402


CONFIRM_PHRASE = "ROTATE_VAULT_PASSPHRASE"


def main() -> int:
    parser = argparse.ArgumentParser(description="Rotate the Personal Notion Hub encrypted vault passphrase.")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Private inbox SQLite DB path.")
    parser.add_argument("--vault-passphrase-env", default="PNH_VAULT_PASSPHRASE", help="Env var containing the current vault passphrase.")
    parser.add_argument("--new-vault-passphrase-env", default="PNH_NEW_VAULT_PASSPHRASE", help="Env var containing the new vault passphrase.")
    parser.add_argument("--prompt-vault-passphrase", action="store_true", help="Prompt for current vault passphrase without echo.")
    parser.add_argument("--prompt-new-vault-passphrase", action="store_true", help="Prompt for new vault passphrase without echo.")
    parser.add_argument("--confirm-new-vault-passphrase", action="store_true", help="Prompt twice and require matching new vault passphrase.")
    parser.add_argument("--preflight-backup", default="", help="Existing encrypted backup path to acknowledge before rotation.")
    parser.add_argument("--confirm", required=True, help=f"Must be exactly {CONFIRM_PHRASE}.")
    parser.add_argument("--dry-run", action="store_true", help="Validate inputs and count decryptable rows without mutating the vault.")
    parser.add_argument("--allow-external-private-paths", action="store_true", help="Allow DB path outside companion/private for tests or explicit local operations.")
    args = parser.parse_args()

    if args.confirm != CONFIRM_PHRASE:
        print("encrypted_vault_passphrase_rotation=false error=confirmation_required", file=sys.stderr)
        return 2
    if not args.dry_run and not args.preflight_backup:
        print("encrypted_vault_passphrase_rotation=false error=preflight_backup_required", file=sys.stderr)
        return 2
    if args.preflight_backup and not Path(args.preflight_backup).expanduser().exists():
        print("encrypted_vault_passphrase_rotation=false error=preflight_backup_missing", file=sys.stderr)
        return 2

    try:
        db_path = require_existing_store(Path(args.db), allow_external=args.allow_external_private_paths)
        current_passphrase = resolve_passphrase(
            env_name=args.vault_passphrase_env,
            label="current vault",
            prompt=args.prompt_vault_passphrase,
        ).value
        new_passphrase = resolve_passphrase(
            env_name=args.new_vault_passphrase_env,
            label="new vault",
            prompt=args.prompt_new_vault_passphrase,
            confirm=args.confirm_new_vault_passphrase,
        ).value
        if args.dry_run:
            from companion.encrypted_vault import init_encrypted_vault  # local import keeps mutation path explicit

            count = len(init_encrypted_vault(db_path, current_passphrase).list_decrypted_captures())
            result = {
                "rotated": False,
                "dryRun": True,
                "captureCount": count,
                "preflightBackupProvided": bool(args.preflight_backup),
                "secretValuePrinted": False,
            }
        else:
            result = {
                **rotate_vault_passphrase(db_path, current_passphrase, new_passphrase),
                "dryRun": False,
                "preflightBackupProvided": True,
            }
    except (OSError, PrivateStoreError, EncryptedVaultError, PassphraseProviderError) as exc:
        print(f"encrypted_vault_passphrase_rotation=false error={exc}", file=sys.stderr)
        return 2

    print(json.dumps({"encryptedVaultPassphraseRotation": result}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
