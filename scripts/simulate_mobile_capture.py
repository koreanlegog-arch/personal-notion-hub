#!/usr/bin/env python3
"""Send a synthetic mobile capture to the local private inbox."""

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
    parser = argparse.ArgumentParser(description="Simulate a mobile-origin capture into the private inbox.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8765", help="Local companion base URL.")
    parser.add_argument("--token-file", default=str(DEFAULT_TOKEN_PATH), help="Bearer token file path.")
    parser.add_argument("--source", default="mobile", help="Capture source label.")
    parser.add_argument("--kind", default="project_brief", help="Capture kind.")
    parser.add_argument("--title", default="Synthetic mobile project brief", help="Capture title.")
    parser.add_argument("--body", default="Synthetic private note for workspace ingress validation.", help="Capture body.")
    parser.add_argument("--body-file", default="", help="Read capture body from a UTF-8 file, or '-' for stdin.")
    parser.add_argument("--sensitivity", default="private", choices=["internal", "private", "highly_sensitive"])
    args = parser.parse_args()

    try:
        endpoint = build_loopback_endpoint(args.base_url)
    except ValueError as exc:
        print(f"mobile_capture_sent=false error={exc}", file=sys.stderr)
        return 2

    try:
        token = read_token(Path(args.token_file))
    except (OSError, PrivateStoreError) as exc:
        print(f"mobile_capture_sent=false error={exc}", file=sys.stderr)
        return 2
    try:
        body = read_capture_body(args.body, args.body_file)
    except OSError as exc:
        print(f"mobile_capture_sent=false error={exc}", file=sys.stderr)
        return 2

    payload = {
        "source": args.source,
        "kind": args.kind,
        "title": args.title,
        "body": body,
        "sensitivity": args.sensitivity,
    }
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

    try:
        opener = urllib.request.build_opener(NoRedirectHandler)
        with opener.open(request, timeout=5) as response:
            result = json.loads(response.read().decode("utf-8"))
            print("mobile_capture_sent=true")
            print(f"http_status={response.status}")
            print(json.dumps(result, ensure_ascii=False, sort_keys=True))
            return 0
    except urllib.error.HTTPError as exc:
        error = exc.read().decode("utf-8", errors="replace")
        print("mobile_capture_sent=false")
        print(f"http_status={exc.code}")
        print(error)
        return 1


def build_loopback_endpoint(base_url: str) -> str:
    parsed = urlsplit(base_url.strip())
    if parsed.scheme != "http":
        raise ValueError("base-url must use http")
    if parsed.username or parsed.password:
        raise ValueError("base-url must not include userinfo")
    if parsed.hostname != "127.0.0.1":
        raise ValueError("base-url must target 127.0.0.1")
    if parsed.query or parsed.fragment:
        raise ValueError("base-url must not include query or fragment")
    if parsed.path not in ("", "/"):
        raise ValueError("base-url must not include a path")
    if parsed.port is None:
        raise ValueError("base-url must include an explicit port")
    return f"http://127.0.0.1:{parsed.port}/api/private/mobile-captures"


def read_capture_body(default_body: str, body_file: str) -> str:
    if not body_file:
        return default_body
    if body_file == "-":
        return sys.stdin.read().strip()
    return Path(body_file).read_text(encoding="utf-8").strip()


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        raise urllib.error.HTTPError(req.full_url, code, "redirect_not_allowed", headers, fp)


if __name__ == "__main__":
    raise SystemExit(main())
