# Release Notes

## 2026-06-05 - Launch Flow Readiness Packet

### Summary

Documented the current owner-operated Launch flow MVP readiness and the usable
capability boundary.

### Included

- `docs/CURRENT_CAPABILITIES.md`
- `ops/runs/PNH-LAUNCH-FLOW-READINESS-20260605/release_readiness.md`
- README update for current Launch dispatch boundaries

### Verdict

Ready for owner-operated MVP use.

Not ready for unattended production automation, real phone data adapters, or
distribution to other users.

## 2026-06-05 - External Reconciliation Planning

### Summary

Added dry-run planning for external metadata reconciliation and Discord/OpenClaw
thread read-refresh capability probing.

### Included

- `scripts/pnh_external_reconciliation_plan.py`
- `scripts/pnh_external_reconciliation_plan_smoke_check.py`
- `scripts/pnh_discord_thread_readiness_probe.py`
- `scripts/pnh_discord_thread_readiness_probe_smoke_check.py`
- `ops/runs/PNH-EXTERNAL-RECONCILIATION-PLAN-20260605/`
- static smoke contracts for both scripts

### Boundaries

- Does not update GitHub labels, state, or comments
- Does not post Discord/OpenClaw messages
- Does not read Discord thread content by default
- Stops at an explicit approval gate before external writes or live Discord reads

### Verification

Recorded in:

- `ops/runs/PNH-EXTERNAL-RECONCILIATION-PLAN-20260605/`

## 2026-06-05 - External Reconciliation Apply

### Summary

Applied the approved GitHub label reconciliation for the verified Launch packet
and implemented metadata-only Discord/OpenClaw thread status refresh.

### Included

- `scripts/pnh_github_label_reconciliation_apply.py`
- `scripts/pnh_github_label_reconciliation_apply_smoke_check.py`
- `scripts/pnh_discord_thread_status_refresh.py`
- `scripts/pnh_discord_thread_status_refresh_smoke_check.py`
- `ops/runs/PNH-GITHUB-LABEL-RECONCILIATION-APPLY-20260605/`
- `ops/runs/PNH-DISCORD-THREAD-STATUS-REFRESH-20260605/`

### Results

- GitHub Issue `#2` now uses `dispatch:worker-done`.
- Discord thread metadata refresh passed without storing message content.
- Reconciliation plan now reports no pending external writes for the verified
  Launch packet.

### Boundaries

- No Discord/OpenClaw messages were posted.
- No worker/model run was started.
- No private command body or message body was stored in evidence.

## 2026-06-05 - Launch Status Sync Browser QA

### Summary

Added Playwright browser QA for confirming redacted dispatch evidence into the
Launch view, browser-local Projects board, and browser-local Tasks board.

### Included

- `tests/launch-status-sync.spec.cjs`
- `scripts/run_playwright_launch_status_sync_qa.sh`
- `ops/runs/PNH-LAUNCH-STATUS-SYNC-QA-20260605/browser_qa.md`
- static smoke contracts for the Launch status sync runner

### Boundaries

- Uses synthetic fixture state only
- Does not contact real companion API, GitHub, Discord, or OpenClaw
- Screenshot artifacts are generated from synthetic data and remain untracked

### Verification

Recorded in:

- `ops/runs/PNH-LAUNCH-STATUS-SYNC-QA-20260605/`

## 2026-06-04 - Phone Ingress MVP

### Summary

Added an explicit private-LAN phone ingress mode so a phone browser can open the
PNH UI from the local companion and send synthetic or low-risk captures into the
workspace private inbox/encrypted vault path.

### Included

- `--enable-phone-ingress` companion flag
- same-origin static UI serving from the companion in phone ingress mode
- private LAN origin validation
- dynamic companion bridge base URL for `http://<LAN_IP>:8765`
- phone ingress smoke check
- LAN info helper
- phone ingress security guide

### Boundaries

- Disabled by default
- Requires private inbox and browser bridge
- Rejects wildcard/public/`localhost`/`0.0.0.0` origins
- Still requires one-time pairing and memory-only browser session token
- No real phone OS adapter, contacts, calls, recordings, calendar, or external service integration

### Verification

Recorded in:

- `ops/runs/PNH-PHONE-INGRESS-MVP-20260604/`

## 2026-06-04 - Redacted Browser QA Runner

### Summary

Added a Playwright-based redacted UI QA test and runner for validating synthetic
Assistant input redaction, browser storage token boundaries, and core viewport
overflow checks.

### Included

- `tests/redacted-ui.spec.cjs`
- `scripts/run_playwright_redacted_ui_qa.sh`
- static smoke contracts for the Playwright runner
- generated browser QA artifacts ignored by Git
- run evidence separating manual browser confirmation from automated runner availability

