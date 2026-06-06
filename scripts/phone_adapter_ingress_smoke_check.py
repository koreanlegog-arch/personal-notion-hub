#!/usr/bin/env python3
"""Smoke check for authenticated phone adapter ingress into encrypted storage."""

from __future__ import annotations

import json
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.encrypted_vault import init_encrypted_vault  # noqa: E402
from companion.private_store import create_token, init_private_store  # noqa: E402
from companion.server import create_server  # noqa: E402


PRIVATE_MARKER = "synthetic-phone-secret-value-0001"


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        db_path = temp / "private" / "pnh_private_inbox.sqlite"
        token_path = temp / "private" / "auth_token"
        passphrase = "synthetic-phone-adapter-passphrase-0001"
        token = create_token(token_path, allow_external=True)
        init_private_store(db_path, allow_external=True)
        vault = init_encrypted_vault(db_path, passphrase)
        server = create_server(
            "127.0.0.1",
            0,
            private_db_path=db_path,
            auth_token=token,
            allow_external_private_paths=True,
            private_vault=vault,
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address[:2]
        base_url = f"http://{host}:{port}"
        try:
            status, unauthorized = request_json(f"{base_url}/api/private/phone-adapter-captures", "POST", fixture())
            assert_true(status == 401 and unauthorized.get("error") == "unauthorized", "unauthorized_phone_adapter_allowed=true")

            status, accepted = request_json(
                f"{base_url}/api/private/phone-adapter-captures",
                "POST",
                fixture(),
                token=token,
            )
            assert_true(status == 201 and accepted.get("ok") is True, "phone_adapter_ingress_failed=true")
            summary = accepted["phoneAdapterCapture"]
            assert_true(summary["recordsAccepted"] == 1, "phone_adapter_record_count_failed=true")
            assert_true(summary["storageMode"] == "encrypted-vault", "phone_adapter_storage_mode_failed=true")
            assert_true(PRIVATE_MARKER not in json.dumps(accepted), "private_marker_leaked_in_response=true")

            status, listed = request_json(f"{base_url}/api/private/mobile-captures", token=token)
            assert_true(status == 200, "mobile_capture_list_failed=true")
            assert_true(PRIVATE_MARKER not in json.dumps(listed), "private_marker_leaked_in_list=true")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    print("phone_adapter_ingress_smoke_check_pass=true")
    print("private_values_printed=false")
    return 0


def fixture() -> dict[str, Any]:
    return {
        "adapter": "phone-call-log-json",
        "items": [
            {
                "title": "Synthetic call summary",
                "body": PRIVATE_MARKER,
                "sensitivity": "highly_sensitive",
            }
        ],
    }


def request_json(
    url: str,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    *,
    token: str = "",
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


if __name__ == "__main__":
    raise SystemExit(main())
