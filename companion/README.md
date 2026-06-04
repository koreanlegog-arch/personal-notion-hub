# Personal Notion Hub Local Companion

This directory contains the loopback-only local companion.

It has two modes:

- fixture preview mode for public-safe validation
- authenticated private inbox mode for workspace-local capture persistence
- optional browser bridge mode for exact-origin Launch UI pairing

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
- exact-origin browser bridge when explicitly enabled
- short-lived one-time pairing code printed only in the local terminal
- short-lived browser session token held in JS memory only

Forbidden:

- external API calls
- request body logging
- response echo of private title/body values
- committed vault, database, backup, or private runtime files
- browser UI integration outside the approved bridge module
- wildcard CORS or non-loopback browser origin
- persistent browser storage of auth material
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

Browser bridge mode:

```bash
python3 scripts/private_inbox_init.py
python3 companion/server.py \
  --host 127.0.0.1 \
  --port 8765 \
  --enable-private-inbox \
  --enable-browser-bridge \
  --allowed-origin http://127.0.0.1:4173
```

Use the local terminal's one-time pairing code in the Launch UI. Do not paste the code into chat, screenshots, docs, or committed files.

Endpoints:

- `GET /api/health`
- `GET /api/schema`
- `POST /api/import/preview`
- `POST /api/private/pair`
- `POST /api/private/mobile-captures`
- `GET /api/private/mobile-captures`
- `GET /api/private/summary`

## Validate

```bash
python3 scripts/companion_smoke_check.py
python3 scripts/private_inbox_smoke_check.py
python3 scripts/browser_bridge_smoke_check.py
```

The smoke check starts an ephemeral loopback server, validates the fake fixture,
checks sensitive-looking payload rejection, and confirms non-loopback bind
rejection.

The private inbox smoke check verifies auth rejection, authorized synthetic
capture storage, redacted responses, and SQLite persistence.

The browser bridge smoke check verifies unsafe config rejection, CORS,
one-time pairing, in-memory session auth compatibility, redacted responses, and
legacy bearer-token compatibility without printing secret values.

## Next Approval Gates

- encrypted vault implementation
- real-data import adapters
- packaging or distribution
- LAN/mobile-device pairing beyond loopback
- automated screenshot-safe browser QA
