# Acceptance Matrix: Local Encrypted Vault MVP

| ID | Criterion | Evidence |
| --- | --- | --- |
| AC1 | Existing plaintext private inbox still works. | `python3 scripts/private_inbox_smoke_check.py` |
| AC2 | Encrypted vault mode is explicit and disabled by default. | server CLI and smoke startup checks |
| AC3 | Missing `cryptography` or missing passphrase fails closed. | `scripts/encrypted_vault_smoke_check.py` |
| AC4 | Private title/body/payload are encrypted before SQLite persistence. | DB byte scan in encrypted vault smoke |
| AC5 | Wrong passphrase cannot decrypt. | encrypted vault smoke |
| AC6 | API responses and status output remain metadata-only. | encrypted vault, private inbox, browser bridge smoke |
| AC7 | Browser bridge remains exact-origin, one-time pairing, memory-only token. | `python3 scripts/browser_bridge_smoke_check.py` |
| AC8 | No private files are tracked. | `git ls-files companion/private`; `git check-ignore` |
| AC9 | Docs distinguish plaintext inbox, encrypted vault MVP, and remaining blockers. | README/security/private data docs diff |
| AC10 | No real private data or secret values are printed. | evidence log plus redaction scans |
