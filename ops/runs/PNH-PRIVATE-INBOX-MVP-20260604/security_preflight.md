# Security Preflight

Date: 2026-06-04

## Security Constraints

- No real secret values may be printed.
- No submitted capture title/body may be echoed in API responses.
- Server must bind only to `127.0.0.1`.
- Private write/read endpoints require bearer token auth.
- Token and SQLite files must live under ignored `companion/private/`.
- Fixture preview mode must remain write-disabled.
- No external APIs, OAuth, cloud sync, daemon, or dependency install.

## Data Classification

- Synthetic mobile capture: allowed for validation.
- Real personal phone/contact/calendar/call data: high sensitivity, not used in this run.
- Token file: secret, ignored, value never printed.
- SQLite private inbox: local private data store, ignored, not encrypted at rest.

## Accepted MVP Risk

The MVP uses stdlib SQLite without encryption-at-rest. This is accepted only to prove source-to-workspace persistence under loopback auth. Long-term high-sensitivity storage requires encryption-at-rest and backup/delete workflow.

## Approval Gates Remaining

- Encryption package or SQLCipher adoption.
- Browser-to-companion pairing/CORS.
- Real phone/contact/calendar/recording adapters.
- Local transcription.
- Cloud sync or remote access.
- Distribution to close friends.

## Logging Policy

Allowed:

- method/path logs
- status booleans
- record IDs and counts
- redacted titles

Forbidden:

- token values
- body text
- raw call content
- phone numbers
- credentials
- private file contents
