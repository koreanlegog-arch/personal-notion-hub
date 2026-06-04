# Task Packet - PNH Assistant Local-First Readiness

Run ID: `PNH-ASSISTANT-LOCAL-FIRST-20260604`
Date: 2026-06-04
Project: `Personal_Notion_Hub`
Status: active validation packet

## 1. Objective

Prepare `Personal_Notion_Hub` to resume assistant/local-companion work by validating the current web UI and fixture-only local companion against release-readiness, browser QA, and privacy-safety criteria.

## 2. Scope

In scope:

- Confirm current static web app can still load and reference required assets.
- Confirm Assistant MVP remains local-only and fixture/manual-input based.
- Confirm local companion prototype remains loopback-only, preview-only, and write-disabled.
- Run browser-oriented QA substitutes available without installing new dependencies.
- Run local companion privacy validation with fake fixtures only.
- Produce evidence that determines whether PNH can safely resume implementation.

Out of scope:

- No real private contacts, schedules, phone data, call logs, recordings, transcripts, or personal notes.
- No encrypted SQLite/vault implementation in this run.
- No browser-to-companion `fetch` integration in this run.
- No OAuth, API key, external API, cloud sync, Telegram, Discord, Notion, Google, Slack, Kakao, or phone integration.
- No deployment or GitHub Pages production validation unless explicitly requested later.
- No new package install or Playwright introduction without separate approval.

## 3. Acceptance Criteria

| ID | Criterion | Validation |
| --- | --- | --- |
| AC-01 | Static app required files are present and referenced assets exist. | `python3 scripts/smoke_check.py` |
| AC-02 | HTML uses CSP and avoids inline event handlers. | `python3 scripts/smoke_check.py` |
| AC-03 | App JavaScript avoids `innerHTML`, `fetch`, and `XMLHttpRequest` in current public shell. | `python3 scripts/smoke_check.py` |
| AC-04 | Local companion starts only on `127.0.0.1`. | `python3 scripts/companion_smoke_check.py` |
| AC-05 | Companion health/schema reports fixture-only preview mode and writes disabled. | `python3 scripts/companion_smoke_check.py` plus optional manual API probe |
| AC-06 | Companion rejects sensitive-looking fixture values without echoing submitted values. | `python3 scripts/companion_smoke_check.py` |
| AC-07 | No vault/database/private runtime artifacts are created by validation. | `python3 scripts/companion_smoke_check.py` and file scan |
| AC-08 | Browser QA status is clearly classified as automated, substitute, manual, or blocked. | `browser_qa.md` evidence |
| AC-09 | Privacy validation says whether implementation may resume and lists approval gates. | `privacy_validation.md` and `release_readiness.md` |

## 4. Required Lanes

- `browser-qa`: Validate static/browser-facing behavior using available local tooling; if no browser automation exists, record substitute checks and blocked automation.
- `security-review`: Validate private-data, secret, loopback, write-disabled, and no-real-data boundaries.
- `release-readiness`: Produce a readiness verdict for resuming implementation, not for public production delivery.

## 5. Risk Classification

Risk level: Medium.

Reason:

- The next product direction may eventually handle highly sensitive personal data.
- Current run is safe only because it uses fixture data, no external services, no vault writes, and no real private data.

## 6. Approval Gates

Require explicit supervisor approval before:

- adding real private data import
- accessing phone contacts, messages, call logs, recordings, calendars, or transcripts
- adding encrypted vault/database writes
- adding browser-to-companion `fetch` integration
- adding CORS/pairing/session token workflows
- adding dependencies, Playwright, packaging, desktop wrappers, or cloud services
- deploying any sensitive-data mode

## 7. Stop Conditions

Stop and report if:

- any validation prints or stores real private data
- companion binds to non-loopback host
- validation creates `.db`, `.sqlite`, `.vault`, private runtime, or log artifacts
- app code contains secret-like values or external network calls not previously approved
- static smoke or companion smoke fails

## 8. Ledger And Evidence

Evidence files for this run:

- `ops/runs/PNH-ASSISTANT-LOCAL-FIRST-20260604/browser_qa.md`
- `ops/runs/PNH-ASSISTANT-LOCAL-FIRST-20260604/privacy_validation.md`
- `ops/runs/PNH-ASSISTANT-LOCAL-FIRST-20260604/release_readiness.md`
