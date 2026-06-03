#!/usr/bin/env python3
"""Static smoke checks for Personal Notion Hub.

This script intentionally avoids external dependencies.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "index.html",
    "favicon.ico",
    "assets/css/styles.css",
    "assets/js/app.js",
    "assets/js/assistant-storage.js",
    "assets/js/assistant-import.js",
    "assets/js/assistant-rules.js",
    "assets/img/workspace-visual.png",
    "data/seed.json",
    "README.md",
    "docs/TEST_PLAN.md",
    "docs/SECURITY_NOTES.md",
    ".github/workflows/pages.yml",
]


class AssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.assets: list[str] = []
        self.has_csp = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = dict(attrs)
        if tag == "link" and data.get("rel") == "stylesheet" and data.get("href"):
            self.assets.append(data["href"])
        if tag == "script" and data.get("src"):
            self.assets.append(data["src"])
        if tag == "meta" and data.get("http-equiv", "").lower() == "content-security-policy":
            self.has_csp = True


def assert_required_files() -> None:
    for rel in REQUIRED:
        path = ROOT / rel
        if not path.exists() or path.stat().st_size == 0:
            raise SystemExit(f"missing_or_empty={rel}")


def assert_html_assets() -> None:
    parser = AssetParser()
    parser.feed((ROOT / "index.html").read_text(encoding="utf-8"))
    if not parser.has_csp:
        raise SystemExit("missing_meta_csp=true")
    for asset in parser.assets:
        asset_path = (ROOT / asset.replace("./", "", 1)).resolve()
        if not asset_path.exists():
            raise SystemExit(f"missing_asset={asset}")


def assert_no_inline_handlers() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    if re.search(r"\son[a-zA-Z]+\s*=", html):
        raise SystemExit("inline_event_handler_found=true")


def assert_expected_app_contracts() -> None:
    js = (ROOT / "assets/js/app.js").read_text(encoding="utf-8")
    expected = [
        "localStorage.getItem",
        "localStorage.setItem",
        "readStoredState",
        "writeStoredState",
        "JSON.parse",
        "JSON.stringify",
        "exportState",
        "handleImport",
        "validateImportedState",
        "renderAssistant",
        "loadAssistantCaptures",
        "PNHAssistantStorage",
        "PNHAssistantImport",
        "PNHAssistantRules",
        "normalizeHttpUrl",
        "textContent",
        "rel = \"noopener noreferrer\"",
    ]
    for token in expected:
        if token not in js:
            raise SystemExit(f"missing_app_contract={token}")
    if "innerHTML" in js:
        raise SystemExit("innerHTML_found=true")


def assert_js_security_contracts() -> None:
    forbidden = ["innerHTML", "fetch(", "XMLHttpRequest("]
    for path in sorted((ROOT / "assets/js").glob("*.js")):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            if token in text:
                raise SystemExit(f"forbidden_js_token={path.relative_to(ROOT)}:{token}")


def assert_workflow_permissions() -> None:
    workflow = (ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8")
    expected = ["contents: read", "pages: write", "id-token: write", "actions/upload-pages-artifact@v4", "actions/deploy-pages@v4"]
    for token in expected:
        if token not in workflow:
            raise SystemExit(f"missing_workflow_contract={token}")


def main() -> int:
    assert_required_files()
    assert_html_assets()
    assert_no_inline_handlers()
    assert_expected_app_contracts()
    assert_js_security_contracts()
    assert_workflow_permissions()
    print("smoke_check_pass=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
