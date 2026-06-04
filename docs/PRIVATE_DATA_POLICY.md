# Private Data Policy

## Purpose

This policy defines what `Personal_Notion_Hub` may and may not do when it evolves toward handling sensitive personal data.

## Default Rule

Real private data must stay local unless a separate architecture, security, and approval gate explicitly allows otherwise.

## Forbidden In Repository

Do not commit:

- real names from private contacts
- phone numbers
- email addresses from private address books
- call logs
- private call summaries
- recordings
- transcripts
- calendar details
- personal relationship notes
- location history
- client data
- private file paths
- tokens, credentials, API keys, OAuth grants, or secrets
- backup JSON or vault files

## Forbidden In Logs And Evidence

Do not include private values in:

- harness evidence logs
- screenshots
- QA reports
- console logs
- terminal output
- GitHub issues
- Discord messages
- review packets
- error traces
- browser QA artifacts
- public Pages artifacts

Allowed evidence should use fake fixtures only.

## Storage Policy

### Public Demo Mode

Allowed:

- static app code
- demo fixture data
- fake assistant examples

Forbidden:

- real private data
- real backups
- vault files

### Browser Private Mode

Allowed:

- low-risk manual data
- demo assistant captures
- local IndexedDB data for personal experimentation

Limitations:

- `localStorage` and `IndexedDB` are not encrypted vaults
- same-origin JavaScript can access the data
- browser profile compromise can expose data

### Local Companion Vault

Minimum target for supervisor-approved sensitive local testing.

Required:

- local-only default
- encrypted vault or equivalent local protection
- explicit backup/export/delete flows
- no cloud sync by default
- sanitized logs
- fixture-only tests
- encrypted backups only
- explicit deletion workflow

Current MVP:

- explicit `--enable-encrypted-vault` mode
- passphrase from no-echo local prompt or local environment variable
- AES-GCM encrypted title/body/payload fields
- PBKDF2-HMAC-SHA256 key derivation with per-vault salt
- metadata-only API responses
- redacted default status output
- keychain readiness audit that prints capability flags only
- synthetic smoke tests for wrong passphrase, tamper rejection, and plaintext absence in DB bytes

Remaining blockers before routine high-sensitivity operation:

- plaintext-to-encrypted migration apply
- OS keychain storage/retrieval
- passphrase recovery or rotation
- screenshot-safe automated QA
- adapter-specific policies for contacts, calendar, calls, recordings, and transcripts

Implemented lifecycle controls:

- encrypted backup envelope creation with no plaintext JSON export
- encrypted restore with duplicate skip by default and explicit replace option
- encrypted capture delete by ID with confirmation phrase
- plaintext migration audit that reports counts only and does not mutate the DB

### Local Private Inbox MVP

Implemented as a transitional storage layer and compatibility path.

Allowed:

- synthetic mobile captures
- low-risk supervisor-approved local private testing
- workspace-local SQLite records under `companion/private/`
- redacted status checks
- explicit loopback browser bridge pairing for synthetic Launch packets

Required:

- `127.0.0.1` loopback only
- bearer token auth for write/read endpoints
- no token value printed in terminal output
- no raw capture body echoed in API responses
- no private inbox files committed to Git
- fixture-only QA for screenshots and public reports
- browser bridge disabled by default
- exact-origin CORS and CSP
- no persistent browser storage for token, pairing code, or session token
- screenshot redaction enabled before capture evidence

Limitations:

- not encrypted at rest
- relies on OS account and file permissions
- not suitable for routine high-sensitivity call transcripts, recordings, client data, or third-party private content
- pairing code is manually copied from local terminal and must not be recorded
- browser session is memory-only and requires re-pairing after reload

The plaintext MVP is acceptable for proving source-to-workspace persistence and compatibility. For sensitive local testing, use encrypted vault mode with prompt-first passphrase handling. Before routine use with high-sensitivity real data, add plaintext migration apply policy, OS keychain storage or recovery policy, and automated redaction validation.

## Call And Recording Data

Call content, recordings, and transcripts are high-sensitivity data.

Before adding them:

- define retention policy
- define deletion policy
- define transcript source
- define whether raw audio is stored
- define whether transcription is local or cloud
- define whether another party's consent or legal constraints apply

Default:

- no raw audio storage
- no automatic recording access
- no cloud transcription
- no transcript commit
- no screenshot evidence with visible call content
- no clipboard copy of sensitive summaries without warning

## Cloud Policy

Cloud is prohibited by default for sensitive data.

Cloud may only be considered after:

- auth design
- encryption design
- access logging
- backup and deletion policy
- incident response plan
- explicit approval

## QA Policy

Browser QA, screenshots, and automation must use fake fixture data.

QA must verify:

- no real private data in repo
- no backup/vault files in artifact
- no secret values in logs
- no external API calls without approval
- public Pages remains demo-safe
- screenshot-safe mode or redacted view is used before real private data mode

## Export And Backup Policy

Browser JSON export is acceptable only for demo and low-risk local data.

Sensitive mode requires:

- encrypted export only
- no automatic plaintext backup
- backup location confirmation
- retention guidance
- delete/restore instructions
- warning that OS/cloud-synced folders can leak backups

Plaintext export filenames such as `personal-notion-hub-YYYY-MM-DD.json` must not be used for sensitive vault exports.

## Clipboard Policy

Clipboard copy is convenient but risky for private summaries.

Sensitive mode requires:

- warning before copying sensitive summaries
- optional redacted copy
- no automatic copy
- clear note that OS clipboard cannot be reliably expired by the app

## Distribution Policy

Before recommending the app to close friends:

- use a clean install package or clear setup instructions
- include privacy limitations
- include backup/delete instructions
- include local-only defaults
- do not include the owner's data
- do not imply cloud-grade security
