# Harness Retrospective: Local Benchmark 2026-06-05

## Summary

This benchmark ran 60 local cycles over about 53.2 minutes.

The supervisor-only arm ran lightweight syntax/static/queue checks. The
harness-run arm ran deeper checks including browser bridge smoke, queue
planning, Assistant dispatch intent Playwright QA, and redacted UI Playwright
QA.

## Results

- supervisor-only cycles: `60`
- supervisor-only failures: `0`
- supervisor-only mean: `0.112s`
- harness-run cycles: `60`
- harness-run failures: `1`
- harness-run mean: `8.066s`
- harness/supervisor mean ratio: `71.822`
- external writes: `false`
- private values printed: `false`
- token values printed: `false`
- raw private body read: `false`

## Finding

The benchmark found one useful defect in the QA harness:

- failed cycle: `18`
- failing command: `bash scripts/run_playwright_assistant_dispatch_intent_qa.sh`
- cause: browser storage was not isolated between repeated Playwright runs
- fix: clear `localStorage`, `sessionStorage`, and
  `personalNotionHubAssistant` IndexedDB before the spec starts
- follow-up check: Assistant dispatch intent Playwright QA passed `10/10`
  consecutive runs after the fix

## Efficiency Interpretation

This run does not prove harness-run is faster. It proves the opposite for this
task shape: deeper harness validation has measurable overhead.

However, the overhead bought useful reliability evidence. The repeated
Playwright lane found a state-contamination flake that a single direct smoke
path would likely miss.

## Score

- score model: `efficiency`
- score: `51.75`
- band: `partial`
- classification: `SUPERVISOR_IMPLEMENTED_EXCEPTION`
- penalty: `10` for one replan/rework loop

## Next Benchmark Rule

For future benchmark runs:

- use browser-storage isolation in every Playwright spec that creates app data
- keep supervisor-only and harness-run scopes closer if measuring speed
- use harness-run when reliability or browser-state flake detection matters
- avoid claiming speedup unless both arms have comparable validation depth
