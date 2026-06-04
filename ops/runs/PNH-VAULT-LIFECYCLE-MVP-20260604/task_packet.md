# Task Packet: Encrypted Vault Lifecycle MVP

## Metadata

- run_id: `PNH-VAULT-LIFECYCLE-MVP-20260604`
- project: `Personal_Notion_Hub`
- date: `2026-06-04`
- command_intents: `security-preflight`, `database-delivery`, `stage-gated-delivery`, `backup`, `restore`, `delete`, `migration-audit`, `qa`, `evidence`, `score`
- ledger: local `ops/runs`

## Objective

Add encrypted backup, restore, delete, and plaintext migration audit workflows for the local encrypted vault so sensitive local testing can move beyond one-way storage.

## Success Criteria

1. Encrypted backup writes an encrypted-only file and never writes decrypted JSON backup artifacts.
2. Backup envelope includes schema version, kind, algorithm, KDF name, KDF iterations, salt, nonce, and ciphertext.
3. Backup and restore passphrases are read from environment variables only; passphrase values are not CLI args, logs, evidence, or committed files.
4. Correct backup passphrase can restore encrypted captures into a fresh vault.
5. Wrong backup passphrase, tampered backup ciphertext, and unsupported backup envelope values fail closed.
6. Delete can remove an encrypted capture by ID and records only non-sensitive audit metadata.
7. Delete responses/status/audit output do not print title, body, payload, passphrase, token, or private raw values.
8. Plaintext migration audit detects `mobile_captures` rows and reports only counts and safe metadata categories.
9. Migration audit does not mutate the database and does not print plaintext title/body/payload values.
10. Existing encrypted vault, private inbox, browser bridge, companion, and static smoke checks still pass.

## Scope

- `companion/encrypted_vault.py`
- `scripts/encrypted_vault_backup.py`
- `scripts/encrypted_vault_restore.py`
- `scripts/encrypted_vault_delete.py`
- `scripts/plaintext_migration_audit.py`
- `scripts/encrypted_vault_backup_restore_smoke_check.py`
- `scripts/encrypted_vault_delete_smoke_check.py`
- `scripts/plaintext_migration_audit_smoke_check.py`
- `scripts/smoke_check.py`
- relevant docs and run evidence

## Out Of Scope

- Installing packages or changing dependency manifests.
- SQLCipher, OS keychain, cloud sync, OAuth, external APIs, phone/calendar/contact adapters.
- Plaintext-to-encrypted migration apply/conversion.
- Secure deletion guarantees beyond SQLite row delete plus optional `VACUUM`.
- Raw audio storage, transcription, or attachment backup.
- Non-loopback network behavior or public deployment changes.

## Risk Classification

- risk: `High`
- reason: backup, restore, and delete define sensitive data lifecycle semantics.

## Routing Decision

Use stage-gated harness. Security and QA sidecars are read-only; supervisor implements and integrates because backup/delete/restore functions share a small tightly coupled module.

| Lane | Agent/Skill | Mode | Purpose |
| --- | --- | --- | --- |
| security | security sidecar + `security-preflight` | read-only | stop conditions and leakage risks |
| QA | QA sidecar | read-only | validation matrix and regression bundle |
| database/lifecycle | `database-delivery` | implementation | backup/restore/delete/audit data semantics |
| integration | supervisor | implementation | scripts, docs, evidence, final verification |

## Approval Gates

This packet treats the supervisor request as approval to implement local-only encrypted lifecycle scripts under these limits:

- no dependency installation
- no external service
- no real private data in tests/evidence
- no passphrase values in chat/logs/docs
- no automatic migration of existing plaintext rows
- no destructive operation against the real default DB during automated validation

Stop and ask again before:

- implementing plaintext migration apply
- deleting all records by default
- changing encryption algorithm/KDF
- adding OS keychain integration
- adding non-loopback/LAN pairing
- adding phone/contact/calendar/recording adapters

## Stop Conditions

- Encrypted backup would require plaintext JSON file output.
- Restore would overwrite or delete existing data without an explicit replace flag.
- Delete would need to expose decrypted values to identify records.
- Migration audit would need to print plaintext values.
- Existing smoke checks regress and cannot be fixed within the approved scope.

## Validation Plan

- `python3 -m py_compile companion/encrypted_vault.py scripts/*.py`
- `python3 scripts/encrypted_vault_backup_restore_smoke_check.py`
- `python3 scripts/encrypted_vault_delete_smoke_check.py`
- `python3 scripts/plaintext_migration_audit_smoke_check.py`
- `python3 scripts/encrypted_vault_smoke_check.py`
- `python3 scripts/private_inbox_smoke_check.py`
- `python3 scripts/browser_bridge_smoke_check.py`
- `python3 scripts/companion_smoke_check.py`
- `python3 scripts/smoke_check.py`
- `git ls-files companion/private`
- `git diff --check`

## Evidence Policy

- Synthetic values only.
- No passphrase, token, session, pairing code, title, body, or payload raw value in evidence.
- No DB dumps.
- Report only pass/fail, counts, file labels, and redacted metadata.
