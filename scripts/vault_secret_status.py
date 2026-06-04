#!/usr/bin/env python3
"""Report local vault secret backend status without printing secret values."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.secret_backends import DEFAULT_PROVIDER, DEFAULT_SECRET_NAME, SecretBackendError, status_secret, status_to_dict  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Check PNH vault secret backend status.")
    parser.add_argument("--provider", default=DEFAULT_PROVIDER, help="Secret provider. Default: windows-dpapi-file.")
    parser.add_argument("--name", default=DEFAULT_SECRET_NAME, help="Secret name.")
    parser.add_argument("--path", default="", help="Optional provider-specific path.")
    args = parser.parse_args()

    try:
        status = status_secret(name=args.name, provider=args.provider, path=args.path)
    except SecretBackendError as exc:
        print(f"vault_secret_status=false error={exc}", file=sys.stderr)
        return 2

    print(json.dumps({"vaultSecretStatus": status_to_dict(status)}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
