# Architecture Review

## Current Architecture

`companion/passphrase_provider.py` supports environment variables and no-echo prompt input. It reports keychain readiness but has no persistent backend.

## Proposed Architecture

Add a provider layer in a future implementation:

```text
CLI/server
-> passphrase_provider
-> optional secret_backends
   -> prompt
   -> env
   -> windows-dpapi-file
```

## Recommended Provider

`windows-dpapi-file` for the current Windows + WSL environment.

## Alternatives

- Windows Credential Manager: more native but helper complexity is higher from WSL.
- Linux Secret Service: not available in this session.
- Third-party keyring package: dependency/supply-chain gate.

## Rollback

Keep prompt/env providers. If `windows-dpapi-file` fails, remove provider config and return to prompt mode. Encrypted vault data format is unaffected.

## Approval Gates

- Backend implementation approval.
- Real secret storage approval.
- Any dependency approval.
