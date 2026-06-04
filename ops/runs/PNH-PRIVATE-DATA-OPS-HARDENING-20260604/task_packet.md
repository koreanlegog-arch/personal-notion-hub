# PNH-PRIVATE-DATA-OPS-HARDENING-20260604 Task Packet

## Objective

Raise the Personal Notion Hub local private data path closer to real sensitive
data readiness by implementing the next local-first security controls.

## Scope

- Implement approved Windows + WSL `windows-dpapi-file` passphrase backend.
- Add CLI wrappers for local vault secret store/status/delete.
- Integrate passphrase provider flags into vault lifecycle scripts and companion startup.
- Document passphrase recovery policy.
- Add plaintext-to-encrypted migration apply gate.
- Add redacted browser QA automation for screenshot/token-handling contracts.
- Document real-data adapter privacy gate.
- Update smoke checks, docs, and release notes.

## Out Of Scope

- Real passphrase storage during automated tests.
- Real private contacts, calls, recordings, transcripts, schedules, or client data.
- External API adapters.
- Cloud sync or remote vault access.
- Package installation.
- Cryptographic recovery mechanism.
- Forensic secure erase.
- Packaged distribution UX.

## Acceptance Criteria

- DPAPI backend stores, retrieves, reports status, and deletes a synthetic secret without printing it.
- Keychain readiness reports `windows-dpapi-file` as implemented when PowerShell is available.
- Vault lifecycle scripts can resolve passphrases from the provider without accepting CLI secret values.
- Plaintext migration apply requires both an existing encrypted backup path and `MIGRATE_PLAINTEXT_TO_ENCRYPTED`.
- Migration apply encrypts synthetic plaintext rows and removes plaintext rows after successful write.
- Migration apply inserts encrypted rows, deletes plaintext rows, and writes audit event in one SQLite transaction.
- Redacted browser QA validates sensitive-field masking and no persistent browser token storage.
- Real-data adapters remain blocked by default behind an explicit privacy gate.
- Smoke checks and regression checks pass with synthetic data only.

## Risk

High for real data because this work touches passphrase storage and plaintext migration. Automated validation uses synthetic data and does not store or print real secrets.
