# PNH-PASSPHRASE-ROTATION-MVP-20260604 Task Packet

## Objective

Add a backup-gated encrypted vault passphrase rotation MVP for Personal Notion Hub.

## Scope

- Re-encrypt encrypted vault rows under a new passphrase without changing schema.
- Require explicit rotation confirmation and an existing encrypted backup path before mutation.
- Preserve prompt/env passphrase input policy.
- Add smoke verification for backup gate, dry-run, old-passphrase rejection, new-passphrase decrypt, audit event, and no secret output.
- Update docs and release notes.

## Out Of Scope

- OS keychain storage/retrieval.
- Passphrase recovery.
- Encryption scheme change.
- Real private data or production-like DB mutation.
- Plaintext-to-encrypted migration apply.

## Acceptance Criteria

- Rotation mutates only after `ROTATE_VAULT_PASSPHRASE` confirmation and `--preflight-backup`.
- Dry-run validates decryptable row count without changing row key IDs.
- Same old/new passphrase is rejected.
- Old passphrase fails after rotation.
- New passphrase decrypts rotated rows.
- Rotation event is recorded without private values.
- Synthetic private strings do not appear in DB bytes or command output.

## Risk

Medium-high for real data because passphrase rotation rewrites encrypted rows. This MVP is implemented and validated only on synthetic temp databases.
