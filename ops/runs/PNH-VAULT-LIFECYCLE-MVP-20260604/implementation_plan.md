# Implementation Plan: Encrypted Vault Lifecycle MVP

## Scope

Implement lifecycle workflows for encrypted capture rows only:

- encrypted backup envelope
- encrypted restore
- single encrypted capture delete
- plaintext migration audit
- smoke checks and documentation

## Design Decisions

- Backup files are encrypted JSON envelopes with ciphertext only.
- Backup payload is decrypted in memory and immediately encrypted under the backup passphrase.
- Restore decrypts the backup envelope and re-encrypts captures into the target vault.
- Duplicate restore skips existing IDs unless `--replace` is explicitly provided.
- Delete operates by encrypted capture ID and does not decrypt private values.
- Plaintext migration is audit-only; apply/conversion remains a future approval gate.
- Smoke tests use temp DBs and synthetic values only.

## Write Set

- `companion/encrypted_vault.py`
- `.gitignore`
- `scripts/encrypted_vault_backup.py`
- `scripts/encrypted_vault_restore.py`
- `scripts/encrypted_vault_delete.py`
- `scripts/plaintext_migration_audit.py`
- `scripts/encrypted_vault_backup_restore_smoke_check.py`
- `scripts/encrypted_vault_delete_smoke_check.py`
- `scripts/plaintext_migration_audit_smoke_check.py`
- `scripts/smoke_check.py`
- docs and run evidence

## Validation

Use the validation bundle in `evidence_log.md`.

## Rollback

Revert the final Git commit. No real private data or default local DB was modified during automated validation.
