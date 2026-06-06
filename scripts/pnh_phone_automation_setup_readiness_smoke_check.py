#!/usr/bin/env python3
"""Smoke check for owner phone automation setup readiness."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_TOKEN_MARKER = "synthetic-phone-token-marker"


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        token_file = temp / "auth_token"
        token_file.write_text(PRIVATE_TOKEN_MARKER, encoding="utf-8")
        os.chmod(token_file, 0o600)
        companion = write_json(
            temp / "companion.json",
            {
                "service": {"active": "active", "enabled": "enabled"},
                "health": {"ok": True, "encryptedVaultEnabled": True},
            },
        )
        tailnet = write_json(
            temp / "tailnet.json",
            {
                "tailnetRunning": True,
                "tailnetIpv4Set": True,
                "tailnetUrl": "http://100.64.0.1:8765/",
                "health": {"ok": True},
            },
        )
        privacy = write_json(
            temp / "privacy.json",
            {"verdict": "ready_for_controlled_real_phone_adapter_run"},
        )
        out = temp / "setup.json"
        result = run_readiness(token_file, companion, tailnet, privacy, out)
        assert_true(result.returncode == 0, result.stderr)
        combined = result.stdout + out.read_text(encoding="utf-8")
        assert_true(PRIVATE_TOKEN_MARKER not in combined, "token_marker_leaked=true")
        assert_true("100.64.0.1" not in combined, "tailnet_ip_persisted=true")
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert_true(payload["verdict"] == "ready_for_owner_phone_tool_configuration", "setup_not_ready=true")
        assert_true(payload["token"]["valuePrinted"] is False, "token_value_printed_flag_wrong=true")

        os.chmod(token_file, 0o644)
        result = run_readiness(token_file, companion, tailnet, privacy, out)
        assert_true(result.returncode == 1, "loose_token_permissions_allowed=true")
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert_true(payload["verdict"] == "not_ready", "not_ready_verdict_missing=true")

    print("pnh_phone_automation_setup_readiness_smoke_check_pass=true")
    print("private_values_printed=false")
    return 0


def write_json(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def run_readiness(token_file: Path, companion: Path, tailnet: Path, privacy: Path, out: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "pnh_phone_automation_setup_readiness.py"),
            "--token-file",
            str(token_file),
            "--allow-external-token-file",
            "--companion-status-json",
            str(companion),
            "--tailnet-status-json",
            str(tailnet),
            "--privacy-gate-json",
            str(privacy),
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())
