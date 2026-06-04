"""Preview-only import validation for the local companion prototype.

This module intentionally uses Python stdlib only and never writes imported data
to disk. Diagnostics identify fields and record indexes, not submitted values.
"""

from __future__ import annotations

import re
from typing import Any


SUPPORTED_COLLECTIONS = ("projects", "tasks", "notes", "routines", "links")
MAX_ITEMS = 100

PRIVATE_KEY_RE = re.compile(
    r"(api[_-]?key|auth|bearer|client[_-]?secret|credential|oauth|password|private|secret|token)",
    re.IGNORECASE,
)
PRIVATE_VALUE_RE = re.compile(
    r"("
    r"sk-[A-Za-z0-9_-]{12,}|"
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|"
    r"\+?\d[\d\s().-]{7,}\d|"
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----"
    r")"
)


SCHEMA: dict[str, Any] = {
    "mode": "fixture-only-preview",
    "schemaVersion": 1,
    "requiredTopLevel": {
        "schemaVersion": "integer, must be 1",
        "items": "array of import records",
    },
    "record": {
        "type": list(SUPPORTED_COLLECTIONS),
        "title": "non-empty string",
        "body": "optional string",
        "tags": "optional array of strings",
        "status": "optional string",
    },
    "limits": {
        "maxItems": MAX_ITEMS,
        "writes": False,
        "externalNetwork": False,
        "privateDataAllowed": False,
    },
}


def zero_counts() -> dict[str, int]:
    return {name: 0 for name in SUPPORTED_COLLECTIONS}


def preview_import(payload: Any) -> dict[str, Any]:
    """Return counts/errors/warnings for a candidate fixture import."""
    counts = zero_counts()
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    if not isinstance(payload, dict):
        errors.append({"path": "$", "code": "payload_must_be_object"})
        return _result(counts, errors, warnings)

    _scan_private_like(payload, "$", errors)
    if errors:
        return _result(counts, errors, warnings)

    if payload.get("schemaVersion") != 1:
        errors.append({"path": "$.schemaVersion", "code": "unsupported_schema_version"})

    items = payload.get("items")
    if not isinstance(items, list):
        errors.append({"path": "$.items", "code": "items_must_be_array"})
        return _result(counts, errors, warnings)

    if len(items) > MAX_ITEMS:
        warnings.append({"path": "$.items", "code": "item_limit_exceeded_preview_truncated"})

    for index, item in enumerate(items[:MAX_ITEMS]):
        item_path = f"$.items[{index}]"
        if not isinstance(item, dict):
            errors.append({"path": item_path, "code": "item_must_be_object"})
            continue

        item_type = item.get("type")
        title = item.get("title")
        item_errors = False

        if item_type not in SUPPORTED_COLLECTIONS:
            errors.append({"path": f"{item_path}.type", "code": "unsupported_type"})
            item_errors = True
        if not isinstance(title, str) or not title.strip():
            errors.append({"path": f"{item_path}.title", "code": "title_required"})
            item_errors = True

        tags = item.get("tags")
        if tags is not None and (
            not isinstance(tags, list) or any(not isinstance(tag, str) for tag in tags)
        ):
            errors.append({"path": f"{item_path}.tags", "code": "tags_must_be_string_array"})
            item_errors = True

        body = item.get("body")
        if body is not None and not isinstance(body, str):
            errors.append({"path": f"{item_path}.body", "code": "body_must_be_string"})
            item_errors = True

        status = item.get("status")
        if status is not None and not isinstance(status, str):
            errors.append({"path": f"{item_path}.status", "code": "status_must_be_string"})
            item_errors = True

        if not item_errors and isinstance(item_type, str):
            counts[item_type] += 1

    return _result(counts, errors, warnings)


def _scan_private_like(value: Any, path: str, errors: list[dict[str, str]]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            private_like_key = isinstance(key, str) and PRIVATE_KEY_RE.search(key)
            key_path = f"{path}.{key}" if _safe_key(key) and not private_like_key else f"{path}.*"
            if private_like_key:
                errors.append({"path": key_path, "code": "private_like_key_rejected"})
            _scan_private_like(child, key_path, errors)
    elif isinstance(value, list):
        for index, child in enumerate(value[:MAX_ITEMS]):
            _scan_private_like(child, f"{path}[{index}]", errors)
    elif isinstance(value, str) and PRIVATE_VALUE_RE.search(value):
        errors.append({"path": path, "code": "private_like_value_rejected"})


def _safe_key(key: Any) -> bool:
    return (
        isinstance(key, str)
        and bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]{0,48}", key))
        and not PRIVATE_VALUE_RE.search(key)
    )


def _result(
    counts: dict[str, int],
    errors: list[dict[str, str]],
    warnings: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "mode": "fixture-only-preview",
        "writesPerformed": False,
        "counts": counts,
        "errors": errors,
        "warnings": warnings,
    }
