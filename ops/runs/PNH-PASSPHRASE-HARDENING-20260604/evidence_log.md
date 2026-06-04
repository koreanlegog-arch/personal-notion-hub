# Evidence Log

## Commands Run

| Command | Result |
| --- | --- |
| `python3 -m py_compile companion/passphrase_provider.py companion/encrypted_vault.py companion/server.py scripts/private_inbox_init.py scripts/private_inbox_status.py scripts/encrypted_vault_backup.py scripts/encrypted_vault_restore.py scripts/encrypted_vault_delete.py scripts/keychain_readiness.py scripts/passphrase_provider_smoke_check.py scripts/smoke_check.py` | pass |
| `python3 scripts/passphrase_provider_smoke_check.py` | pass: `passphrase_provider_smoke_check_pass=true`, `passphrase_value_printed=false` |
| `python3 scripts/keychain_readiness.py` | pass: readiness JSON printed with `secretValuePrinted=false`, `keychainStorageImplemented=false` |
| `python3 scripts/encrypted_vault_backup_restore_smoke_check.py` | pass: `secret_value_printed=false`, `plaintext_found_in_backup=false` |
| `python3 scripts/encrypted_vault_smoke_check.py` | pass: `secret_value_printed=false`, `plaintext_found_in_db=false` |
| `python3 scripts/encrypted_vault_delete_smoke_check.py` | pass: `private_response_values_printed=false` |
| `python3 scripts/plaintext_migration_audit_smoke_check.py` | pass: `private_values_printed=false`, `db_mutated=false` |
| `python3 scripts/private_inbox_smoke_check.py` | pass |
| `python3 scripts/browser_bridge_smoke_check.py` | pass |
| `python3 scripts/companion_smoke_check.py` | pass |
| `python3 scripts/smoke_check.py` | pass |
| `python3 scripts/encrypted_vault_metadata_audit_smoke_check.py` | pass |
| `python3 scripts/encrypted_backup_envelope_audit_smoke_check.py` | pass |
| `git ls-files companion/private encrypted_exports exports` | pass: no tracked private/generated artifacts listed |
| `git check-ignore -v companion/private/backups/test.pnhbackup encrypted_exports/test.pnhbackup exports/test.local.json companion/private/pnh_private_inbox.sqlite` | pass: all sample private/generated artifacts ignored |
| `git diff --check` | pass |
| `python3 /home/koreanlego/projects/scripts/harness_score_run.py ... --write` | pass: score `74.2`, band `useful`, classification `SUPERVISOR_IMPLEMENTED_EXCEPTION` |

## Keychain Readiness Result

- `secret-tool`: unavailable.
- `gnome-keyring-daemon`: unavailable.
- Windows `powershell.exe`: available.
- Windows `cmdkey.exe`: available but intentionally unused for storage because password arguments can be exposed.
- Recommended current mode: prompt.

## Residual Risk

- Actual OS keychain storage/retrieval is not implemented.
- Passphrase recovery and rotation are not implemented.
- Prompt mode is suitable for manual local sessions; non-interactive managed services still need env or a future approved keychain backend.
