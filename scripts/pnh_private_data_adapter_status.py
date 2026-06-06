#!/usr/bin/env python3
"""Print local private data adapter registry status."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.private_adapter_registry import registry_summary  # noqa: E402


def main() -> int:
    payload = {
        "pnhPrivateDataAdapterStatus": True,
        "mode": "local-owner-exported-only",
        "liveExternalAdaptersEnabled": False,
        "externalServicesContacted": False,
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "adapters": registry_summary(),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
