# ADR 0001: Local Companion And Encrypted Vault Direction

## Status

Accepted for planning. Not yet approved for implementation.

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

The first companion prototype should use fake fixtures only and should prove health, import preview, and storage boundary behavior before any real private data adapter is added.

## Consequences

Positive:

- private data can stay local
- storage, backup, and deletion become more reliable
- sensitive import adapters can be added one at a time
- close-friends distribution can be considered later with clearer safety boundaries

Negative:

- implementation becomes more complex
- a local runtime or packaged app may be required
- key management must be decided
- localhost or IPC security must be designed
- dependency review is required before encryption/database packages are introduced
- public Pages and private companion modes must be kept visibly separate
- plaintext JSON export must be restricted to demo/browser mode

## Alternatives Considered

### Browser-only IndexedDB

Rejected as long-term sensitive-data storage. It remains acceptable for demo/MVP use.

### Private cloud backend

Deferred. It adds auth, hosting, secret management, incident response, and higher operational risk.

### Full desktop app immediately

Deferred. It may be appropriate after the local companion prototype proves useful.

## Implementation Gates

Implementation requires separate approval for:

- companion runtime and language
- encrypted vault format
- dependency list
- local communication protocol
- real-data import adapters
- packaging or distribution
- screenshot/redaction policy for private mode
- clipboard behavior for sensitive summaries
- encrypted backup and deletion policy

## Follow-up Actions

1. Create a fixture-only companion prototype specification.
2. Compare Python, Node, and desktop-wrapper implementation paths.
3. Define vault schema and migration plan.
4. Define key management options.
5. Define browser QA fixture policy for companion mode.
6. Decide whether GitHub Pages remains enabled as demo shell only.
