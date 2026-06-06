#!/usr/bin/env python3
"""Print a synthetic phone adapter payload template."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.phone_adapter_ingest import PHONE_ADAPTERS, phone_adapter_schema, phone_adapter_template  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a synthetic PNH phone adapter payload template.")
    parser.add_argument("--adapter", choices=sorted(PHONE_ADAPTERS), default="phone-call-log-json")
    parser.add_argument("--schema", action="store_true", help="Print adapter schema instead of one payload template.")
    parser.add_argument("--out", default="", help="Optional output path.")
    args = parser.parse_args()

    payload = phone_adapter_schema() if args.schema else phone_adapter_template(args.adapter)
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(json.dumps({"pnhPhoneAdapterPayloadTemplate": True, "out": safe_path_label(out), "privateValuesPrinted": False}, sort_keys=True))
    else:
        print(text, end="")
    return 0


def safe_path_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return "[external-path]"


if __name__ == "__main__":
    raise SystemExit(main())
