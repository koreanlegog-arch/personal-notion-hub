# Acceptance Matrix

| Requirement | Verification |
| --- | --- |
| Prompt support exists for encrypted vault init/server/lifecycle scripts | Static smoke check and CLI source inspection |
| Confirmation mismatch fails closed | `scripts/passphrase_provider_smoke_check.py` |
| Short/missing passphrase fails closed | `scripts/passphrase_provider_smoke_check.py` |
| Existing env mode still works | Encrypted vault lifecycle smoke checks |
| Keychain readiness prints no secret | `scripts/keychain_readiness.py` and provider smoke check |
| Docs reflect implemented vs future work | Updated README/docs/release notes |
| No generated private artifacts tracked | `git ls-files` and `git check-ignore` |
