# Personal Notion Hub Local Companion

This directory contains the loopback-only local companion.

It has two modes:

- fixture preview mode for public-safe validation
- authenticated private inbox mode for workspace-local capture persistence

## Boundary

Allowed:

- Python standard library only
- `127.0.0.1` loopback API
- fake fixture validation
- preview counts, errors, and warnings
- bearer-token authenticated private inbox writes when explicitly enabled
- ignored local SQLite private inbox under `companion/private/`
- default scripts reject private DB/token paths outside `companion/private/`
- mobile capture simulation is loopback-only and blocks redirects

Forbidden:

- external API calls
- request body logging
- response echo of private title/body values
- committed vault, database, backup, or private runtime files
- browser UI integration before pairing/CORS/CSP approval
- non-loopback bind addresses

## Run

From `Personal_Notion_Hub`:

```bash
python3 companion/server.py --host 127.0.0.1 --port 8765
```

Private inbox mode:

```bash
python3 scripts/private_inbox_init.py
python3 companion/server.py --host 127.0.0.1 --port 8765 --enable-private-inbox
```

Endpoints:

- `GET /api/health`
- `GET /api/schema`
- `POST /api/import/preview`
- `POST /api/private/mobile-captures`
- `GET /api/private/mobile-captures`
- `GET /api/private/summary`

## Validate

```bash
python3 scripts/companion_smoke_check.py
python3 scripts/private_inbox_smoke_check.py
```

The smoke check starts an ephemeral loopback server, validates the fake fixture,
checks sensitive-looking payload rejection, and confirms non-loopback bind
rejection.

The private inbox smoke check verifies auth rejection, authorized synthetic
capture storage, redacted responses, and SQLite persistence.

## Next Approval Gates

- UI `fetch` integration
- CSP and CORS policy
- one-time pairing or local session token
- encrypted vault implementation
- real-data import adapters
- packaging or distribution
