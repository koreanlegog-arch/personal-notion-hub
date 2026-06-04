# Evidence Log

## Commands Run

| Command | Result |
| --- | --- |
| `python3 -m py_compile companion/secret_backends.py companion/passphrase_provider.py companion/server.py scripts/vault_secret_store.py scripts/vault_secret_status.py scripts/vault_secret_delete.py scripts/vault_secret_smoke_check.py scripts/plaintext_migration_apply.py scripts/plaintext_migration_apply_smoke_check.py scripts/redacted_browser_qa_check.py scripts/smoke_check.py` | pass |
| `python3 scripts/vault_secret_smoke_check.py` | pass: `vault_secret_smoke_check_pass=true`, `secret_value_printed=false` |
| `python3 scripts/plaintext_migration_apply_smoke_check.py` | pass: `plaintext_migration_apply_smoke_check_pass=true`, `private_values_printed=false`, `plaintext_found_after_apply=false` |
| `python3 scripts/redacted_browser_qa_check.py` | pass: `redacted_browser_qa_check_pass=true`, `real_private_values_used=false` |
| `python3 scripts/keychain_readiness.py` | pass: `implementedBackends=["windows-dpapi-file"]`, `keychainStorageImplemented=true`, `secretValuePrinted=false` |
| `python3 scripts/smoke_check.py` | pass |
| `python3 scripts/encrypted_vault_backup_restore_smoke_check.py` | pass: `secret_value_printed=false`, `plaintext_found_in_backup=false` |
| `python3 scripts/encrypted_vault_smoke_check.py` | pass: `secret_value_printed=false`, `plaintext_found_in_db=false` |
| `python3 scripts/encrypted_vault_delete_smoke_check.py` | pass: `secret_value_printed=false`, `private_response_values_printed=false` |
| `python3 scripts/encrypted_vault_rotation_smoke_check.py` | pass: `secret_value_printed=false`, `plaintext_found_after_rotation=false` |
| `python3 scripts/passphrase_provider_smoke_check.py` | pass: `recommended_mode=windows-dpapi-file`, `passphrase_value_printed=false` |
| `python3 scripts/private_inbox_smoke_check.py` | pass: `token_value_printed=false`, `private_response_values_printed=false` |
| `python3 scripts/browser_bridge_smoke_check.py` | pass: `token_value_printed=false`, `session_value_printed=false`, `private_response_values_printed=false` |
| `python3 scripts/encrypted_vault_metadata_audit_smoke_check.py` | pass: `private_values_printed=false`, `db_mutated=false` |
| `python3 scripts/encrypted_backup_envelope_audit_smoke_check.py` | pass: `secret_value_printed=false`, `plaintext_found_in_backup=false` |
| `python3 scripts/plaintext_migration_audit_smoke_check.py` | pass: `private_values_printed=false`, `db_mutated=false` |
| `python3 scripts/companion_smoke_check.py` | pass |
| `git ls-files companion/private encrypted_exports exports` | pass: no tracked private/generated artifacts listed |
| `git check-ignore -v companion/private/backups/test.pnhbackup encrypted_exports/test.pnhbackup exports/test.local.json companion/private/pnh_private_inbox.sqlite` | pass: all sample private/generated artifacts ignored |
| `git diff --check` | pass |
| `python3 /home/koreanlego/projects/scripts/harness_score_run.py ... --write` | pass: score `66.9`, band `partial`, classification `SUPERVISOR_IMPLEMENTED_EXCEPTION` |

## Evidence Notes

- Only synthetic secret and private data values were used.
- No real passphrase was stored by automated tests.
- DPAPI smoke uses a synthetic secret name and deletes it after validation.
- Migration smoke uses a temporary database and backup path.
- Plaintext migration apply performs encrypted insert, plaintext delete, and audit write in one SQLite transaction.

## Residual Risk

- Live browser screenshot QA is still separate from static redaction contract validation.
- `windows-dpapi-file` is local to the current Windows user/machine and is not a recovery mechanism.
- Applying migration on real data still requires a current encrypted backup and explicit operator intent.
