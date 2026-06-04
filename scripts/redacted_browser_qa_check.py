#!/usr/bin/env python3
"""Static redacted browser QA checks for Personal Notion Hub."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require_token(path: Path, token: str) -> None:
    if token not in path.read_text(encoding="utf-8"):
        raise SystemExit(f"missing_redacted_browser_qa_token={path.relative_to(ROOT)}:{token}")


def main() -> int:
    css = ROOT / "assets" / "css" / "styles.css"
    app = ROOT / "assets" / "js" / "app.js"
    bridge = ROOT / "assets" / "js" / "companion-bridge.js"
    html = ROOT / "index.html"

    for token in (
        'body.screenshot-redaction [data-sensitive="true"]',
        "color: transparent",
        "caret-color: transparent",
    ):
        require_token(css, token)
    for token in (
        "toggleScreenshotRedaction",
        "data-sensitive",
        "screenshotRedaction",
    ):
        require_token(app, token)
    for token in (
        "cache: \"no-store\"",
        "let sessionToken = \"\"",
        "sessionStorage",
        "localStorage",
    ):
        text = bridge.read_text(encoding="utf-8")
        if token in {"sessionStorage", "localStorage"}:
            if token in text:
                raise SystemExit(f"redacted_browser_qa_forbidden_bridge_token={token}")
        else:
            require_token(bridge, token)
    require_token(html, "Content-Security-Policy")

    print("redacted_browser_qa_check_pass=true")
    print("real_private_values_used=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
