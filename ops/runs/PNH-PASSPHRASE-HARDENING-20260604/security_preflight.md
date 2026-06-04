# Security Preflight

## Sensitive Surfaces

- Vault passphrase.
- Backup passphrase.
- Encrypted SQLite vault.
- Encrypted backup files.
- Decrypted status inspection path.

## Controls

- No passphrase CLI value flags are introduced.
- Prompt input uses no-echo `getpass`.
- Env mode remains only by env var name.
- Prompt mode wins over env mode when explicitly requested, preventing stale env reuse.
- Readiness audit reports only capability flags.
- OS keychain storage/retrieval remains a separate approval gate.

## Rejected Approach

Windows `cmdkey.exe` was not used as a storage backend because command-line password arguments can be visible to process inspection and shell history patterns.

## Required Evidence

- Provider smoke check.
- Existing encrypted vault backup/restore/delete smoke checks.
- Static smoke contract.
- Git ignore/private artifact checks.
