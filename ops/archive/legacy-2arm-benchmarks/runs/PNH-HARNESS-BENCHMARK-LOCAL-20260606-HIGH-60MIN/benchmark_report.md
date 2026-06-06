# PNH Local Harness Benchmark Report

- run id: `PNH-HARNESS-BENCHMARK-LOCAL-20260606-HIGH-60MIN`
- elapsed minutes: `36.042`
- requested duration minutes: `60.0`
- reasoning effort: `high`
- reasoning policy: `fixed-baseline`
- include playwright: `True`
- cycle count: `200`

## Timing

- supervisor-only mean seconds: `0.114`
- harness-run mean seconds: `9.691`
- harness/supervisor mean ratio: `85.152`

## Failures

- supervisor-only failures: `0`
- harness-run failures: `0`

## Safety

- external writes performed: `False`
- raw private body read: `False`
- private values printed: `False`
- token values printed: `False`

## Interpretation

- verdict: `harness_quality_depth_costs_extra_time`
- note: Harness arm intentionally runs deeper checks; this benchmark measures reliability and overhead, not pure speedup.
