#!/usr/bin/env python3
"""Generate a metadata-safe owner phone automation handoff packet.

The handoff packet consolidates setup readiness, profile templates, and live
probe commands for owner-side phone automation configuration. It never reads or
prints the bearer token value and never persists exact owner-network URLs.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "ops" / "runs" / "PNH-PHONE-AUTOMATION-HANDOFF-20260606" / "phone_automation_handoff.json"
PROFILE_PLACEHOLDER_BASE_URL = "http://<owner-tailnet-ip>:8765"


class HandoffError(ValueError):
    """Raised when the phone automation handoff packet cannot be generated."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate PNH owner phone automation handoff packet.")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output JSON.")
    parser.add_argument("--skip-runtime-checks", action="store_true", help="Use static packet without live readiness commands.")
    args = parser.parse_args()

    try:
        payload = build_packet(args)
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, HandoffError) as exc:
        print(f"pnh_phone_automation_handoff_packet=false error={exc}", file=sys.stderr)
        return 2

    print(json.dumps(redact_stdout(payload, Path(args.out)), ensure_ascii=False, sort_keys=True))
    return 0 if payload["verdict"] in {"ready_for_owner_phone_tool_configuration", "static_packet_generated"} else 1


def build_packet(args: argparse.Namespace) -> dict[str, Any]:
    profile = generate_profile()
    readiness = None
    live_probe = None
    if not args.skip_runtime_checks:
        readiness = run_json_command(["scripts/pnh_phone_automation_setup_readiness.py"], "phone automation readiness")
        live_probe = run_json_command(["scripts/pnh_phone_automation_live_probe.py"], "phone automation live probe")

    verdict = "static_packet_generated"
    if readiness is not None:
        verdict = str(readiness.get("verdict") or "not_ready")

    current_count = None
    if live_probe is not None:
        current_count = live_probe.get("currentCount")

    return {
        "pnhPhoneAutomationHandoffPacket": True,
        "verdict": verdict,
        "profileBaseUrl": PROFILE_PLACEHOLDER_BASE_URL,
        "endpoint": "/api/private/phone-adapter-captures",
        "authHeader": "Bearer <PNH_PRIVATE_INBOX_TOKEN>",
        "tokenPlaceholderOnly": True,
        "runtimeChecksUsed": not args.skip_runtime_checks,
        "readiness": sanitize_readiness(readiness),
        "liveProbe": sanitize_live_probe(live_probe),
        "profiles": profile["profiles"],
        "ownerSetupSequence": owner_setup_sequence(current_count),
        "adapterGuidance": adapter_guidance(),
        "safetyRules": [
            "Do not paste the bearer token into chat, docs, screenshots, or Git.",
            "Copy the token only from the local ignored companion/private/auth_token file into the phone automation tool.",
            "Use owner tailnet or loopback endpoints only until production auth and public exposure are separately reviewed.",
            "Run one synthetic phone automation send before sending real private data.",
            "After the first real private data send, rerun the real-data privacy gate before long-term operation.",
        ],
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "baseUrlValuePrinted": False,
        "exactOwnerNetworkUrlPersisted": False,
        "rawPrivateBodyRead": False,
    }


