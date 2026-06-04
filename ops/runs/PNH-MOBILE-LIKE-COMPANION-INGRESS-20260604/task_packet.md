# Task Packet: PNH Mobile-Like Companion Ingress

## Metadata

- run_id: `PNH-MOBILE-LIKE-COMPANION-INGRESS-20260604`
- project: `Personal_Notion_Hub`
- date: `2026-06-04`
- command_intents: `packetize`, `implement`, `security`, `qa`, `evidence`, `score`
- ledger: local `ops/runs`

## Objective

Prove that a mobile-like project brief entered through a safe local command path can reach the local companion private inbox and persist in workspace-local ignored storage.

## Scope

- Add stdin/file input support to `scripts/simulate_mobile_capture.py`.
- Use the existing bearer token file without printing the token value.
- Send synthetic mobile-like content to `http://127.0.0.1:<port>/api/private/mobile-captures`.
- Keep API responses redacted and metadata-only.
- Add validation for browser bridge contract and private inbox smoke checks.

## Out Of Scope

- Real private data entry.
- Phone/contact/calendar/recording access.
- Cloud sync, Notion API, Discord dispatch, GitHub issue creation, OpenClaw execution.
- Token storage in `localStorage`, `sessionStorage`, IndexedDB, docs, or evidence.
- External origin support.
- Browser-to-companion `fetch`, CORS, CSP, pairing, or session-token UI.
- Encryption-at-rest implementation.

## Acceptance Criteria

1. `simulate_mobile_capture.py` can read mobile-like body content from stdin or a local file.
2. Capture sender still accepts only `http://127.0.0.1:<port>` as the companion base URL.
3. Capture sender still blocks redirects, userinfo, path, query, fragment, and non-loopback host.
4. CLI can send a synthetic project brief to private inbox with bearer auth.
5. Script output does not echo raw launch body or token.
6. `scripts/private_inbox_smoke_check.py` still passes.
7. Static smoke check still confirms no browser `fetch` integration exists.
8. Harness score records efficiency and limitations honestly.

## Risk Classification

- risk: `Low-Medium`
- reason: local private storage and bearer token handling remain in scope, but browser CORS/pairing is explicitly out of scope.

## Required Lanes

| Lane | Owner | Model/Effort | Purpose |
| --- | --- | --- | --- |
| repo-explorer | sidecar | economy/low | inspect current entry points and validation commands |
| security | sidecar | frontier/high | preflight token/private storage risks and block browser fetch scope |
| implementer | supervisor-local | inherit/medium | integrate small UI/server/test changes |
| QA/evidence | supervisor-local | inherit/medium | run smoke checks and record evidence |
| harness-evaluation | supervisor-local | inherit/medium | score efficiency and measurement limits |

## Approval Gates

- No additional approval required for local-only script/test/doc changes inside this project.
- Stop and request approval before browser fetch/CORS/pairing, real external integration, token persistence, encryption dependency, or live dispatch.

## Verification Plan

- `python3 -m py_compile companion/server.py companion/private_store.py scripts/private_inbox_smoke_check.py scripts/smoke_check.py`
- `python3 scripts/private_inbox_smoke_check.py`
- `python3 scripts/smoke_check.py`
- run companion locally and exercise stdin mobile-like capture flow with synthetic data only
- `git diff --check`

## Efficiency Measurement Plan

Internal observed metrics:

- implementer slice count
- sidecar findings used
- supervisor direct implementation ratio
- evidence completeness
- rework count
- unverified claim count
- security issue count
- coordination overhead

Counterfactual/estimated metrics:

- critical path reduction is estimated unless compared against a historical or paired no-harness run.
- elapsed-time speedup must be labeled as estimated unless a controlled A/B run exists.

Current baseline mode: `historical_estimate`, using the prior PNH private inbox run as a supervisor-heavy baseline. No controlled A/B speedup claim is allowed in this run.
