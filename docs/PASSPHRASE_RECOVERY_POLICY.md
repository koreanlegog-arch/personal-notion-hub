# Passphrase Recovery Policy

## Status

Policy gate. There is no cryptographic recovery mechanism for a lost encrypted vault passphrase.

## Rule

If the encrypted vault passphrase is lost, encrypted records and DPAPI-protected passphrase blobs may be unrecoverable.

## Current Controls

- Prompt-first passphrase entry for manual sessions.
- `windows-dpapi-file` backend for approved local persistence.
- Encrypted backup, restore, delete, and passphrase rotation.
- Plaintext-to-encrypted migration apply gate.

## Required Operator Practice

- Store recovery material outside the repository.
- Never paste recovery material into chat, logs, screenshots, GitHub issues, Discord, or evidence.
- Before passphrase rotation, create a fresh encrypted backup and confirm the backup path exists.
- After rotation, verify the new passphrase can decrypt synthetic or approved local records.
- Keep at least one offline recovery note controlled by the supervisor if routine sensitive data is stored.

## Prohibited

- Hard-coded recovery passphrases.
- Recovery hints containing private names, phone numbers, client names, or account identifiers.
- Committed backup files or DPAPI blobs.
- Cloud sync of recovery material without a separate security decision.

## Recovery Drill

For routine sensitive operation, perform a fixture-only drill:

1. Create a synthetic encrypted vault.
2. Create an encrypted backup.
3. Rotate to a new passphrase.
4. Restore from backup into a fresh synthetic vault.
5. Confirm no private values appear in logs or evidence.

## Remaining Risk

This policy reduces operator error but does not provide cryptographic recovery. A separate escrow, hardware-backed key, or managed secret design would require a new approval gate.
