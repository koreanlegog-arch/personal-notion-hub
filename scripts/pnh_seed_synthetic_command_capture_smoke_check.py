#!/usr/bin/env python3
"""Smoke check for synthetic encrypted command capture seeding."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

PRIVATE_TITLE = "synthetic-seed-private-title"
PRIVATE_BODY = "synthetic-seed-private-body"


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "private" / "pnh_private_inbox.sqlite"
        env = os.environ.copy()
        env["PNH_SYNTHETIC_SEED_VAULT_PASSPHRASE"] = "synthetic-seed-vault-passphrase"
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "pnh_seed_synthetic_command_capture.py"),
                "--db",
                str(db_path),
                "--vault-passphrase-env",
                "PNH_SYNTHETIC_SEED_VAULT_PASSPHRASE",
                "--vault-passphrase-provider",
                "",
                "--allow-external-db",
                "--title",
                PRIVATE_TITLE,
                "--body",
                PRIVATE_BODY,
            ],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert_true(result.returncode == 0, f"seed_capture_failed={result.stderr.strip()}")
        assert_true(PRIVATE_TITLE not in result.stdout, "private_title_printed=true")
        assert_true(PRIVATE_BODY not in result.stdout, "private_body_printed=true")
        payload = json.loads(result.stdout)
        assert_true(payload["pnhSeedSyntheticCommandCapture"] is True, "seed_flag_missing=true")
        assert_true(payload["encrypted"] is True, "seed_not_encrypted=true")
        assert_true(payload["storageMode"] == "encrypted-vault", "seed_storage_mode_failed=true")

    print("pnh_seed_synthetic_command_capture_smoke_check_pass=true")
    print("private_values_printed=false")
    print("secret_value_printed=false")
    return 0


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


if __name__ == "__main__":
    raise SystemExit(main())
