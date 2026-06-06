"""Phone automation adapter payload normalization.

This module converts owner-controlled phone automation payloads into private
capture records. It does not write storage by itself and never returns raw
private body values in response summaries.
"""

from __future__ import annotations

from typing import Any


MAX_ITEMS = 20
PHONE_ADAPTERS = {
    "phone-contacts-json": {
        "source": "phone_contacts",
        "kind": "contact",
        "sensitivity": "private",
    },
    "phone-calendar-json": {
        "source": "phone_calendar",
        "kind": "calendar",
        "sensitivity": "private",
    },
    "phone-call-log-json": {
        "source": "phone_call_log",
        "kind": "call_note",
        "sensitivity": "highly_sensitive",
    },
    "phone-recording-transcript-json": {
        "source": "phone_recording",
        "kind": "voice_note",
        "sensitivity": "highly_sensitive",
    },
}


class PhoneAdapterIngestError(ValueError):
    """Raised when a phone adapter payload is invalid."""


def normalize_phone_adapter_payload(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict) or isinstance(payload, list):
        raise PhoneAdapterIngestError("phone adapter payload must be an object")
    adapter_name = str(payload.get("adapter") or "").strip()
    if adapter_name not in PHONE_ADAPTERS:
        raise PhoneAdapterIngestError("unknown phone adapter")
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        raise PhoneAdapterIngestError("items must be a non-empty list")
    if len(items) > MAX_ITEMS:
        raise PhoneAdapterIngestError("too many phone adapter items")

    defaults = PHONE_ADAPTERS[adapter_name]
    records = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise PhoneAdapterIngestError("each item must be an object")
        title = clean_text(item.get("title") or item.get("name") or item.get("summary") or f"{defaults['kind']} {index}")
        body = clean_text(item.get("body") or item.get("text") or item.get("notes") or item.get("description") or "")
        if not body:
            body = clean_text(item)
        records.append(
            {
                "source": defaults["source"],
                "kind": defaults["kind"],
                "title": title,
                "body": body,
                "sensitivity": clean_sensitivity(item.get("sensitivity") or defaults["sensitivity"]),
                "createdAt": clean_text(item.get("createdAt") or item.get("created_at") or payload.get("createdAt") or ""),
            }
        )
    return records


def clean_sensitivity(value: Any) -> str:
    sensitivity = str(value or "").strip()
    return sensitivity if sensitivity in {"internal", "private", "highly_sensitive"} else "private"


def clean_text(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return str(value)
    return " ".join(str(value or "").replace("\r\n", "\n").split()).strip()
