# Harness Command Packet

## Command

- command_intent: `dispatch`
- trigger: supervisor requested browser companion bridge design and implementation with agent efficiency routing
- requested_by: human supervisor
- created_at: `2026-06-04`
- related_run_id: `PNH-BROWSER-COMPANION-BRIDGE-20260604`

## Goal

- objective: implement a local-only browser companion bridge with exact-origin CORS, one-time pairing, memory-only browser session token, and redacted evidence.
- success_criteria:
  - server bridge is disabled unless explicitly enabled.
  - browser can pair and send a synthetic Launch packet when bridge is enabled.
  - token/session values are not persisted or printed.
  - public/static browser-only behavior remains usable.
  - validation commands pass.
- out_of_scope:
  - real private data
  - external service dispatch
  - non-loopback/LAN/mobile-device access
  - encryption-at-rest
  - dependency installation

## Inputs

- source: supervisor request plus architect/security/QA sidecar findings
- files_or_threads:
  - `ops/runs/PNH-BROWSER-COMPANION-BRIDGE-20260604/task_packet.md`
  - `companion/server.py`
  - `index.html`
  - `assets/js/app.js`
  - `scripts/private_inbox_smoke_check.py`
  - `scripts/smoke_check.py`
- constraints:
  - no wildcard CORS
  - no browser persistent secret storage
  - synthetic-only validation
  - no external dependencies
- sensitive_data_present: no

## Routing

| Lane | Agent | Model/Effort | Status |
| --- | --- | --- | --- |
| architect | sidecar | frontier/high | completed |
| security | sidecar | frontier/xhigh | completed |
| QA | sidecar | standard/medium | completed |
| server implementer | implementer | standard/medium | completed |
| browser implementer | implementer | standard/medium | completed |
| supervisor integrator | supervisor | inherit/medium | completed |

## Side Effects

- allowed_file_writes:
  - server slice: `companion/server.py`, `scripts/browser_bridge_smoke_check.py`
  - browser slice: `index.html`, `assets/js/companion-bridge.js`, `assets/js/app.js`, `assets/css/styles.css`, `scripts/smoke_check.py`
  - integration/docs: `README.md`, `docs/SECURITY_NOTES.md`, `docs/TEST_PLAN.md`, `docs/PRIVATE_DATA_POLICY.md`, `docs/LOCAL_COMPANION_ARCHITECTURE.md`, `docs/MOBILE_PROJECT_LAUNCH_AUTOMATION_ROADMAP.md`, `companion/README.md`, `ops/runs/PNH-BROWSER-COMPANION-BRIDGE-20260604/*`
- allowed_commands:
  - Python syntax checks
  - companion/private/browser bridge smoke checks
  - static smoke checks
  - Git ignore checks
- external_calls_allowed: no
- secrets_required: local ignored token file for existing bearer path only; values must not be printed
- live_config_changes_allowed: no

## Approval Gates

- gate: browser companion bridge
- reason: changes a previously documented prohibition, but supervisor requested this bridge with security design and implementation
- approver: human supervisor
- status: approved under local-only/synthetic-only constraints

- gate: real sensitive data use
- reason: SQLite is not encrypted at rest and screenshot/evidence redaction is not fully automated
- approver: human supervisor
- status: not approved

## Output

- expected_output: local-only browser bridge implementation and evidence packet
- output_path: changed files listed in `evidence_log.md`
- evidence_path: `ops/runs/PNH-BROWSER-COMPANION-BRIDGE-20260604/evidence_log.md`
- redaction_rules:
  - never print token/session/pairing values
  - never store real private content in evidence
  - use synthetic payloads only

## Verification

- command: see `evidence_log.md`
- expected_result: all checks pass or blocked reason recorded
- actual_result: browser bridge, redaction, docs, evidence, and verification completed
- not_run_reason:

## Completion

- status: complete
- residual_risk: browser automation is manual/no Playwright dependency in this run
- follow_up: encryption-at-rest and real mobile/LAN pairing remain separate phases
