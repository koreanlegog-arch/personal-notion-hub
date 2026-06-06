#!/usr/bin/env python3
"""Assess readiness for configuring an owner phone automation tool.

This script never prints bearer token values. It checks token-file presence and
permissions, companion service health, owner-tailnet availability, privacy gate
status, and profile template availability.
"""

from __future__ import annotations

import argparse
import json
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.phone_adapter_ingest import PHONE_ADAPTERS  # noqa: E402
from companion.private_store import DEFAULT_TOKEN_PATH  # noqa: E402


DEFAULT_OUT = ROOT / "ops" / "runs" / "PNH-PHONE-AUTOMATION-SETUP-READINESS-20260606" / "setup_readiness.json"


class SetupReadinessError(ValueError):
    """Raised when setup readiness cannot be assessed."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Assess owner phone automation setup readiness.")
    parser.add_argument("--token-file", default=str(DEFAULT_TOKEN_PATH), help="Private bearer token file.")
    parser.add_argument("--allow-external-token-file", action="store_true", help="Allow token file outside companion/private for fixture tests.")
    parser.add_argument("--companion-status-json", default="", help="Fixture companion status JSON.")
    parser.add_argument("--tailnet-status-json", default="", help="Fixture tailnet status JSON.")
    parser.add_argument("--privacy-gate-json", default="", help="Fixture privacy gate JSON.")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output JSON.")
    args = parser.parse_args()

    try:
        token_status = token_file_status(Path(args.token_file), allow_external=args.allow_external_token_file)
        companion = load_or_run(args.companion_status_json, ["scripts/pnh_companion_service_status.py"], "companion status")
        tailnet = load_or_run(args.tailnet_status_json, ["scripts/pnh_tailnet_companion_api_status.py"], "tailnet status")
        privacy = load_or_run(args.privacy_gate_json, ["scripts/pnh_real_data_privacy_gate.py"], "privacy gate")
        payload = build_readiness(token_status, companion, tailnet, privacy)
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, SetupReadinessError) as exc:
        print(f"pnh_phone_automation_setup_readiness=false error={exc}", file=sys.stderr)
        return 2
    print(json.dumps(redact_stdout(payload, Path(args.out)), ensure_ascii=False, sort_keys=True))
    return 0 if payload["verdict"] == "ready_for_owner_phone_tool_configuration" else 1


def build_readiness(
    token_status: dict[str, Any],
    companion: dict[str, Any],
    tailnet: dict[str, Any],
    privacy: dict[str, Any],
) -> dict[str, Any]:
    checks = [
        check("token_file_present", token_status["exists"], "private bearer token file exists"),
        check("token_file_nonempty", token_status["nonempty"], "private bearer token file is non-empty"),
        check("token_file_permission_restricted", token_status["permissionRestricted"], "token file is not group/world readable"),
        check("companion_service_active", companion.get("service", {}).get("active") == "active", "companion user service is active"),
        check("companion_encrypted_vault_health", companion.get("health", {}).get("ok") is True and companion.get("health", {}).get("encryptedVaultEnabled") is True, "companion uses encrypted vault"),
        check("tailnet_running", tailnet.get("tailnetRunning") is True and tailnet.get("tailnetIpv4Set") is True, "owner tailnet is running"),
        check("tailnet_health_ok", tailnet.get("health", {}).get("ok") is True, "tailnet companion API health succeeds"),
        check("privacy_gate_ready", privacy.get("verdict") == "ready_for_controlled_real_phone_adapter_run", "real-data privacy gate is ready"),
    ]
    failed = [item for item in checks if not item["pass"]]
    return {
        "pnhPhoneAutomationSetupReadiness": True,
        "verdict": "ready_for_owner_phone_tool_configuration" if not failed else "not_ready",
        "checks": checks,
        "failedChecks": failed,
        "profileCount": len(PHONE_ADAPTERS),
        "endpoint": "/api/private/phone-adapter-captures",
        "baseUrlPolicy": "owner-tailnet-or-loopback-only",
        "token": {
            "path": token_status["path"],
            "present": token_status["exists"],
            "valuePrinted": False,
            "operatorMustCopyLocally": True,
        },
        "operatorSetupChecklist": [
            "Run pnh_tailnet_companion_api_status.py locally to identify the current owner-tailnet base URL.",
            "Generate profile templates with pnh_phone_automation_profile_template.py.",
            "In the phone automation tool, set Authorization to Bearer plus the local token from companion/private/auth_token.",
            "Do not paste the token into chat, docs, screenshots, Git, or evidence files.",
            "Send one synthetic payload first, then check private_inbox_status.py --include-recent.",
        ],
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
    }


def token_file_status(path: Path, *, allow_external: bool) -> dict[str, Any]:
    if not allow_external:
        try:
            path.resolve().relative_to((ROOT / "companion" / "private").resolve())
        except ValueError as exc:
            raise SetupReadinessError("token file must remain under companion/private") from exc
    exists = path.exists() and path.is_file()
    mode = path.stat().st_mode if exists else 0
    return {
        "path": safe_path_label(path),
        "exists": exists,
        "nonempty": exists and path.stat().st_size > 0,
        "permissionRestricted": exists and (stat.S_IMODE(mode) & 0o077) == 0,
    }


def load_or_run(fixture_path: str, command: list[str], label: str) -> dict[str, Any]:
    if fixture_path:
        try:
            payload = json.loads(Path(fixture_path).read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SetupReadinessError(f"{label} fixture JSON is invalid: {exc.msg}") from exc
        if not isinstance(payload, dict):
            raise SetupReadinessError(f"{label} fixture must be an object")
        return payload
    result = subprocess.run([sys.executable, *command], cwd=ROOT, capture_output=True, text=True, timeout=45, check=False)
    if result.returncode != 0:
        raise SetupReadinessError(f"{label} command failed: {first_line(result.stderr) or first_line(result.stdout)}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise SetupReadinessError(f"{label} command returned invalid JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise SetupReadinessError(f"{label} command returned non-object JSON")
    payload.pop("tailnetUrl", None)
    return payload


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "pass": bool(passed), "detail": detail}


def redact_stdout(payload: dict[str, Any], out_path: Path) -> dict[str, Any]:
    return {
        "pnhPhoneAutomationSetupReadiness": True,
        "verdict": payload["verdict"],
        "profileCount": payload["profileCount"],
        "out": safe_path_label(out_path),
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
    }


def first_line(value: str) -> str:
    return value.strip().splitlines()[0][:240] if value.strip() else ""


def safe_path_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return "[external-path]"


if __name__ == "__main__":
    raise SystemExit(main())
