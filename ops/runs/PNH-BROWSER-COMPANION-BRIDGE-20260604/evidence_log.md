# Evidence Log: Browser Companion Bridge

## Metadata

- run_id: `PNH-BROWSER-COMPANION-BRIDGE-20260604`
- project: `Personal_Notion_Hub`
- date: `2026-06-04`
- mode: local-only, synthetic-only
- sensitive_data_used: no
- secrets_recorded: no

## Outcome

Implemented an explicit browser-to-local-companion bridge for the `Launch` view.

The bridge is disabled by default and requires:

- companion private inbox enabled
- `--enable-browser-bridge`
- exact `--allowed-origin http://127.0.0.1:<port>`
- one-time local pairing code
- memory-only browser session token

## Agent Lanes

| Lane | Role | Result |
| --- | --- | --- |
| architecture | read-only sidecar | Confirmed minimal loopback bridge and disjoint implementation slices. |
| security | read-only sidecar | Required exact-origin CORS, one-time pairing, memory-only browser token, and synthetic-only validation. |
| QA | read-only sidecar | Defined acceptance checks for CORS, auth rejection, redaction, and private inbox compatibility. |
| server implementer | implementer slice | Added bridge enable flags, exact-origin CORS, pairing endpoint, in-memory session auth, and server smoke check. |
| browser implementer | implementer slice | Added CSP, isolated bridge fetch module, Launch pairing/send UI, screenshot redaction, and static contracts. |
| supervisor integrator | integration/review | Integrated docs, evidence, verification, and scoring. |

## Files Changed

- `index.html`
- `assets/js/companion-bridge.js`
- `assets/js/app.js`
- `assets/css/styles.css`
- `companion/server.py`
- `scripts/browser_bridge_smoke_check.py`
- `scripts/smoke_check.py`
- `README.md`
- `companion/README.md`
- `docs/SECURITY_NOTES.md`
- `docs/TEST_PLAN.md`
- `docs/PRIVATE_DATA_POLICY.md`
- `docs/LOCAL_COMPANION_ARCHITECTURE.md`
- `docs/MOBILE_PROJECT_LAUNCH_AUTOMATION_ROADMAP.md`
- `docs/RELEASE_NOTES.md`
- `ops/runs/PNH-BROWSER-COMPANION-BRIDGE-20260604/*`

## Security Evidence

- Browser bridge is off unless `--enable-browser-bridge` is provided.
- Browser bridge startup is rejected unless private inbox mode is also enabled.
- Allowed origin must be exact `http://127.0.0.1:<port>`.
- `localhost`, wildcard, `null`, path-bearing origins, and bad origins are rejected by smoke test.
- Browser session token is not written to `localStorage`, `sessionStorage`, IndexedDB, or cookies.
- Long-lived file bearer token remains for local scripts and is not given to the browser.
- Pairing code can be shown in local terminal for manual pairing but is not recorded in this evidence.
- API responses are metadata-only and do not echo synthetic body/title values.
- Launch screenshot redaction masks sensitive launch text and pairing input before screenshots.

## Verification Commands

| Command | Result |
| --- | --- |
| `python3 -m py_compile companion/server.py scripts/smoke_check.py scripts/browser_bridge_smoke_check.py` | pass |
| `python3 -m py_compile companion/server.py companion/private_store.py scripts/browser_bridge_smoke_check.py scripts/private_inbox_smoke_check.py scripts/companion_smoke_check.py scripts/smoke_check.py` | pass |
| `node --check assets/js/app.js && node --check assets/js/companion-bridge.js` | pass |
| `python3 scripts/smoke_check.py` | `smoke_check_pass=true` |
| `python3 scripts/browser_bridge_smoke_check.py` | `browser_bridge_smoke_check_pass=true`; token/session/private response values were not printed |
| `python3 scripts/private_inbox_smoke_check.py` | `private_inbox_smoke_check_pass=true`; token/private response values were not printed |
| `python3 scripts/companion_smoke_check.py` | `companion_smoke_check_pass=true` |
| `rg ... stale browser bridge phrases ...` | first search used unsafe shell backtick quoting and failed with shell `fetch` lookup; rerun with single quotes succeeded |
| `python3 scripts/harness_score_run.py --score-model efficiency ... --write` | score `82.4`, band `useful`, classification `multi-agent-harness` |
| `git ls-files companion/private` | no tracked private inbox files |
| `git check-ignore -v companion/private/auth_token companion/private/pnh_private_inbox.sqlite` | both paths ignored by `.gitignore` |
| `rg -n 'innerHTML\|XMLHttpRequest\(...' assets index.html companion scripts docs ops/runs/...` | only expected contract/code references found; no real secret values printed |
| `git diff --check` | pass |
| `git status --short --branch` | changed files listed for this bridge run only |

## Harness Efficiency Result

- score_model: `efficiency`
- score: `82.4`
- score_band: `useful`
- classification: `multi-agent-harness`
- implementer_slice_count: `2`
- supervisor_direct_implementation_ratio: `0.28`
- penalties: `0`
- model/cost instrumentation: not metered per agent in this run

This score is not a measured speedup against a supervisor-only counterfactual. It is a proxy based on specialist fit, slice count, evidence quality, acceptance pass rate, supervisor implementation ratio, and coordination penalties.

## Not Yet Verified

- Full browser interaction with a real manually entered pairing code was not run in this evidence packet.
- Automated browser QA with screenshots was not run because no Playwright/browser automation dependency is part of this repo.
- Real mobile/LAN pairing was not attempted and remains out of scope.

## Final Status

- implementation_status: complete
- verification_status: pass
- commit_status: pending at time of evidence creation

## Residual Risks

- SQLite private inbox remains unencrypted at rest.
- Browser session token is memory-only, so reload requires re-pairing.
- Screenshot redaction is best-effort UI masking; fixture-only QA remains mandatory for public evidence.
- The bridge endpoint is fixed to `http://127.0.0.1:8765` in the static client for this MVP.
