# Harness Command Packet

## Command

- command_intent: `implement`
- trigger: supervisor requested the next PNH input flow through `HARNESS_COMMAND_REGISTRY.md`
- requested_by: human supervisor
- created_at: `2026-06-04`
- related_run_id: `PNH-MOBILE-LIKE-COMPANION-INGRESS-20260604`

## Goal

- objective: add a safe mobile-like input path that sends stdin/file content into the local companion private inbox.
- success_criteria:
  - stdin/file body input works.
  - token is read from local ignored token file and never printed.
  - loopback endpoint restrictions remain enforced.
  - smoke checks pass.
  - evidence records actual commands and no fake speedup claim.
- out_of_scope:
  - browser fetch/CORS/pairing
  - real sensitive data
  - external service dispatch
  - encryption dependency

## Inputs

- source: supervisor request and sidecar preflight findings
- files_or_threads:
  - `scripts/simulate_mobile_capture.py`
  - `scripts/private_inbox_smoke_check.py`
  - `README.md`
  - `docs/TEST_PLAN.md`
- constraints:
  - synthetic data only
  - no token values in output or docs
  - no browser integration without separate approval
- sensitive_data_present: no

## Routing

- owner: supervisor-local implementer
- agent_or_skill: `task-packet-authoring`, `security-preflight`, `evidence-collection`, `harness-evaluation`
- model_tier: inherit for implementation, economy/low repo-explorer sidecar, frontier/high security sidecar
- reasoning_effort: medium for implementation, high for security sidecar
- expected_duration: short bounded slice

## Side Effects

- allowed_file_writes:
  - `scripts/simulate_mobile_capture.py`
  - `scripts/private_inbox_smoke_check.py`
  - `README.md`
  - `docs/TEST_PLAN.md`
  - `ops/runs/PNH-MOBILE-LIKE-COMPANION-INGRESS-20260604/*`
- allowed_commands:
  - Python syntax checks
  - private inbox smoke check
  - static smoke check
  - local companion synthetic capture test
- external_calls_allowed: no
- secrets_required: local token file existence only; value must not be printed
- live_config_changes_allowed: no

## Approval Gates

- gate: browser fetch/CORS/pairing
- reason: existing security docs classify browser companion integration as separate approval gate
- approver: human supervisor
- status: not approved for this run

## Output

- expected_output: stdin/file mobile-like capture path and validation evidence
- output_path: changed files listed in evidence log
- evidence_path: `ops/runs/PNH-MOBILE-LIKE-COMPANION-INGRESS-20260604/evidence_log.md`
- redaction_rules:
  - do not print token values
  - do not store real private text in evidence
  - use synthetic payload only

## Verification

- command: see `evidence_log.md`
- expected_result: all checks pass
- actual_result: pending
- not_run_reason:

## Completion

- status: in progress
- residual_risk: efficiency critical-path reduction remains estimated, not A/B proven
- follow_up: browser companion bridge requires separate approval and security design