### Boundaries

- No Playwright/browser download is performed automatically
- If Chromium is unavailable, the runner reports blocked and requests approval for `npx playwright install chromium`
- Screenshot artifacts are generated only from synthetic/redacted data and remain untracked

### Verification

Recorded in:

- `ops/runs/PNH-REDACTED-BROWSER-QA-20260604/`

## 2026-06-04 - Assistant Workspace Ingress MVP

### Summary

Connected Assistant manual inputs to the existing local companion browser bridge
so synthetic or low-risk chat-style inputs can be explicitly sent from the PNH
web UI into the workspace private inbox/encrypted vault path.

### Included

- generic companion bridge `sendCapture` path
- `sendAssistantCapture` wrapper for Assistant inputs
- Assistant `Workspace ingress` panel with status, pairing, redaction, and send-latest controls
- per-capture `Send to Workspace` action
- static smoke contracts for Assistant ingress
- browser bridge smoke extension that stores both launch-style and assistant-style synthetic captures

### Boundaries

- No external mobile/LAN exposure
- No automatic send; every Assistant write requires explicit user action
- No real private data in tests or evidence
- Browser session token remains memory-only

### Verification

Recorded in:

- `ops/runs/PNH-ASSISTANT-WORKSPACE-INGRESS-20260604/`

## 2026-06-04 - Private Data Operations Hardening

### Summary

Implemented the next local-first private data controls for approved sensitive
testing: Windows + WSL DPAPI file passphrase storage, passphrase recovery policy,
backup-gated plaintext migration apply, redacted browser QA contracts, and
real-data adapter privacy gate documentation.

### Included

- `windows-dpapi-file` local passphrase backend using PowerShell DPAPI protected strings
- store/status/delete CLI wrappers that do not print secret values
- provider integration for companion server, inbox initialization/status, backup, restore, delete, rotation, and migration scripts
- passphrase recovery policy documenting that there is no cryptographic recovery mechanism
- plaintext-to-encrypted migration apply gate requiring `MIGRATE_PLAINTEXT_TO_ENCRYPTED` and an existing encrypted backup path
- redacted browser QA static check for screenshot masking and browser token handling boundaries
- real-data adapter privacy gate for contacts, calendar, calls, recordings, transcripts, and external accounts

### Boundaries

- No real passphrase stored by automated tests
- No real private data used in smoke checks or evidence
- No package installation
- No cloud sync, external API adapter, phone adapter, or Telegram/Discord data adapter
- DPAPI blob is local to the current Windows user/machine and is not recovery

### Verification

Recorded in:

- `ops/runs/PNH-PRIVATE-DATA-OPS-HARDENING-20260604/`

## 2026-06-04 - Keychain Backend Design Packet

### Summary

Added a design and approval packet for future OS-backed passphrase persistence.

### Included

- backend comparison for prompt, env, Windows DPAPI file, Windows Credential Manager, Linux Secret Service, and third-party keyring
- recommendation of `windows-dpapi-file` for the current Windows + WSL environment
- explicit rejection of `cmdkey /pass:` for secret input
- approval phrase `APPROVE_PNH_WINDOWS_DPAPI_FILE_BACKEND`
- validation plan requiring synthetic secrets only

### Boundaries

- No actual OS keychain storage/retrieval implementation
- No real passphrase storage
- No package installation
- No real private data in tests or evidence

### Verification

Recorded in:

- `ops/runs/PNH-KEYCHAIN-BACKEND-DESIGN-20260604/`

## 2026-06-04 - Encrypted Vault Passphrase Rotation MVP

### Summary

Added backup-gated encrypted vault passphrase rotation for local vault captures.

### Included

- row-level re-encryption with new vault salt, key ID, and per-row nonces
- explicit `ROTATE_VAULT_PASSPHRASE` confirmation phrase
- existing encrypted backup path acknowledgement before mutation
- dry-run path that counts decryptable rows without changing the DB
- rotation audit event without private title/body/payload values
- smoke check for backup gate, old-passphrase rejection, new-passphrase decrypt, and no secret output

### Boundaries

- No OS keychain storage/retrieval
- No passphrase recovery
- No encryption scheme change
- No plaintext private data in tests or evidence

### Verification

Recorded in:

- `ops/runs/PNH-PASSPHRASE-ROTATION-MVP-20260604/`

## 2026-06-04 - Passphrase Prompt Hardening

### Summary

Added prompt-first passphrase handling and keychain readiness reporting for encrypted vault operations.

### Included

- no-echo prompt provider for vault and backup passphrases
- confirmation prompts for vault initialization and backup creation
- keychain readiness audit that prints capability flags only
- provider smoke check for env/prompt behavior, mismatch rejection, short passphrase rejection, and no secret output
- docs separating implemented prompt handling from future OS keychain storage/retrieval

