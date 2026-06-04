#!/usr/bin/env python3
"""Print keychain/passphrase readiness without exposing secrets."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.passphrase_provider import keychain_readiness  # noqa: E402


def main() -> int:
    print(json.dumps({"keychainReadiness": keychain_readiness()}, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
