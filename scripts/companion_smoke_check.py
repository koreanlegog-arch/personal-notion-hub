#!/usr/bin/env python3
"""Smoke self-test for the fixture-only local companion.

The test starts the server on 127.0.0.1 with an ephemeral port and uses fake
fixture data only. It avoids printing request bodies or fixture values.
"""

from __future__ import annotations

import json
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.server import create_server  # noqa: E402


FIXTURE_PATH = ROOT / "companion" / "fixtures" / "fake_import.json"
FORBIDDEN_ARTIFACT_GLOBS = ("*.vault", "*.sqlite", "*.sqlite3", "*.db")
FORBIDDEN_ARTIFACT_DIRS = (
    ROOT / "companion" / "private",
    ROOT / "companion" / "runtime",
    ROOT / "companion" / "logs",
)


def request_json(url: str, method: str = "GET", payload: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def assert_no_private_artifacts() -> None:
    for pattern in FORBIDDEN_ARTIFACT_GLOBS:
        matches = list(ROOT.rglob(pattern))
        assert_true(not matches, f"forbidden_artifact_found={pattern}")
    for path in FORBIDDEN_ARTIFACT_DIRS:
        assert_true(not path.exists(), f"forbidden_artifact_dir_found={path.relative_to(ROOT)}")


def assert_host_rejected(host: str) -> None:
    try:
        create_server(host, 0)
    except ValueError:
        return
    raise SystemExit(f"non_127_host_rejection_failed={host}")


def assert_private_fixture_rejected(base_url: str, fixture: dict[str, Any], forbidden_values: tuple[str, ...]) -> None:
    status, redacted = request_json(f"{base_url}/api/import/preview", "POST", fixture)
    assert_true(status == 400, "private_like_preview_status_failed=true")
    assert_true(redacted.get("errors"), "private_like_error_missing=true")
    assert_true(all(value == 0 for value in redacted.get("counts", {}).values()), "private_like_counts_not_zero=true")
    response_text = json.dumps(redacted)
    for value in forbidden_values:
        assert_true(value not in response_text, "private_like_value_leaked=true")


def main() -> int:
    assert_no_private_artifacts()
    for host in ("0.0.0.0", "localhost", "::1"):
        assert_host_rejected(host)

    server = create_server("127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    host, port = server.server_address[:2]
    base_url = f"http://{host}:{port}"

    try:
        status, health = request_json(f"{base_url}/api/health")
        assert_true(status == 200 and health.get("ok") is True, "health_check_failed=true")
        assert_true(health.get("loopbackOnly") is True, "loopback_contract_failed=true")
        assert_true(health.get("writesEnabled") is False, "write_contract_failed=true")

        status, schema = request_json(f"{base_url}/api/schema")
        assert_true(status == 200, "schema_check_failed=true")
        assert_true(schema.get("mode") == "fixture-only-preview", "schema_mode_failed=true")
        assert_true(schema.get("limits", {}).get("writes") is False, "schema_write_contract_failed=true")

        fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        status, preview = request_json(f"{base_url}/api/import/preview", "POST", fixture)
        assert_true(status == 200, "preview_status_failed=true")
        assert_true(preview.get("writesPerformed") is False, "preview_write_contract_failed=true")
        assert_true(preview.get("errors") == [], "preview_errors_found=true")
        assert_true(
            preview.get("counts") == {"projects": 1, "tasks": 1, "notes": 1, "routines": 1, "links": 1},
            "preview_counts_failed=true",
        )

        private_cases = [
            (
                {
                    "schemaVersion": 1,
                    "items": [{"type": "notes", "title": "Masked fixture", "body": "sample@example.com"}],
                },
                ("sample@example.com",),
            ),
            (
                {
                    "schemaVersion": 1,
                    "items": [{"type": "notes", "title": "Masked fixture", "api_key": "sk-demoSecretToken12345"}],
                },
                ("api_key", "sk-demoSecretToken12345"),
            ),
            (
                {
                    "schemaVersion": 1,
                    "items": [{"type": "notes", "title": "Masked fixture", "body": "+1 555 010 9999"}],
                },
                ("+1 555 010 9999",),
            ),
            (
                {
                    "schemaVersion": 1,
                    "items": [{"type": "notes", "title": "Masked fixture", "body": "-----BEGIN PRIVATE KEY-----"}],
                },
                ("-----BEGIN PRIVATE KEY-----",),
            ),
        ]
        for private_fixture, forbidden_values in private_cases:
            assert_private_fixture_rejected(base_url, private_fixture, forbidden_values)

        assert_no_private_artifacts()

        print("companion_smoke_check_pass=true")
        return 0
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
