# ADR 0001: Local Companion And Encrypted Vault Direction

## Status

Accepted. Local companion and encrypted capture vault MVP implemented on 2026-06-04.

## Context

`Personal_Notion_Hub` is currently a static browser app with `localStorage` and `IndexedDB` storage. This is useful for a demo and low-risk personal organization, but the intended future scope may include sensitive private data such as contacts, schedules, call notes, recordings, and transcripts.

Public GitHub Pages and browser storage are not sufficient as the long-term storage architecture for that data.

## Decision

Adopt this long-term direction:

```text
Personal_Notion_Hub web UI
-> local companion script/service
-> encrypted SQLite or encrypted local vault
```

The web UI remains the interaction layer. The local companion becomes the private-data and vault boundary. Public Pages remains demo-safe only.

The companion path is implemented in stages:

1. fixture-only preview mode
2. authenticated plaintext private inbox for source-to-workspace persistence
3. explicit encrypted vault mode for sensitive local capture testing
4. owner-only local/tailnet browser bridge for manual phone capture

Real private data adapters remain out of scope until material gate approval.

## Consequences

Positive:

- private data can stay local
- storage, backup, and deletion become more reliable
- sensitive import adapters can be added one at a time
- close-friends distribution can be considered later with clearer safety boundaries

Negative:

- implementation becomes more complex
- a local runtime or packaged app may be required
- key management currently uses the approved local `windows-dpapi-file` provider for the Windows + WSL owner environment
- localhost or IPC security must be designed
- dependency review is required before changing encryption/database packages
- public Pages and private companion modes must be kept visibly separate
- plaintext JSON export must be restricted to demo/browser mode
- real data adapters, always-on operation, and distribution packaging are not yet implemented

## Alternatives Considered

### Browser-only IndexedDB

Rejected as long-term sensitive-data storage. It remains acceptable for demo/MVP use.

### Private cloud backend

Deferred. It adds auth, hosting, secret management, incident response, and higher operational risk.

### Full desktop app immediately

Deferred. It may be appropriate after the local companion prototype proves useful.

## Implemented MVP

Implemented under supervisor approval:

- Python local companion on `127.0.0.1`
- bearer-token protected private endpoints
- exact-origin browser bridge for synthetic Launch packets
- application-level encrypted capture records in SQLite
- AES-GCM via installed `cryptography`
- PBKDF2-HMAC-SHA256 with per-vault salt
- passphrase loaded from no-echo prompt or environment variable name
- fail-closed startup when encryption dependency or passphrase is missing
- metadata-only API responses and redacted default status output
- backup-gated passphrase rotation

## Remaining Implementation Gates

Separate approval is still required for:

- installing or changing encryption/database dependencies
- changing vault encryption scheme
- OS keychain storage/retrieval
- passphrase recovery
- real-data import adapters
- packaging or distribution
- screenshot/redaction policy for routine private mode
- clipboard behavior for sensitive summaries
- encrypted backup/delete/restore workflow
- encrypted export/import
- plaintext-to-encrypted migration
- non-loopback or mobile-device network pairing

## Follow-up Actions

1. Add encrypted backup/delete/restore workflow.
2. Add plaintext-to-encrypted migration audit and conversion gate.
3. Add OS keychain storage/retrieval or a formal passphrase recovery policy.
4. Add encrypted export/import.
5. Define adapter-specific policies for contacts, calendar, calls, recordings, and transcripts.
6. Keep GitHub Pages as demo shell only unless a separate private-data deployment decision is approved.
