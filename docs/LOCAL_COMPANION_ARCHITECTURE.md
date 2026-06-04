# Local Companion Architecture

## Decision Summary

`Personal_Notion_Hub` should evolve toward a local companion model before it handles real private contacts, schedules, call notes, recordings, transcripts, or sensitive relationship notes.

Recommended long-term architecture:

```text
Personal_Notion_Hub web UI
-> local companion service/script
-> encrypted SQLite or encrypted local vault
-> local-only import, search, summary, backup, and deletion workflows
```

The current GitHub Pages/static web app remains useful as a public-safe demo shell and lightweight UI. It must not become the primary storage surface for sensitive personal data.

## Current State

- Static HTML/CSS/JavaScript app.
- No backend, auth, package install, or external API.
- Hub data uses `localStorage`.
- Assistant MVP uses browser `IndexedDB`.
- Public GitHub Pages deployment is possible.
- Demo/fixture data only should be committed.
- Local companion supports fixture-only preview mode.
- Local companion also supports authenticated private inbox mode for workspace-local SQLite capture.

This is acceptable for a demo, low-risk local notes, and proving the private data ingress path. It is not yet an encrypted long-term vault.

## Public Shell Vs Private Data Plane

The project should explicitly separate two modes:

### Public Shell Mode

Used for:

- GitHub Pages demo
- UI development
- fake fixture QA
- public-safe documentation

Must not include:

- real user data
- vault files
- private exports
- private screenshots
- real transcripts
- real contact/calendar/call content

### Private Companion Mode

Used for:

- real private data
- encrypted vault access
- local import adapters
- backup/restore/delete
- future close-friends distribution

The companion is the private data plane. The browser UI is the presentation surface.

## Target Roles

### Web UI

The browser UI should own:

- navigation
- dashboard rendering
- assistant review workflow
- manual import forms
- local companion connection status
- copy/download output drafts
- explicit privacy warnings

The browser UI should not own:

- long-term sensitive data persistence
- encryption key storage
- raw recording storage
- OAuth tokens
- cloud sync
- automatic phone scraping

### Local Companion

The local companion should own:

- private data vault access
- encrypted storage
- backup/export/delete operations
- local import adapters
- local search/indexing
- local rule-based assistant processing
- optional local transcription only after separate approval
- audit-safe logs

### Encrypted Vault

The vault should own:

- contacts metadata
- calendar/event records
- call notes
- voice memo metadata
- optional transcript text
- personal notes
- assistant captures and suggestions
- deletion and export records

Raw audio should not be added to the first vault implementation unless storage, retention, and transcript policies are approved.

## Architecture Options

### Option A: Browser-Only IndexedDB

Use current browser storage only.

Pros:

- simplest
- no install
- no local service

Cons:

- weak long-term backup
- weak migration control
- no strong encryption boundary
- difficult to manage sensitive data reliably

Use only for MVP/demo.

### Option B: Local Script + Encrypted SQLite

Run a local companion script that manages an encrypted SQLite database or encrypted vault file.

Pros:

- best near-term balance
- local-only by default
- easier backup and migration
- better schema management
- testable without cloud

Cons:

- requires local runtime
- requires packaging and key-management decisions
- browser-to-local communication must be secured

Recommended next direction.

### Option C: Desktop App Wrapper

Package the UI and local vault into a desktop app.

Pros:

- cleaner user experience for close-friends distribution
- fewer browser-origin issues
- can manage local files more directly

Cons:

- packaging complexity
- update distribution burden
- signing/trust concerns

Consider after Option B proves useful.

### Option D: Private Cloud Backend

Use a private backend with auth and encrypted storage.

Pros:

- multi-device convenience
- easier remote access

Cons:

- largest security burden
- secrets, auth, hosting, backup, access logs, and incident response required
- not appropriate as the first sensitive-data architecture

Not recommended now.

## Data Flow

First implemented local-companion flow:

```text
virtual mobile input
-> local companion bearer-token auth
-> private inbox validation
-> ignored workspace SQLite write
-> redacted status check
```

No automatic external API call is part of this flow.

Target encrypted-vault flow remains:

```text
manual input / local file import
-> browser UI preview
-> local companion validation
-> encrypted vault write
-> local assistant rule processing
-> UI review
-> export / backup / delete
```

## Local Communication Options

### Localhost HTTP

Example:

```text
http://127.0.0.1:<port>
```

Pros:

- easy for browser UI
- easy to test

Risks:

- local CSRF-style requests from other pages
- port exposure
- accidental binding to non-loopback interface

Requirements:

- bind to `127.0.0.1` only
- random local session token or one-time pairing
- CORS restricted to the app origin
- reject non-loopback bind addresses by default
- request size limits for imports and transcripts
- no wildcard CORS
- no companion control from public web origins
- no raw secret values in logs

### Local File Bridge

The UI exports/imports local files while a script manages the vault.

Pros:

- no local port
- simpler security story

Cons:

- less convenient
- weaker live assistant workflow

Good transitional option.

### Desktop IPC

Use desktop app IPC after packaging.

Pros:

- strong app boundary
- better UX

Cons:

- packaging complexity

Consider later.

## Storage Direction

Preferred first storage target:

