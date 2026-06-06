#!/usr/bin/env python3
"""Generate metadata-safe phone automation profile templates.

The output is intended for owner-controlled tools such as Tasker, Shortcuts, or
MacroDroid. It uses placeholders for endpoint host and bearer token and never
prints real token values.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.phone_adapter_ingest import PHONE_ADAPTERS, phone_adapter_template  # noqa: E402


DEFAULT_OUT = ROOT / "ops" / "runs" / "PNH-PHONE-AUTOMATION-PROFILE-20260606" / "phone_automation_profile.json"
DEFAULT_BASE_URL = "http://<owner-tailnet-ip>:8765"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate PNH phone automation profile templates.")
    parser.add_argument("--adapter", default="all", help="Adapter name or all.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Placeholder or owner URL.")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output JSON.")
    args = parser.parse_args()

    selected = selected_adapters(args.adapter)
    payload = {
        "pnhPhoneAutomationProfileTemplate": True,
        "baseUrl": safe_base_url(args.base_url),
        "endpoint": "/api/private/phone-adapter-captures",
        "method": "POST",
        "contentType": "application/json",
        "authHeader": "Bearer <PNH_PRIVATE_INBOX_TOKEN>",
        "tokenPlaceholderOnly": True,
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "profiles": [profile_for(name, args.base_url) for name in selected],
        "operatorWarnings": [
            "Do not paste the real bearer token into chat, docs, screenshots, or Git.",
            "Store the token only in the phone automation tool's local secret field if available.",
            "Use owner tailnet/local endpoint only until production auth is separately reviewed.",
        ],
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(redact_stdout(payload, out_path), ensure_ascii=False, sort_keys=True))
    return 0


def selected_adapters(value: str) -> list[str]:
    if value == "all":
        return sorted(PHONE_ADAPTERS)
    if value not in PHONE_ADAPTERS:
        raise SystemExit(f"unknown_phone_adapter={value}")
    return [value]


def profile_for(adapter: str, base_url: str) -> dict[str, Any]:
    template = phone_adapter_template(adapter)
    return {
        "adapter": adapter,
        "name": f"PNH {adapter}",
        "url": f"{safe_base_url(base_url).rstrip('/')}/api/private/phone-adapter-captures",
        "headers": {
            "Authorization": "Bearer <PNH_PRIVATE_INBOX_TOKEN>",
            "Content-Type": "application/json",
        },
        "bodyTemplate": template,
        "responsePolicy": "metadata-only",
    }


def safe_base_url(value: str) -> str:
    text = " ".join(str(value or "").split()).strip() or DEFAULT_BASE_URL
    if len(text) > 200:
        raise SystemExit("base_url_too_long=true")
    if any(secretish in text.lower() for secretish in ("token=", "bearer ", "password=", "secret=")):
        raise SystemExit("base_url_contains_secret_like_value=true")
    return text


def redact_stdout(payload: dict[str, Any], out_path: Path) -> dict[str, Any]:
    return {
        "pnhPhoneAutomationProfileTemplate": True,
        "profileCount": len(payload["profiles"]),
        "out": safe_path_label(out_path),
        "tokenPlaceholderOnly": True,
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
    }


def safe_path_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return "[external-path]"


if __name__ == "__main__":
    raise SystemExit(main())
