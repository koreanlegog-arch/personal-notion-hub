# Security Preflight

## Verdict

Conditional proceed for a script-based mobile-like ingress slice.

Do not implement browser-to-companion `fetch`, CORS, CSP, pairing, or session token UI in this run. Those remain separate approval gates because the current project security docs classify browser companion integration as higher-risk.

## Allowed

- Synthetic project brief body through stdin or local fixture file.
- Existing loopback companion endpoint: `http://127.0.0.1:<port>/api/private/mobile-captures`.
- Existing bearer token file read without printing value.
- Redacted status/evidence only.
- Ignored SQLite private inbox persistence proof.

## Not Allowed

- Real contacts, schedules, call logs, recordings, transcripts, client data, credentials, token values, or actual private notes.
- Browser screenshots containing private-like body text.
- DB dump or raw SQLite row output.
- Token in command output, Markdown, screenshots, localStorage, sessionStorage, IndexedDB, or Git.
- Non-loopback host, redirects, userinfo, path/query/fragment in companion base URL.
- External service dispatch.

## Sidecar Findings Used

- Repo explorer found that current safe path is the existing `simulate_mobile_capture.py -> companion/server.py -> private_store.py` flow.
- Security sidecar flagged browser UI integration as a separate gate because CORS/CSP/pairing/session token design is not yet approved.
- Both sidecars confirmed that `companion/private/` artifacts exist locally and must remain ignored; values were not read.

## Implementer Constraints

- Preserve `build_loopback_endpoint()` restrictions.
- Keep API response metadata-only.
- Add stdin/file input without echoing body text.
- Keep token file default under ignored `companion/private/`.
- Keep validation synthetic-only.

## Validation Checks

- `python3 scripts/private_inbox_smoke_check.py`
- `python3 scripts/smoke_check.py`
- `git ls-files companion/private`
- `git check-ignore -v companion/private/auth_token companion/private/pnh_private_inbox.sqlite`

## Real Sensitive Data

Not allowed in this run.
