# Acceptance Matrix: Encrypted Vault Lifecycle MVP

| ID | Criterion | Evidence |
| --- | --- | --- |
| AC1 | Backup file is encrypted-only and contains no synthetic private plaintext. | `python3 scripts/encrypted_vault_backup_restore_smoke_check.py` |
| AC2 | Correct backup passphrase restores to a fresh vault. | backup/restore smoke |
| AC3 | Wrong passphrase and tampered backup fail closed. | backup/restore smoke |
| AC4 | Delete removes encrypted capture row and redacted list entry. | `python3 scripts/encrypted_vault_delete_smoke_check.py` |
| AC5 | Delete audit/output prints no private values. | delete smoke |
| AC6 | Plaintext migration audit detects plaintext rows without printing values. | `python3 scripts/plaintext_migration_audit_smoke_check.py` |
| AC7 | Migration audit does not mutate DB. | migration audit smoke |
| AC8 | Existing encrypted/private/browser/companion/static checks pass. | regression smoke bundle |
| AC9 | Generated private artifacts remain untracked. | `git ls-files companion/private`; `git status --short` |
| AC10 | No unverified success claims remain in evidence. | evidence log |
