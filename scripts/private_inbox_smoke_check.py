#!/usr/bin/env python3
"""Smoke self-test for the authenticated local private inbox."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.private_store import create_token, init_private_store, list_captures, store_summary  # noqa: E402
from companion.server import create_server  # noqa: E402


FORBIDDEN_VALUES = (
    "synthetic-private-call-content",
    "synthetic-contact-010-0000-0000",
)


def request_json(
    url: str,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    token: str | None = None,
) -> tuple[int, dict[str, Any]]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def assert_no_forbidden_values(payload: dict[str, Any]) -> None:
    response_text = json.dumps(payload, ensure_ascii=False)
    for value in FORBIDDEN_VALUES:
        assert_true(value not in response_text, "private_value_leaked_in_response=true")


def assert_host_rejected(host: str) -> None:
    try:
        create_server(host, 0)
    except ValueError:
        return
    raise SystemExit(f"non_127_host_rejection_failed={host}")


def main() -> int:
    for host in ("0.0.0.0", "localhost", "::1"):
        assert_host_rejected(host)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        db_path = temp_root / "private" / "pnh_private_inbox.sqlite"
        token_path = temp_root / "private" / "auth_token"
        init_private_store(db_path, allow_external=True)
        token = create_token(token_path, allow_external=True)
        os.chmod(token_path, 0o644)
        token = create_token(token_path, allow_external=True)
        assert_true(token_path.stat().st_mode & 0o777 == 0o600, "token_permission_repair_failed=true")

        server = create_server(
            "127.0.0.1",
            0,
            private_db_path=db_path,
            auth_token=token,
            allow_external_private_paths=True,
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        host, port = server.server_address[:2]
        base_url = f"http://{host}:{port}"

        try:
            status, health = request_json(f"{base_url}/api/health")
            assert_true(status == 200 and health.get("writesEnabled") is True, "private_health_failed=true")
            assert_true(health.get("authRequired") is True, "private_auth_contract_failed=true")

            payload = {
                "source": "mobile",
                "kind": "call_note",
                "title": FORBIDDEN_VALUES[1],
                "body": FORBIDDEN_VALUES[0],
                "sensitivity": "highly_sensitive",
            }

            status, unauthorized = request_json(f"{base_url}/api/private/mobile-captures", "POST", payload)
            assert_true(status == 401, "missing_auth_rejection_failed=true")
            assert_no_forbidden_values(unauthorized)

            status, wrong_auth = request_json(
                f"{base_url}/api/private/mobile-captures",
                "POST",
                payload,
                token="wrong-token",
            )
            assert_true(status == 401, "wrong_auth_rejection_failed=true")
            assert_no_forbidden_values(wrong_auth)

            status, stored = request_json(f"{base_url}/api/private/mobile-captures", "POST", payload, token=token)
            assert_true(status == 201, "authorized_capture_status_failed=true")
            assert_true(stored.get("writesPerformed") is True, "authorized_capture_write_failed=true")
            assert_no_forbidden_values(stored)

            status, summary = request_json(f"{base_url}/api/private/summary", token=token)
            assert_true(status == 200, "private_summary_status_failed=true")
            assert_true(summary.get("summary", {}).get("totalCaptures") == 1, "private_summary_count_failed=true")
            assert_true("dbPath" not in summary.get("summary", {}), "http_summary_path_leaked=true")
            assert_no_forbidden_values(summary)

            status, listed = request_json(f"{base_url}/api/private/mobile-captures", token=token)
            assert_true(status == 200 and len(listed.get("items", [])) == 1, "private_list_failed=true")
            assert_no_forbidden_values(listed)

            status, invalid_limit = request_json(f"{base_url}/api/private/mobile-captures?limit=abc", token=token)
            assert_true(status == 400 and invalid_limit.get("error") == "invalid_limit", "invalid_limit_contract_failed=true")

            local_summary = store_summary(db_path, allow_external=True)
            assert_true(local_summary["totalCaptures"] == 1, "sqlite_summary_count_failed=true")
            recent = list_captures(db_path, include_body=False, allow_external=True)
            assert_true(recent and "body" not in recent[0], "redacted_list_contract_failed=true")

            print("private_inbox_smoke_check_pass=true")
            print("token_value_printed=false")
            print("private_response_values_printed=false")
            return 0
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
