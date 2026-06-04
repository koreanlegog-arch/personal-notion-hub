# Evidence Log

## Commands Run

| Command | Result |
| --- | --- |
| `python3 scripts/keychain_readiness.py` | pass: `windows-dpapi-file` available and recommended; no secret value printed. |
| `python3 scripts/vault_secret_status.py --provider windows-dpapi-file` | pass: provider available, `set=true`, no secret value printed. |
| `python3 scripts/plaintext_migration_audit.py` | pass: `plaintextRowCount=5`, `encryptedRowCount=0`, values not printed. |
| `python3 scripts/private_inbox_status.py` | pass: total captures `5`, all plaintext inbox, private values redacted. |
| `python3 scripts/encrypted_vault_smoke_check.py` | pass. |
| `python3 scripts/encrypted_vault_backup_restore_smoke_check.py` | pass. |
| `python3 scripts/encrypted_vault_delete_smoke_check.py` | pass. |
| `python3 scripts/encrypted_vault_rotation_smoke_check.py` | pass. |
| `python3 scripts/plaintext_migration_apply_smoke_check.py` | pass. |
| `python3 scripts/vault_secret_smoke_check.py` | pass. |
| `python3 scripts/sensitive_owner_readiness_check.py` | pass: verdict `not_ready`, blockers `vault_passphrase_not_stored`, `plaintext_inbox_rows_present`, no private/secret value printed. |
| `python3 -m py_compile scripts/sensitive_owner_readiness_check.py scripts/smoke_check.py` | pass. |
| `python3 scripts/smoke_check.py` | pass. |
| `git diff --check` | pass. |
| `python3 /home/koreanlego/projects/scripts/harness_score_run.py ... --write` | pass: score `76.5`, band `useful`, classification `SUPERVISOR_IMPLEMENTED_EXCEPTION`. |

## Current Verdict

`ready_for_sensitive_local_owner_mode`.

Reason:

- vault passphrase is stored in the approved local backend
- plaintext inbox rows were migrated to encrypted vault rows
- synthetic owner capture writes through encrypted vault mode
- private/secret values were not printed

## Harness Score

- Score: `76.5`
- Band: `useful`
- Classification: `SUPERVISOR_IMPLEMENTED_EXCEPTION`

Interpretation: useful as a gated security/readiness start. It intentionally
blocks real sensitive entry until operator passphrase setup and plaintext row
resolution are complete.

## Migration Evidence

| Command | Result |
| --- | --- |
| `python3 scripts/private_inbox_init.py --enable-encrypted-vault --vault-passphrase-provider windows-dpapi-file` | pass: encrypted vault initialized without printing passphrase or token value. |
| `python3 scripts/encrypted_vault_backup.py --out companion/private/backups/pnh-pre-migration-*.pnhbackup --vault-passphrase-provider windows-dpapi-file --backup-passphrase-provider windows-dpapi-file` | pass: encrypted preflight backup created, `captureCount=0`, no secret value printed. |
| `python3 scripts/plaintext_migration_apply.py --dry-run` | pass: `migratableRowCount=5`, no mutation. |
| `python3 scripts/plaintext_migration_apply.py --preflight-backup ... --confirm MIGRATE_PLAINTEXT_TO_ENCRYPTED --vault-passphrase-provider windows-dpapi-file` | pass: 5 plaintext rows migrated and deleted. |
| `python3 scripts/plaintext_migration_audit.py --fail-on-plaintext` | pass: `plaintextRowCount=0`, `encryptedRowCount=6` after owner smoke. |
| `python3 companion/server.py --host 127.0.0.1 --port 8765 --enable-private-inbox --enable-encrypted-vault --vault-passphrase-provider windows-dpapi-file` | pass: loopback encrypted companion started for synthetic owner smoke. |
| `python3 scripts/simulate_mobile_capture.py ...` | pass: synthetic capture returned metadata-only response with `storageMode=encrypted-vault`. |
| `python3 scripts/sensitive_owner_readiness_check.py` | pass: verdict `ready_for_sensitive_local_owner_mode`, no private/secret value printed. |
| `python3 scripts/encrypted_vault_backup.py --out companion/private/backups/pnh-post-owner-smoke-*.pnhbackup --vault-passphrase-provider windows-dpapi-file --backup-passphrase-provider windows-dpapi-file` | pass: encrypted post-smoke backup created, `captureCount=6`, no secret value printed. |

## No-Secret Evidence Rule

This run records counts, capability flags, and redacted metadata only. It does
not include passphrases, tokens, pairing codes, capture body text, or decrypted
private values.
