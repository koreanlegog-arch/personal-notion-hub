# Task Packet: Browser Companion Bridge

## Metadata

- run_id: `PNH-BROWSER-COMPANION-BRIDGE-20260604`
- project: `Personal_Notion_Hub`
- date: `2026-06-04`
- command_intents: `packetize`, `dispatch`, `slice`, `implement`, `security`, `qa`, `evidence`, `score`
- ledger: local `ops/runs`

## Objective

Design and implement the first secure browser-to-local-companion bridge so a Launch dispatch packet can be sent from the web UI to the loopback private inbox without storing long-lived secrets in browser storage.

## Success Criteria

1. Browser bridge is explicitly approved and documented as a private local companion mode, not public Pages sync.
2. Companion only enables browser bridge when started with an explicit flag.
3. CORS allowlist accepts only configured `http://127.0.0.1:<port>` origins; no wildcard, no `null`, no `localhost` by default.
4. `index.html` CSP allows only the default local companion endpoint via `connect-src`.
5. Browser UI does not store bearer token, pairing code, or session token in `localStorage`, `sessionStorage`, or IndexedDB.
6. Pairing uses a short-lived one-time pairing code to issue an in-memory session token.
7. Private write endpoint accepts browser session tokens and existing script bearer token path remains compatible.
8. UI can check health, pair session, and send a synthetic Launch packet to private inbox.
9. UI provides best-effort screenshot redaction for sensitive launch text and pairing input.
10. API responses, logs, docs, and evidence do not echo token values or raw private body values.
11. Static, server, browser-bridge, and private inbox smoke checks pass.

## Scope

- Server-side browser bridge:
  - CORS allowlist
  - `OPTIONS` preflight
  - one-time pairing endpoint
  - in-memory browser session tokens
  - CLI flags for bridge enablement and allowed origin
- Browser-side bridge:
  - CSP `connect-src` for default loopback companion
  - Launch view status/pair/send controls
  - in-memory session token only
  - loopback base URL validation
- Validation:
  - browser bridge smoke test without real private data
  - static security checks updated to allow only controlled `fetch`
- Documentation:
  - security notes, test plan, README, companion README
  - run evidence and harness evaluation

## Out Of Scope

- Real private data.
- External services, Notion API, Discord dispatch, GitHub issue creation, OpenClaw execution.
- Non-loopback origins.
- `localhost`, `file://`, `Origin: null`, HTTPS tunneling, mobile LAN access.
- Persistent browser token storage.
- Encrypted vault implementation.
- Packaging/distribution.

## Risk Classification

- risk: `Medium-High`
- reason: introduces browser-to-local private data plane and session auth, even though loopback-only and synthetic-only validation.

## Routing Decision

Use multi-agent harness because the work crosses browser UI, server auth/CORS, QA, and security boundaries.

| Lane | Agent | Model/Effort | Write Scope | Purpose |
| --- | --- | --- | --- | --- |
| architecture | architect | frontier/high | read-only | confirm minimal architecture and slices |
| security | security | frontier/xhigh | read-only | preflight and release gates |
| QA | QA | standard/medium | read-only | acceptance matrix and checks |
| server implementer | implementer | standard/medium | `companion/server.py`, `scripts/browser_bridge_smoke_check.py`, companion test hooks | implement server/session/CORS slice |
| browser implementer | implementer | standard/medium | `index.html`, `assets/js/app.js`, `assets/css/styles.css`, `scripts/smoke_check.py` | implement UI/CSP/static contract slice |
| supervisor integrator | supervisor | inherit/medium | docs/run/evidence/integration | integrate, verify, score |

## Approval Gates

This task packet treats the supervisor request as approval to design and implement the local-only browser bridge under these limits:

- no external service calls
- no real private data
- no dependency installation
- no persistent browser secret storage
- no non-loopback access

Stop and ask again before any of:

- external or LAN access
- real mobile device pairing beyond local loopback
- encryption dependency
- live Discord/GitHub/OpenClaw dispatch
- accepting a security blocker

## Stop Conditions

- CORS requires wildcard or `Origin: null`.
- Pairing/session token must be persisted in browser storage to work.
- Static smoke cannot distinguish controlled fetch from arbitrary fetch.
- Server smoke cannot validate session tokens without printing token values.
- Browser UI requires new dependencies.

## Validation Plan

- `python3 -m py_compile companion/server.py scripts/browser_bridge_smoke_check.py scripts/private_inbox_smoke_check.py scripts/smoke_check.py`
- `python3 scripts/browser_bridge_smoke_check.py`
- `python3 scripts/private_inbox_smoke_check.py`
- `python3 scripts/smoke_check.py`
- `git ls-files companion/private`
- `git check-ignore -v companion/private/auth_token companion/private/pnh_private_inbox.sqlite`
- `git diff --check`

## Evidence Policy

- Use synthetic Launch payloads only.
- Do not store or print session token values.
- Do not capture screenshots with private-like body text.
- Evidence records metadata, command results, and redacted statuses only.