def generate_profile() -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as temp_dir:
        out = Path(temp_dir) / "profile.json"
        result = subprocess.run(
            [
                sys.executable,
                "scripts/pnh_phone_automation_profile_template.py",
                "--base-url",
                PROFILE_PLACEHOLDER_BASE_URL,
                "--out",
                str(out),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        if result.returncode != 0:
            raise HandoffError(first_line(result.stderr) or first_line(result.stdout) or "profile template failed")
        payload = json.loads(out.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise HandoffError("profile template returned non-object JSON")
        return payload


def run_json_command(command: list[str], label: str) -> dict[str, Any]:
    result = subprocess.run([sys.executable, *command], cwd=ROOT, capture_output=True, text=True, timeout=60, check=False)
    if result.returncode != 0:
        raise HandoffError(f"{label} failed: {first_line(result.stderr) or first_line(result.stdout)}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise HandoffError(f"{label} returned invalid JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise HandoffError(f"{label} returned non-object JSON")
    payload.pop("tailnetUrl", None)
    return payload


def sanitize_readiness(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if payload is None:
        return None
    failed = payload.get("failedChecks")
    failed_count = len(failed) if isinstance(failed, list) else 0 if payload.get("verdict") == "ready_for_owner_phone_tool_configuration" else None
    return {
        "verdict": payload.get("verdict"),
        "profileCount": payload.get("profileCount"),
        "failedCheckCount": failed_count,
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
    }


def sanitize_live_probe(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if payload is None:
        return None
    latest = payload.get("latestPhoneCapture") or {}
    latest_source = latest.get("source") if isinstance(latest, dict) else None
    latest_storage = latest.get("storageMode") if isinstance(latest, dict) else None
    return {
        "verdict": payload.get("verdict"),
        "currentCount": payload.get("currentCount"),
        "latestPhoneCaptureSource": latest_source or payload.get("latestPhoneCaptureSource"),
        "latestPhoneCaptureStorageMode": latest_storage or payload.get("latestPhoneCaptureStorageMode"),
        "rawPrivateBodyRead": False,
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
    }


def owner_setup_sequence(current_count: Any) -> list[dict[str, Any]]:
    baseline = "<current-total-captures>" if current_count is None else str(current_count)
    return [
        {
            "step": "confirm-local-readiness",
            "command": "python3 scripts/pnh_phone_automation_setup_readiness.py",
            "expected": "ready_for_owner_phone_tool_configuration",
        },
        {
            "step": "generate-placeholder-profiles",
            "command": "python3 scripts/pnh_phone_automation_profile_template.py",
            "expected": "profiles use Bearer <PNH_PRIVATE_INBOX_TOKEN>",
        },
        {
            "step": "copy-token-locally",
            "command": "manual-owner-action: copy companion/private/auth_token into the phone automation tool secret field",
            "expected": "token is never pasted into chat/docs/Git",
        },
        {
            "step": "configure-phone-automation-endpoint",
            "command": "manual-owner-action: replace <owner-tailnet-ip> in the phone tool only",
            "expected": "repo evidence still contains placeholder-only endpoint",
        },
        {
            "step": "start-live-probe",
            "command": (
                "python3 scripts/pnh_phone_automation_live_probe.py "
                f"--baseline-count {baseline} --timeout-seconds 120"
            ),
            "expected": "new_phone_capture_detected",
        },
        {
            "step": "send-one-synthetic-phone-payload",
            "command": "manual-owner-action: run the phone automation action with fixture/synthetic data first",
            "expected": "encrypted-vault row count increases by at least 1",
        },
        {
            "step": "final-real-data-gate",
            "command": "python3 scripts/pnh_real_data_privacy_gate.py",
            "expected": "ready_for_controlled_real_phone_adapter_run",
        },
    ]


def adapter_guidance() -> list[dict[str, str]]:
    return [
        {
            "adapter": "phone-contacts-json",
            "useFor": "owner-exported or phone-automation contact snapshots",
            "minimumFields": "title/name plus body/text/notes or full item JSON",
        },
        {
            "adapter": "phone-calendar-json",
            "useFor": "calendar events or daily schedule snapshots",
            "minimumFields": "title/summary plus body/description/notes",
        },
        {
            "adapter": "phone-call-log-json",
            "useFor": "call notes or call-log summaries",
            "minimumFields": "title/name plus notes/body",
        },
        {
            "adapter": "phone-recording-transcript-json",
            "useFor": "recording transcript snippets prepared by owner automation",
            "minimumFields": "title plus transcript body/text",
        },
    ]


def redact_stdout(payload: dict[str, Any], out_path: Path) -> dict[str, Any]:
    return {
        "pnhPhoneAutomationHandoffPacket": True,
        "verdict": payload["verdict"],
        "profileCount": len(payload["profiles"]),
        "out": safe_path_label(out_path),
        "tokenPlaceholderOnly": True,
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "baseUrlValuePrinted": False,
        "exactOwnerNetworkUrlPersisted": False,
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