```text
encrypted SQLite-compatible vault or encrypted local JSON vault
```

Selection criteria:

- no network dependency
- deterministic backup/export
- passphrase or OS-keychain strategy
- schema migration support
- deletion support
- no plaintext private data in repo, logs, reports, or screenshots

Do not add an encryption package until a concrete implementation plan and dependency review are approved.

## Implemented Private Inbox MVP

The current MVP uses Python standard library SQLite as a local private inbox.

Implemented protections:

- `127.0.0.1` bind only
- bearer token loaded from `companion/private/auth_token`
- token value is not printed by scripts
- `companion/private/` is ignored by Git
- private DB/token paths outside `companion/private/` are rejected by default
- simulated mobile sender accepts only `http://127.0.0.1:<port>` and blocks redirects
- status command does not create a missing DB
- best-effort `0700` private directory permission
- best-effort `0600` token and database file permission
- API write responses return metadata only
- recent status output redacts titles and omits bodies
- fixture preview mode remains write-disabled

Not yet implemented:

- encryption-at-rest
- OS keychain integration
- CORS/pairing between the public web UI and companion
- phone/contact/calendar/recording adapters
- local transcription
- backup/delete/restore workflow for sensitive records

This MVP is sufficient to prove that a mobile-like input can reach workspace-local private storage. For long-term storage of highly sensitive records, encryption-at-rest and explicit backup/delete workflows are the next blockers.

## Candidate Vault Designs

### SQLCipher SQLite

Best fit when schema, search, and migrations matter.

Risks:

- native dependency and packaging complexity
- key management must be correct
- binary distribution is harder for close friends

### SQLite With Application-Level Field Encryption

Useful if SQLCipher packaging is too heavy.

Risks:

- query/search limitations
- higher chance of implementation mistakes
- metadata may remain plaintext unless explicitly protected

### Encrypted Blob Vault Plus Metadata Index

Useful for large artifacts such as transcripts, attachments, or future audio metadata.

Default for first sensitive implementation:

- store structured records in encrypted SQLite or encrypted fields
- store large artifacts as encrypted blobs
- do not store raw audio until retention and deletion policy is approved

## Migration Path

1. Keep current browser-only Assistant MVP as demo/public-safe.
2. Use current JSON export as migration input, but keep it demo/browser-only until encrypted export is approved.
3. Add architecture docs and approval gates.
4. Add a local companion proof of concept using fake fixture data only. Done.
5. Add `GET /api/health`, `GET /api/schema`, and `POST /api/import/preview` before any vault write endpoint. Done.
6. Add authenticated private inbox write endpoint and local SQLite store. Done.
7. Add secure pairing between UI and companion.
8. Add encrypted vault schema.
9. Add encrypted export/import/delete validation.
10. Add selected real-data import adapters one by one, each behind approval.
11. Only then consider distribution to close friends.

## Distribution To Close Friends

Before sharing beyond the owner, require:

- private-data warning on first launch
- clear local-only statement
- no cloud sync by default
- no bundled personal data
- no token collection
- backup and delete instructions
- compatibility notes
- rollback/uninstall instructions
- security limitations documented plainly
- per-user vault key or passphrase
- no shared master password
- release checksum
- no bundled owner data
- no automatic cloud telemetry

## Approval Gates

The current local companion script and private inbox MVP were created under supervisor request on 2026-06-04.

Separate approval is still required before:

- installing encryption/database dependencies
- choosing a vault encryption scheme
- opening any non-loopback or long-running localhost service
- adding phone/contact/calendar/recording import adapters
- adding transcription
- adding cloud sync or OAuth
- packaging for other users
- accepting any plaintext private-data storage risk
- changing GitHub Pages from demo shell to private-data surface
- enabling clipboard copy for sensitive summaries without warning/redaction policy
- enabling screenshot/browser QA with real data

## Recommended Next Step

Upgrade the private inbox into a hardened local vault. The next implementation should prove:

- encryption-at-rest or equivalent vault protection
- backup/delete/restore workflow
- CORS/pairing policy before browser `fetch`
- redacted review UI for sensitive records
- adapter-by-adapter approval gates for phone, calendar, contacts, recordings, and transcripts

## Fixture-Only Prototype Status

The first implementation prototype is intentionally narrower than private companion mode.

Current prototype boundary:

- Python standard library only
- `127.0.0.1` loopback only
- `GET /api/health`
- `GET /api/schema`
- `POST /api/import/preview`
- fake fixtures only
- no vault/database/encryption package
- no private data adapters
- no browser UI connection yet

The prototype is not a sensitive-data storage system. Its job is to validate the companion boundary and QA loop before pairing, CORS, encrypted storage, or real import adapters are approved.

## Private Inbox MVP Status

The private inbox is a working local ingestion MVP, not a final vault.

Current contract:

- initialize with `python3 scripts/private_inbox_init.py`
- run with `python3 companion/server.py --host 127.0.0.1 --port 8765 --enable-private-inbox`
- simulate phone-like input with `python3 scripts/simulate_mobile_capture.py`
- verify storage with `python3 scripts/private_inbox_status.py`
- validate security contracts with `python3 scripts/private_inbox_smoke_check.py`

The critical success criterion is source-to-workspace persistence, not UI polish.
