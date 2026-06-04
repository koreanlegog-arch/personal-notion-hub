"""Local secret backend helpers for Personal Notion Hub.

Only synthetic tests should store values automatically. Real passphrases remain
operator-controlled and must never be printed by CLI wrappers.
"""

from __future__ import annotations

import base64
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


DEFAULT_PROVIDER = "windows-dpapi-file"
DEFAULT_SECRET_NAME = "vault-passphrase"
SERVICE_NAME = "personal-notion-hub"


class SecretBackendError(ValueError):
    """Raised when a local secret backend cannot safely complete an operation."""


@dataclass(frozen=True)
class SecretStatus:
    provider: str
    name: str
    available: bool
    set: bool
    path_label: str
    secret_value_printed: bool = False


def backend_available(provider: str = DEFAULT_PROVIDER) -> bool:
    if provider != DEFAULT_PROVIDER:
        return False
    return shutil.which("powershell.exe") is not None


def default_secret_path(name: str = DEFAULT_SECRET_NAME) -> str:
    _validate_name(name)
    local_app_data = _run_powershell(
        "$ErrorActionPreference = 'Stop'; [Console]::Out.Write($env:LOCALAPPDATA)",
        input_text="",
    )
    if not local_app_data:
        raise SecretBackendError("windows LOCALAPPDATA is unavailable")
    return str(Path(local_app_data) / "PersonalNotionHub" / "secrets" / f"{name}.dpapi")


def store_secret(
    value: str,
    *,
    name: str = DEFAULT_SECRET_NAME,
    provider: str = DEFAULT_PROVIDER,
    path: str = "",
) -> SecretStatus:
    _validate_provider(provider)
    _validate_name(name)
    if not value:
        raise SecretBackendError("secret value is missing")
    target = path or default_secret_path(name)
    encoded_path = _b64(target)
    script = f"""
$ErrorActionPreference = 'Stop'
$path = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{encoded_path}'))
$secret = [Console]::In.ReadToEnd()
$secret = $secret.TrimEnd("`r", "`n")
if ([string]::IsNullOrEmpty($secret)) {{ throw 'secret value is missing' }}
$secure = ConvertTo-SecureString -String $secret -AsPlainText -Force
$encrypted = ConvertFrom-SecureString -SecureString $secure
$parent = Split-Path -Parent $path
New-Item -ItemType Directory -Force -Path $parent | Out-Null
Set-Content -Path $path -Value $encrypted -NoNewline -Encoding UTF8
"""
    _run_powershell(script, input_text=value)
    return status_secret(name=name, provider=provider, path=target)


def retrieve_secret(
    *,
    name: str = DEFAULT_SECRET_NAME,
    provider: str = DEFAULT_PROVIDER,
    path: str = "",
) -> str:
    _validate_provider(provider)
    _validate_name(name)
    target = path or default_secret_path(name)
    encoded_path = _b64(target)
    script = f"""
$ErrorActionPreference = 'Stop'
$path = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{encoded_path}'))
if (-not (Test-Path -LiteralPath $path)) {{ throw 'secret file is missing' }}
$encrypted = Get-Content -LiteralPath $path -Raw
$secure = ConvertTo-SecureString -String $encrypted
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {{
  $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
  [Console]::Out.Write($plain)
}} finally {{
  if ($bstr -ne [IntPtr]::Zero) {{
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
  }}
}}
"""
    value = _run_powershell(script, input_text="")
    if not value:
        raise SecretBackendError("secret value is unavailable")
    return value


def delete_secret(
    *,
    name: str = DEFAULT_SECRET_NAME,
    provider: str = DEFAULT_PROVIDER,
    path: str = "",
) -> SecretStatus:
    _validate_provider(provider)
    _validate_name(name)
    target = path or default_secret_path(name)
    encoded_path = _b64(target)
    script = f"""
$ErrorActionPreference = 'Stop'
$path = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{encoded_path}'))
if (Test-Path -LiteralPath $path) {{
  Remove-Item -LiteralPath $path -Force
}}
"""
    _run_powershell(script, input_text="")
    return status_secret(name=name, provider=provider, path=target)


def status_secret(
    *,
    name: str = DEFAULT_SECRET_NAME,
    provider: str = DEFAULT_PROVIDER,
    path: str = "",
) -> SecretStatus:
    _validate_provider(provider)
    _validate_name(name)
    available = backend_available(provider)
    target = path
    if available and not target:
        try:
            target = default_secret_path(name)
        except SecretBackendError:
            target = ""
    exists = False
    if available and target:
        encoded_path = _b64(target)
        script = f"""
$ErrorActionPreference = 'Stop'
$path = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{encoded_path}'))
if (Test-Path -LiteralPath $path) {{ [Console]::Out.Write('true') }} else {{ [Console]::Out.Write('false') }}
"""
        exists = _run_powershell(script, input_text="") == "true"
    return SecretStatus(
        provider=provider,
        name=name,
        available=available,
        set=exists,
        path_label=_safe_path_label(target),
    )


def status_to_dict(status: SecretStatus) -> dict[str, object]:
    return {
        "provider": status.provider,
        "name": status.name,
        "available": status.available,
        "set": status.set,
        "pathLabel": status.path_label,
        "secretValuePrinted": status.secret_value_printed,
    }


def _run_powershell(script: str, *, input_text: str) -> str:
    executable = shutil.which("powershell.exe")
    if not executable:
        raise SecretBackendError("powershell.exe is unavailable")
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    try:
        result = subprocess.run(
            [executable, "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
            input=input_text.encode("utf-8"),
            capture_output=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SecretBackendError("powershell secret backend failed") from exc
    if result.returncode != 0:
        raise SecretBackendError("powershell secret backend returned an error")
    return result.stdout.decode("utf-8", errors="replace")


def _validate_provider(provider: str) -> None:
    if provider != DEFAULT_PROVIDER:
        raise SecretBackendError("unsupported secret provider")


def _validate_name(name: str) -> None:
    if not name or not all(char.isalnum() or char in {"-", "_", "."} for char in name):
        raise SecretBackendError("secret name is invalid")


def _b64(value: str) -> str:
    return base64.b64encode(value.encode("utf-8")).decode("ascii")


def _safe_path_label(path: str) -> str:
    if not path:
        return ""
    normalized = path.replace("\\", "/")
    if "/PersonalNotionHub/secrets/" in normalized:
        return "[windows-localappdata]/PersonalNotionHub/secrets/" + normalized.rsplit("/", 1)[-1]
    return "[custom-secret-path]"
