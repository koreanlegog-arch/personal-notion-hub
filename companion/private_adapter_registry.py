"""Private adapter registry for owner-exported PNH local imports."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PrivateAdapter:
    name: str
    kind: str
    source: str
    extensions: tuple[str, ...]
    sensitivity: str
    live_external: bool = False


ADAPTERS: dict[str, PrivateAdapter] = {
    "contacts-csv": PrivateAdapter(
        name="contacts-csv",
        kind="contact",
        source="contacts_adapter",
        extensions=(".csv",),
        sensitivity="private",
    ),
    "calendar-ics": PrivateAdapter(
        name="calendar-ics",
        kind="calendar",
        source="calendar_adapter",
        extensions=(".ics",),
        sensitivity="private",
    ),
    "call-log-csv": PrivateAdapter(
        name="call-log-csv",
        kind="call_note",
        source="call_log_adapter",
        extensions=(".csv",),
        sensitivity="highly_sensitive",
    ),
    "recording-transcript-txt": PrivateAdapter(
        name="recording-transcript-txt",
        kind="voice_note",
        source="recording_transcript_adapter",
        extensions=(".txt",),
        sensitivity="highly_sensitive",
    ),
}


def adapter_names() -> list[str]:
    return sorted(ADAPTERS)


def adapter_for_name(name: str) -> PrivateAdapter:
    try:
        return ADAPTERS[name]
    except KeyError as exc:
        raise ValueError(f"unsupported adapter: {name}") from exc


def infer_adapter_from_path(path: Path) -> str:
    suffix = path.suffix.lower()
    lower_name = path.name.lower()
    if suffix == ".ics":
        return "calendar-ics"
    if suffix == ".txt":
        return "recording-transcript-txt"
    if suffix == ".csv":
        if any(token in lower_name for token in ("call", "calls", "phone-log", "call-log")):
            return "call-log-csv"
        return "contacts-csv"
    raise ValueError(f"unsupported owner-exported file extension: {suffix or '[none]'}")


def registry_summary() -> list[dict[str, object]]:
    return [
        {
            "adapter": adapter.name,
            "kind": adapter.kind,
            "source": adapter.source,
            "extensions": list(adapter.extensions),
            "sensitivity": adapter.sensitivity,
            "liveExternal": adapter.live_external,
            "storageMode": "encrypted-vault",
        }
        for adapter in sorted(ADAPTERS.values(), key=lambda item: item.name)
    ]