### Boundaries

- No OS keychain storage/retrieval
- No passphrase recovery; rotation was added in a later same-day MVP
- No package installation or dependency manifest change
- No real private data in tests or evidence

### Verification

Recorded in:

- `ops/runs/PNH-PASSPHRASE-HARDENING-20260604/`

## 2026-06-04 - Encrypted Vault Lifecycle MVP

### Summary

Added encrypted backup, restore, delete, and plaintext migration audit workflows for local encrypted vault captures.

### Included

- encrypted backup envelope creation with schema, algorithm, KDF, salt, nonce, and ciphertext
- encrypted restore from backup into a fresh or existing vault
- duplicate restore skip by default and explicit replace option
- encrypted capture delete by ID with confirmation phrase
- non-sensitive delete audit event
- plaintext migration audit that reports counts and category counts only
- lifecycle smoke checks for backup/restore, delete, and migration audit

### Boundaries

- No plaintext sensitive JSON backup
- No plaintext migration apply/conversion
- No OS keychain storage/retrieval
- No forensic secure erase guarantee
- No real phone/contact/calendar/recording adapters
- No real private data in tests or evidence

### Verification

Recorded in:

- `ops/runs/PNH-VAULT-LIFECYCLE-MVP-20260604/`

## 2026-06-04 - Local Encrypted Vault MVP

### Summary

Added explicit encrypted vault mode for local companion captures so supervisor-approved sensitive test records can be stored in encrypted SQLite rows rather than plaintext private inbox columns.

### Included

- `companion/encrypted_vault.py` with AES-GCM encrypted capture records
- PBKDF2-HMAC-SHA256 key derivation with per-vault salt
- `--enable-encrypted-vault` and `--vault-passphrase-env` companion flags
- prompt-first passphrase options for manual local sessions
- keychain readiness audit without secret storage or secret output
- encrypted private store integration with metadata-only API responses
- encrypted vault initialization option in `scripts/private_inbox_init.py`
- redacted status compatibility for encrypted rows
- encrypted vault smoke check for fail-closed startup, wrong-passphrase rejection, tamper rejection, redacted responses, and plaintext absence in DB bytes
- docs distinguishing plaintext private inbox, encrypted vault MVP, and remaining high-sensitivity blockers

### Boundaries

- No package installation or dependency manifest change
- No OS keychain storage/retrieval yet
- No passphrase recovery yet; rotation was added in a later same-day MVP
- Encrypted capture backup/delete/restore is now implemented in the lifecycle MVP
- Plaintext-to-encrypted migration apply is still not implemented
- No real phone/contact/calendar/recording adapters
- No real private data in tests or evidence

### Verification

Recorded in:

- `ops/runs/PNH-LOCAL-ENCRYPTED-VAULT-MVP-20260604/`

## 2026-06-04 - Browser Companion Bridge

### Summary

Added an explicit loopback browser bridge so the Launch UI can pair with the local companion and write a synthetic dispatch packet to the ignored private inbox.

### Included

- `--enable-browser-bridge` and `--allowed-origin` companion flags
- exact-origin CORS preflight for private browser endpoints
- one-time pairing endpoint issuing memory-only browser session tokens
- isolated `assets/js/companion-bridge.js` fetch module
- Launch UI companion status, pairing, disconnect, send-latest, and screenshot redaction controls
- browser bridge smoke test covering CORS, pairing replay, session write, and redacted responses
- static smoke contract limiting browser `fetch` to the bridge module

### Boundaries

- No external service integration
- No non-loopback/LAN/mobile-device pairing
- No long-lived file token sent to the browser
- No browser persistent storage for auth material
- No real private data
- No encryption-at-rest yet

### Verification

Recorded in:

- `ops/runs/PNH-BROWSER-COMPANION-BRIDGE-20260604/`

## 2026-06-04 - Local Private Inbox MVP

### Summary

Added a working local companion private inbox for proving that phone-like input can reach workspace-local storage.

### Included

- authenticated `/api/private/mobile-captures` write endpoint
- authenticated private inbox summary/list endpoints
- ignored SQLite private inbox storage
- local bearer token initialization script
- synthetic mobile capture sender script
- redacted private inbox status script
- fixture-based private inbox smoke test
- updated docs for local companion, private data policy, security, and testing

### Boundaries

- No external service integration
- No phone/contact/calendar/recording adapter
- No encryption-at-rest yet
- No raw private values in API responses, status output, or test evidence

### Verification

Recorded in:

- `ops/runs/PNH-PRIVATE-INBOX-MVP-20260604/`

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
