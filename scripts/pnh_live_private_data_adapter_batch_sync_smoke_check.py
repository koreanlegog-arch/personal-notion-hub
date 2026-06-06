#!/usr/bin/env python3
"""Smoke check for live private data adapter batch readiness."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        out = Path(temp_dir) / "batch.json"
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_live_private_data_adapter_batch_sync.py"),
                "--out",
                str(out),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert_true(result.returncode == 0, result.stderr)
        payload = json.loads(result.stdout)
        assert_true(payload["pnhLivePrivateDataAdapterBatchSync"] is True, "batch_flag_missing=true")
        assert_true(payload["mode"] == "readiness", "unexpected_batch_mode=true")
        assert_true(payload["externalServicesContacted"] is False, "external_service_contacted=true")
        assert_true(payload["privateValuesPrinted"] is False, "private_values_printed=true")
        assert_true(payload["tokenValuePrinted"] is False, "token_values_printed=true")
        assert_true(payload["adapterCount"] >= 4, "adapter_count_too_low=true")

    print("pnh_live_private_data_adapter_batch_sync_smoke_check_pass=true")
    print("private_values_printed=false")
    return 0


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())
