# PNH Unattended Remote Command Plan

Date: 2026-06-06

## Summary

Current PNH mobile access proves that a phone can pair, submit captures, and
create dispatch records. It does not yet satisfy the intended operating model:
the owner should be able to leave the computer, open the phone, submit a command,
and have the local workspace progress through dispatch, worker execution,
evidence, and status reporting without terminal interaction.

Two design defects block that operating model:

1. The browser pairing flow depends on a one-time code printed to the local
   terminal. That proves local possession, but it also makes remote use
   impossible unless the owner is physically at the computer.
2. The post-capture workflow still depends on manual terminal commands for
   dispatch application, worker-session capture, semantic progress parsing, and
   completion audit recovery.

## Current Architecture

### Mobile browser path

```text
phone browser
-> Tailscale tailnet URL
-> Windows portproxy
-> WSL companion server
-> browser pairing code from terminal
-> memory-only browser session token
-> /api/private/mobile-captures
-> encrypted local vault
```

Strengths:

- local-first and owner-tailnet scoped
- exact origin checks
- encrypted vault storage
- no raw private body in command output or tracked evidence
- one-time pairing and memory-only session minimize persistent browser secret risk

Weaknesses:

- terminal-visible pairing code is incompatible with remote unattended use
- session token is memory-only, so every restart/new phone context needs local
  terminal access again
- UI send success does not imply dispatch/worker completion

### Dispatch path

```text
encrypted private inbox
-> queue plan
-> pnh_auto_dispatch_from_inbox apply
-> GitHub Issue
-> Discord/OpenClaw thread
-> dispatch state
-> worker-session capture
-> semantic progress parse
-> evidence summary
-> completion audit
```

Strengths:

- metadata-safe dispatch
- duplicate dispatch prevention
- GitHub/Discord/OpenClaw evidence exists
- queue, rollback, and rate-limit foundations exist

Weaknesses:

- scheduler tick is mostly observational and dry-run oriented
- new dispatched records can sit at `67%` evidence completeness until a terminal
  command captures worker-session evidence
- completion audit drops from ready state while worker evidence is incomplete
- owner receives no reliable remote status loop unless manually checking

## Proposed Architecture

### Target flow

```text
owner phone
-> trusted owner authentication
-> command capture
-> encrypted vault write
-> bounded auto-dispatch
-> worker orchestration
-> semantic progress/evidence update
-> supervisor status notification
```

The owner should only intervene when:

- the command is ambiguous or blocked
- a material approval gate is reached
- a privacy/security gate fails
- the system needs credential rotation or service repair

## Authentication Plan

### Phase 1: Remote pairing delivery without terminal dependence

Goal: remove the immediate contradiction while preserving existing pairing
semantics.

Change:

- Keep one-time pairing code and short TTL.
- Add an owner-only remote pairing handoff path that can send or expose the
  pairing code through an approved owner channel instead of only stdout.
- Acceptable channels:
  - owner-only Discord DM or locked `#approvals`
  - Telegram alert channel if later enabled
  - local private handoff file consumed by an already-approved bot/gateway

Security controls:

- pairing code remains one-time and short-lived
- code is never committed
- code is not written to tracked evidence
- channel must be allowlisted to owner identity
- pairing event is logged metadata-only: issuedAt, expiresAt, deliveryChannel,
  usedAt, client label, no code value

Implementation shape:

- `companion/server.py`: emit pairing events to an ignored runtime file when
  configured, not just stdout
- `scripts/pnh_remote_pairing_handoff.py`: read latest pairing metadata and
  deliver or summarize via owner-approved channel
- `scripts/pnh_remote_pairing_handoff_smoke_check.py`
- docs update in `TAILSCALE_REMOTE_ACCESS_RUNBOOK.md`

This is a quick fix, not the final identity model.

### Phase 2: Persistent owner device session

Goal: daily remote use should not require pairing every time.

Change:

