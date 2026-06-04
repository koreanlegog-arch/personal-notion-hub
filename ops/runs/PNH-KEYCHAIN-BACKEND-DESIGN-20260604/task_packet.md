# PNH-KEYCHAIN-BACKEND-DESIGN-20260604 Task Packet

## Objective

Design the next OS-backed persistent passphrase backend for Personal Notion Hub without implementing or storing secrets.

## Scope

- Compare prompt, env, Windows DPAPI file, Windows Credential Manager, Linux Secret Service, and third-party keyring options.
- Recommend the safest next backend for the current Windows + WSL environment.
- Define approval phrase, implementation constraints, validation plan, and rollback boundary.
- Update documentation so future implementation can proceed without ambiguity.

## Out Of Scope

- Actual OS keychain storage/retrieval implementation.
- Real passphrase storage.
- Package installation.
- Windows service, daemon, or system keyring configuration changes.
- Real private-data ingestion.

## Acceptance Criteria

- A backend decision document exists.
- The recommendation is explicit and environment-specific.
- Dangerous options such as `cmdkey /pass:` are rejected.
- Approval phrase and implementation stop conditions are documented.
- Validation plan uses synthetic secrets only.

## Risk

Medium. The task is design-only, but the future implementation affects secret handling.
