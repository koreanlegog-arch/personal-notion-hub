#!/usr/bin/env python3
"""Smoke check for PNH owner device credential storage semantics."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.owner_device_sessions import (  # noqa: E402
    issue_owner_device_credential,
    revoke_owner_device_credential,
    validate_owner_device_credential,
)


def main() -> int:
    temp_root = Path(tempfile.mkdtemp(prefix="pnh-owner-device-smoke-"))
    try:
        store_path = temp_root / "owner_devices.json"
        issued = issue_owner_device_credential(store_path, device_label="smoke phone", origin="http://127.0.0.1:8765")
        credential = issued["credential"]
        store = json.loads(store_path.read_text(encoding="utf-8"))
        raw_store = store_path.read_text(encoding="utf-8")
        if credential in raw_store:
            raise AssertionError("raw owner device credential stored")
        devices = store.get("devices", [])
        if not devices or not devices[0].get("credentialSalt"):
            raise AssertionError("credential salt missing")
        metadata = validate_owner_device_credential(credential, store_path, origin="http://127.0.0.1:8765")
        if metadata is None:
            raise AssertionError("issued credential did not validate")
        if validate_owner_device_credential(credential, store_path, origin="http://127.0.0.1:9999") is not None:
            raise AssertionError("origin-bound credential validated for wrong origin")
        if not revoke_owner_device_credential(credential, store_path):
            raise AssertionError("credential revoke failed")
        if validate_owner_device_credential(credential, store_path, origin="http://127.0.0.1:8765") is not None:
            raise AssertionError("revoked credential still validated")
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
    print("pnh_owner_device_sessions_smoke_check_pass=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
