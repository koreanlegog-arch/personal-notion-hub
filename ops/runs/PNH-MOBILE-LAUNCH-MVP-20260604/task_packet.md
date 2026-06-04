# Task Packet - PNH Mobile Project Launch MVP

Run ID: `PNH-MOBILE-LAUNCH-MVP-20260604`
Date: 2026-06-04
Project: `Personal_Notion_Hub`
Status: implemented

## Objective

Add a local-only MVP that lets the supervisor write a mobile project overview and convert it into a dispatch packet that a home project team can use to start work.

## Scope

- Add a `Launch` navigation view.
- Add mobile-friendly project brief input.
- Generate dispatch packet, Discord draft, and GitHub issue draft.
- Allow local creation of Project and starter Tasks.
- Keep all behavior local-only and dependency-free.
- Document the long-term automation roadmap.

## Out Of Scope

- No actual Discord/GitHub/OpenClaw dispatch.
- No external API.
- No token or secret workflow.
- No private-data vault writes.
- No phone/contact/calendar/call/recording access.
- No dependency installation.

## Acceptance Criteria

- Launch view is reachable from navigation.
- Project title and objective are required.
- Packet can be generated from a project brief.
- Packet includes objective, outcome, constraints, acceptance criteria, lanes, and approval gates.
- Discord and GitHub drafts are copyable.
- Local start creates one project and starter tasks.
- Repeated local start does not duplicate starter tasks.
- Existing smoke check passes.
- No new external network call is introduced in app code.

## Lanes

- product/UX: define mobile launch flow
- implementation: update HTML/CSS/JS
- security: keep external dispatch as approval-gated draft only
- QA: run static smoke and local HTTP asset checks
- release-readiness: decide whether next local-only slice can proceed

## Approval Gates

- actual Discord dispatch
- GitHub issue creation
- OpenClaw command execution
- browser-to-companion `fetch`
- auth/session/pairing
- real private data handling
