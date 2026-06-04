#!/usr/bin/env python3
"""Delete one encrypted vault capture by ID without printing private values."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.encrypted_vault import EncryptedVaultError, delete_encrypted_capture, init_encrypted_vault  # noqa: E402
from companion.passphrase_provider import PassphraseProviderError, resolve_passphrase  # noqa: E402
from companion.private_store import DEFAULT_DB_PATH, PrivateStoreError, require_existing_store  # noqa: E402


CONFIRM_PHRASE = "DELETE_CAPTURE"


def main() -> int:
    parser = argparse.ArgumentParser(description="Delete one encrypted Personal Notion Hub vault capture.")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Private inbox SQLite DB path.")
    parser.add_argument("--capture-id", required=True, help="Encrypted capture ID to delete.")
    parser.add_argument("--vault-passphrase-env", default="PNH_VAULT_PASSPHRASE", help="Env var containing the vault passphrase.")
    parser.add_argument("--prompt-vault-passphrase", action="store_true", help="Prompt for vault passphrase without echo.")
    parser.add_argument("--vault-passphrase-provider", default="", help="Optional vault passphrase provider.")
    parser.add_argument("--vault-passphrase-name", default="vault-passphrase", help="Provider secret name.")
    parser.add_argument("--vault-passphrase-file", default="", help="Provider-specific secret file path.")
    parser.add_argument("--confirm", required=True, help=f"Must be exactly {CONFIRM_PHRASE}.")
    parser.add_argument("--vacuum", action="store_true", help="Run SQLite VACUUM after deletion. Not a forensic secure erase guarantee.")
    parser.add_argument("--allow-external-private-paths", action="store_true", help="Allow DB path outside companion/private for tests or explicit local operations.")
    args = parser.parse_args()

    if args.confirm != CONFIRM_PHRASE:
        print("encrypted_vault_delete=false error=confirmation_required", file=sys.stderr)
        return 2

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
        result = delete_encrypted_capture(
            init_encrypted_vault(db_path, vault_passphrase),
            args.capture_id,
            vacuum=args.vacuum,
        )
    except (OSError, PrivateStoreError, EncryptedVaultError, PassphraseProviderError) as exc:
        print(f"encrypted_vault_delete=false error={exc}", file=sys.stderr)
        return 2

    print(json.dumps({"encryptedVaultDelete": result}, ensure_ascii=False, sort_keys=True))
    return 0 if result["deleted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
