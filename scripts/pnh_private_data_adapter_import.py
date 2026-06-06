#!/usr/bin/env python3
"""Import owner-exported private data into the encrypted PNH inbox.

This is a local-first import adapter MVP. It does not connect to phone APIs,
cloud accounts, OAuth, or external services. Input files are assumed to be
created or exported by the owner and are stored only through the local private
store. Values are never printed.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.encrypted_vault import init_encrypted_vault  # noqa: E402
from companion.passphrase_provider import resolve_passphrase  # noqa: E402
from companion.private_store import DEFAULT_DB_PATH, PrivateStoreError, insert_capture  # noqa: E402


DEFAULT_OUT = ROOT / "ops" / "runs" / "PNH-PRIVATE-DATA-ADAPTER-IMPORT-20260606" / "adapter_import_plan.json"
ADAPTER_KINDS = {
    "contacts-csv": "contact",
    "calendar-ics": "calendar",
    "call-log-csv": "call_note",
    "recording-transcript-txt": "voice_note",
}


class AdapterImportError(ValueError):
    """Raised when adapter import cannot proceed safely."""


def main() -> int:
    parser = argparse.ArgumentParser(description="Import owner-exported private data into encrypted PNH storage.")
    parser.add_argument("--adapter", required=True, choices=sorted(ADAPTER_KINDS), help="Adapter type.")
    parser.add_argument("--input", required=True, help="Owner-exported local input file.")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Private inbox DB path.")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Plan/result output JSON.")
    parser.add_argument("--limit", type=int, default=50, help="Maximum rows/events to import.")
    parser.add_argument("--vault-passphrase-env", default="", help="Optional passphrase env var.")
    parser.add_argument("--prompt-vault-passphrase", action="store_true", help="Prompt for vault passphrase.")
    parser.add_argument("--vault-passphrase-provider", default="", help="Passphrase provider such as windows-dpapi-file.")
    parser.add_argument("--vault-passphrase-name", default="vault-passphrase", help="Provider secret name.")
    parser.add_argument("--vault-passphrase-file", default="", help="Provider secret file path.")
    parser.add_argument("--allow-external-db", action="store_true", help="Allow DB outside companion/private for fixture tests.")
    parser.add_argument("--apply", action="store_true", help="Write records to encrypted vault.")
    parser.add_argument("--approve-real-data-adapter", action="store_true", help="Required with --apply.")
    args = parser.parse_args()

    try:
        input_path = Path(args.input)
        records = parse_adapter_records(args.adapter, input_path, limit=args.limit)
        db_path = Path(args.db)
        result = {
            "pnhPrivateDataAdapterImport": True,
            "mode": "apply" if args.apply else "dry-run",
            "adapter": args.adapter,
            "inputFile": safe_input_label(input_path),
            "recordsParsed": len(records),
            "recordsWritten": 0,
            "storageMode": "encrypted-vault",
            "externalServicesContacted": False,
            "privateValuesPrinted": False,
            "tokenValuePrinted": False,
            "approvalGate": {
                "requiredForApply": True,
                "reason": "real-data adapter apply stores owner-exported private data in the encrypted local vault",
            },
            "recordKinds": sorted({item["kind"] for item in records}),
        }
        if args.apply:
            if not args.approve_real_data_adapter:
                raise AdapterImportError("--apply requires --approve-real-data-adapter")
            passphrase = resolve_adapter_passphrase(args)
            vault = init_encrypted_vault(db_path, passphrase)
            for record in records:
                insert_capture(db_path, record, allow_external=args.allow_external_db, vault=vault)
            result["recordsWritten"] = len(records)
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except Exception as exc:
        print(f"pnh_private_data_adapter_import=false error={exc}", file=sys.stderr)
        return 2
    print(json.dumps({**result, "out": safe_output_label(Path(args.out))}, ensure_ascii=False, sort_keys=True))
    return 0


def parse_adapter_records(adapter: str, input_path: Path, *, limit: int) -> list[dict[str, Any]]:
    if not input_path.exists() or not input_path.is_file():
        raise AdapterImportError("input file is missing")
    bounded = min(max(int(limit), 1), 500)
    if adapter == "contacts-csv":
        return parse_contacts_csv(input_path, bounded)
    if adapter == "call-log-csv":
        return parse_call_log_csv(input_path, bounded)
    if adapter == "calendar-ics":
        return parse_calendar_ics(input_path, bounded)
    if adapter == "recording-transcript-txt":
        return parse_recording_transcript(input_path)
    raise AdapterImportError("unsupported adapter")


def parse_contacts_csv(path: Path, limit: int) -> list[dict[str, Any]]:
    rows = read_csv_rows(path, limit)
    records = []
    for idx, row in enumerate(rows, start=1):
        name = row_value(row, "name", "full_name", "display_name") or f"Contact {idx}"
        body = json.dumps(redact_preserving_payload(row), ensure_ascii=False, sort_keys=True)
        records.append(base_record("contacts_adapter", "contact", f"Contact import: {name}", body, "private"))
    return records


def parse_call_log_csv(path: Path, limit: int) -> list[dict[str, Any]]:
    rows = read_csv_rows(path, limit)
    records = []
    for idx, row in enumerate(rows, start=1):
        label = row_value(row, "name", "phone", "number") or f"Call {idx}"
        when = row_value(row, "timestamp", "date", "time") or "unknown-time"
        body = json.dumps(redact_preserving_payload(row), ensure_ascii=False, sort_keys=True)
        records.append(base_record("call_log_adapter", "call_note", f"Call log import: {label} {when}", body, "highly_sensitive"))
    return records


def parse_calendar_ics(path: Path, limit: int) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    events = []
    for raw_event in text.split("BEGIN:VEVENT")[1:]:
        event = raw_event.split("END:VEVENT", 1)[0]
        fields = parse_ics_fields(event)
        title = fields.get("SUMMARY") or f"Calendar event {len(events) + 1}"
        start = fields.get("DTSTART") or "unknown-start"
        body = json.dumps(fields, ensure_ascii=False, sort_keys=True)
        events.append(base_record("calendar_adapter", "calendar", f"Calendar import: {title} {start}", body, "private"))
        if len(events) >= limit:
            break
    if not events:
        raise AdapterImportError("no VEVENT records found")
    return events


def parse_recording_transcript(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise AdapterImportError("transcript is empty")
    title = f"Recording transcript import: {path.stem}"
    return [base_record("recording_transcript_adapter", "voice_note", title, text, "highly_sensitive")]


def read_csv_rows(path: Path, limit: int) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise AdapterImportError("CSV has no data rows")
    return [{str(k or "").strip().lower(): str(v or "").strip() for k, v in row.items()} for row in rows[:limit]]


def parse_ics_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.replace("\r\n", "\n").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.split(";", 1)[0].strip().upper()] = value.strip()
    return fields


def row_value(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value:
            return value
    return ""


def redact_preserving_payload(row: dict[str, str]) -> dict[str, str]:
    return dict(row)


def base_record(source: str, kind: str, title: str, body: str, sensitivity: str) -> dict[str, Any]:
    return {
        "source": source,
        "kind": kind,
        "title": title,
        "body": body,
        "sensitivity": sensitivity,
    }


def resolve_adapter_passphrase(args: argparse.Namespace) -> str:
    if not args.vault_passphrase_env and not args.prompt_vault_passphrase and not args.vault_passphrase_provider:
        raise AdapterImportError("--apply requires vault passphrase env, prompt, or provider")
    return resolve_passphrase(
        env_name=args.vault_passphrase_env or "PNH_VAULT_PASSPHRASE",
        label="vault",
        prompt=args.prompt_vault_passphrase,
        provider=args.vault_passphrase_provider,
        secret_name=args.vault_passphrase_name,
        secret_path=args.vault_passphrase_file,
    ).value


def safe_input_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return "[owner-local-input-file]"


def safe_output_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return "[external-path]"


if __name__ == "__main__":
    raise SystemExit(main())
