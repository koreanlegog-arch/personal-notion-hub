# Acceptance Matrix

| Requirement | Verification |
| --- | --- |
| Rotation requires backup acknowledgement | `scripts/encrypted_vault_rotation_smoke_check.py` no-backup case |
| Dry-run does not mutate row key IDs | `scripts/encrypted_vault_rotation_smoke_check.py` dry-run case |
| Same old/new passphrase rejected | `scripts/encrypted_vault_rotation_smoke_check.py` same-passphrase case |
| Old passphrase rejected after rotation | `scripts/encrypted_vault_rotation_smoke_check.py` old-passphrase case |
| New passphrase decrypts after rotation | `scripts/encrypted_vault_rotation_smoke_check.py` new-passphrase case |
| No private values in output or DB bytes | `scripts/encrypted_vault_rotation_smoke_check.py` secret/plaintext checks |
| Static contract includes rotation files | `scripts/smoke_check.py` |
