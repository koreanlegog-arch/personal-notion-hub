#!/usr/bin/env python3
"""Delete a local vault secret backend entry without printing secret values."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.secret_backends import DEFAULT_PROVIDER, DEFAULT_SECRET_NAME, SecretBackendError, delete_secret, status_to_dict  # noqa: E402


CONFIRM_PHRASE = "DELETE_VAULT_SECRET"


def main() -> int:
    parser = argparse.ArgumentParser(description="Delete a PNH vault secret backend entry.")
    parser.add_argument("--provider", default=DEFAULT_PROVIDER, help="Secret provider. Default: windows-dpapi-file.")
    parser.add_argument("--name", default=DEFAULT_SECRET_NAME, help="Secret name.")
    parser.add_argument("--path", default="", help="Optional provider-specific path.")
    parser.add_argument("--confirm", required=True, help=f"Must be exactly {CONFIRM_PHRASE}.")
    args = parser.parse_args()

    if args.confirm != CONFIRM_PHRASE:
        print("vault_secret_delete=false error=confirmation_required", file=sys.stderr)
        return 2

    try:
        status = delete_secret(name=args.name, provider=args.provider, path=args.path)
    except SecretBackendError as exc:
        print(f"vault_secret_delete=false error={exc}", file=sys.stderr)
        return 2

    print(json.dumps({"vaultSecretDelete": status_to_dict(status)}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
