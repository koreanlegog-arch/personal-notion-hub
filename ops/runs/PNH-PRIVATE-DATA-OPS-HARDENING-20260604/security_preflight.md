# Security Preflight

## Data Classes

- Vault passphrase: secret, never printed, never accepted as a CLI value.
- Plaintext inbox rows: sensitive when real; synthetic only during validation.
- Encrypted vault rows: sensitive metadata plus encrypted private payload.
- Browser pairing/session tokens: secret, browser memory only.
- Adapter inputs: blocked for real data until adapter-specific gates are approved.

## Controls

- `windows-dpapi-file` uses PowerShell DPAPI protected strings and stdin secret input.
- CLI wrappers report only provider/name/set/path labels.
- Plaintext migration apply requires `--preflight-backup`.
- Plaintext migration apply requires `--confirm MIGRATE_PLAINTEXT_TO_ENCRYPTED`.
- Vault secret delete requires `--confirm DELETE_VAULT_SECRET`.
- Redacted browser QA checks CSS masking and no persistent token storage.
- Real-data adapter privacy gate keeps real adapters blocked by default.

## Approval Gates

- Storing a real passphrase through `windows-dpapi-file` remains an operator action.
- Running migration apply on real rows requires a current encrypted backup and explicit supervisor intent.
- Connecting contacts, calendar, calls, recordings, transcripts, Notion, or external accounts requires a separate adapter packet.
- Distribution to other users requires recovery, backup, delete, and packaging UX review.

## Residual Risks

- DPAPI file is tied to the current Windows user/machine and is not recovery.
- Losing the passphrase and all backups can make vault data unrecoverable.
- Plaintext row deletion is logical deletion, not forensic secure erase.
- Static redaction checks do not replace live browser screenshot QA.
