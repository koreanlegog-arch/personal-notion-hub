#!/usr/bin/env python3
"""Smoke check for phone adapter template and send rehearsal."""

from __future__ import annotations

import json
import subprocess
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


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        db_path = temp / "private" / "pnh_private_inbox.sqlite"
        token_path = temp / "private" / "auth_token"
        payload_path = temp / "payload.json"
        token = create_token(token_path, allow_external=True)
        init_private_store(db_path, allow_external=True)
        vault = init_encrypted_vault(db_path, "synthetic-phone-send-passphrase-0001")

        template = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_phone_adapter_payload_template.py"),
                "--adapter",
                "phone-recording-transcript-json",
                "--out",
                str(payload_path),
            ],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        assert_true(template.returncode == 0, template.stderr)
        assert_true(payload_path.exists(), "phone_template_not_written=true")

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
            status, schema = request_json(f"{base_url}/api/private/phone-adapter-schema", token=token)
            assert_true(status == 200 and schema.get("ok") is True, "phone_adapter_schema_failed=true")
            sender = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "pnh_phone_adapter_send.py"),
                    "--base-url",
                    base_url,
                    "--token-file",
                    str(token_path),
                    "--allow-external-token-file",
                    "--payload",
                    str(payload_path),
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            assert_true(sender.returncode == 0, sender.stderr)
            payload = json.loads(sender.stdout)
            assert_true(payload["pnhPhoneAdapterSend"] is True, "phone_adapter_send_failed=true")
            assert_true(payload["recordsAccepted"] == 1, "phone_adapter_send_count_failed=true")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    print("pnh_phone_adapter_send_smoke_check_pass=true")
    print("private_values_printed=false")
    return 0


def request_json(url: str, *, token: str = "") -> tuple[int, dict[str, Any]]:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers, method="GET")
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
