#!/usr/bin/env python3
"""Run an owner phone capture session with post-capture verification.

The session takes a metadata-only baseline, waits for the next phone automation
capture, and optionally runs the final privacy gate plus completion audit after
the capture arrives. It never decrypts private bodies and never prints token or
owner-network URL values.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.private_store import DEFAULT_DB_PATH, PrivateStoreError, store_summary  # noqa: E402
from scripts.pnh_phone_automation_live_probe import probe as run_live_probe  # noqa: E402


DEFAULT_OUT = ROOT / "ops" / "runs" / "PNH-OWNER-PHONE-CAPTURE-SESSION-20260606" / "owner_phone_capture_session.json"


class OwnerPhoneSessionError(ValueError):
    """Raised when an owner phone capture session cannot run safely."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Run owner phone capture session verification.")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Private inbox DB path.")
    parser.add_argument("--baseline-count", type=int, default=None, help="Known total count before owner phone send.")
    parser.add_argument("--timeout-seconds", type=float, default=120.0, help="Wait for phone capture.")
    parser.add_argument("--poll-seconds", type=float, default=2.0, help="Polling interval.")
    parser.add_argument("--source-prefix", default="phone_", help="Required phone source prefix.")
    parser.add_argument("--allow-external-db", action="store_true", help="Allow fixture DB outside companion/private.")
    parser.add_argument("--allow-plaintext", action="store_true", help="Allow plaintext in fixture diagnostics.")
    parser.add_argument("--skip-post-checks", action="store_true", help="Skip post-capture privacy/audit commands.")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output JSON.")
    args = parser.parse_args()

    try:
        payload = run_session(args)
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, PrivateStoreError, OwnerPhoneSessionError) as exc:
        print(f"pnh_owner_phone_capture_session=false error={exc}", file=sys.stderr)
        return 2

    print(json.dumps(redact_stdout(payload, Path(args.out)), ensure_ascii=False, sort_keys=True))
    return 0 if payload["success"] else 1


def run_session(args: argparse.Namespace) -> dict[str, Any]:
    db_path = Path(args.db)
    before = store_summary(db_path, create_if_missing=False, allow_external=args.allow_external_db)
    baseline = args.baseline_count if args.baseline_count is not None else int(before.get("totalCaptures") or 0)
    if baseline < 0:
        raise OwnerPhoneSessionError("baseline count must be zero or greater")
    probe_args = argparse.Namespace(
        db=str(db_path),
        baseline_count=baseline,
        timeout_seconds=args.timeout_seconds,
        poll_seconds=args.poll_seconds,
        source_prefix=args.source_prefix,
        allow_external_db=args.allow_external_db,
        allow_plaintext=args.allow_plaintext,
        out="",
    )
    probe_result = run_live_probe(probe_args)
    after = store_summary(db_path, create_if_missing=False, allow_external=args.allow_external_db)
    post_checks = {}
    if probe_result["success"] and not args.skip_post_checks and not args.allow_external_db:
        post_checks = {
            "privacyGate": run_json(["scripts/pnh_real_data_privacy_gate.py"], "privacy gate"),
            "completionAudit": run_json(["scripts/pnh_assistant_mvp_completion_audit.py"], "completion audit"),
        }
    success = bool(probe_result["success"])
    if post_checks:
        success = success and post_checks["privacyGate"].get("verdict") == "ready_for_controlled_real_phone_adapter_run"
        success = success and post_checks["completionAudit"].get("readyForOwnerControlledMvpUse") is True
    return {
        "pnhOwnerPhoneCaptureSession": True,
        "generatedAt": utc_now(),
        "success": success,
        "verdict": "owner_phone_capture_verified" if success else "owner_phone_capture_not_detected",
        "baselineCount": baseline,
        "before": sanitize_summary(before),
        "after": sanitize_summary(after),
        "probe": sanitize_probe(probe_result),
        "postChecksRun": bool(post_checks),
        "postChecks": sanitize_post_checks(post_checks),
        "ownerNextAction": owner_next_action(success, post_checks),
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "baseUrlValuePrinted": False,
        "exactOwnerNetworkUrlPersisted": False,
        "rawPrivateBodyRead": False,
    }


