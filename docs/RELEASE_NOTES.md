# Release Notes

## 2026-06-04 - Mobile Launch MVP

### Summary

Added a local-only `Launch` view for turning a mobile project brief into a dispatch packet for future team automation.

### Included

- `Launch` navigation item
- mobile project brief form
- dispatch packet generation
- Discord command draft copy
- GitHub issue draft copy
- local Project and starter Task creation
- duplicate-safe local start behavior
- roadmap document for mobile project launch automation

### Boundaries

- No actual Discord/GitHub/OpenClaw dispatch
- No external API
- No token/secret handling
- No real private data ingest
- No dependency installation

### Verification

Recorded in:

- `ops/runs/PNH-MOBILE-LAUNCH-MVP-20260604/`

## 2026-06-03 - Initial Web Release

### Summary

Initial release of `Personal Notion Hub`, a static Notion-style personal operations workspace.

Live URL:

```text
https://koreanlegog-arch.github.io/personal-notion-hub/
```

Repository:

```text
https://github.com/koreanlegog-arch/personal-notion-hub
```

### Included

- Dashboard-first operations hub
- Projects, Tasks, Notes, Routines, Links, Settings
- Quick Capture
- localStorage persistence
- JSON export/import
- Import confirmation and pre-import backup
- `http`/`https` link allowlist
- Project delete unlink handling
- Light/dark theme
- Responsive sidebar and inspector panel
- GitHub Pages workflow deployment
- Static smoke check script

### Verification

Commands:

```bash
python3 scripts/smoke_check.py
node --check assets/js/app.js
python3 -m json.tool data/seed.json
python3 -m http.server 4173
curl -I http://127.0.0.1:4173/
curl -I http://127.0.0.1:4173/assets/css/styles.css
curl -I http://127.0.0.1:4173/assets/js/app.js
curl -I http://127.0.0.1:4173/assets/img/workspace-visual.png
curl -I https://koreanlegog-arch.github.io/personal-notion-hub/
curl -I https://koreanlegog-arch.github.io/personal-notion-hub/assets/css/styles.css
curl -I https://koreanlegog-arch.github.io/personal-notion-hub/assets/js/app.js
curl -I https://koreanlegog-arch.github.io/personal-notion-hub/favicon.ico
```

Results:

- Static smoke check: pass
- JavaScript syntax: pass
- Seed JSON parse: pass
- Local static server assets: 200 OK
- GitHub Pages deployment: success
- Pages URL and core assets: 200 OK

### Agent Review Integration

Parallel agent review found and influenced fixes:

- GitHub Pages deployment boundary required independent repository setup.
- Link URL storage needed `http`/`https` allowlist.
- `localStorage` read/write required exception handling.
- Import needed confirmation and schema validation.
- Task board layout needed safer responsive grid behavior.
- Project deletion needed linked task/note cleanup.

### Known Limitations

- No backend or sync.
- No authentication.
- localStorage is not encrypted.
- Browser automation tests are not installed in the current environment.
- GitHub Actions currently reports a Node.js 20 deprecation annotation for official Pages actions even when Node 24 opt-in is enabled. Deployment succeeds.

### Data Policy

Only demo/sample data is committed. Real personal data should stay in browser localStorage or exported private JSON backups that are not committed.
