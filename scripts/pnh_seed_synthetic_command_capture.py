#!/usr/bin/env python3
"""Seed one synthetic encrypted PNH command capture for end-to-end rehearsal."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.encrypted_vault import EncryptedVaultError, init_encrypted_vault  # noqa: E402
from companion.passphrase_provider import PassphraseProviderError, resolve_passphrase  # noqa: E402
from companion.private_store import DEFAULT_DB_PATH, PrivateStoreError, insert_capture  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed a synthetic encrypted PNH command capture.")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Private inbox SQLite DB path.")
    parser.add_argument("--kind", default="project_brief", choices=["project_brief", "task_request", "daily_command", "urgent_approval"])
    parser.add_argument("--title", default="Synthetic PNH launch rehearsal packet", help="Synthetic title.")
    parser.add_argument("--body", default="Synthetic metadata-safe launch brief for PNH dispatch rehearsal.", help="Synthetic body.")
    parser.add_argument("--source", default="mobile_web", help="Source label.")
    parser.add_argument("--sensitivity", default="private", choices=["internal", "private", "highly_sensitive"])
    parser.add_argument("--vault-passphrase-env", default="PNH_VAULT_PASSPHRASE", help="Env var containing vault passphrase.")
    parser.add_argument("--vault-passphrase-provider", default="windows-dpapi-file", help="Passphrase provider.")
    parser.add_argument("--vault-passphrase-name", default="vault-passphrase", help="Provider secret name.")
    parser.add_argument("--vault-passphrase-file", default="", help="Provider-specific secret file path.")
    parser.add_argument("--allow-external-db", action="store_true", help="Allow a DB outside companion/private for fixture tests.")
    args = parser.parse_args()

    try:
        passphrase = resolve_passphrase(
            env_name=args.vault_passphrase_env,
            label="vault",
            provider=args.vault_passphrase_provider,
            secret_name=args.vault_passphrase_name,
            secret_path=args.vault_passphrase_file,
        ).value
        vault = init_encrypted_vault(Path(args.db), passphrase)
        capture = insert_capture(
            Path(args.db),
            {
                "source": args.source,
                "kind": args.kind,
                "title": args.title,
                "body": args.body,
                "sensitivity": args.sensitivity,
            },
            allow_external=args.allow_external_db,
            vault=vault,
        )
    except (EncryptedVaultError, PassphraseProviderError, PrivateStoreError, OSError) as exc:
        print(f"pnh_seed_synthetic_command_capture=false error={exc}", file=sys.stderr)
        return 2

    print(
        json.dumps(
            {
                "pnhSeedSyntheticCommandCapture": True,
                "captureId": capture.get("id", ""),
                "kind": capture.get("kind", ""),
                "storageMode": capture.get("storageMode", ""),
                "encrypted": bool(capture.get("encrypted")),
                "privateValuesPrinted": False,
                "secretValuePrinted": False,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
