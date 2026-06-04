# Implementation Plan: Local Encrypted Vault MVP

## Design Decision

Use an explicit encrypted mode instead of silently changing the existing plaintext private inbox.

Modes:

- `fixture-only-preview`: no writes.
- `private-inbox`: current transitional plaintext SQLite inbox.
- `encrypted-vault`: explicit encrypted SQLite vault using `cryptography` AES-GCM.

The encrypted vault stores private `title`, `body`, and `payload_json` inside one authenticated encrypted JSON blob. Operational metadata needed for counts and routing remains plaintext:

- `id`
- `source`
- `kind`
- `sensitivity`
- `status`
- `created_at`
- `stored_at`
- `storage_mode`
- `key_id`
- `algorithm`

## Passphrase Strategy

MVP uses environment variable passphrase loading:

- default env name: `PNH_VAULT_PASSPHRASE`
- scripts may accept `--vault-passphrase-env NAME`
- no CLI passphrase argument
- no tracked passphrase file
- no printed passphrase, derived key, salt, nonce, ciphertext, title, body, or payload

If passphrase is missing, vault startup fails.

## Crypto Strategy

- AES-GCM for authenticated encryption.
- PBKDF2-HMAC-SHA256 for key derivation.
- Per-vault random salt stored in SQLite `meta`.
- Random nonce per encrypted record.
- Associated data binds ciphertext to record metadata.

## Schema Strategy

Do not mutate existing `mobile_captures` plaintext rows.

Add a separate table:

```sql
encrypted_mobile_captures (
  id TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  kind TEXT NOT NULL,
  sensitivity TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  stored_at TEXT NOT NULL,
  key_id TEXT NOT NULL,
  algorithm TEXT NOT NULL,
  nonce TEXT NOT NULL,
  ciphertext TEXT NOT NULL
)
```

Summary and list paths must include encrypted rows without decrypting private values.

## Integration Steps

1. Add `companion/encrypted_vault.py`.
2. Add encrypted table initialization and encrypted insert/list/summary adapters in `private_store.py`.
3. Add `--enable-encrypted-vault` and `--vault-passphrase-env` to companion startup.
4. Make encrypted vault imply private inbox mode and fail closed when dependencies/passphrase are unavailable.
5. Add encrypted vault init option to `private_inbox_init.py`.
6. Add encrypted vault status fields to `private_inbox_status.py`.
7. Add `scripts/encrypted_vault_smoke_check.py`.
8. Update static smoke, docs, release notes, and run evidence.

## Compatibility Requirements

- Existing `private_inbox_smoke_check.py` must continue to pass.
- Existing `browser_bridge_smoke_check.py` must continue to pass.
- Browser bridge can write to encrypted vault when the server is started in encrypted mode, but API responses remain metadata-only.
- `companion/private/` remains ignored.

## Release Blockers After MVP

- backup/delete/restore workflow
- passphrase recovery guidance and loss warning
- encrypted export/import
- migration plan for existing plaintext rows
- real mobile/contact/calendar/call/recording adapters
- automated screenshot-safe browser QA
