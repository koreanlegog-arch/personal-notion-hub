# PNH Benchmark Model Catalog

This catalog defines benchmark models to collect comparable speed, quality, and supervisor-load data across future harness experiments.

## local-validation-four-mode

- purpose: Measure local syntax, smoke, bridge, queue, and browser QA workload across four operation modes.
- task families: `pnh-local-validation, web-ui-local-validation`
- recommended reasoning: `medium`
- default modes: `supervisor-only, supervisor-central, normal-harness, strict-harness`
- primary metrics: `elapsed_minutes, operational_efficiency_score, quality_adjusted_efficiency`
- when to use: Before changing harness defaults or after QA automation changes.

## docs-review-four-mode

- purpose: Compare documentation/template work where planning, writing, review, and evidence collection can split naturally.
- task families: `documentation-delivery, template-maintenance, runbook-maintenance`
- recommended reasoning: `medium`
- default modes: `supervisor-only, supervisor-central, normal-harness, strict-harness`
- primary metrics: `elapsed_minutes, total_quality_score, rework_count`
- when to use: When tuning harness behavior for docs-heavy operations.

## security-sensitive-change-four-mode

- purpose: Measure security-preflight, implementation, review, and validation separation for sensitive local storage/auth work.
- task families: `security-sensitive-local-storage, auth-boundary-change, secret-handling-workflow`
- recommended reasoning: `high`
- default modes: `supervisor-only, supervisor-central, normal-harness, strict-harness`
- primary metrics: `defect_count, security_risk_handling_score, quality_adjusted_efficiency`
- when to use: Before accepting sensitive-data MVP changes or modifying auth/encryption behavior.

## external-dispatch-dry-run-four-mode

- purpose: Compare ledger, Discord/OpenClaw, and queue dispatch dry-runs without live side effects.
- task families: `external-dispatch-dry-run, ledger-sync-dry-run, chatops-dispatch-dry-run`
- recommended reasoning: `medium`
- default modes: `supervisor-only, supervisor-central, normal-harness, strict-harness`
- primary metrics: `elapsed_minutes, cross_mode_contamination, evidence_quality`
- when to use: Before enabling live dispatch, GitHub issue mutation, or Discord thread updates.

## incident-debug-four-mode

- purpose: Compare diagnosis speed and fix quality for failing tests, port conflicts, race conditions, and integration defects.
- task families: `bug-triage, browser-qa-failure, integration-debug`
- recommended reasoning: `high`
- default modes: `supervisor-only, supervisor-central, normal-harness, strict-harness`
- primary metrics: `elapsed_minutes, rework_count, defect_count, verification_depth_score`
- when to use: When failures recur or harness routing may reduce debugging time.

## release-readiness-four-mode

- purpose: Compare release packet, QA checklist, security gate, evidence summary, and handoff review distribution.
- task families: `release-readiness, client-handoff, delivery-gate`
- recommended reasoning: `high`
- default modes: `supervisor-only, supervisor-central, normal-harness, strict-harness`
- primary metrics: `total_quality_score, evidence_report_score, supervisor_direct_implementation_ratio`
- when to use: Before external handoff, deployment readiness decisions, or pilot release.

## long-run-unattended-four-mode

- purpose: Measure sustained queue processing, rollback behavior, rate-limit behavior, and failure recovery over longer unattended runs.
- task families: `unattended-dispatch, queue-processing, rollback-recovery`
- recommended reasoning: `medium`
- default modes: `supervisor-only, supervisor-central, normal-harness, strict-harness`
- primary metrics: `defect_count, rework_count, stop_condition_triggered, elapsed_minutes`
- when to use: Only when the user explicitly starts a longer benchmark window.
