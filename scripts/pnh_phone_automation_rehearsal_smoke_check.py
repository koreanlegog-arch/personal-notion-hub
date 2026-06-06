#!/usr/bin/env python3
"""Smoke check for synthetic phone automation rehearsal runner."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import threading
from pathlib import Path


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
        out = temp / "rehearsal.json"
        token = create_token(token_path, allow_external=True)
        init_private_store(db_path, allow_external=True)
        vault = init_encrypted_vault(db_path, "synthetic-phone-rehearsal-passphrase-0001")
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
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "pnh_phone_automation_rehearsal.py"),
                    "--adapter",
                    "phone-call-log-json",
                    "--base-url",
                    f"http://{host}:{port}",
                    "--token-file",
                    str(token_path),
                    "--allow-external-token-file",
                    "--skip-inbox-delta",
                    "--out",
                    str(out),
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            assert_true(result.returncode == 0, result.stderr)
            payload = json.loads(out.read_text(encoding="utf-8"))
            assert_true(payload["success"] is True, "rehearsal_failed=true")
            assert_true(payload["recordsAccepted"] == 1, "records_accepted_wrong=true")
            assert_true(payload["baseUrlValuePrinted"] is False, "base_url_printed=true")
            assert_true(token not in result.stdout + out.read_text(encoding="utf-8"), "token_value_leaked=true")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    print("pnh_phone_automation_rehearsal_smoke_check_pass=true")
    print("private_values_printed=false")
    return 0


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())