- After successful pairing, issue a scoped owner-device refresh credential.
- Store only a hash/server-side metadata in `companion/private/`.
- Store the client credential only on the owner's phone browser/PWA context.
- Use short-lived browser session tokens derived from the refresh credential.

Suggested scopes:

- `capture:write`
- `dispatch:intent`
- `status:read`
- no raw vault read
- no secret read
- no destructive operations

Security controls:

- token rotation
- explicit revoke command
- device label
- lastSeenAt metadata
- max age, for example 14-30 days
- tailnet origin requirement
- CSP remains strict
- no third-party JS

Risk:

- ordinary browser storage is weaker than OS keychain. This is acceptable only
  inside owner-only Tailscale MVP if the token has narrow scopes and can be
  revoked. For stronger long-term posture, move to WebAuthn/passkeys or a
  native wrapper.

### Phase 3: Strong owner identity

Goal: replace long-lived browser secrets with stronger identity.

Options:

- WebAuthn/passkey for browser UI
- Tailscale identity-aware access if available and compatible
- native mobile wrapper using OS secure storage
- Telegram/Discord approval only for high-risk gates, not for every command

Recommended later target:

- WebAuthn/passkey for browser sign-in
- Tailscale for network boundary
- local encrypted vault remains storage boundary

## Automation Plan

### Phase 1: Capture-to-dispatch automation

Goal: once a mobile command packet is stored, dispatch should happen without
manual terminal commands.

Change:

- Extend scheduler with an apply lane:
  - find queue candidate
  - apply `pnh_unattended_dispatch_pilot.py --apply`
  - enforce queue limit, lock, duplicate detection, rollback snapshot
  - no raw private body in prompt, GitHub issue, Discord thread, or evidence

New/changed artifacts:

- `scripts/pnh_unattended_orchestrator.py`
- `scripts/pnh_unattended_orchestrator_smoke_check.py`
- `scripts/pnh_scheduler_tick.py` job: `unattended-dispatch-apply`
- ignored runtime evidence under `companion/private/scheduler/`
- tracked metadata summary under `ops/runs/PNH-UNATTENDED-ORCHESTRATOR-*`

### Phase 2: Dispatch-to-worker automation

Goal: dispatched records should not stall at `67%` evidence completeness.

Change:

- Add a worker-capture lane:
  - find dispatch records missing `worker_session`
  - generate metadata-safe worker prompt from dispatch state, not private body
  - run bounded OpenClaw worker capture
  - record worker session metadata
  - parse semantic progress
  - update dispatch evidence

New/changed artifacts:

- `scripts/pnh_dispatch_worker_completion_orchestrator.py`
- worker prompt template that explicitly excludes raw private body
- smoke checks for no secret/private value leakage
- scheduler job: `dispatch-worker-completion`

### Phase 3: Completion/status loop

Goal: the owner sees whether the system accepted, dispatched, completed, or
blocked the command without opening a terminal.

Change:

- After each automation tick:
  - run dispatch evidence summary
  - run completion audit
  - post metadata-only status to owner-approved Discord/Telegram channel
  - optionally update UI local status on next browser refresh

Status labels:

- `stored`
- `queued`
- `dispatched`
- `worker_running`
- `worker_done`
- `blocked`
- `needs_supervisor_approval`
- `privacy_gate_failed`

## Service Plan

Current services should be split by responsibility:

1. `pnh-companion.service`
   - stable headless API on `127.0.0.1:8765`
   - encrypted vault
   - no browser bridge
   - phone automation API target

2. `pnh-browser-session.service` or Tailscale Serve profile
   - owner browser UI on tailnet
   - browser bridge enabled
   - should not require terminal-visible code after persistent device setup

3. `pnh-scheduler.timer`
   - observational checks
   - apply lane only when enabled by project policy and rate limits

4. `pnh-worker-orchestrator.timer`
   - dispatch-to-worker evidence completion loop
   - bounded concurrency
   - metadata-only prompts

## Recommended Implementation Order

