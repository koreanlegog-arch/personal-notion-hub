#!/usr/bin/env python3
"""Print private inbox status without exposing stored private values."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.encrypted_vault import EncryptedVaultError, load_vault_from_env  # noqa: E402
from companion.private_store import DEFAULT_DB_PATH, PrivateStoreError, list_captures, store_summary  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect private inbox status with redacted recent records.")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="SQLite DB path.")
    parser.add_argument("--limit", type=int, default=5, help="Recent item count.")
    parser.add_argument("--vault-passphrase-env", default="", help="Optional env var for decrypted local-only inspection.")
    parser.add_argument("--include-decrypted", action="store_true", help="Include decrypted values. Do not use for evidence.")
    args = parser.parse_args()

    db_path = Path(args.db)
    try:
        vault = None
        if args.include_decrypted:
            if not args.vault_passphrase_env:
                raise PrivateStoreError("--include-decrypted requires --vault-passphrase-env")
            vault = load_vault_from_env(db_path, args.vault_passphrase_env)
        result = {
            "privateInbox": store_summary(db_path, create_if_missing=False),
            "recent": list_captures(
                db_path,
                limit=args.limit,
                include_body=args.include_decrypted,
                create_if_missing=False,
                vault=vault,
            ),
            "privateValuesPrinted": bool(args.include_decrypted),
        }
    except (OSError, PrivateStoreError, EncryptedVaultError) as exc:
        print(f"private_inbox_status=false error={exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