def run_json(command: list[str], label: str) -> dict[str, Any]:
    result = subprocess.run([sys.executable, *command], cwd=ROOT, capture_output=True, text=True, timeout=120, check=False)
    if result.returncode != 0:
        return {
            "ok": False,
            "label": label,
            "returnCode": result.returncode,
            "stdoutFirstLine": first_line(result.stdout),
            "stderrFirstLine": first_line(result.stderr),
        }
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return {"ok": False, "label": label, "error": f"invalid JSON: {exc.msg}"}
    if not isinstance(payload, dict):
        return {"ok": False, "label": label, "error": "non-object JSON"}
    payload.pop("tailnetUrl", None)
    payload["ok"] = True
    return payload


def sanitize_summary(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "totalCaptures": summary.get("totalCaptures"),
        "byStorageMode": summary.get("byStorageMode", {}),
        "encryptedVaultEnabled": summary.get("encryptedVaultEnabled"),
    }


def sanitize_probe(payload: dict[str, Any]) -> dict[str, Any]:
    latest = payload.get("latestPhoneCapture") or {}
    return {
        "success": payload.get("success"),
        "verdict": payload.get("verdict"),
        "mode": payload.get("mode"),
        "baselineCount": payload.get("baselineCount"),
        "currentCount": payload.get("currentCount"),
        "delta": payload.get("delta"),
        "latestPhoneCapture": {
            "id": latest.get("id"),
            "source": latest.get("source"),
            "kind": latest.get("kind"),
            "sensitivity": latest.get("sensitivity"),
            "status": latest.get("status"),
            "storageMode": latest.get("storageMode"),
            "encrypted": latest.get("encrypted"),
            "title": "[encrypted]" if latest.get("encrypted") else "[redacted]",
        }
        if isinstance(latest, dict) and latest
        else None,
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "rawPrivateBodyRead": False,
    }


def sanitize_post_checks(post_checks: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if not post_checks:
        return {}
    privacy = post_checks.get("privacyGate", {})
    audit = post_checks.get("completionAudit", {})
    return {
        "privacyGate": {
            "ok": privacy.get("ok"),
            "verdict": privacy.get("verdict"),
            "blockerCount": len(privacy.get("blockers", [])) if isinstance(privacy.get("blockers"), list) else None,
        },
        "completionAudit": {
            "ok": audit.get("ok"),
            "verdict": audit.get("verdict"),
            "readyForOwnerControlledMvpUse": audit.get("readyForOwnerControlledMvpUse"),
            "completionPercent": audit.get("completionPercent"),
            "userActionCount": len(audit.get("userActionsRequired", [])) if isinstance(audit.get("userActionsRequired"), list) else None,
        },
    }


def owner_next_action(success: bool, post_checks: dict[str, dict[str, Any]]) -> str:
    if not success:
        return "send_phone_payload_or_check_phone_tool_configuration"
    if not post_checks:
        return "run_final_privacy_gate_before_real_long_term_operation"
    return "ready_for_controlled_owner_operation"


def redact_stdout(payload: dict[str, Any], out_path: Path) -> dict[str, Any]:
    return {
        "pnhOwnerPhoneCaptureSession": True,
        "success": payload["success"],
        "verdict": payload["verdict"],
        "baselineCount": payload["baselineCount"],
        "currentCount": payload["probe"]["currentCount"],
        "delta": payload["probe"]["delta"],
        "postChecksRun": payload["postChecksRun"],
        "ownerNextAction": payload["ownerNextAction"],
        "out": safe_path_label(out_path),
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "rawPrivateBodyRead": False,
    }


def first_line(value: str) -> str:
    return value.strip().splitlines()[0][:240] if value.strip() else ""


def safe_path_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return "[external-path]"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


if __name__ == "__main__":
    raise SystemExit(main())
