# PNH Four-Mode Operation Benchmark

- run id: `PNH-4MODE-BENCHMARK-20260605-SETS3`
- set count: `3`
- mode records: `12`
- operation log: `ops/runs/harness_operation_mode_measurements.jsonl`
- external writes performed: `False`

## Aggregate Timing

- supervisor-only: mean `8.195s`, min `8.174s`, max `8.237s`
- supervisor-central: mean `9.59s`, min `7.889s`, max `12.976s`
- normal-harness: mean `3.906s`, min `3.854s`, max `3.938s`
- strict-harness: mean `3.929s`, min `3.869s`, max `4.004s`

## Interpretation

- Raw wall-clock winner: `normal-harness`.
- Quality-adjusted winner from operation-mode summary: `strict-harness`.
- `supervisor-central` was not consistently faster than `supervisor-only` in this local proxy workload because browser QA still sits on the delegated critical path.
- The useful signal is not agent count. The useful signal is whether specialist lanes remove work from the critical path without adding rework.

## Data Integrity Notes

- All 12 mode records completed with `failureCount=0`.
- External writes were not performed.
- Private body reads and token value printing were not performed.
- Secret-pattern review matches in this run are scanner pattern strings or fixture values, not live secret values.

## Per Set

### PNH-4MODE-BENCHMARK-20260605-001
- fastest mode: `normal-harness`
- highest quality mode: `strict-harness`
- supervisor-only: `8.174s`
- supervisor-central: `7.904s`
- normal-harness: `3.854s`
- strict-harness: `3.869s`

### PNH-4MODE-BENCHMARK-20260605-002
- fastest mode: `strict-harness`
- highest quality mode: `strict-harness`
- supervisor-only: `8.174s`
- supervisor-central: `12.976s`
- normal-harness: `3.927s`
- strict-harness: `3.915s`

### PNH-4MODE-BENCHMARK-20260605-003
- fastest mode: `normal-harness`
- highest quality mode: `strict-harness`
- supervisor-only: `8.237s`
- supervisor-central: `7.889s`
- normal-harness: `3.938s`
- strict-harness: `4.004s`
