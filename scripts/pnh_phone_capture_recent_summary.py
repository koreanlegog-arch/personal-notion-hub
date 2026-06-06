#!/usr/bin/env python3
"""Summarize recent phone automation captures without reading private bodies."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.private_store import DEFAULT_DB_PATH, PrivateStoreError, list_captures, store_summary  # noqa: E402


DEFAULT_OUT = ROOT / "ops" / "runs" / "PNH-PHONE-CAPTURE-RECENT-SUMMARY-20260606" / "phone_capture_recent_summary.json"
PHONE_SOURCE_PREFIX = "phone_"


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize recent PNH phone captures metadata-only.")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Private inbox DB path.")
    parser.add_argument("--limit", type=int, default=50, help="Recent captures to inspect.")
    parser.add_argument("--source-prefix", default=PHONE_SOURCE_PREFIX, help="Phone source prefix.")
    parser.add_argument("--allow-external-db", action="store_true", help="Allow fixture DB outside companion/private.")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output JSON.")
    args = parser.parse_args()

    try:
        payload = summarize(args)
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, PrivateStoreError) as exc:
        print(f"pnh_phone_capture_recent_summary=false error={exc}", file=sys.stderr)
        return 2

    print(json.dumps(redact_stdout(payload, Path(args.out)), ensure_ascii=False, sort_keys=True))
    return 0


def summarize(args: argparse.Namespace) -> dict[str, Any]:
    db_path = Path(args.db)
    summary = store_summary(db_path, create_if_missing=False, allow_external=args.allow_external_db)
    captures = list_captures(
        db_path,
        limit=args.limit,
        include_body=False,
        create_if_missing=False,
        allow_external=args.allow_external_db,
    )
    phone_captures = [item for item in captures if str(item.get("source") or "").startswith(args.source_prefix)]
    sources = Counter(str(item.get("source") or "") for item in phone_captures)
    kinds = Counter(str(item.get("kind") or "") for item in phone_captures)
    sensitivities = Counter(str(item.get("sensitivity") or "") for item in phone_captures)
    encrypted_count = sum(1 for item in phone_captures if item.get("storageMode") == "encrypted-vault" and item.get("encrypted"))
    plaintext_count = sum(1 for item in phone_captures if item.get("storageMode") == "plaintext-inbox")
    latest = sanitize_capture(phone_captures[0]) if phone_captures else None
    missing_sources = [
        source
        for source in ("phone_contacts", "phone_calendar", "phone_call_log", "phone_recording")
        if source not in sources
    ]
    verdict = "phone_capture_recent_summary_ready" if phone_captures and plaintext_count == 0 else "no_recent_phone_capture" if not phone_captures else "phone_capture_plaintext_risk"
    return {
        "pnhPhoneCaptureRecentSummary": True,
        "verdict": verdict,
        "capturesInspected": len(captures),
        "phoneCaptureCount": len(phone_captures),
        "encryptedPhoneCaptureCount": encrypted_count,
        "plaintextPhoneCaptureCount": plaintext_count,
        "totalPrivateInboxCaptures": summary.get("totalCaptures"),
        "bySource": dict(sorted(sources.items())),
        "byKind": dict(sorted(kinds.items())),
        "bySensitivity": dict(sorted(sensitivities.items())),
        "latestPhoneCapture": latest,
        "missingPhoneSourcesInRecentWindow": missing_sources,
        "coverageNote": coverage_note(missing_sources),
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "baseUrlValuePrinted": False,
        "exactOwnerNetworkUrlPersisted": False,
        "rawPrivateBodyRead": False,
    }


def sanitize_capture(capture: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": capture.get("id"),
        "source": capture.get("source"),
        "kind": capture.get("kind"),
        "sensitivity": capture.get("sensitivity"),
        "status": capture.get("status"),
        "createdAt": capture.get("createdAt"),
        "storedAt": capture.get("storedAt"),
        "storageMode": capture.get("storageMode"),
        "encrypted": bool(capture.get("encrypted")),
        "title": "[encrypted]" if capture.get("encrypted") else "[redacted]",
    }


def coverage_note(missing_sources: list[str]) -> str:
    if not missing_sources:
        return "all_supported_phone_sources_seen_in_recent_window"
    return "not_all_supported_phone_sources_seen_yet"


def redact_stdout(payload: dict[str, Any], out_path: Path) -> dict[str, Any]:
    latest = payload.get("latestPhoneCapture") or {}
    return {
        "pnhPhoneCaptureRecentSummary": True,
        "verdict": payload["verdict"],
        "phoneCaptureCount": payload["phoneCaptureCount"],
        "encryptedPhoneCaptureCount": payload["encryptedPhoneCaptureCount"],
        "plaintextPhoneCaptureCount": payload["plaintextPhoneCaptureCount"],
        "latestPhoneCaptureSource": latest.get("source"),
        "latestPhoneCaptureStorageMode": latest.get("storageMode"),
        "out": safe_path_label(out_path),
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "rawPrivateBodyRead": False,
    }


def safe_path_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return "[external-path]"


if __name__ == "__main__":
    raise SystemExit(main())
