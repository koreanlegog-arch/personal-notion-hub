# Task Packet: Local Encrypted Vault MVP

## Metadata

- run_id: `PNH-LOCAL-ENCRYPTED-VAULT-MVP-20260604`
- project: `Personal_Notion_Hub`
- date: `2026-06-04`
- command_intents: `security-preflight`, `database-delivery`, `stage-gated-delivery`, `implement`, `qa`, `evidence`, `score`
- ledger: local `ops/runs`

## Objective

Upgrade the current local private inbox so approved sensitive captures can be stored in an encrypted local SQLite vault instead of plaintext SQLite columns.

## Success Criteria

1. Encrypted vault mode is explicit and disabled by default.
2. No new package is installed; `cryptography` is used only if already available, and the vault fails closed if it is missing.
3. Passphrase is read from an environment variable or secure prompt path; it is never passed as a CLI value, printed, logged, stored, or committed.
4. AES-GCM encrypts private title/body/payload values before SQLite persistence.
5. PBKDF2-HMAC-SHA256 derives the vault key from passphrase and per-vault salt.
6. Plaintext private values do not appear in the encrypted SQLite file, API responses, status output, evidence, or Git-tracked files.
7. Existing plaintext private inbox mode and browser bridge smoke checks remain compatible.
8. Status/summary can report counts and redacted metadata without decrypting private values.
9. A smoke test proves encrypted write, redacted response, decrypt-with-passphrase, wrong-passphrase rejection, and plaintext absence in DB bytes.
10. Documentation distinguishes transitional plaintext inbox, encrypted vault MVP, and remaining blockers.

## Scope

- `companion/encrypted_vault.py`
- `companion/private_store.py`
- `companion/server.py`
- `scripts/private_inbox_init.py`
- `scripts/private_inbox_status.py`
- `scripts/encrypted_vault_smoke_check.py`
- `scripts/smoke_check.py`
- relevant docs and run evidence

## Out Of Scope

- Installing packages or changing package versions.
- SQLCipher, OS keychain, cloud sync, OAuth, external APIs, phone/calendar/contact adapters.
- Raw audio storage or transcription.
- Automated backup/delete/restore implementation beyond documented blockers.
- Migrating old plaintext private inbox rows into encrypted rows.
- Public GitHub Pages private data sync.

## Risk Classification

- risk: `High`
- reason: storage design now becomes suitable for real sensitive input only within explicit local encrypted mode.

## Routing Decision

Use stage-gated harness because the work crosses crypto boundary, local DB schema, companion server auth, docs, smoke tests, and future measurement infrastructure.

| Lane | Agent/Skill | Model/Effort | Write Scope | Purpose |
| --- | --- | --- | --- | --- |
| architecture | architect sidecar | high | read-only | confirm minimum architecture and stop conditions |
| security | security sidecar | high | read-only | security preflight and release blockers |
| vault implementer | implementer | medium | `companion/encrypted_vault.py`, `companion/private_store.py`, `scripts/encrypted_vault_smoke_check.py` | encrypted data plane |
| server/scripts implementer | implementer | medium | `companion/server.py`, `scripts/private_inbox_init.py`, `scripts/private_inbox_status.py`, `scripts/smoke_check.py` | runtime integration |
| docs/evidence integrator | supervisor | medium | docs, run evidence, harness score | integration and verification |

## Approval Gates

This packet treats the supervisor request as approval to implement a local encrypted vault MVP under these limits:

- no dependency installation
- no external service
- no real private data in tests/evidence
- no passphrase values in chat/logs/docs
- no migration of existing plaintext data

Stop and ask again before:

- installing `cryptography` or any package
- changing dependency manifests
- adding OS keychain integration
- enabling non-loopback/LAN access
- accepting plaintext storage for high-sensitivity routine use
- adding real phone/contact/calendar/recording adapters

## Stop Conditions

- `cryptography` is unavailable and no approved dependency install exists.
- The implementation requires homegrown encryption primitives.
- Passphrase must be stored in tracked config or CLI history to operate.
- Smoke test cannot prove plaintext absence in DB bytes.
- Existing private inbox or browser bridge checks regress.

## Validation Plan

- `python3 -m py_compile companion/*.py scripts/*.py`
- `python3 scripts/encrypted_vault_smoke_check.py`
- `python3 scripts/private_inbox_smoke_check.py`
- `python3 scripts/browser_bridge_smoke_check.py`
- `python3 scripts/companion_smoke_check.py`
- `python3 scripts/smoke_check.py`
- `git ls-files companion/private`
- `git check-ignore -v companion/private/auth_token companion/private/pnh_private_inbox.sqlite companion/private/*vault*`
- `rg` redaction scan for forbidden synthetic private values
- `git diff --check`

## Evidence Policy

- Synthetic values only.
- No passphrase, token, session, or pairing values in output.
- No DB dumps.
- Report only pass/fail, metadata, paths, and redacted counts.
