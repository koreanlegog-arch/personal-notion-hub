"""Passphrase input helpers for Personal Notion Hub local vault scripts.

The provider supports environment variables, interactive no-echo prompts, and
approved local secret backends. Callers must never print returned passphrases.
"""

from __future__ import annotations

import getpass
import os
import shutil
import sys
from dataclasses import dataclass
from typing import Callable

try:
    from .encrypted_vault import MIN_PASSPHRASE_LENGTH
    from .secret_backends import DEFAULT_PROVIDER, DEFAULT_SECRET_NAME, retrieve_secret
except ImportError:  # pragma: no cover - supports direct companion script execution.
    from encrypted_vault import MIN_PASSPHRASE_LENGTH  # type: ignore
    from secret_backends import DEFAULT_PROVIDER, DEFAULT_SECRET_NAME, retrieve_secret  # type: ignore


PromptFunc = Callable[[str], str]


class PassphraseProviderError(ValueError):
    """Raised when a passphrase cannot be safely collected."""


@dataclass(frozen=True)
class PassphraseResult:
    value: str
    source: str
    value_printed: bool = False


def resolve_passphrase(
    *,
    env_name: str,
    label: str,
    allow_env: bool = True,
    prompt: bool = False,
    confirm: bool = False,
    provider: str = "",
    secret_name: str = DEFAULT_SECRET_NAME,
    secret_path: str = "",
    prompt_func: PromptFunc | None = None,
) -> PassphraseResult:
    """Resolve a passphrase from env or no-echo prompt.

    Env lookup remains the default for compatibility. When prompt mode is
    requested, prompt input wins over env so stale shell values are not reused
    accidentally. The returned value must never be printed by callers.
    """

    if allow_env and not prompt:
        env_value = os.environ.get(env_name)
        if env_value:
            _validate_passphrase(env_value, label)
            return PassphraseResult(env_value, source=f"env:{env_name}")

    if provider and not prompt:
        if provider != DEFAULT_PROVIDER:
            raise PassphraseProviderError("unsupported passphrase provider")
        try:
            provider_value = retrieve_secret(name=secret_name, provider=provider, path=secret_path)
        except Exception as exc:
            raise PassphraseProviderError("passphrase provider is unavailable") from exc
        _validate_passphrase(provider_value, label)
        return PassphraseResult(provider_value, source=f"provider:{provider}")

    if not prompt:
        raise PassphraseProviderError(
            f"{label} passphrase is missing; set {env_name} or use the prompt option"
        )
    if not sys.stdin.isatty() and prompt_func is None:
        raise PassphraseProviderError(f"{label} passphrase prompt requires an interactive terminal")

    active_prompt = prompt_func or getpass.getpass
    first = active_prompt(f"{label} passphrase: ")
    _validate_passphrase(first, label)
    if confirm:
        second = active_prompt(f"Confirm {label} passphrase: ")
        if first != second:
            raise PassphraseProviderError(f"{label} passphrase confirmation mismatch")
    return PassphraseResult(first, source="prompt")


def keychain_readiness() -> dict[str, object]:
    """Return non-secret keychain readiness information for the current host."""

    return {
        "secretToolAvailable": bool(shutil.which("secret-tool")),
        "gnomeKeyringDaemonAvailable": bool(shutil.which("gnome-keyring-daemon")),
        "powershellExeAvailable": bool(shutil.which("powershell.exe")),
        "cmdkeyExeAvailable": bool(shutil.which("cmdkey.exe")),
        "implementedBackends": ["windows-dpapi-file"],
        "recommendedMode": "windows-dpapi-file" if shutil.which("powershell.exe") else "prompt",
        "keychainStorageImplemented": True,
        "secretValuePrinted": False,
        "notes": [
            "env and prompt modes are implemented",
            "windows-dpapi-file storage is implemented for approved local use",
            "cmdkey.exe is not used because password arguments can be exposed through process listings",
        ],
    }


def _validate_passphrase(value: str, label: str) -> None:
    if not isinstance(value, str) or len(value) < MIN_PASSPHRASE_LENGTH:
        raise PassphraseProviderError(f"{label} passphrase is missing or too short")
