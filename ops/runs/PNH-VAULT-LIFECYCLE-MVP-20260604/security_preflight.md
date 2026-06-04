# Security Preflight: Encrypted Vault Lifecycle MVP

## Security Constraints

- Backup files must be encrypted envelopes, not plaintext JSON exports.
- Passphrases must be provided by environment variable name only.
- Scripts must print `secret_value_printed=false` style evidence, never secret values.
- Delete audit may store event type, capture ID, source label, timestamp, and result only.
- Plaintext migration audit may report row counts and category counts only.
- Automated validation must use temp databases and synthetic fixtures only.
- `companion/private/` and generated backup files must remain ignored by Git.

## Blockers

- None for local-only MVP under current constraints.

## Approval Gates

- Plaintext migration apply/conversion requires separate approval.
- Changing algorithm/KDF requires separate approval.
- OS keychain, packaging, adapters, and non-loopback access require separate approval.
- Deleting real supervisor data remains a manual action and must not be triggered by smoke tests.

## Accepted Risk Candidates

- SQLite secure deletion is not guaranteed by a normal row delete. The delete script may optionally run `VACUUM`, but this is not a forensic secure erase guarantee.
- Backup path may live in a cloud-synced folder; scripts warn through docs, but local filesystem policy cannot fully prevent that.
- Manual env passphrase management remains until OS keychain/passphrase prompt hardening.

## Release Constraints

- New backup/restore/delete/audit smoke checks must pass.
- Existing encrypted vault/private inbox/browser bridge checks must pass.
- No generated backup/vault/private runtime artifacts may be tracked.
