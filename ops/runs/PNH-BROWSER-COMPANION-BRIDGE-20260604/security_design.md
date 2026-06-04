# Security Design: Browser Companion Bridge

## Verdict

Proceed under local-only, synthetic-only constraints.

The bridge is allowed only as an explicitly enabled private companion mode. It is not a public Pages sync mechanism and must not handle routine high-sensitivity real data until encryption-at-rest, retention, backup/delete/restore, and screenshot redaction controls are implemented.

## Required Design

### Server

- Bind only to `127.0.0.1`.
- Browser bridge disabled by default.
- Enable bridge only with an explicit flag such as `--enable-browser-bridge`.
- Accept CORS only for an exact configured origin such as `http://127.0.0.1:4173`.
- Never emit `Access-Control-Allow-Origin: *`.
- Reject `Origin: null`, missing origin for browser-only endpoints, `localhost`, non-loopback, and unapproved ports.
- Add `OPTIONS` preflight for the private browser endpoints.
- Require `Content-Type: application/json` and size limits.
- Do not log Origin, Authorization, request body, session token, title, or body.
- The local startup terminal may print the one-time pairing code for manual pairing; do not record it in reports, screenshots, or committed files.

### Pairing And Session

- Long-lived file bearer token remains only for CLI/local script path.
- Browser must not receive or store the long-lived file token.
- Browser gets only a short-lived in-memory session token through one-time pairing.
- Pairing code is short-lived, one-time use, and not stored in tracked files.
- Session token stays in JS memory only and is cleared on reload/disconnect.
- Missing/wrong/expired session returns `401` and does not write to DB.

### Browser

- CSP allows only `connect-src 'self' http://127.0.0.1:8765`.
- Bridge fetch calls live in one isolated file.
- UI does not use localStorage/sessionStorage/IndexedDB for token, pairing code, or session token.
- UI starts writes only on explicit user action.
- UI can disconnect and clear in-memory session state.
- Browser-only fallback remains when companion is offline or disabled.
- UI provides best-effort screenshot redaction for sensitive launch text and pairing input.

### Data And Evidence

- Use synthetic data only for validation.
- API responses remain metadata-only.
- List/status output remains redacted.
- No screenshots with private-like body text.
- No DB dumps in evidence.

## Forbidden

- Real contacts, call logs, recordings, transcripts, schedules, client data, credentials, or actual private notes.
- Wildcard CORS.
- Cookie-based companion auth.
- Persistent browser storage of auth material.
- Non-loopback or LAN access.
- Public Pages bridge to companion without explicit origin/security review.
- External API, OAuth, cloud sync, Discord/GitHub/OpenClaw dispatch.

## Release Gates

Block release if any of these occur:

- browser bridge works without explicit server flag.
- wildcard CORS appears.
- token/session values appear in command output, docs, screenshots, localStorage, sessionStorage, IndexedDB, or Git.
- pairing code appears in committed files, reports, screenshots, browser storage, or evidence logs.
- bad origin can pair or write.
- missing/wrong auth writes to DB.
- private response echoes title/body.
- static smoke cannot isolate allowed fetch usage.

## Validation

- server smoke validates CORS/session/pairing failure modes.
- static smoke validates CSP and controlled fetch only.
- private inbox smoke validates legacy CLI bearer path remains working.
- browser/manual QA validates pair/disconnect/send latest Launch packet and screenshot redaction with synthetic payload only.
