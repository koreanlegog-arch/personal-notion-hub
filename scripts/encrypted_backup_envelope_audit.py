#!/usr/bin/env python3
"""Audit encrypted backup envelope metadata without decrypting private data."""

from __future__ import annotations

import argparse
import base64
import binascii
import json
import sys
from pathlib import Path
from typing import Any


EXPECTED_SCHEMA_VERSION = 1
EXPECTED_KIND = "pnh.encrypted-vault-backup"
EXPECTED_ALGORITHM = "AES-256-GCM"
EXPECTED_KDF = "PBKDF2-HMAC-SHA256"
EXPECTED_KDF_ITERATIONS = 390_000
REQUIRED_FIELDS = (
    "schemaVersion",
    "kind",
    "algorithm",
    "kdf",
    "kdfIterations",
    "salt",
    "nonce",
    "ciphertext",
)


class EnvelopeAuditError(ValueError):
    """Raised when the backup envelope cannot be safely audited."""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit encrypted Personal Notion Hub backup envelope metadata without decrypting it."
    )
    parser.add_argument("--backup", required=True, help="Encrypted *.pnhbackup file path.")
    parser.add_argument(
        "--fail-on-unsupported",
        action="store_true",
        help="Exit non-zero when the envelope metadata is present but unsupported.",
    )
    args = parser.parse_args()

    try:
        result, unsupported = audit_envelope(Path(args.backup))
        if unsupported and args.fail_on_unsupported:
            raise EnvelopeAuditError("encrypted backup envelope is unsupported")
    except (OSError, EnvelopeAuditError) as exc:
        print(f"encrypted_backup_envelope_audit=false error={exc}", file=sys.stderr)
        return 2

    print(json.dumps({"encryptedBackupEnvelopeAudit": result}, ensure_ascii=False, sort_keys=True))
    return 0


def audit_envelope(path: Path) -> tuple[dict[str, Any], bool]:
    envelope = _load_envelope(path)
    _require_shape(envelope)

    salt = _decode_required_bytes(envelope["salt"], "salt")
    nonce = _decode_required_bytes(envelope["nonce"], "nonce")
    ciphertext = _decode_required_bytes(envelope["ciphertext"], "ciphertext")
    if not salt:
        raise EnvelopeAuditError("encrypted backup envelope salt is empty")
    if not nonce:
        raise EnvelopeAuditError("encrypted backup envelope nonce is empty")
    if not ciphertext:
        raise EnvelopeAuditError("encrypted backup envelope ciphertext is empty")

    unsupported = (
        envelope["schemaVersion"] != EXPECTED_SCHEMA_VERSION
        or envelope["kind"] != EXPECTED_KIND
        or envelope["algorithm"] != EXPECTED_ALGORITHM
        or envelope["kdf"] != EXPECTED_KDF
        or envelope["kdfIterations"] != EXPECTED_KDF_ITERATIONS
    )
    return (
        {
            "algorithm": envelope["algorithm"],
            "ciphertextBytes": len(ciphertext),
            "kdf": envelope["kdf"],
            "kdfIterations": envelope["kdfIterations"],
            "kind": envelope["kind"],
            "schemaVersion": envelope["schemaVersion"],
            "valuesPrinted": False,
        },
        unsupported,
    )


def _load_envelope(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise EnvelopeAuditError("encrypted backup file is missing")
    try:
        raw_text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise EnvelopeAuditError("encrypted backup must be UTF-8 JSON") from exc
    try:
        envelope = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise EnvelopeAuditError("encrypted backup is invalid JSON") from exc
    if not isinstance(envelope, dict):
        raise EnvelopeAuditError("encrypted backup envelope must be an object")
    return envelope


def _require_shape(envelope: dict[str, Any]) -> None:
    for field in REQUIRED_FIELDS:
        if field not in envelope:
            raise EnvelopeAuditError(f"encrypted backup envelope missing {field}")
    for field in ("kind", "algorithm", "kdf", "salt", "nonce", "ciphertext"):
        if not isinstance(envelope[field], str) or not envelope[field]:
            raise EnvelopeAuditError(f"encrypted backup envelope {field} is invalid")
    if not isinstance(envelope["schemaVersion"], int):
        raise EnvelopeAuditError("encrypted backup envelope schemaVersion is invalid")
    if not isinstance(envelope["kdfIterations"], int):
        raise EnvelopeAuditError("encrypted backup envelope kdfIterations is invalid")


def _decode_required_bytes(value: str, field: str) -> bytes:
    try:
        return base64.b64decode(value.encode("ascii"), altchars=b"-_", validate=True)
    except (UnicodeEncodeError, binascii.Error) as exc:
        raise EnvelopeAuditError(f"encrypted backup envelope {field} is invalid") from exc


if __name__ == "__main__":
    raise SystemExit(main())
