# PNH Local Harness Benchmark Report

- run id: `PNH-HARNESS-BENCHMARK-LOCAL-20260605`
- elapsed minutes: `53.186`
- requested duration minutes: `55.0`
- reasoning effort: `medium`
- reasoning policy: `fixed-baseline`
- include playwright: `True`
- cycle count: `60`

## Timing

- supervisor-only mean seconds: `0.112`
- harness-run mean seconds: `8.066`
- harness/supervisor mean ratio: `71.822`

## Failures

- supervisor-only failures: `0`
- harness-run failures: `1`

## Safety

- external writes performed: `False`
- raw private body read: `False`
- private values printed: `False`
- token values printed: `False`

## Interpretation

- verdict: `harness_quality_depth_costs_extra_time`
- note: Harness arm intentionally runs deeper checks; this benchmark measures reliability and overhead, not pure speedup.

## Finding

- cycle 18 failed in `bash scripts/run_playwright_assistant_dispatch_intent_qa.sh`.
- failure type: browser QA state-isolation flake.
- root cause: the Playwright spec did not clear prior `localStorage` and
  `IndexedDB` assistant captures before each run, so repeated benchmark cycles
  could select stale matching cards.
- product impact: no confirmed product payload defect. The issue was in the QA
  harness.
- fix: clear `localStorage`, `sessionStorage`, and
  `personalNotionHubAssistant` IndexedDB at the start of
  `tests/assistant-dispatch-intent.spec.cjs`.
- recheck: `bash scripts/run_playwright_assistant_dispatch_intent_qa.sh` passed
  10 consecutive times after the fix.

## Harness Score

- score: `51.75`
- band: `partial`
- classification: `SUPERVISOR_IMPLEMENTED_EXCEPTION`
- reason: this benchmark used local automated validation rather than real
  subagent implementation lanes.
- penalty: `10` for one replan/rework loop caused by the QA flake.
