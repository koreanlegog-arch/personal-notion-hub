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
- Local companion now supports explicit loopback browser bridge mode for synthetic Launch UI pairing.
- Local companion now supports explicit encrypted vault mode for sensitive local captures when `cryptography` and local passphrase input are available.

This is acceptable for a demo, low-risk local notes, proving the private data ingress path, and supervisor-approved sensitive local testing in encrypted vault mode. It is not yet a full long-term private-data system because plaintext migration apply, OS keychain storage/retrieval, real-data adapters, and adapter-specific policies are still missing.

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

Implemented encrypted-vault MVP flow:

```text
virtual mobile input / Launch bridge packet
-> local companion validation
-> AES-GCM encrypted SQLite record
-> redacted metadata/status output
-> optional local decrypt with passphrase for owner inspection
```

Target long-term flow remains:

```text
manual input / approved local adapter import
-> browser UI preview
-> local companion validation
-> encrypted vault write
-> local assistant rule processing
-> UI review
-> encrypted export / backup / delete
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

Do not install a new encryption package until a concrete implementation plan and dependency review are approved. The current MVP uses installed `cryptography` only; if it is unavailable, encrypted mode fails closed.

## Implemented Private Inbox MVP

The current plaintext MVP uses Python standard library SQLite as a local private inbox and remains available for compatibility.

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
- browser bridge is disabled by default and uses exact-origin CORS
- Launch UI uses memory-only browser sessions and best-effort screenshot redaction

Not yet implemented:

- OS keychain storage/retrieval
- phone/contact/calendar/recording adapters
- local transcription
- plaintext-to-encrypted migration apply
- encrypted attachment/audio export/import
- passphrase recovery

## Implemented Encrypted Vault MVP

The encrypted vault MVP stores private capture fields in `encrypted_mobile_captures`.

Implemented protections:

- explicit `--enable-encrypted-vault` startup flag
- passphrase loaded from no-echo prompt, `PNH_VAULT_PASSPHRASE`, or a configured env var name
- fail-closed startup when `cryptography` or passphrase is unavailable
- AES-GCM authenticated encryption
- PBKDF2-HMAC-SHA256 key derivation with per-vault salt
- random nonce per capture
- metadata-only API responses
- redacted default status output
- wrong-passphrase rejection
- tamper rejection
- DB byte scan smoke check for synthetic plaintext absence
- prompt/keychain readiness smoke check without secret output
- backup-gated passphrase rotation smoke check

Not yet implemented:

- OS keychain storage/retrieval
- passphrase recovery
- plaintext private inbox migration apply
- local search over encrypted private fields
- adapter-specific ingestion for real contacts, calendar, calls, recordings, or transcripts

Implemented lifecycle controls:

- encrypted backup envelope creation
- encrypted restore into a fresh or existing vault
- duplicate restore skip by default
- explicit capture delete with confirmation phrase
- passphrase rotation with existing encrypted backup acknowledgement
- plaintext migration audit without value disclosure

This MVP is sufficient to prove that a mobile-like input can reach workspace-local encrypted storage and can be backed up, restored, deleted at row level, and rotated to a new passphrase. For routine high-sensitivity operation, plaintext migration apply, OS keychain storage/retrieval or recovery policy, real-data adapters, and adapter-specific policies are the next blockers.

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
7. Add secure pairing between UI and companion. Done for loopback-only synthetic Launch bridge.
8. Add encrypted vault schema. Done for capture records.
9. Add encrypted export/import/delete validation. Done for encrypted capture rows.
10. Add plaintext-to-encrypted migration guard. Done as audit-only.
11. Add selected real-data import adapters one by one, each behind approval.
12. Only then consider distribution to close friends.

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
- changing vault encryption scheme
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

Upgrade the encrypted vault MVP into an operational private-data system. The next implementation should prove:

- plaintext-to-encrypted migration apply
- OS keychain storage/retrieval
- passphrase recovery
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
- browser UI connection only through explicit loopback bridge mode

The prototype is not a sensitive-data storage system. Its job is to validate the companion boundary and QA loop before encrypted storage or real import adapters are approved.

## Private Inbox MVP Status

The private inbox is a working local ingestion MVP, not a final vault.

Current contract:

- initialize with `python3 scripts/private_inbox_init.py`
- run with `python3 companion/server.py --host 127.0.0.1 --port 8765 --enable-private-inbox`
- optionally run browser bridge with `--enable-browser-bridge --allowed-origin http://127.0.0.1:4173`
- simulate phone-like input with `python3 scripts/simulate_mobile_capture.py`
- verify storage with `python3 scripts/private_inbox_status.py`
- validate security contracts with `python3 scripts/private_inbox_smoke_check.py`
- validate browser bridge contracts with `python3 scripts/browser_bridge_smoke_check.py`

The critical success criterion is source-to-workspace persistence, not UI polish.

## Encrypted Vault MVP Status

Current contract:

- initialize with `python3 scripts/private_inbox_init.py --enable-encrypted-vault`
- run with `python3 companion/server.py --host 127.0.0.1 --port 8765 --enable-private-inbox --enable-encrypted-vault`
- keep `PNH_VAULT_PASSPHRASE` local and do not record it in chat, screenshots, logs, or docs
- validate with `python3 scripts/encrypted_vault_smoke_check.py`
- validate passphrase prompt/keychain readiness with `python3 scripts/passphrase_provider_smoke_check.py` and `python3 scripts/keychain_readiness.py`
- validate lifecycle with `python3 scripts/encrypted_vault_backup_restore_smoke_check.py`, `python3 scripts/encrypted_vault_delete_smoke_check.py`, and `python3 scripts/plaintext_migration_audit_smoke_check.py`
- validate the approved backend implementation plan against `docs/PASSPHRASE_KEYCHAIN_BACKEND_DESIGN.md` before adding persistent secret storage

The critical success criterion is encrypted source-to-workspace persistence with redacted evidence.
