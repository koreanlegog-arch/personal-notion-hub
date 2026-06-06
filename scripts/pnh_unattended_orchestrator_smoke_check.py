#!/usr/bin/env python3
"""Smoke check for the PNH unattended orchestrator wrapper."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.private_store import init_private_store, insert_capture  # noqa: E402

SECRET = "synthetic-private-body-do-not-leak"


def main() -> int:
    temp_root = Path(tempfile.mkdtemp(prefix="pnh-unattended-orchestrator-smoke-"))
    try:
        db_path = temp_root / "private.sqlite"
        run_dir = temp_root / "run"
        make_private_inbox(db_path)
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_unattended_orchestrator.py"),
                "--run-dir",
                str(run_dir),
                "--db",
                str(db_path),
                "--state-file",
                str(temp_root / "dispatch_state.json"),
                "--history-json",
                str(temp_root / "dispatch_history.json"),
                "--trigger-capture-id",
                "capture-synthetic",
                "--cooldown-minutes",
                "0",
                "--max-external-writes-per-hour",
                "0",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        combined = result.stdout + "\n" + result.stderr
        if result.returncode != 0:
            raise AssertionError(combined)
        if SECRET in combined:
            raise AssertionError("private body leaked in orchestrator stdout/stderr")
        summary_path = next(run_dir.glob("*/unattended_orchestrator_summary.json"), run_dir / "unattended_orchestrator_summary.json")
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if not summary.get("pnhUnattendedOrchestrator"):
            raise AssertionError("orchestrator summary marker missing")
        if summary.get("rawPrivateBodyRead"):
            raise AssertionError("raw private body read flag must be false")
        summary_text = summary_path.read_text(encoding="utf-8")
        if SECRET in summary_text:
            raise AssertionError("private body leaked in orchestrator summary")
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
    print("pnh_unattended_orchestrator_smoke_check_pass=true")
    return 0


def make_private_inbox(path: Path) -> None:
    init_private_store(path, allow_external=True)
    insert_capture(
        path,
        {
            "id": "capture-synthetic",
            "source": "mobile_web",
            "kind": "task_request",
            "title": "Synthetic task",
            "body": SECRET,
            "sensitivity": "internal",
            "createdAt": "2026-06-06T00:00:00Z",
        },
        allow_external=True,
    )


if __name__ == "__main__":
    raise SystemExit(main())
