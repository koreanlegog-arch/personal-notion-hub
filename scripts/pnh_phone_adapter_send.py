#!/usr/bin/env python3
"""Send a phone adapter payload to the local companion without printing secrets."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.private_store import DEFAULT_TOKEN_PATH, PrivateStoreError, read_token  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Send a PNH phone adapter payload to the companion.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8765", help="Companion base URL.")
    parser.add_argument("--token-file", default=str(DEFAULT_TOKEN_PATH), help="Bearer token file.")
    parser.add_argument("--payload", required=True, help="Payload JSON file.")
    parser.add_argument("--allow-owner-network", action="store_true", help="Allow private LAN, tailnet, or https endpoint.")
    parser.add_argument("--allow-external-token-file", action="store_true", help="Allow token file outside companion/private for fixture tests.")
    args = parser.parse_args()

    try:
        endpoint = build_endpoint(args.base_url, allow_owner_network=args.allow_owner_network)
        token = read_token(Path(args.token_file), allow_external=args.allow_external_token_file)
        payload = json.loads(Path(args.payload).read_text(encoding="utf-8"))
        status, result = post_json(endpoint, token, payload)
    except (OSError, ValueError, PrivateStoreError, json.JSONDecodeError) as exc:
        print(f"pnh_phone_adapter_send=false error={exc}", file=sys.stderr)
        return 2

    print(
        json.dumps(
            {
                "pnhPhoneAdapterSend": status in {200, 201},
                "httpStatus": status,
                "recordsAccepted": result.get("phoneAdapterCapture", {}).get("recordsAccepted", 0),
                "captureIds": result.get("phoneAdapterCapture", {}).get("captureIds", []),
                "privateValuesPrinted": False,
                "tokenValuePrinted": False,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if status in {200, 201} else 1


def build_endpoint(base_url: str, *, allow_owner_network: bool) -> str:
    parsed = urlsplit(base_url.strip())
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("base-url must use http or https")
    if parsed.username or parsed.password:
        raise ValueError("base-url must not include userinfo")
    if parsed.query or parsed.fragment:
        raise ValueError("base-url must not include query or fragment")
    if parsed.path not in {"", "/"}:
        raise ValueError("base-url must not include a path")
    if parsed.hostname != "127.0.0.1" and not allow_owner_network:
        raise ValueError("non-loopback base-url requires --allow-owner-network")
    if parsed.port is None and parsed.scheme == "http":
        raise ValueError("http base-url must include an explicit port")
    netloc = parsed.netloc
    return f"{parsed.scheme}://{netloc}/api/private/phone-adapter-captures"


def post_json(endpoint: str, token: str, payload: dict[str, object]) -> tuple[int, dict[str, object]]:
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    opener = urllib.request.build_opener(NoRedirectHandler)
    try:
        with opener.open(request, timeout=10) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = {"error": "http_error"}
        return exc.code, parsed


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        raise urllib.error.HTTPError(req.full_url, code, "redirect_not_allowed", headers, fp)


if __name__ == "__main__":
    raise SystemExit(main())
