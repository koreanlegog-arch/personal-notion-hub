# Security Preflight: Local Encrypted Vault MVP

## Security Constraints

- Use a vetted library: `cryptography` AES-GCM only.
- Do not implement custom ciphers, custom MACs, or unauthenticated encryption.
- Do not install dependencies in this run.
- If `cryptography` import fails, vault mode must fail closed.
- Passphrase may come from an environment variable or secure prompt, but must not be passed as a command argument.
- Do not print passphrase, derived key, nonce, ciphertext, token, pairing code, session token, title, body, or payload values.
- Do not store passphrase or derived key in SQLite, logs, docs, browser storage, or Git-tracked files.
- Keep companion binding to `127.0.0.1`.
- Use fixture-only synthetic values in tests.

## Required Controls

- PBKDF2-HMAC-SHA256 with per-vault random salt.
- AES-GCM with unique random nonce per record.
- Store only encrypted private payload plus non-sensitive operational metadata.
- Use authenticated associated data tied to record id/source/kind/sensitivity/status timestamps.
- Wrong passphrase must fail with an authentication error, not produce corrupted plaintext.
- API responses remain metadata-only.
- Status output remains redacted.
- Existing plaintext private inbox mode remains available only as transitional mode.

## Blockers

- Routine real high-sensitivity use still requires backup/delete/restore workflow.
- Passphrase loss means data is unrecoverable; this must be documented.
- Browser screenshots with real data require redaction mode and fake-fixture QA discipline.
- Existing plaintext rows are not migrated in this MVP.

## Release Constraints

- `scripts/encrypted_vault_smoke_check.py` must pass.
- Existing private inbox and browser bridge smoke checks must pass.
- `companion/private/` must remain ignored.
- No secret/private values in evidence.
