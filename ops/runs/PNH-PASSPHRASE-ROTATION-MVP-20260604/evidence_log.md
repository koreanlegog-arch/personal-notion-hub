# Evidence Log

## Commands Run

| Command | Result |
| --- | --- |
| `python3 -m py_compile companion/encrypted_vault.py companion/passphrase_provider.py scripts/encrypted_vault_rotate_passphrase.py scripts/encrypted_vault_rotation_smoke_check.py scripts/smoke_check.py` | pass |
| `python3 scripts/encrypted_vault_rotation_smoke_check.py` | pass: `secret_value_printed=false`, `plaintext_found_after_rotation=false` |
| `python3 scripts/encrypted_vault_backup_restore_smoke_check.py` | pass: `secret_value_printed=false`, `plaintext_found_in_backup=false` |
| `python3 scripts/encrypted_vault_smoke_check.py` | pass: `secret_value_printed=false`, `plaintext_found_in_db=false` |
| `python3 scripts/encrypted_vault_delete_smoke_check.py` | pass: `private_response_values_printed=false` |
| `python3 scripts/smoke_check.py` | pass |
| `python3 scripts/passphrase_provider_smoke_check.py` | pass |
| `python3 scripts/private_inbox_smoke_check.py` | pass |
| `python3 scripts/browser_bridge_smoke_check.py` | pass |
| `python3 scripts/companion_smoke_check.py` | pass |
| `python3 scripts/encrypted_vault_metadata_audit_smoke_check.py` | pass |
| `python3 scripts/encrypted_backup_envelope_audit_smoke_check.py` | pass |
| `python3 scripts/plaintext_migration_audit_smoke_check.py` | pass |
| `git ls-files companion/private encrypted_exports exports` | pass: no tracked private/generated artifacts listed |
| `git check-ignore -v companion/private/backups/test.pnhbackup encrypted_exports/test.pnhbackup exports/test.local.json companion/private/pnh_private_inbox.sqlite` | pass: all sample private/generated artifacts ignored |
| `git diff --check` | pass |
| `python3 /home/koreanlego/projects/scripts/harness_score_run.py ... --write` | pass: score `75.45`, band `useful`, classification `SUPERVISOR_IMPLEMENTED_EXCEPTION` |

## Rotation Evidence

- Rotation without `--preflight-backup` is rejected.
- Dry-run leaves row key IDs unchanged.
- Same current/new passphrase is rejected.
- Successful rotation changes key ID and re-encrypts rows.
- Old passphrase fails to decrypt after rotation.
- New passphrase decrypts after rotation.
- Rotation audit event is present.

## Residual Risk

- Running rotation on real data still requires operator discipline: fresh backup, known new passphrase, and recovery plan.
- No OS keychain storage/retrieval.
- No passphrase recovery mechanism.
