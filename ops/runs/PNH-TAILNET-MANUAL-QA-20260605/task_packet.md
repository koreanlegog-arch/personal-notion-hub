# Task Packet: PNH Tailnet Manual Phone QA

Date: 2026-06-05

## Objective

Confirm that a real phone browser can send a PNH capture through Tailscale into the workspace encrypted vault.

## Scope

- Open temporary owner-only tailnet fallback path.
- Confirm phone capture reaches PNH private inbox.
- Confirm storage mode is encrypted vault.
- Confirm private values are not printed in evidence.
- Add repeatable start/stop helper scripts.

## Out Of Scope

- Public deployment.
- Persistent always-on gateway.
- Reading or decrypting the user's capture body.
- Storing pairing code or session token in docs.

## Acceptance Criteria

- `privateInboxTotalCaptures` increases after phone submission.
- `encryptedVaultRows` increases after phone submission.
- Recent capture shows `encrypted=true` and `storageMode=encrypted-vault`.
- Evidence records no private value.
- Temporary forwarding can be removed.
- Future sessions can be started/stopped with helper scripts.

