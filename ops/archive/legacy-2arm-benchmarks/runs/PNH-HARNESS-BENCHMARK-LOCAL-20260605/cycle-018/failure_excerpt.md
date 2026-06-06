# Cycle 018 Failure Excerpt

## Failed Command

```bash
bash scripts/run_playwright_assistant_dispatch_intent_qa.sh
```

## Failure

Playwright could not find the `Assistant note` badge for the newly inserted
synthetic assistant note.

## Classification

- type: QA harness flake
- product defect confirmed: no
- root cause: browser storage was not isolated between repeated Playwright runs
- fix: clear `localStorage`, `sessionStorage`, and
  `personalNotionHubAssistant` IndexedDB at the start of
  `tests/assistant-dispatch-intent.spec.cjs`

## Recheck

`bash scripts/run_playwright_assistant_dispatch_intent_qa.sh` passed 10
consecutive runs after the fix.
