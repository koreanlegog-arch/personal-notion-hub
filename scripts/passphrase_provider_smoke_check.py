#!/usr/bin/env python3
"""Smoke self-test for passphrase provider behavior."""

from __future__ import annotations

import contextlib
import io
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.passphrase_provider import PassphraseProviderError, keychain_readiness, resolve_passphrase  # noqa: E402


FORBIDDEN_VALUE = "synthetic-provider-secret-passphrase"


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def assert_no_secret_output(text: str) -> None:
    assert_true(FORBIDDEN_VALUE not in text, "passphrase_value_printed=true")


def main() -> int:
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
        env_name = "PNH_SYNTHETIC_PROVIDER_PASSPHRASE"
        os.environ[env_name] = FORBIDDEN_VALUE
        try:
            result = resolve_passphrase(env_name=env_name, label="vault")
            assert_true(result.source == f"env:{env_name}", "env_source_failed=true")
            assert_true(result.value == FORBIDDEN_VALUE, "env_value_failed=true")
            assert_true(result.value_printed is False, "env_value_printed_flag_failed=true")
        finally:
            os.environ.pop(env_name, None)

        prompts = iter([FORBIDDEN_VALUE, FORBIDDEN_VALUE])
        prompt_result = resolve_passphrase(
            env_name="PNH_SYNTHETIC_MISSING_PROVIDER_PASSPHRASE",
            label="backup",
            prompt=True,
            confirm=True,
            prompt_func=lambda _message: next(prompts),
        )
        assert_true(prompt_result.source == "prompt", "prompt_source_failed=true")
        assert_true(prompt_result.value == FORBIDDEN_VALUE, "prompt_value_failed=true")

        mismatch_prompts = iter([FORBIDDEN_VALUE, FORBIDDEN_VALUE + "-different"])
        try:
            resolve_passphrase(
                env_name="PNH_SYNTHETIC_MISSING_PROVIDER_PASSPHRASE",
                label="backup",
                prompt=True,
                confirm=True,
                prompt_func=lambda _message: next(mismatch_prompts),
            )
        except PassphraseProviderError:
            pass
        else:
            raise SystemExit("prompt_confirmation_mismatch_accepted=true")

        try:
            resolve_passphrase(
                env_name="PNH_SYNTHETIC_MISSING_PROVIDER_PASSPHRASE",
                label="vault",
                prompt=False,
            )
        except PassphraseProviderError:
            pass
        else:
            raise SystemExit("missing_passphrase_accepted=true")

        try:
            resolve_passphrase(
                env_name="PNH_SYNTHETIC_MISSING_PROVIDER_PASSPHRASE",
                label="vault",
                prompt=True,
                prompt_func=lambda _message: "too-short",
            )
        except PassphraseProviderError:
            pass
        else:
            raise SystemExit("short_passphrase_accepted=true")

        readiness = keychain_readiness()
        assert_true(readiness["secretValuePrinted"] is False, "keychain_status_secret_printed=true")
        if readiness["powershellExeAvailable"]:
            assert_true(
                readiness["recommendedMode"] == "windows-dpapi-file",
                "keychain_recommended_mode_failed=true",
            )
            assert_true("windows-dpapi-file" in readiness["implementedBackends"], "keychain_backend_missing=true")
            assert_true(readiness["keychainStorageImplemented"] is True, "keychain_storage_flag_failed=true")
        else:
            assert_true(readiness["recommendedMode"] == "prompt", "keychain_recommended_mode_failed=true")

    assert_no_secret_output(captured.getvalue())
    print("passphrase_provider_smoke_check_pass=true")
    print("passphrase_value_printed=false")
    print(f"recommended_mode={keychain_readiness()['recommendedMode']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
