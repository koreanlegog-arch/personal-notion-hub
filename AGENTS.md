# AGENTS.md - Personal Notion Hub Project Instructions

This file extends the workspace-level instructions in `/home/koreanlego/projects/AGENTS.md`.
Follow the workspace instructions unless this project-specific file defines a more specific rule.

## Project Context

Personal Notion Hub is a local-first personal command hub and assistant workflow project.
It includes browser UI, local companion services, encrypted local storage, phone ingress,
GitHub/Discord/OpenClaw dispatch rehearsal, and delivery-team automation evidence.

Treat private captures, command bodies, vault data, pairing/session tokens, browser
screenshots, GitHub/Discord metadata, and local runtime configuration as sensitive.

## Approval Gate Override

The human supervisor has delegated routine PNH development, verification, Git checkpoint,
GitHub upload, bounded test/implementation dispatch operations, and bounded
OpenClaw worker/model execution to Codex when they are needed to progress or test
this project.

Do not ask for approval for:

- local code, docs, scripts, templates, tests, or evidence updates inside this project
- smoke tests, browser QA, redacted screenshot QA, and local privacy/security checks
- routine `git add`, `git commit`, and `git push` for scoped PNH work
- Git/GitHub upload checks needed to verify repository sync or delivery evidence
- test-only approval simulations that do not mutate external systems or expose secrets
- local dry-runs and read-only status refreshes
- bounded GitHub Issue, Discord/OpenClaw thread/message, and local dispatch-state
  create/update operations when they are for PNH test, rehearsal, implementation, or
  evidence collection
- unattended dispatch pilot apply runs when they use the existing PNH queue, rate-limit,
  rollback, redaction, and evidence scripts and only dispatch metadata-safe command
  packets
- OpenClaw worker/model execution when it is bounded to a PNH test, rehearsal,
  implementation, QA, review, or evidence task, uses a metadata-safe prompt, does not
  include raw private command bodies, and stores only redacted worker metadata

Proceed through these items autonomously, then report what was done and verified.

## Material Approval Gates

Still ask before work that would materially change risk, cost, external systems, or
private-data exposure.

Approval is required for:

- destructive data operations or irreversible migrations
- storing, printing, committing, or transmitting real private content or secret values
- changing authentication, authorization, encryption policy, or recovery policy
- adding dependencies, package managers, MCP servers, plugins, daemons, schedulers, or
  external services
- modifying real OpenClaw, Discord, Telegram, GitHub, Tailscale, OS keychain, firewall,
  portproxy, or service configuration beyond an already approved runbook step
- dispatching external worker batches that exceed the existing PNH test/implementation
  queue limits, bypass rollback/evidence controls, expose private bodies, or target
  systems outside the approved PNH GitHub/Discord/OpenClaw workflow
- running worker/model tasks with raw private command bodies, secrets, client data,
  unbounded prompts, auto-delivered replies, or actions outside the scoped PNH
  test/implementation workflow
- broad rewrites or architecture direction changes

When a material gate is opened, state why the gate is material and what specific action
will happen after approval.

## Operating Expectations

- Use phase-level progress, not micro-approval.
- If the next step is reversible and within the active PNH phase, continue.
- Prefer dry-run, metadata-safe evidence, and redacted artifacts for external workflow
  rehearsals.
- Never print secret values or raw private command bodies in reports, logs, screenshots,
  commits, or chat.
- Keep final reports concise unless the supervisor asks for a full packet.
