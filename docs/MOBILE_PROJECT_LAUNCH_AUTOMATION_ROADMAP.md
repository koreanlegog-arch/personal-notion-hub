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

Automation should be introduced through explicit gates:

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

Current MVP does not:

- send data to Discord
- create GitHub issues
- call OpenClaw
- fetch from local companion
- write encrypted vault data
- handle real private data

## 6. Security And Privacy Constraints

Until separately approved:

- no real private data in launch packets
- no client secrets or tokens
- no automatic external dispatch
- no browser `fetch` to companion
- no cloud sync
- no phone/contact/call/recording access
- no screenshots containing sensitive project contents

If project launch briefs become sensitive, PNH must move from public/static shell mode to a private local companion or authenticated private backend.

## 7. Next Implementation Stages

### Stage 1: Local Packet MVP

Status: implemented.

- Launch view
- packet generation
- local project/task creation
- copy/export drafts

### Stage 2: Local Companion Readiness UI

Add:

- companion status card
- manual probe instructions
- no data transfer by default
- no `fetch` until approved

### Stage 3: Approved GitHub Ledger Bridge

Add after approval:

- create issue from launch packet
- update issue status
- map issue to PNH launch packet
- no token in repo

### Stage 4: Approved Discord/OpenClaw Dispatch

Add after approval:

- dispatch packet to Discord channel
- task ID/thread mapping
- approval channel checks
- result/evidence return path

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

Run the Launch MVP manually from mobile/desktop.

Then implement Stage 2:

```text
Local companion readiness UI
-> show disconnected/connected status
-> explain manual probe command
-> prepare future secure pairing requirements
-> still no private data or automatic fetch
```
