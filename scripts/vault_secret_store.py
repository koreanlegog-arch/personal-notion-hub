#!/usr/bin/env python3
"""Store a vault passphrase in an approved local secret backend."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.passphrase_provider import PassphraseProviderError, resolve_passphrase  # noqa: E402
from companion.secret_backends import (  # noqa: E402
    DEFAULT_PROVIDER,
    DEFAULT_SECRET_NAME,
    SecretBackendError,
    status_to_dict,
    store_secret,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Store a PNH vault passphrase without printing the value.")
    parser.add_argument("--provider", default=DEFAULT_PROVIDER, help="Secret provider. Default: windows-dpapi-file.")
    parser.add_argument("--name", default=DEFAULT_SECRET_NAME, help="Secret name.")
    parser.add_argument("--path", default="", help="Optional provider-specific path for tests or explicit local use.")
    parser.add_argument("--passphrase-env", default="PNH_VAULT_PASSPHRASE", help="Env var containing passphrase when prompt is not used.")
    parser.add_argument("--prompt", action="store_true", help="Prompt for passphrase without echo.")
    parser.add_argument("--confirm", action="store_true", help="Prompt twice and require matching passphrase.")
    args = parser.parse_args()

    try:
        passphrase = resolve_passphrase(
            env_name=args.passphrase_env,
            label="vault",
            prompt=args.prompt,
            confirm=args.confirm,
        ).value
        status = store_secret(passphrase, name=args.name, provider=args.provider, path=args.path)
    except (PassphraseProviderError, SecretBackendError) as exc:
        print(f"vault_secret_store=false error={exc}", file=sys.stderr)
        return 2

    print(json.dumps({"vaultSecretStore": status_to_dict(status)}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
