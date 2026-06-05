# PNH Benchmark Regression Thresholds

Thresholds are generated from existing completed benchmark records. Provisional thresholds warn but should not hard-block until sample count is sufficient.

## benchmark-runner-smoke

- minimum samples for active gate: `3`

| Mode | Status | Samples | Max elapsed min | Min quality | Min operational | Max rework | Max defect |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| supervisor-only | provisional | 1 | 0.1863 | 19 | 40.38 | 1 | 1 |
| supervisor-central | provisional | 0 |  |  |  |  |  |
| normal-harness | provisional | 0 |  |  |  |  |  |
| strict-harness | provisional | 0 |  |  |  |  |  |

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

## release-readiness

- minimum samples for active gate: `3`

| Mode | Status | Samples | Max elapsed min | Min quality | Min operational | Max rework | Max defect |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| supervisor-only | provisional | 0 |  |  |  |  |  |
| supervisor-central | active | 10 | 0.2051 | 23 | 55.25 | 1 | 1 |
| normal-harness | active | 10 | 0.1489 | 24 | 69.45 | 1 | 1 |
| strict-harness | active | 10 | 0.1401 | 27 | 68.72 | 1 | 1 |

## security-sensitive-local-storage

- minimum samples for active gate: `3`

| Mode | Status | Samples | Max elapsed min | Min quality | Min operational | Max rework | Max defect |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| supervisor-only | provisional | 0 |  |  |  |  |  |
| supervisor-central | active | 10 | 0.1913 | 23 | 55.25 | 1 | 1 |
| normal-harness | active | 10 | 0.0922 | 24 | 69.45 | 1 | 1 |
| strict-harness | active | 10 | 0.213 | 27 | 68.72 | 1 | 1 |

## unattended-dispatch

- minimum samples for active gate: `3`

| Mode | Status | Samples | Max elapsed min | Min quality | Min operational | Max rework | Max defect |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| supervisor-only | provisional | 0 |  |  |  |  |  |
| supervisor-central | provisional | 0 |  |  |  |  |  |
| normal-harness | active | 10 | 0.1471 | 24 | 69.45 | 1 | 1 |
| strict-harness | active | 10 | 0.1014 | 27 | 68.72 | 1 | 1 |
