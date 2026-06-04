#!/usr/bin/env python3
"""Loopback-only HTTP companion prototype.

Endpoints:
- GET /api/health
- GET /api/schema
- POST /api/import/preview
"""

from __future__ import annotations

import argparse
import json
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlsplit

try:
    from .preview import SCHEMA, preview_import, zero_counts
except ImportError:  # pragma: no cover - supports direct script execution.
    from preview import SCHEMA, preview_import, zero_counts


MAX_BODY_BYTES = 64 * 1024
ALLOWED_HOST = "127.0.0.1"


class CompanionServer(ThreadingHTTPServer):
    allow_reuse_address = True


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
                    "mode": "fixture-only-preview",
                    "loopbackOnly": True,
                    "writesEnabled": False,
                },
            )
            return
        if path == "/api/schema":
            self._send_json(HTTPStatus.OK, SCHEMA)
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self) -> None:
        if self._path() != "/api/import/preview":
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return

        content_type = self.headers.get("Content-Type", "")
        if "application/json" not in content_type.lower():
            self._send_json(
                HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                _error_result("$.headers.content-type", "content_type_must_be_application_json"),
            )
            return

        length_header = self.headers.get("Content-Length")
        try:
            length = int(length_header or "0")
        except ValueError:
            self._send_json(HTTPStatus.BAD_REQUEST, _error_result("$.headers.content-length", "invalid_content_length"))
            return

        if length <= 0:
            self._send_json(HTTPStatus.BAD_REQUEST, _error_result("$", "empty_body"))
            return
        if length > MAX_BODY_BYTES:
            self._send_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, _error_result("$", "body_too_large"))
            return

        raw_body = self.rfile.read(length)
        try:
            payload: Any = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(HTTPStatus.BAD_REQUEST, _error_result("$", "invalid_json"))
            return

        result = preview_import(payload)
        status = HTTPStatus.BAD_REQUEST if result["errors"] else HTTPStatus.OK
        self._send_json(status, result)

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


def create_server(host: str = "127.0.0.1", port: int = 8765) -> CompanionServer:
    if host != ALLOWED_HOST:
        raise ValueError("companion server must bind to 127.0.0.1 only")
    return CompanionServer((host, port), CompanionHandler)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the fixture-only Personal Notion Hub companion.")
    parser.add_argument("--host", default="127.0.0.1", help="Loopback host only. Default: 127.0.0.1")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind. Default: 8765")
    args = parser.parse_args()

    try:
        httpd = create_server(args.host, args.port)
    except ValueError as exc:
        print(f"startup_error={exc}", file=sys.stderr)
        return 2

    host, port = httpd.server_address[:2]
    print(f"companion_listening=http://{host}:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("companion_shutdown=keyboard_interrupt")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
