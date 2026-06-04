# PNH Private Inbox MVP Task Packet

Date: 2026-06-04

## Objective

Build a working local-first private inbox path for `Personal_Notion_Hub` so a phone-like input can reach workspace-local storage through a local companion.

## Corrected Lesson

Previous issue: the prior MVP emphasized mobile project launch UI before proving the most important automation path.

Corrected rule:

```text
For automation intake work, prove source -> companion -> workspace persistence before UI polish.
```

## Scope

- Add authenticated local companion write endpoint.
- Add ignored workspace-local SQLite private inbox.
- Add init, simulated mobile capture, status, and smoke-check scripts.
- Preserve fixture-only preview mode and its no-write contract.
- Update security, architecture, QA, and release docs.

## Out Of Scope

- Real phone/contact/calendar/recording adapters.
- Browser UI `fetch` integration.
- CORS/pairing flow.
- Encryption-at-rest.
- Cloud sync or external APIs.
- Public deployment changes.

## Acceptance Criteria

- `127.0.0.1` remains the only allowed bind host.
- Private write endpoint rejects missing or wrong bearer token.
- Authorized synthetic mobile capture is written to local SQLite.
- API responses do not echo submitted title/body values.
- Status command proves persistence without printing private values.
- Fixture-only preview still performs no private writes.
- Private inbox files remain ignored by Git.
- Mobile sender cannot send bearer token or payload to non-loopback URL.
- DB/token path overrides outside `companion/private/` are rejected by default.
- Status command does not create a missing database.

## Expected Files

- `companion/private_store.py`
- `companion/server.py`
- `scripts/private_inbox_init.py`
- `scripts/simulate_mobile_capture.py`
- `scripts/private_inbox_status.py`
- `scripts/private_inbox_smoke_check.py`
- `scripts/companion_smoke_check.py`
- `scripts/smoke_check.py`
- `docs/LOCAL_COMPANION_ARCHITECTURE.md`
- `docs/PRIVATE_DATA_POLICY.md`
- `docs/SECURITY_NOTES.md`
- `docs/TEST_PLAN.md`
- `docs/RELEASE_NOTES.md`
- `README.md`
- `companion/README.md`

## Validation Plan

- Python compile check.
- Static smoke check.
- Fixture companion smoke check.
- Private inbox smoke check with synthetic data.
- Real local private inbox initialization.
- Real local companion run on `127.0.0.1:8765`.
- Simulated mobile capture into the local inbox.
- Redacted private inbox status check.
- Git ignore/untracked check for `companion/private/`.

## Risk Level

Medium.

Reason: this adds local auth and persistent storage for sensitive-workflow preparation. Risk is bounded by no external service, no dependency install, loopback-only bind, ignored local files, and no token/value printing.
