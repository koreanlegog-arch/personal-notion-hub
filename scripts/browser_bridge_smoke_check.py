#!/usr/bin/env python3
"""Smoke self-test for the local browser bridge auth and CORS boundary."""

from __future__ import annotations

import json
import subprocess
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

from companion.private_store import create_token, init_private_store, list_captures, store_summary  # noqa: E402
from companion.server import create_server  # noqa: E402


ALLOWED_ORIGIN = "http://127.0.0.1:8000"
BAD_ORIGIN = "http://localhost:8000"
FORBIDDEN_VALUES = (
    "synthetic-browser-bridge-body",
    "synthetic-browser-bridge-title",
    "synthetic-assistant-bridge-body",
    "synthetic-assistant-bridge-title",
)


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


def request_options(url: str, origin: str) -> tuple[int, dict[str, str]]:
    request = urllib.request.Request(
        url,
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization, Content-Type",
        },
        method="OPTIONS",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, dict(response.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers)


def _decode_json(response: HTTPResponse | urllib.error.HTTPError) -> dict[str, Any]:
    raw_body = response.read().decode("utf-8")
    if not raw_body:
        return {}
    return json.loads(raw_body)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def assert_no_forbidden_values(payload: dict[str, Any]) -> None:
    response_text = json.dumps(payload, ensure_ascii=False)
    for value in FORBIDDEN_VALUES:
        assert_true(value not in response_text, "private_value_leaked_in_response=true")


def assert_no_secret_values(payload: dict[str, Any], *values: str) -> None:
    response_text = json.dumps(payload, ensure_ascii=False)
    for value in values:
        assert_true(value not in response_text, "secret_value_leaked_in_response_body=true")


def assert_server_rejected(**kwargs: Any) -> None:
    try:
        create_server("127.0.0.1", 0, **kwargs)
    except ValueError:
        return
    raise SystemExit("unsafe_browser_bridge_config_accepted=true")


