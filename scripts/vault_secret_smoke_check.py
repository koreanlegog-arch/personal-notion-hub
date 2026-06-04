#!/usr/bin/env python3
"""Synthetic smoke test for the windows-dpapi-file vault secret backend."""

from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.secret_backends import backend_available, delete_secret, retrieve_secret  # noqa: E402


FORBIDDEN_VALUE = "synthetic-dpapi-vault-passphrase"


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def assert_no_secret_output(text: str) -> None:
    assert_true(FORBIDDEN_VALUE not in text, "vault_secret_value_printed=true")


def run_script(args: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert_no_secret_output(result.stdout + result.stderr)
    return result


def main() -> int:
    if not backend_available():
        print("vault_secret_smoke_check_skipped=true")
        print("reason=windows_dpapi_file_backend_unavailable")
        return 0

    captured = io.StringIO()
    with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
        secret_name = "synthetic-vault-secret-smoke"
        try:
            delete_secret(name=secret_name)
        except Exception:
            pass
        try:
            env = os.environ.copy()
            env["PNH_SYNTHETIC_DPAPI_PASSPHRASE"] = FORBIDDEN_VALUE

            store = run_script(
                [
                    str(ROOT / "scripts" / "vault_secret_store.py"),
                    "--name",
                    secret_name,
                    "--passphrase-env",
                    "PNH_SYNTHETIC_DPAPI_PASSPHRASE",
                ],
                env,
            )
            assert_true(store.returncode == 0, "vault_secret_store_failed=true")
            store_payload = json.loads(store.stdout)
            assert_true(store_payload["vaultSecretStore"]["set"] is True, "vault_secret_not_set=true")

            status = run_script([str(ROOT / "scripts" / "vault_secret_status.py"), "--name", secret_name], env)
            assert_true(status.returncode == 0, "vault_secret_status_failed=true")
            status_payload = json.loads(status.stdout)
            assert_true(status_payload["vaultSecretStatus"]["set"] is True, "vault_secret_status_not_set=true")

            retrieved = retrieve_secret(name=secret_name)
            assert_true(retrieved == FORBIDDEN_VALUE, "vault_secret_retrieve_failed=true")

            delete = run_script(
                [
                    str(ROOT / "scripts" / "vault_secret_delete.py"),
                    "--name",
                    secret_name,
                    "--confirm",
                    "DELETE_VAULT_SECRET",
                ],
                env,
            )
            assert_true(delete.returncode == 0, "vault_secret_delete_failed=true")
            delete_payload = json.loads(delete.stdout)
            assert_true(delete_payload["vaultSecretDelete"]["set"] is False, "vault_secret_delete_not_cleared=true")
            try:
                retrieve_secret(name=secret_name)
            except Exception:
                pass
            else:
                raise SystemExit("vault_secret_file_remains=true")
        finally:
            try:
                delete_secret(name=secret_name)
            except Exception:
                pass

    assert_no_secret_output(captured.getvalue())
    print("vault_secret_smoke_check_pass=true")
    print("secret_value_printed=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
