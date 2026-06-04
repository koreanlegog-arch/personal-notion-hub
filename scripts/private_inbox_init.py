#!/usr/bin/env python3
"""Initialize the local private inbox without printing secrets."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.encrypted_vault import EncryptedVaultError, init_encrypted_vault  # noqa: E402
from companion.passphrase_provider import PassphraseProviderError, resolve_passphrase  # noqa: E402
from companion.private_store import (  # noqa: E402
    DEFAULT_DB_PATH,
    DEFAULT_TOKEN_PATH,
    PrivateStoreError,
    create_token,
    init_private_store,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize Personal Notion Hub private inbox storage.")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="SQLite DB path.")
    parser.add_argument("--token-file", default=str(DEFAULT_TOKEN_PATH), help="Bearer token file path.")
    parser.add_argument("--enable-encrypted-vault", action="store_true", help="Initialize encrypted vault tables.")
    parser.add_argument("--vault-passphrase-env", default="PNH_VAULT_PASSPHRASE", help="Environment variable containing vault passphrase.")
    parser.add_argument("--prompt-vault-passphrase", action="store_true", help="Prompt for vault passphrase without echo instead of requiring shell input.")
    parser.add_argument("--confirm-vault-passphrase", action="store_true", help="Prompt twice and require matching vault passphrase.")
    parser.add_argument("--vault-passphrase-provider", default="", help="Optional passphrase provider, for example windows-dpapi-file.")
    parser.add_argument("--vault-passphrase-name", default="vault-passphrase", help="Provider secret name.")
    parser.add_argument("--vault-passphrase-file", default="", help="Provider-specific secret file path.")
    args = parser.parse_args()

    db_path = Path(args.db)
    token_path = Path(args.token_file)

    try:
        init_private_store(db_path)
        create_token(token_path, overwrite=False)
        if args.enable_encrypted_vault:
            vault_passphrase = resolve_passphrase(
                env_name=args.vault_passphrase_env,
                label="vault",
                prompt=args.prompt_vault_passphrase,
                confirm=args.confirm_vault_passphrase,
                provider=args.vault_passphrase_provider,
                secret_name=args.vault_passphrase_name,
                secret_path=args.vault_passphrase_file,
            ).value
            init_encrypted_vault(db_path, vault_passphrase)
    except (OSError, PrivateStoreError) as exc:
        print(f"private_inbox_initialized=false error={exc}", file=sys.stderr)
        return 2
    except (EncryptedVaultError, PassphraseProviderError) as exc:
        print(f"private_inbox_initialized=false error={exc}", file=sys.stderr)
        return 2

    print("private_inbox_initialized=true")
    print(f"db_path={display_path(db_path)}")
    print(f"token_file={display_path(token_path)}")
    print("token_set=true")
    print("token_value_printed=false")
    print(f"encrypted_vault_enabled={str(args.enable_encrypted_vault).lower()}")
    print("vault_passphrase_value_printed=false")
    print("storage_scope=local_ignored_workspace")
    return 0


def display_path(path: Path) -> Path:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT)
    except ValueError:
        return resolved


if __name__ == "__main__":
    raise SystemExit(main())
