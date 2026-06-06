# PNH Benchmark Regression Thresholds

Thresholds are generated from existing completed benchmark records. Provisional thresholds warn but should not hard-block until sample count is sufficient.

## bug-triage

- minimum samples for active gate: `3`

| Mode | Status | Samples | Max elapsed min | Min quality | Min operational | Max rework | Max defect |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| supervisor-only | active | 10 | 0.3542 | 19 | 40.38 | 1 | 1 |
| supervisor-central | active | 10 | 0.198 | 23 | 55.25 | 1 | 1 |
| normal-harness | active | 10 | 0.0972 | 24 | 69.45 | 1 | 1 |
| strict-harness | active | 10 | 0.0983 | 27 | 68.72 | 1 | 1 |

## documentation-delivery

- minimum samples for active gate: `3`

| Mode | Status | Samples | Max elapsed min | Min quality | Min operational | Max rework | Max defect |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| supervisor-only | active | 10 | 0.2349 | 19 | 40.38 | 1 | 1 |
| supervisor-central | active | 10 | 0.3049 | 23 | 55.25 | 1 | 1 |
| normal-harness | active | 10 | 0.1483 | 24 | 69.45 | 1 | 1 |
| strict-harness | active | 10 | 0.0914 | 27 | 68.72 | 1 | 1 |

## external-dispatch-dry-run

- minimum samples for active gate: `3`

| Mode | Status | Samples | Max elapsed min | Min quality | Min operational | Max rework | Max defect |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| supervisor-only | active | 10 | 0.3209 | 19 | 40.38 | 1 | 1 |
| supervisor-central | active | 10 | 0.1932 | 23 | 55.25 | 1 | 1 |
| normal-harness | active | 10 | 0.094 | 24 | 69.45 | 1 | 1 |
| strict-harness | active | 10 | 0.096 | 27 | 68.72 | 1 | 1 |

## pnh-local-validation

- minimum samples for active gate: `3`

| Mode | Status | Samples | Max elapsed min | Min quality | Min operational | Max rework | Max defect |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| supervisor-only | active | 13 | 0.2228 | 19 | 40.38 | 1 | 1 |
| supervisor-central | active | 13 | 0.2694 | 23 | 55.25 | 1 | 1 |
| normal-harness | active | 13 | 0.16 | 24 | 69.45 | 1 | 1 |
| strict-harness | active | 13 | 0.0998 | 27 | 68.72 | 1 | 1 |
