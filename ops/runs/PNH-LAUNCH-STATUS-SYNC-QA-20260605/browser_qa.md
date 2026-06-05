# Browser QA Evidence - PNH Launch Status Sync

Date: 2026-06-06

## Scope

Validate that redacted dispatch state can be refreshed into the Launch view and then confirmed into browser-local Launch, Projects, and Tasks records.

This follow-up run also validates that the command packet status surface shows
the current stage as a user-visible rail: `Inbox -> Ledger -> Thread -> Worker
-> Review`.

This QA uses synthetic fixture state only. It does not contact the real companion API, GitHub, Discord, or OpenClaw.

## Scenario

1. Start local static server through `scripts/run_playwright_launch_status_sync_qa.sh`.
2. Seed browser `localStorage` with one synthetic Launch packet that references the dispatched packet id.
3. Replace `window.PNHCompanionBridge.dispatchState()` with a metadata-only fixture.
4. Open Launch.
5. Run `Check` to put the UI into paired state.
6. Run `Refresh Status`.
7. Assert the command packet status card shows the `Review ready` stage and all
   five stage rail labels.
8. Confirm mapping.
9. Confirm task status.
10. Assert browser-local Launch, Projects, and Tasks records reflect
    `worker_done` and `evidenceCompleteness=100`.

## Result

Pass.

Evidence:

- `playwright_launch_status_sync_qa_pass=true`
- command: `NODE_PATH=/home/koreanlego/.npm/_npx/420ff84f11983ee5/node_modules npx -p @playwright/test playwright test tests/launch-status-sync.spec.cjs --reporter=line`
- screenshot artifact: `ops/runs/PNH-LAUNCH-STATUS-SYNC-QA-20260605/artifacts/launch-status-sync-desktop.png`
- server log: `ops/runs/PNH-LAUNCH-STATUS-SYNC-QA-20260605/artifacts/http-server.log`

## Findings

- First QA attempt found that `Refresh Status` remains disabled until the UI's paired state is updated. The test now follows the real user flow by clicking `Check` before refresh.
- Second QA attempt found an overly broad locator in the test because `Task worker_done` appears in both the status panel and Launch card. The test now scopes assertions to the Launch item card.
- This follow-up QA found additional strict locator ambiguity after adding the
  visible stage rail because `Review ready` and `Worker` appear in multiple
  places. The test now scopes assertions to `.operator-action-banner` and
  `.command-packet-stage-rail`.

## Residual Risk

- This is fixture-based browser QA. The real companion bridge path is separately covered by companion/browser bridge smoke tests.
- Screenshot artifacts are generated from synthetic data and remain untracked.
