# Acceptance Matrix

| Requirement | Evidence |
| --- | --- |
| DPAPI backend implemented without CLI secret values | `companion/secret_backends.py`, `scripts/vault_secret_store.py`, `scripts/vault_secret_smoke_check.py` |
| Secret output is redacted | `vault_secret_smoke_check_pass=true`, `secret_value_printed=false` |
| Provider integrated into lifecycle scripts | `--vault-passphrase-provider`, `--backup-passphrase-provider`, and provider name flags in companion/scripts |
| Migration apply is gated | `scripts/plaintext_migration_apply.py` requires backup path and `MIGRATE_PLAINTEXT_TO_ENCRYPTED` |
| Migration preserves encrypted readability | `plaintext_migration_apply_smoke_check_pass=true` |
| Browser QA redaction contract exists | `scripts/redacted_browser_qa_check.py` |
| Real adapters remain blocked | `docs/REAL_DATA_ADAPTER_PRIVACY_GATE.md` |
| Recovery limitations documented | `docs/PASSPHRASE_RECOVERY_POLICY.md` |
