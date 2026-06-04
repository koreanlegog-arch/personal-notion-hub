# Security Preflight

## Constraints

- Do not accept passphrase values as CLI arguments.
- Do not print passphrase, decrypted title, body, payload, or backup passphrase values.
- Do not rotate without explicit confirmation phrase.
- Do not rotate without an existing encrypted backup path.
- Do not run rotation against real private data during automated checks.

## Data Handling

- Plaintext exists only in process memory during decrypt/re-encrypt.
- SQLite mutation is transaction-scoped.
- The vault salt, key ID, row nonce, and row ciphertext change.
- Audit event records only event type, source, and timestamp.

## Approval Gates

- Running rotation on real supervisor data requires a fresh backup and explicit operator intent.
- OS keychain storage/retrieval remains a separate design and approval gate.
- Passphrase recovery is not implemented; losing the new passphrase can make data unrecoverable.
