# Approval Gate Archive: PNH

Date: 2026-06-05

## Purpose

This archive records approval-gate statements that were correct at the time of older PNH packets but are now superseded by later approval, implementation, and verification.

Do not delete the original historical packet. Use this archive as the current interpretation layer.

## Superseded Or Closed Gates

| Archive ID | Source | Old gate | Current interpretation |
| --- | --- | --- | --- |
| `PNH-GATE-CLOSED-BRIDGE-20260605` | `ops/runs/PNH-MOBILE-LIKE-COMPANION-INGRESS-20260604/*` | Browser UI fetch/CORS/pairing was out of scope until separately approved. | Closed for exact-origin local/tailnet bridge. Broader origins or public backend remain gated. |
| `PNH-GATE-CLOSED-VAULT-20260605` | `ops/runs/PNH-PRIVATE-INBOX-MVP-20260604/security_preflight.md` | Encrypted vault and sensitive local use remained future gates. | Closed for encrypted capture rows with approved passphrase provider. |
| `PNH-GATE-CLOSED-KEYCHAIN-20260605` | `ops/runs/PNH-PASSPHRASE-HARDENING-20260604/security_preflight.md` | OS keychain storage/retrieval remained a separate approval gate. | Closed for `windows-dpapi-file` provider in Windows + WSL owner environment. |
| `PNH-GATE-CLOSED-REMOTE-INGRESS-20260605` | `docs/PHONE_INGRESS_SECURITY.md`, `ops/runs/PNH-PHONE-INGRESS-REACHABILITY-20260605/*` | Private tunnel strategy required separate approval. | Closed for owner-only Tailscale fallback with temporary cleanup. Public tunnels remain gated. |
| `PNH-GATE-CLOSED-REDACTED-QA-20260605` | `ops/runs/PNH-ASSISTANT-LOCAL-FIRST-20260604/browser_qa.md` | New browser tooling / screenshot QA required separate approval. | Closed for current redacted Playwright QA path. Screenshots with real sensitive values remain gated. |

## Still Active Gates

The following are not superseded:

- real phone/contact/calendar/call/recording adapters
- raw audio storage or transcription
- cloud sync, OAuth, external APIs, public tunnel, hosted backend
- automatic GitHub issue mutation
- automatic Discord/OpenClaw dispatch
- always-on daemon/service exposure
- packaging for other users
- encryption/KDF/vault format changes
- plaintext sensitive-data risk acceptance

## Link To Active Policy

Current active interpretation lives in:

- `docs/APPROVAL_GATE_POLICY.md`

