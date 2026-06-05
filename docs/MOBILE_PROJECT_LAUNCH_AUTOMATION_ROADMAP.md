# Mobile Project Launch Automation Roadmap

Status: active direction document
Date: 2026-06-04

## 1. Goal

`Personal_Notion_Hub`의 장기 목표는 단순 개인 일정/루틴 관리가 아니다.

최종 목표는 다음 흐름이다.

```text
mobile user writes a project brief
-> Personal_Notion_Hub turns it into a dispatch packet
-> home project team reads the packet
-> AI Delivery Operating System routes work
-> workers execute, review, QA, security-check, and report
-> result and evidence return to the hub
```

The hub should become the supervisor's mobile command intake surface.

## 2. Product Role

PNH should own:

- mobile project intake
- project brief normalization
- acceptance criteria draft
- initial work slicing draft
- team dispatch packet
- local project/task creation
- status and evidence review
- supervisor approval history

PNH should not directly own, in the public/static mode:

- secret storage
- real private data vault
- automatic Discord/GitHub/OpenClaw execution
- cloud sync
- phone/contact/call/recording access
- production deployment decisions

## 3. System Direction

Recommended architecture:

```text
PNH mobile web UI
-> launch packet generator
-> local companion or approved backend bridge
-> GitHub Issues/Projects ledger
-> Discord/OpenClaw worker control plane
-> Codex/agent harness
-> evidence and status returned to PNH
```

Near-term PNH remains static/local-only. It generates packets and copy/export drafts.

Automation should be introduced through material gates:

1. local packet generation
2. local project/task creation
3. manual copy to Discord/GitHub
4. approved local companion bridge
5. approved GitHub issue creation
6. approved Discord/OpenClaw dispatch
7. status/evidence sync back into PNH

## 4. Required Capabilities

### Intake

- mobile-friendly project brief form
- objective, desired outcome, constraints, deadline, priority, sensitivity
- out-of-scope and approval gate capture

### Packet Generation

- task packet
- Discord dispatch draft
- GitHub issue draft
- acceptance criteria draft
- suggested lanes
- approval gates

### Ledger

- localStorage/local export for MVP
- future GitHub Issues/Projects bridge
- task IDs and status history

### Worker Dispatch

- Discord/OpenClaw command draft for MVP
- future approved dispatch adapter
- supervisor approval channel before external action

### Evidence Return

- QA/security/release-readiness status
- worker result summary
- residual risk
- final handoff note

## 5. MVP Implemented In This Pass

Added `Launch` view.

Current MVP supports:

- mobile-friendly project brief form
- local dispatch packet generation
- copyable dispatch packet
- copyable Discord command draft
- copyable GitHub issue draft
- local creation of a Project plus starter Tasks
- duplicate-safe local start behavior
- local-only storage

Current public/static MVP does not:

- send data to Discord
- create GitHub issues
- call OpenClaw
- directly store private data in the public browser shell

Private companion mode now supports encrypted vault capture and owner-only tailnet ingress. That private data plane is separate from public/static mode.

## 6. Security And Privacy Constraints

Current material gates:

- no real private data in public/static launch packets
- no client secrets or tokens
- no automatic external dispatch
- no browser `fetch` to companion outside the approved exact-origin local/tailnet bridge
- no cloud sync
- no phone/contact/call/recording access
- no screenshots, logs, or evidence containing sensitive project contents

If project launch briefs become sensitive, PNH must move from public/static shell mode to a private local companion or authenticated private backend.

## 7. Next Implementation Stages

### Stage 1: Local Packet MVP

Status: implemented.

- Launch view
- packet generation
- local project/task creation
- copy/export drafts

### Stage 2: Local Companion Readiness UI

Status: implemented for owner-only local/tailnet bridge and encrypted capture.

Implemented:

- companion status card
- one-time pairing UI
- send latest Launch packet to local private inbox
- no data transfer before explicit user action
- screenshot redaction toggle
- browser automation QA
- encrypted vault
- real mobile/LAN pairing decision
- Tailscale owner-only phone ingress rehearsal

### Stage 3: Approved GitHub Ledger Bridge

Status: first privacy-preserving live issue rehearsal completed.

Implemented inside the approved local/private boundary:

- command type field for mobile Launch intake
- `pnh_mobile_command_packet` payload for companion writes
- queued/not-dispatched metadata for future routing
- privacy-preserving GitHub Issue payload dry-run
- apply-mode approval flags for future live issue creation
- approved live GitHub issue creation without raw private body
- GitHub issue comment linked to Discord/OpenClaw dispatch rehearsal

Still pending:

- update issue status
- map issue to PNH launch packet
- no token in repo remains enforced
- dedupe and repeated ledger update strategy

Reference:

- `docs/GITHUB_LEDGER_BRIDGE_DESIGN.md`
- `scripts/github_ledger_bridge.py`
- `ops/runs/PNH-GITHUB-LEDGER-BRIDGE-20260605/`

### Stage 4: Approved Discord/OpenClaw Dispatch

Status: first controlled Discord/OpenClaw routing rehearsal completed.

Implemented:

- OpenClaw Discord thread creation in `#command-center`
- worker lifecycle rehearsal messages
- `#audit-log` mapping message
- GitHub issue comment linking ledger and Discord thread

Still pending:

- automatic dispatch job from PNH local command packet
- durable mapping stored back into PNH local state
- real OpenClaw worker-session execution and result capture
- gateway auth/sandbox hardening follow-up

### Stage 5: Full Supervisor Mobile Loop

Add:

- mobile project intake
- automated dispatch
- worker progress status
- review/QA/security evidence
- final supervisor approval
- archived handoff package

## 8. Open Decisions

- Whether PNH remains static GitHub Pages plus local companion, or moves to private authenticated app for mobile multi-device sync.
- Whether GitHub Issues or PNH-local ledger is the primary durable source of truth.
- Whether Discord/OpenClaw dispatch should be manual-copy, local companion-driven, or server-driven.
- How to authenticate mobile supervisor actions safely.
- How to separate private project briefs from public demo artifacts.

## 9. Recommended Next Step

Run GitHub ledger bridge apply only after approving the external write gate.

Then implement Stage 2:

```text
Local companion readiness UI
-> show disconnected/connected status
-> pair through one-time local terminal code
-> send synthetic launch packet to private inbox
-> keep real private data blocked until vault hardening
```
