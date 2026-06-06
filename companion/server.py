#!/usr/bin/env python3
"""Loopback-only HTTP companion prototype.

Endpoints:
- GET /api/health
- GET /api/schema
- POST /api/import/preview
- POST /api/private/mobile-captures
- POST /api/private/phone-adapter-captures
- GET /api/private/phone-adapter-schema
- GET /api/private/mobile-captures
- GET /api/private/summary
- GET /api/private/dispatch-state
- GET /api/private/command-packet-status
- POST /api/private/single-command-packet/run
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import secrets
import sqlite3
import sys
import time
from ipaddress import ip_address
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

try:
    from .command_packet_status import build_command_packet_status
    from .dispatch_summary import summarize_dispatch_record
    from .encrypted_vault import EncryptedVault, EncryptedVaultError, cryptography_available, init_encrypted_vault
    from .passphrase_provider import PassphraseProviderError, resolve_passphrase
    from .private_store import (
        DEFAULT_DB_PATH,
        DEFAULT_TOKEN_PATH,
        PrivateStoreError,
        init_private_store,
        insert_capture,
        list_captures,
        read_token,
        store_summary,
    )
    from .phone_adapter_ingest import PhoneAdapterIngestError, normalize_phone_adapter_payload, phone_adapter_schema
    from .preview import SCHEMA, preview_import, zero_counts
    from .single_command_packet_runner import SingleCommandPacketRunError, run_single_command_packet_from_browser
except ImportError:  # pragma: no cover - supports direct script execution.
    from command_packet_status import build_command_packet_status  # type: ignore
    from dispatch_summary import summarize_dispatch_record  # type: ignore
    from encrypted_vault import EncryptedVault, EncryptedVaultError, cryptography_available, init_encrypted_vault  # type: ignore
    from passphrase_provider import PassphraseProviderError, resolve_passphrase  # type: ignore
    from private_store import (  # type: ignore
        DEFAULT_DB_PATH,
        DEFAULT_TOKEN_PATH,
        PrivateStoreError,
        init_private_store,
        insert_capture,
        list_captures,
        read_token,
        store_summary,
    )
    from phone_adapter_ingest import PhoneAdapterIngestError, normalize_phone_adapter_payload, phone_adapter_schema  # type: ignore
    from preview import SCHEMA, preview_import, zero_counts
    from single_command_packet_runner import SingleCommandPacketRunError, run_single_command_packet_from_browser  # type: ignore


MAX_BODY_BYTES = 64 * 1024
MAX_PRIVATE_BODY_BYTES = 128 * 1024
ALLOWED_HOST = "127.0.0.1"
PHONE_BIND_HOSTS = {"0.0.0.0"}
BROWSER_SESSION_TTL_SECONDS = 10 * 60
BROWSER_PAIRING_TTL_SECONDS = 5 * 60
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DISPATCH_STATE_PATH = ROOT / "companion" / "private" / "pnh_dispatch_state.json"
STATIC_ALLOWED_PREFIXES = ("assets/", "data/")
STATIC_ALLOWED_FILES = {"index.html", "favicon.ico"}


class CompanionServer(ThreadingHTTPServer):
    allow_reuse_address = True

    def __init__(
        self,
        server_address: tuple[str, int],
        handler_class: type[BaseHTTPRequestHandler],
        *,
        private_db_path: Path | None = None,
        auth_token: str | None = None,
        allow_external_private_paths: bool = False,
        private_vault: EncryptedVault | None = None,
        browser_bridge_enabled: bool = False,
        allowed_origin: str | None = None,
        phone_ingress_enabled: bool = False,
        tailnet_ingress_enabled: bool = False,
        browser_session_ttl_seconds: int = BROWSER_SESSION_TTL_SECONDS,
        browser_pairing_ttl_seconds: int = BROWSER_PAIRING_TTL_SECONDS,
    ) -> None:
        super().__init__(server_address, handler_class)
        self.private_db_path = private_db_path
        self.auth_token = auth_token
        self.allow_external_private_paths = allow_external_private_paths
        self.private_vault = private_vault
        self.browser_bridge_enabled = browser_bridge_enabled
        self.allowed_origin = allowed_origin
        self.phone_ingress_enabled = phone_ingress_enabled
        self.tailnet_ingress_enabled = tailnet_ingress_enabled
        self.browser_session_ttl_seconds = browser_session_ttl_seconds
        self.browser_pairing_ttl_seconds = browser_pairing_ttl_seconds
        self.browser_pairing_code = secrets.token_urlsafe(12) if browser_bridge_enabled else ""
        self._pairing_code_expires_at = time.monotonic() + browser_pairing_ttl_seconds
        self._pairing_code_used = False
        self._browser_sessions: dict[str, float] = {}

    @property
    def private_enabled(self) -> bool:
        return self.private_db_path is not None and bool(self.auth_token)

    @property
    def private_storage_mode(self) -> str:
        if self.private_vault is not None:
            return "encrypted-vault"
        if self.private_enabled:
            return "plaintext-inbox"
        return "disabled"

    def create_browser_session(self, pairing_code: str) -> str | None:
        if not self.browser_bridge_enabled or not self.private_enabled or self._pairing_code_used:
            return None
        if self._pairing_code_expires_at <= time.monotonic():
            return None
        expected = self.browser_pairing_code
        if not secrets.compare_digest(pairing_code, expected):
            return None
        self._pairing_code_used = True
        self.browser_pairing_code = ""
        session_token = secrets.token_urlsafe(32)
        self._browser_sessions[session_token] = time.monotonic() + self.browser_session_ttl_seconds
        return session_token

    def has_browser_session(self, session_token: str) -> bool:
        expires_at = self._browser_sessions.get(session_token)
        if expires_at is None:
            return False
        if expires_at <= time.monotonic():
            self._browser_sessions.pop(session_token, None)
            return False
        return True


class CompanionHandler(BaseHTTPRequestHandler):
    server_version = "PersonalNotionCompanion/0.1"
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:
        path = self._path()
        if path == "/api/health":
            self._send_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "mode": "private-inbox" if self.server.private_enabled else "fixture-only-preview",
                    "loopbackOnly": not self.server.phone_ingress_enabled,
                    "phoneIngress": {
                        "enabled": self.server.phone_ingress_enabled,
                        "staticUiServed": self.server.phone_ingress_enabled,
                    },
                    "tailnetIngress": {
                        "enabled": self.server.tailnet_ingress_enabled,
                        "staticUiServed": self.server.tailnet_ingress_enabled,
                    },
                    "writesEnabled": self.server.private_enabled,
                    "authRequired": self.server.private_enabled,
                    "privateStoreConfigured": self.server.private_enabled,
                    "storageMode": self.server.private_storage_mode,
                    "encryptedVault": {
                        "enabled": self.server.private_vault is not None,
                        "cryptographyAvailable": cryptography_available(),
                        "algorithm": self.server.private_vault.algorithm if self.server.private_vault else "",
                    },
                    "browserBridge": {
                        "enabled": self.server.browser_bridge_enabled,
                        "allowedOriginConfigured": bool(self.server.allowed_origin),
                        "sessionTtlSeconds": self.server.browser_session_ttl_seconds,
                        "pairingTtlSeconds": self.server.browser_pairing_ttl_seconds,
                    },
                },
            )
            return
        if path == "/api/schema":
            schema = dict(SCHEMA)
            schema["privateInbox"] = {
                "enabled": self.server.private_enabled,
                "auth": "bearer-token" if self.server.private_enabled else "disabled",
                "writeEndpoint": "/api/private/mobile-captures",
                "phoneAdapterEndpoint": "/api/private/phone-adapter-captures",
                "phoneAdapterSchemaEndpoint": "/api/private/phone-adapter-schema",
                "summaryEndpoint": "/api/private/summary",
                "dispatchStateEndpoint": "/api/private/dispatch-state",
                "commandPacketStatusEndpoint": "/api/private/command-packet-status",
                "singleCommandPacketRunEndpoint": "/api/private/single-command-packet/run",
                "responsePolicy": "metadata-only",
                "storageMode": self.server.private_storage_mode,
                "encryptedVaultEnabled": self.server.private_vault is not None,
            }
            schema["browserBridge"] = {
                "enabled": self.server.browser_bridge_enabled,
                "pairEndpoint": "/api/private/pair",
                "allowedOriginConfigured": bool(self.server.allowed_origin),
                "responsePolicy": "metadata-only",
                "phoneIngressEnabled": self.server.phone_ingress_enabled,
                "tailnetIngressEnabled": self.server.tailnet_ingress_enabled,
            }
            self._send_json(HTTPStatus.OK, schema)
            return
        if (self.server.phone_ingress_enabled or self.server.tailnet_ingress_enabled) and self._serve_static_if_allowed(path):
            return
        if path == "/api/private/summary":
            if not self._require_private_auth():
                return
            summary = store_summary(
                self.server.private_db_path,
                allow_external=self.server.allow_external_private_paths,
            )
            summary.pop("dbPath", None)
            self._send_json(HTTPStatus.OK, {"ok": True, "summary": summary})
            return
        if path == "/api/private/dispatch-state":
            if not self._require_private_auth():
                return
            try:
                state = _load_dispatch_state(DEFAULT_DISPATCH_STATE_PATH)
            except (OSError, ValueError):
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "dispatch_state_read_failed"})
                return
            self._send_json(HTTPStatus.OK, {"ok": True, "dispatchState": _summarize_dispatch_state(state)})
            return
        if path == "/api/private/command-packet-status":
            if not self._require_private_auth():
                return
            try:
                state = _load_dispatch_state(DEFAULT_DISPATCH_STATE_PATH)
            except (OSError, ValueError):
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "command_packet_status_read_failed"})
                return
            self._send_json(HTTPStatus.OK, {"ok": True, "commandPacketStatus": build_command_packet_status(state)})
            return
        if path == "/api/private/mobile-captures":
            if not self._require_private_auth():
                return
            query = parse_qs(urlsplit(self.path).query)
            limit = query.get("limit", ["20"])[0]
            try:
                parsed_limit = int(limit)
            except ValueError:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_limit"})
                return
            try:
                items = list_captures(
                    self.server.private_db_path,
                    limit=parsed_limit,
                    include_body=False,
                    allow_external=self.server.allow_external_private_paths,
                    vault=self.server.private_vault,
                )
            except (OSError, sqlite3.Error, ValueError):
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "private_store_read_failed"})
                return
            self._send_json(HTTPStatus.OK, {"ok": True, "items": items})
            return
        if path == "/api/private/phone-adapter-schema":
            if not self._require_private_auth():
                return
            self._send_json(HTTPStatus.OK, {"ok": True, "phoneAdapterSchema": phone_adapter_schema()})
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self) -> None:
        path = self._path()
        if path == "/api/import/preview":
            self._handle_import_preview()
            return
        if path == "/api/private/pair":
            self._handle_private_pair()
            return
        if path == "/api/private/mobile-captures":
            self._handle_private_capture()
            return
        if path == "/api/private/phone-adapter-captures":
            self._handle_phone_adapter_capture()
            return
        if path == "/api/private/single-command-packet/run":
            self._handle_single_command_packet_run()
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_OPTIONS(self) -> None:
        if self._path() not in {
            "/api/private/pair",
            "/api/private/mobile-captures",
            "/api/private/phone-adapter-schema",
            "/api/private/phone-adapter-captures",
            "/api/private/summary",
            "/api/private/dispatch-state",
            "/api/private/command-packet-status",
            "/api/private/single-command-packet/run",
        }:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        if not self._origin_allowed():
            self._send_json(HTTPStatus.FORBIDDEN, {"error": "origin_not_allowed"})
            return
        self.send_response(HTTPStatus.NO_CONTENT)
        self._send_cors_headers()
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Max-Age", "300")
        self.send_header("Content-Length", "0")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def _handle_import_preview(self) -> None:
        payload, error = self._read_json_payload(MAX_BODY_BYTES)
        if error:
            status, path, code = error
            self._send_json(status, _error_result(path, code))
            return

        result = preview_import(payload)
        status = HTTPStatus.BAD_REQUEST if result["errors"] else HTTPStatus.OK
        self._send_json(status, result)

    def _handle_private_pair(self) -> None:
        if not self.server.browser_bridge_enabled:
            self._send_json(HTTPStatus.FORBIDDEN, {"error": "browser_bridge_disabled"})
            return
        if not self._origin_allowed():
            self._send_json(HTTPStatus.FORBIDDEN, {"error": "origin_not_allowed"})
            return
        if not self.server.private_enabled:
            self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "private_inbox_disabled"})
            return

        payload, error = self._read_json_payload(MAX_BODY_BYTES)
        if error:
            status, _path, code = error
            self._send_json(status, {"error": code})
            return
        if not isinstance(payload, dict):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "pairing_payload_must_be_object"})
            return

        pairing_code = str(payload.get("pairingCode") or "")
        session_token = self.server.create_browser_session(pairing_code)
        if session_token is None:
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return

        self._send_json(
            HTTPStatus.CREATED,
            {
                "ok": True,
                "paired": True,
                "session": {
                    "issued": True,
                    "ttlSeconds": self.server.browser_session_ttl_seconds,
                },
            },
            extra_headers={"X-PNH-Browser-Session": session_token},
        )

    def _handle_private_capture(self) -> None:
        if not self._require_private_auth():
            return

        payload, error = self._read_json_payload(MAX_PRIVATE_BODY_BYTES)
        if error:
            status, _path, code = error
            self._send_json(status, {"error": code})
            return

        try:
            capture = insert_capture(
                self.server.private_db_path,
                payload,
                allow_external=self.server.allow_external_private_paths,
                vault=self.server.private_vault,
            )
        except PrivateStoreError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        except (OSError, sqlite3.Error):
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "private_store_write_failed"})
            return

        self._send_json(HTTPStatus.CREATED, {"ok": True, "writesPerformed": True, "capture": capture})

    def _handle_phone_adapter_capture(self) -> None:
        if not self._require_private_auth():
            return

        payload, error = self._read_json_payload(MAX_PRIVATE_BODY_BYTES)
        if error:
            status, _path, code = error
            self._send_json(status, {"error": code})
            return

        try:
            records = normalize_phone_adapter_payload(payload)
            captures = [
                insert_capture(
                    self.server.private_db_path,
                    record,
                    allow_external=self.server.allow_external_private_paths,
                    vault=self.server.private_vault,
                    dedupe=True,
                )
                for record in records
            ]
        except (PhoneAdapterIngestError, PrivateStoreError) as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        except (OSError, sqlite3.Error):
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "phone_adapter_store_write_failed"})
            return

        self._send_json(
            HTTPStatus.CREATED,
            {
                "ok": True,
                "writesPerformed": True,
                "phoneAdapterCapture": {
                    "recordsAccepted": len(captures),
                    "recordsWritten": len([item for item in captures if not item.get("duplicateSkipped")]),
                    "duplicatesSkipped": len([item for item in captures if item.get("duplicateSkipped")]),
                    "captureIds": [item["id"] for item in captures],
                    "storageMode": self.server.private_storage_mode,
                    "privateValuesPrinted": False,
                },
            },
        )

    def _handle_single_command_packet_run(self) -> None:
        if not self._require_private_auth():
            return

        payload, error = self._read_json_payload(MAX_BODY_BYTES)
        if error:
            status, _path, code = error
            self._send_json(status, {"error": code})
            return
        if not isinstance(payload, dict):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "single_command_packet_payload_must_be_object"})
            return

        mode = str(payload.get("mode") or "dry-run")
        confirm_apply = str(payload.get("confirmApply") or "")
        try:
            result = run_single_command_packet_from_browser(mode=mode, confirm_apply=confirm_apply)
        except SingleCommandPacketRunError as exc:
            self._send_json(
                HTTPStatus(exc.status_code),
                {
                    "ok": False,
                    "error": exc.code,
                    "externalWritesPerformed": False,
                    "workerRunPerformed": False,
                    "privateValuesPrinted": False,
                    "rawPrivateBodyRead": False,
                },
            )
            return
        except (OSError, TimeoutError):
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {
                    "ok": False,
                    "error": "single_command_packet_run_unavailable",
                    "externalWritesPerformed": False,
                    "workerRunPerformed": False,
                    "privateValuesPrinted": False,
                    "rawPrivateBodyRead": False,
                },
            )
            return

        self._send_json(HTTPStatus.OK, {"ok": bool(result.get("ok")), "singleCommandPacketRun": result})

    def _read_json_payload(
        self,
        max_body_bytes: int,
    ) -> tuple[Any | None, tuple[HTTPStatus, str, str] | None]:
        content_type = self.headers.get("Content-Type", "")
        if "application/json" not in content_type.lower():
            return None, (
                HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                "$.headers.content-type",
                "content_type_must_be_application_json",
            )

        length_header = self.headers.get("Content-Length")
        try:
            length = int(length_header or "0")
        except ValueError:
            return None, (HTTPStatus.BAD_REQUEST, "$.headers.content-length", "invalid_content_length")

        if length <= 0:
            return None, (HTTPStatus.BAD_REQUEST, "$", "empty_body")
        if length > max_body_bytes:
            return None, (HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "$", "body_too_large")

        raw_body = self.rfile.read(length)
        try:
            return json.loads(raw_body.decode("utf-8")), None
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None, (HTTPStatus.BAD_REQUEST, "$", "invalid_json")

    def _require_private_auth(self) -> bool:
        if not self.server.private_enabled:
            self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "private_inbox_disabled"})
            return False

        if self.headers.get("Origin") and not self._origin_allowed():
            self._send_json(HTTPStatus.FORBIDDEN, {"error": "origin_not_allowed"})
            return False

        auth_header = self.headers.get("Authorization", "")
        prefix = "Bearer "
        if not auth_header.startswith(prefix):
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return False

        presented = auth_header[len(prefix) :].strip()
        expected = self.server.auth_token or ""
        if not secrets.compare_digest(presented, expected):
            if not (self._origin_allowed() and self.server.has_browser_session(presented)):
                self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                return False
        return True

    def log_message(self, format: str, *args: Any) -> None:
        client_label = _client_label(self.server)
        sys.stderr.write(f"companion_request method={self.command} path={self._path()} client={client_label}\n")

    def log_error(self, format: str, *args: Any) -> None:
        client_label = _client_label(self.server)
        sys.stderr.write(f"companion_error method={self.command} path={self._path()} client={client_label}\n")

    def _path(self) -> str:
        return urlsplit(self.path).path

    def _origin_allowed(self) -> bool:
        if not self.server.browser_bridge_enabled:
            return False
        origin = self.headers.get("Origin", "")
        allowed_origin = self.server.allowed_origin or ""
        return bool(origin) and origin == allowed_origin

    def _send_cors_headers(self) -> None:
        if self._origin_allowed():
            self.send_header("Access-Control-Allow-Origin", self.server.allowed_origin or "")
            self.send_header("Access-Control-Expose-Headers", "X-PNH-Browser-Session")
            self.send_header("Vary", "Origin")

    def _send_json(
        self,
        status: HTTPStatus,
        payload: dict[str, Any],
        *,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self._send_cors_headers()
        for name, value in (extra_headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def _serve_static_if_allowed(self, path: str) -> bool:
        rel = "index.html" if path in {"", "/"} else path.lstrip("/")
        if not _static_path_allowed(rel):
            return False
        target = (ROOT / rel).resolve()
        if not target.is_file() or ROOT not in target.parents:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return True
        body = target.read_bytes()
        content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)
        return True


def _error_result(path: str, code: str) -> dict[str, Any]:
    return {
        "mode": "fixture-only-preview",
        "writesPerformed": False,
        "counts": zero_counts(),
        "errors": [{"path": path, "code": code}],
        "warnings": [],
    }


def _load_dispatch_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("dispatch state must be an object")
    return value


def _summarize_dispatch_state(state: dict[str, Any], limit: int = 20) -> dict[str, Any]:
    records = []
    for packet_id, value in sorted(state.items(), key=lambda item: str(item[1].get("updatedAt", "")), reverse=True):
        if not isinstance(value, dict):
            continue
        records.append(summarize_dispatch_record(str(packet_id), value))
    return {
        "totalRecords": len(records),
        "githubLinked": sum(1 for item in records if item["githubIssueSet"]),
        "discordLinked": sum(1 for item in records if item["discordThreadSet"]),
        "workerResults": sum(1 for item in records if item["workerResultSet"]),
        "privateValuesPrinted": False,
        "records": records[:limit],
    }


def create_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    *,
    private_db_path: Path | None = None,
    auth_token: str | None = None,
    allow_external_private_paths: bool = False,
    private_vault: EncryptedVault | None = None,
    browser_bridge_enabled: bool = False,
    allowed_origin: str | None = None,
    phone_ingress_enabled: bool = False,
    tailnet_ingress_enabled: bool = False,
    browser_session_ttl_seconds: int = BROWSER_SESSION_TTL_SECONDS,
    browser_pairing_ttl_seconds: int = BROWSER_PAIRING_TTL_SECONDS,
) -> CompanionServer:
    if phone_ingress_enabled and tailnet_ingress_enabled:
        raise ValueError("phone ingress and tailnet ingress are separate modes")
    if host != ALLOWED_HOST and not phone_ingress_enabled:
        raise ValueError("companion server must bind to 127.0.0.1 only unless --enable-phone-ingress is set")
    if tailnet_ingress_enabled and host != ALLOWED_HOST:
        raise ValueError("tailnet ingress must bind to 127.0.0.1 and be exposed through Tailscale Serve")
    if phone_ingress_enabled and host not in PHONE_BIND_HOSTS and not _is_private_or_loopback_host(host):
        raise ValueError("phone ingress host must be 0.0.0.0, 127.0.0.1, or a private LAN IP")
    if (phone_ingress_enabled or tailnet_ingress_enabled) and not browser_bridge_enabled:
        raise ValueError("phone ingress requires --enable-browser-bridge")
    if browser_bridge_enabled:
        if not allowed_origin:
            raise ValueError("browser bridge requires --allowed-origin")
        parsed_origin = urlsplit(allowed_origin)
        if _has_origin_path_or_credentials(parsed_origin):
            raise ValueError("browser bridge allowed origin must not include path, query, credentials, or fragment")
        if tailnet_ingress_enabled:
            if not _is_tailnet_allowed_origin(parsed_origin):
                raise ValueError(
                    "tailnet ingress allowed origin must be https://<device>.<tailnet>.ts.net "
                    "or http://<tailnet-ip-or-dns>:8765"
                )
        elif (
            parsed_origin.scheme != "http"
            or not parsed_origin.hostname
            or not parsed_origin.port
        ):
            raise ValueError("browser bridge allowed origin must be http://<host>:<port>")
        elif phone_ingress_enabled:
            if parsed_origin.hostname in {"0.0.0.0", "localhost"}:
                raise ValueError("phone ingress allowed origin must use a concrete loopback or private LAN host")
            if not _is_private_or_loopback_host(parsed_origin.hostname):
                raise ValueError("phone ingress allowed origin must use loopback or private LAN host")
        elif parsed_origin.hostname != ALLOWED_HOST:
            raise ValueError("browser bridge allowed origin must be http://127.0.0.1:<port>")
    return CompanionServer(
        (host, port),
        CompanionHandler,
        private_db_path=private_db_path,
        auth_token=auth_token,
        allow_external_private_paths=allow_external_private_paths,
        private_vault=private_vault,
        browser_bridge_enabled=browser_bridge_enabled,
        allowed_origin=allowed_origin,
        phone_ingress_enabled=phone_ingress_enabled,
        tailnet_ingress_enabled=tailnet_ingress_enabled,
        browser_session_ttl_seconds=browser_session_ttl_seconds,
        browser_pairing_ttl_seconds=browser_pairing_ttl_seconds,
    )


def _has_origin_path_or_credentials(parsed_origin: Any) -> bool:
    return bool(
        parsed_origin.path
        or parsed_origin.query
        or parsed_origin.fragment
        or parsed_origin.username
        or parsed_origin.password
    )


def _client_label(server: CompanionServer) -> str:
    if server.tailnet_ingress_enabled:
        return "tailnet"
    if server.phone_ingress_enabled:
        return "lan"
    return "loopback"


def _is_private_or_loopback_host(host: str) -> bool:
    try:
        parsed = ip_address(host)
    except ValueError:
        return False
    return parsed.is_private or parsed.is_loopback


def _is_tailnet_ipv4_host(host: str) -> bool:
    try:
        parsed = ip_address(host)
    except ValueError:
        return False
    return parsed.version == 4 and ip_address("100.64.0.0") <= parsed <= ip_address("100.127.255.255")


def _is_tailnet_allowed_origin(parsed_origin) -> bool:
    hostname = parsed_origin.hostname or ""
    if (
        parsed_origin.scheme == "https"
        and hostname.endswith(".ts.net")
        and parsed_origin.port in {None, 443}
    ):
        return True
    if parsed_origin.scheme != "http" or parsed_origin.port != 8765:
        return False
    return hostname.endswith(".ts.net") or _is_tailnet_ipv4_host(hostname)


def _static_path_allowed(rel: str) -> bool:
    if ".." in Path(rel).parts or rel.startswith("/"):
        return False
    if rel in STATIC_ALLOWED_FILES:
        return True
    return rel.startswith(STATIC_ALLOWED_PREFIXES)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the local Personal Notion Hub companion.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host. Default: 127.0.0.1. Non-loopback requires --enable-phone-ingress.")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind. Default: 8765")
    parser.add_argument("--enable-private-inbox", action="store_true", help="Enable authenticated local private inbox writes.")
    parser.add_argument("--enable-encrypted-vault", action="store_true", help="Store private captures in encrypted vault mode.")
    parser.add_argument("--vault-passphrase-env", default="PNH_VAULT_PASSPHRASE", help="Environment variable containing vault passphrase.")
    parser.add_argument("--prompt-vault-passphrase", action="store_true", help="Prompt for vault passphrase without echo. Intended for manual local sessions.")
    parser.add_argument("--vault-passphrase-provider", default="", help="Optional passphrase provider, for example windows-dpapi-file.")
    parser.add_argument("--vault-passphrase-name", default="vault-passphrase", help="Provider secret name.")
    parser.add_argument("--vault-passphrase-file", default="", help="Provider-specific secret file path.")
    parser.add_argument("--enable-browser-bridge", action="store_true", help="Enable exact-origin browser bridge pairing.")
    parser.add_argument("--allowed-origin", default="", help="Allowed browser origin, for example http://127.0.0.1:8000.")
    parser.add_argument("--enable-phone-ingress", action="store_true", help="Serve PNH UI/API for explicit private LAN phone testing.")
    parser.add_argument("--enable-tailnet-ingress", action="store_true", help="Serve PNH UI/API through Tailscale Serve while binding only to 127.0.0.1.")
    parser.add_argument("--private-db", default="", help="Private inbox SQLite path. Default: companion/private/...")
    parser.add_argument("--token-file", default="", help="Auth token file path. Default: companion/private/auth_token")
    args = parser.parse_args()

    if args.enable_browser_bridge and not args.enable_private_inbox:
        print("startup_error=browser_bridge_requires_private_inbox", file=sys.stderr)
        return 2
    if args.enable_encrypted_vault and not args.enable_private_inbox:
        print("startup_error=encrypted_vault_requires_private_inbox", file=sys.stderr)
        return 2

    private_db_path = None
    auth_token = None
    private_vault = None
    if args.enable_private_inbox:
        private_db_path = Path(args.private_db) if args.private_db else DEFAULT_DB_PATH
        token_path = Path(args.token_file) if args.token_file else DEFAULT_TOKEN_PATH
        try:
            auth_token = read_token(token_path)
            init_private_store(private_db_path)
            if args.enable_encrypted_vault:
                vault_passphrase = resolve_passphrase(
                    env_name=args.vault_passphrase_env,
                    label="vault",
                    prompt=args.prompt_vault_passphrase,
                    provider=args.vault_passphrase_provider,
                    secret_name=args.vault_passphrase_name,
                    secret_path=args.vault_passphrase_file,
                ).value
                private_vault = init_encrypted_vault(private_db_path, vault_passphrase)
        except (OSError, PrivateStoreError) as exc:
            print(f"startup_error=private_inbox_unavailable detail={exc}", file=sys.stderr)
            return 2
        except (EncryptedVaultError, PassphraseProviderError) as exc:
            print(f"startup_error=encrypted_vault_unavailable detail={exc}", file=sys.stderr)
            return 2

    try:
        httpd = create_server(
            args.host,
            args.port,
            private_db_path=private_db_path,
            auth_token=auth_token,
            private_vault=private_vault,
            browser_bridge_enabled=args.enable_browser_bridge,
            allowed_origin=args.allowed_origin or None,
            phone_ingress_enabled=args.enable_phone_ingress,
            tailnet_ingress_enabled=args.enable_tailnet_ingress,
        )
    except ValueError as exc:
        print(f"startup_error={exc}", file=sys.stderr)
        return 2

    host, port = httpd.server_address[:2]
    print(f"companion_listening=http://{host}:{port}")
    print(f"private_inbox_enabled={httpd.private_enabled}")
    print(f"private_storage_mode={httpd.private_storage_mode}")
    print(f"encrypted_vault_enabled={httpd.private_vault is not None}")
    print(f"browser_bridge_enabled={httpd.browser_bridge_enabled}")
    print(f"phone_ingress_enabled={httpd.phone_ingress_enabled}")
    print(f"tailnet_ingress_enabled={httpd.tailnet_ingress_enabled}")
    if httpd.browser_bridge_enabled:
        print(f"browser_pairing_code={httpd.browser_pairing_code}")
        print(f"browser_pairing_code_ttl_seconds={httpd.browser_pairing_ttl_seconds}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("companion_shutdown=keyboard_interrupt")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
