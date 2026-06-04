# Personal Notion Hub Local Companion Prototype

This directory contains the fixture-only local companion prototype.

## Boundary

Allowed:

- Python standard library only
- `127.0.0.1` loopback API
- fake fixture validation
- preview counts, errors, and warnings

Forbidden:

- real contacts, schedules, calls, recordings, transcripts, private notes, client data, tokens, or credentials
- vault, database, backup, or private runtime file writes
- external API calls
- browser UI integration before pairing/CORS/CSP approval
- non-loopback bind addresses

## Run

From `Personal_Notion_Hub`:

```bash
python3 companion/server.py --host 127.0.0.1 --port 8765
```

Endpoints:

- `GET /api/health`
- `GET /api/schema`
- `POST /api/import/preview`

## Validate

```bash
python3 scripts/companion_smoke_check.py
```

The smoke check starts an ephemeral loopback server, validates the fake fixture,
checks sensitive-looking payload rejection, and confirms non-loopback bind
rejection.

## Next Approval Gates

- UI `fetch` integration
- CSP and CORS policy
- one-time pairing or local session token
- encrypted vault implementation
- real-data import adapters
- packaging or distribution