def main() -> int:
    assert_server_rejected(browser_bridge_enabled=True)
    assert_server_rejected(browser_bridge_enabled=True, allowed_origin="http://localhost:8000")
    assert_server_rejected(browser_bridge_enabled=True, allowed_origin="*")
    assert_server_rejected(browser_bridge_enabled=True, allowed_origin="null")
    assert_server_rejected(browser_bridge_enabled=True, allowed_origin="http://127.0.0.1:8000/app")
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "companion" / "server.py"),
            "--enable-browser-bridge",
            "--allowed-origin",
            ALLOWED_ORIGIN,
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert_true(result.returncode == 2, "browser_bridge_without_private_inbox_started=true")
    assert_true("browser_bridge_requires_private_inbox" in result.stderr, "bridge_private_inbox_gate_missing=true")

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
            browser_bridge_enabled=True,
            allowed_origin=ALLOWED_ORIGIN,
            browser_session_ttl_seconds=60,
        )
        pairing_code = server.browser_pairing_code
        assert_true(pairing_code and pairing_code != file_token, "pairing_code_not_separated_from_file_token=true")
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        host, port = server.server_address[:2]
        base_url = f"http://{host}:{port}"

        try:
            status, headers = request_options(f"{base_url}/api/private/pair", ALLOWED_ORIGIN)
            assert_true(status == 204, "allowed_origin_preflight_failed=true")
            assert_true(headers.get("Access-Control-Allow-Origin") == ALLOWED_ORIGIN, "allowed_origin_header_failed=true")
            assert_true(headers.get("Access-Control-Allow-Origin") != "*", "wildcard_cors_allowed=true")

            status, headers = request_options(f"{base_url}/api/private/pair", BAD_ORIGIN)
            assert_true(status == 403, "bad_origin_preflight_rejection_failed=true")
            assert_true(headers.get("Access-Control-Allow-Origin") is None, "bad_origin_cors_header_leaked=true")

            capture_payload = {
                "source": "mobile_web",
                "kind": "project_brief",
                "title": FORBIDDEN_VALUES[1],
                "body": FORBIDDEN_VALUES[0],
                "sensitivity": "highly_sensitive",
            }

            status, missing_auth, _headers = request_json(
                f"{base_url}/api/private/mobile-captures",
                "POST",
                capture_payload,
                origin=ALLOWED_ORIGIN,
            )
            assert_true(status == 401, "missing_browser_auth_rejection_failed=true")
            assert_no_forbidden_values(missing_auth)

            status, wrong_auth, _headers = request_json(
                f"{base_url}/api/private/mobile-captures",
                "POST",
                capture_payload,
                token="wrong-browser-session",
                origin=ALLOWED_ORIGIN,
            )
            assert_true(status == 401, "wrong_browser_auth_rejection_failed=true")
            assert_no_forbidden_values(wrong_auth)

            status, bad_origin, headers = request_json(
                f"{base_url}/api/private/mobile-captures",
                "POST",
                capture_payload,
                token=file_token,
                origin=BAD_ORIGIN,
            )
            assert_true(status == 403 and bad_origin.get("error") == "origin_not_allowed", "bad_origin_rejection_failed=true")
            assert_true(headers.get("Access-Control-Allow-Origin") is None, "bad_origin_write_cors_header_leaked=true")

            status, paired, headers = request_json(
                f"{base_url}/api/private/pair",
                "POST",
                {"pairingCode": file_token},
                origin=ALLOWED_ORIGIN,
            )
            assert_true(status == 401 and paired.get("error") == "unauthorized", "file_token_pairing_allowed=true")

            status, paired, headers = request_json(
                f"{base_url}/api/private/pair",
                "POST",
                {"pairingCode": pairing_code},
                origin=ALLOWED_ORIGIN,
            )
            browser_session = headers.get("X-PNH-Browser-Session", "")
            assert_true(status == 201 and paired.get("paired") is True, "browser_pairing_failed=true")
            assert_true(len(browser_session) >= 32, "browser_session_header_missing=true")
            assert_no_secret_values(paired, file_token, pairing_code, browser_session)

            status, replay_pair, _headers = request_json(
                f"{base_url}/api/private/pair",
                "POST",
                {"pairingCode": pairing_code},
                origin=ALLOWED_ORIGIN,
            )
            assert_true(status == 401 and replay_pair.get("error") == "unauthorized", "pairing_code_replay_allowed=true")

            status, stored, _headers = request_json(
                f"{base_url}/api/private/mobile-captures",
                "POST",
                capture_payload,
                token=browser_session,
                origin=ALLOWED_ORIGIN,
            )
            assert_true(status == 201 and stored.get("writesPerformed") is True, "session_capture_write_failed=true")
            assert_no_forbidden_values(stored)
            assert_no_secret_values(stored, file_token, browser_session)

            assistant_payload = {
                "source": "mobile_web",
                "kind": "assistant_capture",
                "title": FORBIDDEN_VALUES[3],
                "body": FORBIDDEN_VALUES[2],
                "sensitivity": "internal",
                "payloadType": "pnh_assistant_capture",
                "assistantSource": "my_memo",
            }
            status, assistant_stored, _headers = request_json(
                f"{base_url}/api/private/mobile-captures",
                "POST",
                assistant_payload,
                token=browser_session,
                origin=ALLOWED_ORIGIN,
            )
            assert_true(status == 201 and assistant_stored.get("writesPerformed") is True, "assistant_session_capture_write_failed=true")
            assert_no_forbidden_values(assistant_stored)
            assert_no_secret_values(assistant_stored, file_token, browser_session)

            status, summary, _headers = request_json(
                f"{base_url}/api/private/summary",
                token=browser_session,
                origin=ALLOWED_ORIGIN,
            )
            assert_true(status == 200, "session_summary_failed=true")
            assert_true(summary.get("summary", {}).get("totalCaptures") == 2, "session_summary_count_failed=true")
            assert_true("dbPath" not in summary.get("summary", {}), "summary_path_leaked=true")
            assert_no_forbidden_values(summary)
            assert_no_secret_values(summary, file_token, browser_session)

            status, file_bearer_summary, _headers = request_json(f"{base_url}/api/private/summary", token=file_token)
            assert_true(status == 200 and file_bearer_summary.get("summary", {}).get("totalCaptures") == 2, "file_bearer_auth_failed=true")

            local_summary = store_summary(db_path, allow_external=True)
            recent = list_captures(db_path, include_body=False, allow_external=True)
            assert_true(local_summary["totalCaptures"] == 2, "sqlite_session_write_missing=true")
            assert_true(recent and "body" not in recent[0], "redacted_list_contract_failed=true")

            print("browser_bridge_smoke_check_pass=true")
            print("token_value_printed=false")
            print("session_value_printed=false")
            print("private_response_values_printed=false")
            return 0
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