### Slice 1: Remote pairing handoff quick fix

Purpose:

- allow pairing when the owner is away from the computer

Expected result:

- terminal code is no longer the only way to pair
- pairing code delivery is owner-channel based and metadata-audited

Risk:

- Medium, because it changes auth UX

Validation:

- smoke test: code not written to tracked files
- smoke test: expired/used code rejected
- remote handoff evidence contains no code value

### Slice 2: Auto-dispatch apply lane

Purpose:

- remove manual terminal dispatch after mobile send

Expected result:

- command packet moves from encrypted inbox to GitHub/Discord dispatch without
  owner terminal commands

Risk:

- Medium, because it performs bounded external writes

Validation:

- fixture queue
- dry-run no writes
- apply with one candidate
- duplicate dispatch prevention
- rollback snapshot

### Slice 3: Worker completion lane

Purpose:

- prevent dispatched records from stalling at `67%`

Expected result:

- worker session metadata is captured automatically
- semantic progress fields are populated
- evidence completeness returns to `100%`

Risk:

- Medium, because it uses OpenClaw worker/model execution

Validation:

- metadata-safe prompt check
- no raw private body
- worker result recorded
- semantic progress parsed
- completion audit recovers

### Slice 4: Persistent owner device session

Purpose:

- stop repeated pairing for routine remote use

Expected result:

- owner phone can reconnect without terminal code within approved TTL
- device can be revoked

Risk:

- High, because it changes authentication behavior

Validation:

- token hash only server-side
- refresh token not printed
- revocation works
- expired token rejected
- status endpoint exposes metadata only

### Slice 5: Remote status/approval notifications

Purpose:

- owner receives command status without terminal checks

Expected result:

- mobile command lifecycle is visible from Discord/Telegram/UI

Risk:

- Low to Medium, depending on channel and payload

Validation:

- no private body in notification
- status transitions correct
- material gates still stop and request approval

## Alternatives Considered

### Keep terminal pairing

Rejected. It is secure but contradicts remote command operation.

### Make browser session token permanent in localStorage immediately

Rejected as the first step. It is fast but weakens the current security model
too abruptly. Use it only as a scoped, revocable owner-device credential after
explicit design and tests.

### Public cloud auth and hosted backend

Deferred. It may solve remote identity, but it changes exposure, cost, and
security posture. Not needed for owner-only MVP while Tailscale works.

### Telegram-only control

Deferred. Telegram is useful for alerts, but Discord/OpenClaw/GitHub are already
the dispatch ledger/control-plane path. Telegram should be optional notification
or approval fallback, not the primary worker ledger.

## Current Immediate Finding

The latest mobile test shows:

- mobile encrypted captures increased to `23`
- plaintext rows remain `0`
- two new `task_request` records reached GitHub/Discord dispatch
- those two records are currently missing worker-session evidence
- completion audit is expected to stay below `17/17` until worker completion
  automation records results

This confirms the capture and dispatch front half works. The missing automation
is now the back half: worker execution, progress parsing, evidence, and status
notification.

## Approval Gates

Already delegated within PNH:

- bounded GitHub/Discord dispatch for PNH metadata-safe command packets
- bounded OpenClaw worker/model execution for PNH evidence tasks
- local helper scripts, scheduler checks, commits, pushes

Material gates still required:

- persistent owner-device auth rollout
- changing token storage or browser secret persistence policy
- public/cloud exposure
- multi-user distribution
- raw private body use in worker prompts
- destructive data operations

## Recommended Next Action

Implement Slice 2 and Slice 3 first:

1. `pnh_unattended_orchestrator.py`
2. `pnh_dispatch_worker_completion_orchestrator.py`
3. scheduler integration in dry-run first, then bounded apply
4. evidence and completion audit recovery

Then implement Slice 1 remote pairing handoff, followed by Slice 4 persistent
owner-device session. This order fixes the automation bottleneck immediately
while keeping the authentication risk isolated for a deliberate patch.
