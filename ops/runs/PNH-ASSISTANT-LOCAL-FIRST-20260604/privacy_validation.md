# Privacy Validation Evidence - PNH Assistant Local-First Readiness

Run ID: `PNH-ASSISTANT-LOCAL-FIRST-20260604`
Date: 2026-06-04
Scope: Assistant MVP and fixture-only local companion privacy boundary

## 1. Privacy Verdict

Current state is acceptable for fixture-only implementation work and public-safe UI development.

Current state is not approved for real private contacts, schedules, phone records, call contents, recordings, transcripts, or sensitive relationship notes.

## 2. Commands Run

```bash
python3 scripts/companion_smoke_check.py
python3 -m py_compile companion/server.py companion/preview.py scripts/smoke_check.py scripts/companion_smoke_check.py
find . -maxdepth 4 -type f \( -name '*.db' -o -name '*.sqlite' -o -name '*.sqlite3' -o -name '*.vault' -o -name '*.local.json' -o -name '*.backup.json' -o -name '*.log' \) -printf '%p\n' | sort
find companion -maxdepth 2 -type d \( -name private -o -name runtime -o -name logs \) -print
git ls-files -co --exclude-standard -z | ... secret-pattern scan with path/line output only
```

## 3. Results

| Check | Result | Evidence |
| --- | --- | --- |
| Companion smoke | Pass | `companion_smoke_check_pass=true` |
| Python compile | Pass | no compile output, exit code 0 |
| Private artifacts scan | Pass | no `.db`, `.sqlite`, `.sqlite3`, `.vault`, `.local.json`, `.backup.json`, or `.log` files found |
| Private runtime dir scan | Pass | no `companion/private`, `companion/runtime`, or `companion/logs` dirs found |
| Secret candidate scan | Review needed but no confirmed secret | path/line-only candidates were reviewed |

## 4. Secret Candidate Review

The scan intentionally printed only path and line numbers. Findings:

- `assets/js/app.js:65`
- `assets/js/app.js:77`
- `scripts/companion_smoke_check.py:123`
- `scripts/companion_smoke_check.py:125`
- `scripts/companion_smoke_check.py:137`
- `scripts/companion_smoke_check.py:139`

Assessment:

- `assets/js/app.js` findings are false positives caused by demo record identifiers containing text that matches generic token patterns.
- `scripts/companion_smoke_check.py` findings are intentional fake sensitive fixtures used to verify rejection and redaction behavior.
- No real secret, token, credential, private key, or private user data was confirmed.

## 5. Data Flow Assessment

Current public shell:

```text
manual/demo browser input
-> local JavaScript normalization/rules
-> localStorage / IndexedDB
-> copy/export/manual review
```

Current companion prototype:

```text
fake fixture POST
-> 127.0.0.1 preview-only server
-> schema/counts/errors response
-> no writes
```

Observed privacy controls:

- Companion host must be `127.0.0.1`.
- Companion mode is fixture-only preview.
- Companion writes are disabled.
- Companion rejects sensitive-looking fixture values.
- Rejection tests verify sensitive submitted values are not echoed back.
- No vault/database/runtime artifacts were created.
- Current app JS does not use browser `fetch` or `XMLHttpRequest`.

## 6. Required Approval Gates Before Sensitive Mode

Do not proceed without explicit approval for:

- encrypted vault/database write design
- key management and backup/delete policy
- browser-to-companion connection design
- CORS, origin, pairing/session token, and request size limits
- real contacts, calendar, call logs, phone data, recordings, or transcripts
- cloud transcription, cloud sync, external API, OAuth, or token storage
- screenshots or QA logs containing real private data

## 7. Residual Risk

- `localStorage` and `IndexedDB` are not encrypted vaults.
- Fixture-only companion does not yet prove encrypted-vault safety.
- No CORS/pairing/session-token design has been implemented.
- No local companion UI integration exists yet.
- Legal/consent policy for call recordings and transcripts remains unresolved and must be handled before any real call-content workflow.
