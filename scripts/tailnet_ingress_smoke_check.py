#!/usr/bin/env python3
"""Synthetic smoke check for Tailscale Serve tailnet ingress boundaries."""

from __future__ import annotations

import json
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from http.client import HTTPResponse
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.private_store import create_token, init_private_store, store_summary  # noqa: E402
from companion.server import create_server  # noqa: E402


ALLOWED_ORIGIN = "https://desktop-example.tail000000.ts.net"
ALLOWED_HTTP_TAILNET_DNS_ORIGIN = "http://desktop-example.tail000000.ts.net:8765"
ALLOWED_HTTP_TAILNET_IP_ORIGIN = "http://100.64.0.1:8765"
BAD_HTTP_NON_TAILNET_ORIGIN = "http://203.0.113.10:8765"
BAD_PUBLIC_ORIGIN = "https://example.com"
FORBIDDEN_BODY = "synthetic-tailnet-ingress-body"
FORBIDDEN_TITLE = "synthetic-tailnet-ingress-title"


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def request_json(
    url: str,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    token: str | None = None,
    origin: str | None = None,
) -> tuple[int, dict[str, Any], dict[str, str]]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if origin:
        headers["Origin"] = origin
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, _decode_json(response), dict(response.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, _decode_json(exc), dict(exc.headers)


def request_text(url: str) -> tuple[int, str, dict[str, str]]:
    request = urllib.request.Request(url, headers={"Accept": "text/html"}, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, response.read().decode("utf-8", errors="replace"), dict(response.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace"), dict(exc.headers)


def _decode_json(response: HTTPResponse | urllib.error.HTTPError) -> dict[str, Any]:
    raw_body = response.read().decode("utf-8")
    if not raw_body:
        return {}
    return json.loads(raw_body)


def assert_no_private_values(payload: dict[str, Any]) -> None:
    text = json.dumps(payload, ensure_ascii=False)
    assert_true(FORBIDDEN_BODY not in text, "tailnet_ingress_private_body_leaked=true")
    assert_true(FORBIDDEN_TITLE not in text, "tailnet_ingress_private_title_leaked=true")


def assert_server_rejected(message: str, *args: Any, **kwargs: Any) -> None:
    try:
        server = create_server(*args, **kwargs)
    except ValueError:
        return
    server.server_close()
    raise SystemExit(message)


def main() -> int:
    assert_server_rejected(
        "tailnet_ingress_without_bridge_accepted=true",
        "127.0.0.1",
        0,
        tailnet_ingress_enabled=True,
        allowed_origin=ALLOWED_ORIGIN,
    )
    assert_server_rejected(
        "tailnet_ingress_non_loopback_bind_accepted=true",
        "0.0.0.0",
        0,
        tailnet_ingress_enabled=True,
        browser_bridge_enabled=True,
        allowed_origin=ALLOWED_ORIGIN,
    )
    assert_server_rejected(
        "tailnet_ingress_public_origin_accepted=true",
        "127.0.0.1",
        0,
        tailnet_ingress_enabled=True,
        browser_bridge_enabled=True,
        allowed_origin=BAD_PUBLIC_ORIGIN,
    )
    assert_server_rejected(
        "tailnet_ingress_http_non_tailnet_origin_accepted=true",
        "127.0.0.1",
        0,
        tailnet_ingress_enabled=True,
        browser_bridge_enabled=True,
        allowed_origin=BAD_HTTP_NON_TAILNET_ORIGIN,
    )
    assert_server_rejected(
        "tailnet_ingress_wildcard_origin_accepted=true",
        "127.0.0.1",
        0,
        tailnet_ingress_enabled=True,
        browser_bridge_enabled=True,
        allowed_origin="*",
    )
    for allowed_origin in (ALLOWED_HTTP_TAILNET_DNS_ORIGIN, ALLOWED_HTTP_TAILNET_IP_ORIGIN):
        server = create_server(
            "127.0.0.1",
            0,
            tailnet_ingress_enabled=True,
            browser_bridge_enabled=True,
            allowed_origin=allowed_origin,
        )
        server.server_close()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        db_path = temp_root / "private" / "pnh_private_inbox.sqlite"
        token_path = temp_root / "private" / "auth_token"
        init_private_store(db_path, allow_external=True)
        file_token = create_token(token_path, allow_external=True)

        server = create_server(
            "127.0.0.1",
            0,
            private_db_path=db_path,
            auth_token=file_token,
            allow_external_private_paths=True,
            tailnet_ingress_enabled=True,
            browser_bridge_enabled=True,
            allowed_origin=ALLOWED_ORIGIN,
            browser_session_ttl_seconds=60,
        )
        pairing_code = server.browser_pairing_code
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address[:2]
        base_url = f"http://{host}:{port}"
        try:
            status, html, headers = request_text(f"{base_url}/")
            assert_true(status == 200, "tailnet_ingress_static_root_failed=true")
            assert_true("Personal Notion Hub" in html, "tailnet_ingress_static_root_missing_app=true")
            assert_true(headers.get("Cache-Control") == "no-store", "tailnet_ingress_static_cache_policy_failed=true")

            status, health, _headers = request_json(f"{base_url}/api/health")
            assert_true(status == 200, "tailnet_ingress_health_failed=true")
            assert_true(health.get("tailnetIngress", {}).get("enabled") is True, "tailnet_ingress_health_flag_failed=true")
            assert_true(health.get("loopbackOnly") is True, "tailnet_ingress_loopback_flag_failed=true")

            status, paired, headers = request_json(
                f"{base_url}/api/private/pair",
                "POST",
                {"pairingCode": pairing_code},
                origin=ALLOWED_ORIGIN,
            )
            browser_session = headers.get("X-PNH-Browser-Session", "")
            assert_true(status == 201 and len(browser_session) >= 32, "tailnet_ingress_pairing_failed=true")

            payload = {
                "source": "mobile_web",
                "kind": "assistant_capture",
                "title": FORBIDDEN_TITLE,
                "body": FORBIDDEN_BODY,
                "sensitivity": "internal",
                "payloadType": "pnh_tailnet_ingress_capture",
            }
            status, stored, _headers = request_json(
                f"{base_url}/api/private/mobile-captures",
                "POST",
                payload,
                token=browser_session,
                origin=ALLOWED_ORIGIN,
            )
            assert_true(status == 201 and stored.get("writesPerformed") is True, "tailnet_ingress_capture_write_failed=true")
            assert_no_private_values(stored)
            summary = store_summary(db_path, allow_external=True)
            assert_true(summary["totalCaptures"] == 1, "tailnet_ingress_sqlite_write_missing=true")
        finally:
            server.shutdown()
            server.server_close()

    print("tailnet_ingress_smoke_check_pass=true")
    print("private_values_printed=false")
    print("tailnet_ingress_loopback_bind_required=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
