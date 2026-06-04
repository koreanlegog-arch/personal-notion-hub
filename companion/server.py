#!/usr/bin/env python3
"""Loopback-only HTTP companion prototype.

Endpoints:
- GET /api/health
- GET /api/schema
- POST /api/import/preview
- POST /api/private/mobile-captures
- GET /api/private/mobile-captures
- GET /api/private/summary
"""

from __future__ import annotations

import argparse
import json
import secrets
import sqlite3
import sys
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

try:
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
    from .preview import SCHEMA, preview_import, zero_counts
except ImportError:  # pragma: no cover - supports direct script execution.
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
    from preview import SCHEMA, preview_import, zero_counts


MAX_BODY_BYTES = 64 * 1024
MAX_PRIVATE_BODY_BYTES = 128 * 1024
ALLOWED_HOST = "127.0.0.1"
BROWSER_SESSION_TTL_SECONDS = 10 * 60
BROWSER_PAIRING_TTL_SECONDS = 5 * 60


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
                    "loopbackOnly": True,
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
                "summaryEndpoint": "/api/private/summary",
                "responsePolicy": "metadata-only",
                "storageMode": self.server.private_storage_mode,
                "encryptedVaultEnabled": self.server.private_vault is not None,
            }
            schema["browserBridge"] = {
                "enabled": self.server.browser_bridge_enabled,
                "pairEndpoint": "/api/private/pair",
                "allowedOriginConfigured": bool(self.server.allowed_origin),
                "responsePolicy": "metadata-only",
            }
            self._send_json(HTTPStatus.OK, schema)
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
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_OPTIONS(self) -> None:
        if self._path() not in {
            "/api/private/pair",
            "/api/private/mobile-captures",
            "/api/private/summary",
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
        sys.stderr.write(f"companion_request method={self.command} path={self._path()} client=loopback\n")

    def log_error(self, format: str, *args: Any) -> None:
        sys.stderr.write(f"companion_error method={self.command} path={self._path()} client=loopback\n")

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


def _error_result(path: str, code: str) -> dict[str, Any]:
    return {
        "mode": "fixture-only-preview",
        "writesPerformed": False,
        "counts": zero_counts(),
        "errors": [{"path": path, "code": code}],
        "warnings": [],
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
    browser_session_ttl_seconds: int = BROWSER_SESSION_TTL_SECONDS,
    browser_pairing_ttl_seconds: int = BROWSER_PAIRING_TTL_SECONDS,
) -> CompanionServer:
    if host != ALLOWED_HOST:
        raise ValueError("companion server must bind to 127.0.0.1 only")
    if browser_bridge_enabled:
        if not allowed_origin:
            raise ValueError("browser bridge requires --allowed-origin")
        parsed_origin = urlsplit(allowed_origin)
        if (
            parsed_origin.scheme != "http"
            or parsed_origin.hostname != ALLOWED_HOST
            or not parsed_origin.port
            or parsed_origin.path
            or parsed_origin.query
            or parsed_origin.fragment
            or parsed_origin.username
            or parsed_origin.password
        ):
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
        browser_session_ttl_seconds=browser_session_ttl_seconds,
        browser_pairing_ttl_seconds=browser_pairing_ttl_seconds,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the loopback-only Personal Notion Hub companion.")
    parser.add_argument("--host", default="127.0.0.1", help="Loopback host only. Default: 127.0.0.1")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind. Default: 8765")
    parser.add_argument("--enable-private-inbox", action="store_true", help="Enable authenticated local private inbox writes.")
    parser.add_argument("--enable-encrypted-vault", action="store_true", help="Store private captures in encrypted vault mode.")
    parser.add_argument("--vault-passphrase-env", default="PNH_VAULT_PASSPHRASE", help="Environment variable containing vault passphrase.")
    parser.add_argument("--prompt-vault-passphrase", action="store_true", help="Prompt for vault passphrase without echo. Intended for manual local sessions.")
    parser.add_argument("--enable-browser-bridge", action="store_true", help="Enable exact-origin browser bridge pairing.")
    parser.add_argument("--allowed-origin", default="", help="Allowed browser origin, for example http://127.0.0.1:8000.")
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
