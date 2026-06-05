# Task Packet: PNH Dispatch Candidate Export

Date: 2026-06-05

## Objective

Export a metadata-only dispatch candidate from the local private inbox so PNH mobile captures can feed the idempotent dispatch job without manually preparing JSON.

## Scope

- Add candidate export script.
- Use redacted metadata by default.
- Prefer encrypted-vault candidates.
- Block plaintext inbox candidates unless explicitly allowed for fixture compatibility.
- Add smoke validation.

## Out Of Scope

- Decrypting private bodies.
- Creating GitHub Issues or Discord threads.
- Mutating browser localStorage.
- Auto-dispatching every capture.

## Acceptance Criteria

- Candidate export does not print raw private title/body.
- Plaintext rows are blocked unless `--allow-plaintext` is passed.
- Output is compatible with `scripts/pnh_dispatch_job.py`.
- Validation evidence is recorded.

## Risk Level

Low-Medium.

Reason: this is local-only metadata export, but it prepares an automation path toward external dispatch.
