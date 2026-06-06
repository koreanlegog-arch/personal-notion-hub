#!/usr/bin/env python3
"""Check current docs for stale script command references.

The check is metadata-only. It scans supervisor-facing docs for
`scripts/...` references and verifies that referenced scripts still exist.
Historical run logs are intentionally excluded because they are immutable
evidence, not current operating guidance.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "ops" / "runs" / "PNH-DOC-SCRIPT-DRIFT-CHECK-20260606" / "doc_script_drift_check.json"
DOC_ROOTS = [ROOT / "README.md", ROOT / "AGENTS.md", ROOT / "docs"]
SCRIPT_REF_RE = re.compile(r"(?<![\w./-])(scripts/[A-Za-z0-9_./-]+\.(?:py|sh|ps1|cjs))")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check current docs for stale script references.")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output JSON path.")
    args = parser.parse_args()

    try:
        payload = build_report()
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        print(f"pnh_doc_script_drift_check=false error={exc}", file=sys.stderr)
        return 2

    print(json.dumps(redact_stdout(payload), ensure_ascii=False, sort_keys=True))
    return 0 if not payload["missingScriptRefs"] else 1


def build_report() -> dict[str, Any]:
    refs: dict[str, list[str]] = {}
    scanned_docs = []
    for doc_path in iter_current_docs():
        scanned_docs.append(safe_rel(doc_path))
        text = doc_path.read_text(encoding="utf-8")
        for match in SCRIPT_REF_RE.finditer(text):
            rel = normalize_ref(match.group(1))
            refs.setdefault(rel, []).append(safe_rel(doc_path))

    missing = []
    existing = []
    for rel in sorted(refs):
        exists = (ROOT / rel).exists()
        item = {
            "script": rel,
            "referencedBy": sorted(set(refs[rel])),
        }
        if exists:
            existing.append(item)
        else:
            missing.append(item)

    return {
        "pnhDocScriptDriftCheck": True,
        "generatedAt": utc_now(),
        "scannedDocs": scanned_docs,
        "scriptRefCount": len(refs),
        "existingScriptRefCount": len(existing),
        "missingScriptRefCount": len(missing),
        "missingScriptRefs": missing,
        "verdict": "current_docs_script_refs_ok" if not missing else "current_docs_script_refs_drift_detected",
        "workMode": {
            "mode": "supervisor-central",
            "efficiencyNote": (
                "A focused drift checker replaces repeated manual grep over the current docs and "
                "keeps historical ops/runs evidence out of the active contract."
            ),
        },
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "exactOwnerNetworkUrlPersisted": False,
        "rawPrivateBodyRead": False,
    }


def iter_current_docs() -> list[Path]:
    docs: list[Path] = []
    for root in DOC_ROOTS:
        if root.is_file():
            docs.append(root)
        elif root.is_dir():
            docs.extend(sorted(path for path in root.rglob("*.md") if path.is_file()))
    return sorted(docs)


def normalize_ref(ref: str) -> str:
    while "//" in ref:
        ref = ref.replace("//", "/")
    return ref.rstrip(".,;:)")


def safe_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.name


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def redact_stdout(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "pnhDocScriptDriftCheck": payload["pnhDocScriptDriftCheck"],
        "scriptRefCount": payload["scriptRefCount"],
        "missingScriptRefCount": payload["missingScriptRefCount"],
        "out": safe_rel(DEFAULT_OUT),
        "privateValuesPrinted": False,
        "tokenValuePrinted": False,
        "verdict": payload["verdict"],
    }


if __name__ == "__main__":
    raise SystemExit(main())
