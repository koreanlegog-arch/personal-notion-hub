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
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

try:
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
    ) -> None:
        super().__init__(server_address, handler_class)
        self.private_db_path = private_db_path
        self.auth_token = auth_token
        self.allow_external_private_paths = allow_external_private_paths

    @property
    def private_enabled(self) -> bool:
        return self.private_db_path is not None and bool(self.auth_token)


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
        if path == "/api/private/mobile-captures":
            self._handle_private_capture()
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def _handle_import_preview(self) -> None:
        payload, error = self._read_json_payload(MAX_BODY_BYTES)
        if error:
            status, path, code = error
            self._send_json(status, _error_result(path, code))
            return

        result = preview_import(payload)
        status = HTTPStatus.BAD_REQUEST if result["errors"] else HTTPStatus.OK
        self._send_json(status, result)

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

        auth_header = self.headers.get("Authorization", "")
        prefix = "Bearer "
        if not auth_header.startswith(prefix):
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return False

        presented = auth_header[len(prefix) :].strip()
        expected = self.server.auth_token or ""
        if not secrets.compare_digest(presented, expected):
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return False
        return True

    def log_message(self, format: str, *args: Any) -> None:
        sys.stderr.write(f"companion_request method={self.command} path={self._path()} client=loopback\n")

    def log_error(self, format: str, *args: Any) -> None:
        sys.stderr.write(f"companion_error method={self.command} path={self._path()} client=loopback\n")

    def _path(self) -> str:
        return urlsplit(self.path).path

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
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
) -> CompanionServer:
    if host != ALLOWED_HOST:
        raise ValueError("companion server must bind to 127.0.0.1 only")
    return CompanionServer(
        (host, port),
        CompanionHandler,
        private_db_path=private_db_path,
        auth_token=auth_token,
        allow_external_private_paths=allow_external_private_paths,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the loopback-only Personal Notion Hub companion.")
    parser.add_argument("--host", default="127.0.0.1", help="Loopback host only. Default: 127.0.0.1")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind. Default: 8765")
    parser.add_argument("--enable-private-inbox", action="store_true", help="Enable authenticated local private inbox writes.")
    parser.add_argument("--private-db", default="", help="Private inbox SQLite path. Default: companion/private/...")
    parser.add_argument("--token-file", default="", help="Auth token file path. Default: companion/private/auth_token")
    args = parser.parse_args()

    private_db_path = None
    auth_token = None
    if args.enable_private_inbox:
        private_db_path = Path(args.private_db) if args.private_db else DEFAULT_DB_PATH
        token_path = Path(args.token_file) if args.token_file else DEFAULT_TOKEN_PATH
        try:
            auth_token = read_token(token_path)
            init_private_store(private_db_path)
        except (OSError, PrivateStoreError) as exc:
            print(f"startup_error=private_inbox_unavailable detail={exc}", file=sys.stderr)
            return 2

    try:
        httpd = create_server(args.host, args.port, private_db_path=private_db_path, auth_token=auth_token)
    except ValueError as exc:
        print(f"startup_error={exc}", file=sys.stderr)
        return 2

    host, port = httpd.server_address[:2]
    print(f"companion_listening=http://{host}:{port}")
    print(f"private_inbox_enabled={httpd.private_enabled}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("companion_shutdown=keyboard_interrupt")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
