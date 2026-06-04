# Security Preflight - PNH Mobile Launch MVP

Run ID: `PNH-MOBILE-LAUNCH-MVP-20260604`
Date: 2026-06-04

## Constraints Applied

- Launch MVP is local-only.
- It generates copyable drafts only.
- It does not send Discord messages.
- It does not create GitHub issues.
- It does not call OpenClaw.
- It does not store tokens or secrets.
- It does not use `fetch` or `XMLHttpRequest`.
- It does not ingest real private data.

## Commands Run

```bash
python3 scripts/companion_smoke_check.py
python3 -m py_compile companion/server.py companion/preview.py scripts/smoke_check.py scripts/companion_smoke_check.py
find . -maxdepth 4 -type f \( -name '*.db' -o -name '*.sqlite' -o -name '*.sqlite3' -o -name '*.vault' -o -name '*.local.json' -o -name '*.backup.json' -o -name '*.log' \) -printf '%p\n' | sort
```

## Results

- Companion smoke passed.
- Python compile passed.
- No private data artifact files were found.
- `.gitignore` excludes Python cache artifacts, local exports, private vault/database files, and secret-like filenames.

## Approval Gates

Explicit approval remains required before:

- automatic Discord dispatch
- GitHub issue creation
- OpenClaw command execution
- browser-to-companion `fetch`
- pairing/session-token design
- real private data in launch packets
- cloud sync or external API

## Residual Risk

- Launch packets are stored in browser `localStorage`; sensitive project briefs should not be entered until private storage is implemented.
- Clipboard copy can expose sensitive text through OS clipboard history.
- Public GitHub Pages mode must remain demo/public-safe.
