# PNH-REDACTED-BROWSER-QA-20260604 Task Packet

## Objective

Add and run browser QA coverage for Personal Notion Hub's redacted UI path after
the supervisor confirmed the Assistant-to-workspace ingress flow in a real
browser.

## Scope

- Record supervisor-confirmed manual browser QA for Assistant workspace ingress.
- Add a Playwright redacted UI QA test using synthetic data only.
- Add a no-install runner that starts a local static server and runs Playwright when local browser tooling is available.
- Keep generated screenshots/traces out of Git.
- Update test plan, release notes, and smoke contracts.

## Out Of Scope

- Installing Playwright browsers without approval.
- Capturing screenshots with real private data.
- LAN/mobile-device ingress.
- External service integration.
- Real contacts, calls, recordings, transcripts, calendar, or client data.

## Acceptance Criteria

- Manual browser QA status is recorded without secret values.
- Playwright test validates redaction CSS application before screenshot capture.
- Playwright test validates browser storage does not retain pairing/session token material.
- Playwright test validates core desktop/mobile views do not horizontally overflow.
- Runner reports blocked rather than failing unclearly when Chromium is unavailable.
- Static smoke recognizes the Playwright test and runner contracts.

## Risk

Medium. Browser QA artifacts can expose screen content, so artifacts must stay
synthetic/redacted and ignored by Git.
