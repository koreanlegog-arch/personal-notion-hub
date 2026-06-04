# Passphrase Keychain Backend Design

## Status

Design packet. No OS keychain storage or retrieval is implemented in this step.

## Objective

Define the safest next backend for storing or retrieving the Personal Notion Hub encrypted vault passphrase in the current Windows + WSL operating environment.

## Current State

Implemented:

- `env` passphrase source for non-interactive local runs.
- no-echo prompt source for manual local sessions.
- confirmation prompts for new passphrases.
- keychain readiness reporting without secret storage.
- encrypted vault backup, restore, delete, and backup-gated passphrase rotation.

Not implemented:

- OS keychain storage/retrieval.
- passphrase recovery.
- real private-data adapter ingestion.

## Requirements

- Do not pass passphrases as command-line arguments.
- Do not print passphrase values in stdout, stderr, logs, screenshots, or evidence.
- Do not create a new package dependency without approval.
- Prefer local-only and least-privilege behavior.
- Support WSL operator workflows.
- Preserve prompt mode as a fallback.
- Fail closed when the backend is unavailable.

## Backend Options

| Option | Fit | Pros | Risks | Current Recommendation |
| --- | --- | --- | --- | --- |
| Prompt-only | High | Already implemented, no persistence, no extra dependency | Manual input required each run | Keep as default manual mode |
| Environment variable | Medium | Works for services and scripts | Shell/session exposure, stale values, operator mistakes | Keep only for controlled non-interactive runs |
| Windows DPAPI-protected file via PowerShell | High for current WSL | Built into Windows, no new package, can bind decryptability to current Windows user/machine | Not a true keychain UI, Windows-account portability limits, PowerShell bridge must be carefully implemented | Preferred next implementation candidate |
| Windows Credential Manager via Win32 API | Medium | True Windows credential store | WSL cannot directly call Win32 APIs from Linux Python, helper complexity, `cmdkey` is unsafe for secret input | Defer unless a Windows-side helper is approved |
| Linux Secret Service via D-Bus | Low in current WSL | Standard Linux desktop secret API | Current environment lacks `secret-tool` and keyring daemon; WSL session D-Bus reliability risk | Defer until native Linux desktop/keyring exists |
| Third-party keyring package | Medium | Cross-platform abstraction | New dependency and supply-chain review required | Defer until package approval |

## Recommended Architecture

### Phase 1: Keep Prompt As Default

Continue using:

```bash
python3 companion/server.py \
  --enable-private-inbox \
  --enable-encrypted-vault \
  --prompt-vault-passphrase
```

This remains the safest mode for manual local sessions.

### Phase 2: Add Windows DPAPI Protected File Backend

Proposed provider name:

```text
windows-dpapi-file
```

Proposed local secret reference:

```text
service=personal-notion-hub
name=vault-passphrase
scope=current-windows-user
```

Proposed storage path:

```text
%LOCALAPPDATA%\PersonalNotionHub\secrets\vault-passphrase.dpapi
```

WSL-facing behavior:

```bash
python3 scripts/vault_secret_store.py --provider windows-dpapi-file --name vault-passphrase --prompt
python3 scripts/vault_secret_status.py --provider windows-dpapi-file
python3 companion/server.py --enable-private-inbox --enable-encrypted-vault --vault-passphrase-provider windows-dpapi-file
```

Implementation constraints:

- PowerShell script must be passed through stdin or a checked-in helper file, not constructed with secret command-line arguments.
- Secret value must be passed through stdin, not CLI args.
- Output must report only `set=true`, `provider=windows-dpapi-file`, and non-sensitive metadata.
- Decryption must fail closed when the Windows user or machine cannot decrypt the blob.
- The DPAPI blob file must be ignored by Git.

### Phase 3: Optional Native Backend

When the project runs outside WSL or in a packaged app, revisit:

- Windows Credential Manager through a native Windows helper.
- Secret Service through `secret-tool` or D-Bus.
- A reviewed third-party keyring package.

## Threat Model

| Threat | Control |
| --- | --- |
| Passphrase appears in shell history | No CLI passphrase value flags |
| Passphrase appears in process list | Do not use `cmdkey /pass:` or any command-line secret argument |
| Passphrase appears in logs/evidence | Provider outputs status flags only |
| Wrong backend silently falls back | Fail closed unless fallback is explicitly requested |
| DPAPI blob committed | Ignore path and smoke-check sample secret paths |
| User loses Windows account access | Document that DPAPI-protected blob is not recovery |
| WSL service cannot access Windows user context | Keep prompt/env fallback and require startup validation |

## Approval Packet For Implementation

Approval phrase:

```text
APPROVE_PNH_WINDOWS_DPAPI_FILE_BACKEND
```

If approved, implementation should add:

- `companion/secret_backends.py`
- `scripts/vault_secret_store.py`
- `scripts/vault_secret_status.py`
- `scripts/vault_secret_delete.py`
- smoke check with synthetic passphrase only
- `.gitignore` entry for local DPAPI blob paths
- docs update for operator use

Implementation must not:

- store a real passphrase during tests
- print the passphrase
- use `cmdkey /pass:...`
- install packages
- mutate real vault data
- remove prompt/env fallback

## Validation Plan

- `python3 scripts/keychain_readiness.py`
- synthetic store/retrieve/delete smoke using a fake passphrase
- assert secret value absent from stdout/stderr
- assert generated secret blob paths are ignored
- assert companion can read synthetic passphrase through the provider in a temp DB only
- regression smoke suite for encrypted vault backup/restore/delete/rotation

## Decision

Proceed only after supervisor approval with `APPROVE_PNH_WINDOWS_DPAPI_FILE_BACKEND`.

Until then, use prompt mode for manual sessions and environment variable mode only for controlled non-interactive local runs.

## References

- Microsoft `CredWriteW`: https://learn.microsoft.com/en-us/windows/win32/api/wincred/nf-wincred-credwritew
- Microsoft `CryptProtectData`: https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata
- Microsoft PowerShell `ConvertFrom-SecureString`: https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.security/convertfrom-securestring
- freedesktop Secret Service API: https://specifications.freedesktop.org/secret-service/latest-single/
- Python `getpass`: https://docs.python.org/3/library/getpass.html
