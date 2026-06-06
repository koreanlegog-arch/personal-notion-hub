"""Owner device refresh credentials for the PNH browser bridge.

This module stores only salted credential hashes and metadata. The raw owner
device credential is returned once to the browser and must not be logged or
written to tracked evidence.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OWNER_DEVICE_STORE = ROOT / "companion" / "private" / "owner_devices.json"
TOKEN_PREFIX = "pnh_odc_"


class OwnerDeviceSessionError(ValueError):
    """Raised when owner device credential state is invalid."""


def issue_owner_device_credential(
    store_path: Path = DEFAULT_OWNER_DEVICE_STORE,
    *,
    ttl_days: int = 14,
    device_label: str = "owner-browser",
    origin: str = "",
    max_devices: int = 5,
) -> dict[str, Any]:
    """Create a refresh credential and persist only its hash metadata."""

    ttl_days = max(1, min(int(ttl_days), 30))
    max_devices = max(1, min(int(max_devices), 20))
    credential = TOKEN_PREFIX + secrets.token_urlsafe(32)
    now = utc_now()
    expires_at = (datetime.now(timezone.utc) + timedelta(days=ttl_days)).isoformat(timespec="seconds")
    store = load_store(store_path)
    devices = [item for item in store.get("devices", []) if not is_expired(item)]
    salt = secrets.token_hex(16)
    record = {
        "id": "owner-device-" + secrets.token_hex(8),
        "credentialSalt": salt,
        "credentialHash": hash_credential(credential, salt=salt),
        "deviceLabel": compact(device_label, max_len=80) or "owner-browser",
        "origin": compact(origin, max_len=180),
        "scopes": ["capture:write", "dispatch:intent", "status:read"],
        "createdAt": now,
        "expiresAt": expires_at,
        "lastSeenAt": "",
        "revokedAt": "",
    }
    devices.insert(0, record)
    store["devices"] = devices[:max_devices]
    store["updatedAt"] = now
    save_store(store_path, store)
    return {
        "credential": credential,
        "metadata": public_device_metadata(record),
        "ttlSeconds": ttl_days * 24 * 60 * 60,
    }


def validate_owner_device_credential(
    credential: str,
    store_path: Path = DEFAULT_OWNER_DEVICE_STORE,
    *,
    origin: str = "",
) -> dict[str, Any] | None:
    """Return public metadata if the credential is active, otherwise None."""

    credential = str(credential or "").strip()
    if not credential.startswith(TOKEN_PREFIX):
        return None
    store = load_store(store_path)
    now = utc_now()
    changed = False
    for item in store.get("devices", []):
        if not credential_matches(credential, item):
            continue
        if item.get("revokedAt") or is_expired(item):
            return None
        if origin and item.get("origin") and item.get("origin") != origin:
            return None
        item["lastSeenAt"] = now
        changed = True
        if changed:
            store["updatedAt"] = now
            save_store(store_path, store)
        return public_device_metadata(item)
    return None


def revoke_owner_device_credential(
    credential: str,
    store_path: Path = DEFAULT_OWNER_DEVICE_STORE,
) -> bool:
    """Revoke a credential by hash without exposing the raw credential."""

    credential = str(credential or "").strip()
    if not credential:
        return False
    store = load_store(store_path)
    now = utc_now()
    changed = False
    for item in store.get("devices", []):
        if credential_matches(credential, item) and not item.get("revokedAt"):
            item["revokedAt"] = now
            changed = True
    if changed:
        store["updatedAt"] = now
        save_store(store_path, store)
    return changed


def owner_device_summary(store_path: Path = DEFAULT_OWNER_DEVICE_STORE) -> dict[str, Any]:
    store = load_store(store_path)
    devices = store.get("devices", [])
    active = [item for item in devices if not item.get("revokedAt") and not is_expired(item)]
    return {
        "storePath": safe_path_label(store_path),
        "deviceCount": len(devices),
        "activeDeviceCount": len(active),
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
    }


def load_store(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schemaVersion": 1, "devices": [], "updatedAt": ""}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise OwnerDeviceSessionError("owner device store JSON is invalid") from exc
    if not isinstance(payload, dict):
        raise OwnerDeviceSessionError("owner device store must be an object")
    payload.setdefault("schemaVersion", 1)
    payload.setdefault("devices", [])
    if not isinstance(payload["devices"], list):
        raise OwnerDeviceSessionError("owner device store devices must be a list")
    return payload


def save_store(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        os.chmod(path, 0o600)
        os.chmod(path.parent, 0o700)
    except OSError:
        pass


def credential_matches(credential: str, record: dict[str, Any]) -> bool:
    stored = str(record.get("credentialHash") or "")
    if not stored:
        return False
    salt = str(record.get("credentialSalt") or "")
    expected = hash_credential(credential, salt=salt)
    if secrets.compare_digest(stored, expected):
        return True
    # Backward-compatible fallback for any local ignored store created before
    # salted hashes were introduced. New records always include a salt.
    if not salt:
        return secrets.compare_digest(stored, hash_credential(credential))
    return False


def hash_credential(credential: str, *, salt: str = "") -> str:
    if not credential:
        return ""
    material = f"{salt}:{credential}" if salt else credential
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def public_device_metadata(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": record.get("id", ""),
        "deviceLabel": record.get("deviceLabel", ""),
        "scopes": record.get("scopes", []),
        "createdAt": record.get("createdAt", ""),
        "expiresAt": record.get("expiresAt", ""),
        "lastSeenAt": record.get("lastSeenAt", ""),
        "originBound": bool(record.get("origin")),
    }


def is_expired(record: dict[str, Any]) -> bool:
    try:
        expires_at = datetime.fromisoformat(str(record.get("expiresAt") or "").replace("Z", "+00:00"))
    except ValueError:
        return True
    return expires_at <= datetime.now(timezone.utc)


def compact(value: Any, *, max_len: int) -> str:
    return " ".join(str(value or "").replace("\n", " ").split()).strip()[:max_len]


def safe_path_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return "[external-path]"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
