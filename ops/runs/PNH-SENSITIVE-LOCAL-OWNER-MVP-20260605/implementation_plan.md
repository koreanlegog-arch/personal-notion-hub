# Implementation Plan

## Stage 1: Readiness Automation

Add `scripts/sensitive_owner_readiness_check.py` to consolidate:

- keychain readiness
- vault passphrase storage status
- plaintext migration audit
- private inbox redacted status

Expected result: `not_ready` until operator stores a vault passphrase and resolves plaintext rows.

## Stage 2: Operator Passphrase Setup

Local operator command:

```bash
python3 scripts/vault_secret_store.py \
  --provider windows-dpapi-file \
  --name vault-passphrase \
  --prompt
```

Do not paste the passphrase into chat, docs, screenshots, logs, or command-line arguments.

## Stage 3: Backup-Gated Plaintext Resolution

Options:

- If rows are test/synthetic only: delete/reset the local private inbox after explicit operator confirmation.
- If rows should be retained: create encrypted backup, run plaintext migration apply with confirmation, then audit.

No automatic migration or deletion is performed in this run.

## Stage 4: Sensitive Local Owner Run

Run the companion in encrypted mode:

```bash
python3 companion/server.py \
  --host 127.0.0.1 \
  --port 8765 \
  --enable-private-inbox \
  --enable-encrypted-vault \
  --vault-passphrase-provider windows-dpapi-file
```

Then use low-risk synthetic input first and verify encrypted row count increases.

## Stop Conditions

- readiness check reports `privateOrSecretValuePrinted=true`
- plaintext rows remain when routine sensitive data entry is planned
- passphrase backend is unavailable
- encrypted backup cannot be created before migration
- redacted QA fails
