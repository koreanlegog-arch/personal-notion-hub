# Evidence Log: Local Encrypted Vault MVP

## Run

- run_id: `PNH-LOCAL-ENCRYPTED-VAULT-MVP-20260604`
- project: `Personal_Notion_Hub`
- date: `2026-06-04`
- evidence policy: synthetic data only; no passphrase, token, pairing code, session token, or private raw value recorded

## Commands Executed

```bash
python3 -m py_compile companion/encrypted_vault.py companion/private_store.py companion/server.py scripts/encrypted_vault_smoke_check.py scripts/private_inbox_init.py scripts/private_inbox_status.py scripts/private_inbox_smoke_check.py scripts/browser_bridge_smoke_check.py scripts/companion_smoke_check.py scripts/smoke_check.py
```

Result: pass.

```bash
python3 scripts/encrypted_vault_smoke_check.py
```

Result:

```text
encrypted_vault_smoke_check_pass=true
secret_value_printed=false
plaintext_found_in_db=false
```

```bash
python3 scripts/private_inbox_smoke_check.py
```

Result:

```text
private_inbox_smoke_check_pass=true
token_value_printed=false
private_response_values_printed=false
```

```bash
python3 scripts/browser_bridge_smoke_check.py
```

Result:

```text
browser_bridge_smoke_check_pass=true
token_value_printed=false
session_value_printed=false
private_response_values_printed=false
```

```bash
python3 scripts/companion_smoke_check.py
```

Result:

```text
companion_smoke_check_pass=true
```

```bash
python3 scripts/smoke_check.py
```

Result:

```text
smoke_check_pass=true
```

```bash
git ls-files companion/private
```

Result: no tracked private runtime files.

```bash
git check-ignore -v companion/private/auth_token companion/private/pnh_private_inbox.sqlite companion/private/pnh_private_inbox.sqlite-journal companion/private/pnh_private_inbox.sqlite-wal companion/private/pnh_private_inbox.sqlite-shm
```

Result: all checked private runtime files are ignored by `.gitignore`.

```bash
rg -n "synthetic-vault-secret|DISCORD_BOT_TOKEN|TELEGRAM_BOT_TOKEN|OPENAI_API_KEY|BEGIN (RSA|OPENSSH|EC) PRIVATE KEY" .
```

Result: synthetic vault sentinel strings exist only inside `scripts/encrypted_vault_smoke_check.py` as fixture values used to prove non-disclosure.

## Acceptance Evidence

| Criterion | Status | Evidence |
| --- | --- | --- |
| Explicit encrypted vault mode | pass | `--enable-encrypted-vault` required; startup gate covered by encrypted vault smoke |
| No dependency install | pass | no package install or manifest change performed |
| Passphrase not printed | pass | `secret_value_printed=false`; scripts use env var name only |
| AES-GCM encrypted private fields | pass | encrypted vault smoke and static smoke contract |
| PBKDF2-HMAC-SHA256 key derivation | pass | static smoke contract and `companion/encrypted_vault.py` |
| Plaintext absence in DB bytes | pass | `plaintext_found_in_db=false` |
| Wrong passphrase rejected | pass | encrypted vault smoke |
| Tampered ciphertext rejected | pass | encrypted vault smoke |
| Existing private inbox compatible | pass | `private_inbox_smoke_check_pass=true` |
| Browser bridge compatible | pass | `browser_bridge_smoke_check_pass=true` |
| Private runtime files untracked | pass | `git ls-files companion/private` returned no files |

## Remaining Risks

- Existing plaintext private inbox rows are not migrated automatically.
- Backup/delete/restore and encrypted export/import are not implemented.
- Passphrase management is manual; OS keychain or packaged prompt is not implemented.
- No phone/contact/calendar/call/recording adapters are implemented.
- Browser screenshot redaction remains best-effort UI masking.
