#!/usr/bin/env python3
"""Smoke check for metadata-safe private ingest deduplication."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.encrypted_vault import init_encrypted_vault  # noqa: E402
from companion.private_store import create_token, init_private_store, insert_capture, store_summary  # noqa: E402
from companion.server import create_server  # noqa: E402


PASSPHRASE = "synthetic-dedup-passphrase-0001"
PRIVATE_MARKER = "PRIVATE_DEDUP_MARKER_010-1234-5678"


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        db_path = temp / "private" / "pnh_private_inbox.sqlite"
        token_path = temp / "private" / "auth_token"
        fixture = temp / "contacts.json"
        out = temp / "adapter.json"
        init_private_store(db_path, allow_external=True)
        vault = init_encrypted_vault(db_path, PASSPHRASE)
        payload = {
            "source": "contacts_json_adapter",
            "kind": "contact",
            "title": "Synthetic contact",
            "body": PRIVATE_MARKER,
            "sensitivity": "private",
        }
        first = insert_capture(db_path, payload, allow_external=True, vault=vault, dedupe=True)
        second = insert_capture(db_path, payload, allow_external=True, vault=vault, dedupe=True)
        summary = store_summary(db_path, allow_external=True)
        assert_true(first.get("duplicateSkipped") is False, "first_insert_marked_duplicate=true")
        assert_true(second.get("duplicateSkipped") is True, "second_insert_not_deduped=true")
        assert_true(summary["totalCaptures"] == 1, "dedup_direct_count_wrong=true")

        fixture.write_text(json.dumps([{"name": "Synthetic contact", "phone": PRIVATE_MARKER}], ensure_ascii=False), encoding="utf-8")
        env = os.environ.copy()
        env["PNH_DEDUP_TEST_PASSPHRASE"] = PASSPHRASE
        applied = run_adapter_import(db_path, fixture, out, env)
        assert_true(applied.returncode == 0, applied.stderr)
        combined = applied.stdout + out.read_text(encoding="utf-8")
        assert_true(PRIVATE_MARKER not in combined, "private_marker_leaked_adapter=true")
        first_adapter_result = json.loads(out.read_text(encoding="utf-8"))
        assert_true(first_adapter_result["recordsWritten"] == 1, "adapter_first_write_failed=true")

        duplicate_applied = run_adapter_import(db_path, fixture, out, env)
        assert_true(duplicate_applied.returncode == 0, duplicate_applied.stderr)
        adapter_result = json.loads(out.read_text(encoding="utf-8"))
        assert_true(adapter_result["duplicatesSkipped"] == 1, "adapter_duplicate_not_skipped=true")
        assert_true(store_summary(db_path, allow_external=True)["totalCaptures"] == 2, "dedup_adapter_count_wrong=true")

        token = create_token(token_path, allow_external=True)
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
            first_response = post_phone_adapter(
                f"http://{host}:{port}/api/private/phone-adapter-captures",
                token,
                {
                    "adapter": "phone-contacts-json",
                    "items": [
                        {
                            "title": "Synthetic contact",
                            "body": PRIVATE_MARKER,
                            "sensitivity": "private",
                        }
                    ],
                },
            )
            assert_true(first_response["phoneAdapterCapture"]["recordsWritten"] == 1, "phone_first_write_failed=true")
            response = post_phone_adapter(
                f"http://{host}:{port}/api/private/phone-adapter-captures",
                token,
                {
                    "adapter": "phone-contacts-json",
                    "items": [
                        {
                            "title": "Synthetic contact",
                            "body": PRIVATE_MARKER,
                            "sensitivity": "private",
                        }
                    ],
                },
            )
            assert_true(response["phoneAdapterCapture"]["duplicatesSkipped"] == 1, "phone_duplicate_not_skipped=true")
            assert_true(PRIVATE_MARKER not in json.dumps(response, ensure_ascii=False), "phone_response_private_leak=true")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    print("pnh_private_ingest_dedup_smoke_check_pass=true")
    print("private_values_printed=false")
    print("raw_private_body_read=false")
    return 0


def post_phone_adapter(url: str, token: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def run_adapter_import(
    db_path: Path,
    fixture: Path,
    out: Path,
    env: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "pnh_private_data_adapter_import.py"),
            "--adapter",
            "contacts-json",
            "--input",
            str(fixture),
            "--db",
            str(db_path),
            "--allow-external-db",
            "--vault-passphrase-env",
            "PNH_DEDUP_TEST_PASSPHRASE",
            "--apply",
            "--approve-real-data-adapter",
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
        env=env,
    )


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())
