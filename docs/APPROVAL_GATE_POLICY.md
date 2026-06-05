# PNH Approval Gate Policy

Date: 2026-06-05

## Purpose

This document separates closed approval gates from active material gates for `Personal_Notion_Hub`.

Historical `ops/runs/*` packets record the state at the time of each run. They should not be treated as the current approval policy when newer evidence shows the gate was approved, implemented, and verified.

## Current Principle

Use phase-level approval, not repeated micro-approval.

Inside an approved phase, proceed autonomously on reversible implementation details, helper scripts, docs, validation commands, small UI changes, and cleanup that does not materially change risk.

Escalate only when the work changes scope, external exposure, security posture, storage model, dependency surface, legal risk, or delivery direction.

## Closed Gates

These gates were previously approval-required, but are now approved, implemented, and verified for owner-only MVP use:

| Gate | Current status | Evidence |
| --- | --- | --- |
| Local companion private inbox | closed | `ops/runs/PNH-PRIVATE-INBOX-MVP-20260604/` |
| Browser-to-companion bridge with exact origin and pairing | closed | `ops/runs/PNH-BROWSER-COMPANION-BRIDGE-20260604/` |
| Encrypted vault for capture rows | closed | `ops/runs/PNH-LOCAL-ENCRYPTED-VAULT-MVP-20260604/` |
| Backup/delete/restore for encrypted captures | closed | `ops/runs/PNH-VAULT-LIFECYCLE-MVP-20260604/` |
| Plaintext-to-encrypted migration apply gate | closed | `ops/runs/PNH-PRIVATE-DATA-OPS-HARDENING-20260604/` |
| Windows DPAPI file passphrase provider | closed | `ops/runs/PNH-SENSITIVE-LOCAL-OWNER-MVP-20260605/` |
| Redacted browser QA for current UI | closed | `ops/runs/PNH-REDACTED-BROWSER-QA-20260604/` |
| Owner-only Tailscale remote ingress rehearsal | closed | `ops/runs/PNH-REMOTE-ACCESS-TAILSCALE-20260605/` and `ops/runs/PNH-TAILNET-MANUAL-QA-20260605/` |
| Bounded PNH GitHub/Discord/OpenClaw dispatch rehearsal and implementation writes | closed | `AGENTS.md`, `ops/runs/PNH-COMMAND-PACKET-20260605T145838Z/`, `ops/runs/PNH-AUTO-DISPATCH-RETRY-20260605/` |

Closed does not mean unrestricted. It means repeat work inside the same approved boundary should not request fresh supervisor approval unless risk changes.

## Active Material Gates

These still require supervisor approval before implementation or live activation:

- GitHub Issues/Projects creation or mutation outside the bounded PNH workflow.
- Discord/OpenClaw worker dispatch outside the bounded PNH workflow, without metadata-safe prompts, beyond queue/rate-limit controls, or targeting non-PNH systems.
- Any new external API, OAuth, cloud sync, hosted backend, or public tunnel.
- Any token, credential, or secret storage workflow beyond the approved local provider.
- Phone/contact/calendar/call/recording adapter activation with real data.
- Raw audio storage or transcription, especially cloud transcription.
- Long-running always-on remote service, daemonization, or unattended startup.
- Packaging or distribution to other users.
- Changing the encryption algorithm, KDF, vault format, or backup envelope.
- Accepting plaintext sensitive-data storage risk.
- Client-facing deployment or public internet exposure.
- Screenshot, browser QA, logs, or reports containing real sensitive values.

Do not reopen a material gate only because a command internally passes an
`--approve-*` flag for an already delegated PNH workflow. Those flags are script
safety interlocks, not a fresh supervisor prompt, when the action remains inside
the closed bounded PNH scope above.

## No-Approval Fast Path

No new approval is needed for:

- Updating docs to reflect already verified status.
- Adding or fixing local helper scripts that only manage the approved Tailscale fallback path and clean up after themselves.
- Running existing smoke/readiness checks.
- Adding typed local command packet fields if they only write to the approved encrypted vault and do not dispatch externally.
- Improving UI status labels for local/tailnet/private-inbox state.
- Writing evidence logs that do not include secret or private values.

## Review Rule For Historical Packets

When an old packet says "separate approval required", check this document and newer `ops/runs/*/release_readiness.md` before escalating.

If a gate appears in both "Closed Gates" and "Active Material Gates", the active gate wins only for materially broader use. Example: owner-only Tailscale manual ingress is closed; public tunnel or always-on remote service remains active material gate.
