# PNH Benchmark Regression Thresholds

Thresholds are generated from existing completed benchmark records. Provisional thresholds warn but should not hard-block until sample count is sufficient.

## pnh-local-validation

- minimum samples for active gate: `3`

| Mode | Status | Samples | Max elapsed min | Min quality | Min operational | Max rework | Max defect |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| supervisor-only | active | 3 | 0.1839 | 19 | 40.38 | 1 | 1 |
| supervisor-central | active | 3 | 0.2379 | 23 | 55.25 | 1 | 1 |
| normal-harness | active | 3 | 0.0883 | 24 | 69.45 | 1 | 1 |
| strict-harness | active | 3 | 0.0882 | 27 | 68.72 | 1 | 1 |
