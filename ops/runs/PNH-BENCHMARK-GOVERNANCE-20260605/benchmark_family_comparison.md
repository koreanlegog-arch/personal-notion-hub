# PNH Benchmark Family Comparison

- generated at: `2026-06-05T16:43:45+00:00`
- source log: `ops/runs/harness_operation_mode_measurements.jsonl`
- completed usable records: `253`
- minimum samples per active threshold: `3`

## benchmark-runner-smoke

- fastest mode: `supervisor-only`
- best operational efficiency mode: `supervisor-only`
- best quality-adjusted mode: `supervisor-only`
- lowest supervisor load mode: `supervisor-only`

| Mode | Samples | Median elapsed min | Operational efficiency | Quality adjusted | Quality score | Supervisor ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| supervisor-only | 1 | 0.138 | 47.5 | 152.2 | 21 | 1 |
| supervisor-central | 0 |  |  |  |  |  |
| normal-harness | 0 |  |  |  |  |  |
| strict-harness | 0 |  |  |  |  |  |

## bug-triage

- fastest mode: `normal-harness`
- best operational efficiency mode: `normal-harness`
- best quality-adjusted mode: `strict-harness`
- lowest supervisor load mode: `strict-harness`

| Mode | Samples | Median elapsed min | Operational efficiency | Quality adjusted | Quality score | Supervisor ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| supervisor-only | 10 | 0.1514 | 47.5 | 138.7 | 21 | 1 |
| supervisor-central | 10 | 0.1467 | 65 | 170.4 | 25 | 0.65 |
| normal-harness | 10 | 0.072 | 81.7 | 361.4 | 26 | 0.35 |
| strict-harness | 10 | 0.0728 | 80.85 | 398.1 | 29 | 0.15 |

## documentation-delivery

- fastest mode: `strict-harness`
- best operational efficiency mode: `normal-harness`
- best quality-adjusted mode: `strict-harness`
- lowest supervisor load mode: `strict-harness`

| Mode | Samples | Median elapsed min | Operational efficiency | Quality adjusted | Quality score | Supervisor ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| supervisor-only | 10 | 0.1409 | 47.5 | 149 | 21 | 1 |
| supervisor-central | 10 | 0.1379 | 65 | 181.4 | 25 | 0.65 |
| normal-harness | 10 | 0.0678 | 81.7 | 383.2 | 26 | 0.35 |
| strict-harness | 10 | 0.0677 | 80.85 | 428.7 | 29 | 0.15 |

## external-dispatch-dry-run

- fastest mode: `normal-harness`
- best operational efficiency mode: `normal-harness`
- best quality-adjusted mode: `strict-harness`
- lowest supervisor load mode: `strict-harness`

| Mode | Samples | Median elapsed min | Operational efficiency | Quality adjusted | Quality score | Supervisor ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| supervisor-only | 10 | 0.1581 | 47.5 | 133.2 | 21 | 1 |
| supervisor-central | 10 | 0.1431 | 65 | 174.6 | 25 | 0.65 |
| normal-harness | 10 | 0.0696 | 81.7 | 373.3 | 26 | 0.35 |
| strict-harness | 10 | 0.0711 | 80.85 | 407.6 | 29 | 0.15 |

## pnh-local-validation

- fastest mode: `normal-harness`
- best operational efficiency mode: `normal-harness`
- best quality-adjusted mode: `strict-harness`
- lowest supervisor load mode: `strict-harness`

| Mode | Samples | Median elapsed min | Operational efficiency | Quality adjusted | Quality score | Supervisor ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| supervisor-only | 13 | 0.1376 | 47.5 | 152.6 | 21 | 1 |
| supervisor-central | 13 | 0.1348 | 65 | 185.5 | 25 | 0.65 |
| normal-harness | 13 | 0.0658 | 81.7 | 395.1 | 26 | 0.35 |
| strict-harness | 13 | 0.0668 | 80.85 | 434.1 | 29 | 0.15 |

## release-readiness

- fastest mode: `normal-harness`
- best operational efficiency mode: `normal-harness`
- best quality-adjusted mode: `strict-harness`
- lowest supervisor load mode: `strict-harness`

| Mode | Samples | Median elapsed min | Operational efficiency | Quality adjusted | Quality score | Supervisor ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| supervisor-only | 0 |  |  |  |  |  |
| supervisor-central | 10 | 0.1519 | 65 | 164.6 | 25 | 0.65 |
| normal-harness | 10 | 0.0733 | 81.7 | 354.9 | 26 | 0.35 |
| strict-harness | 10 | 0.0748 | 80.85 | 387.7 | 29 | 0.15 |

## security-sensitive-local-storage

- fastest mode: `normal-harness`
- best operational efficiency mode: `normal-harness`
- best quality-adjusted mode: `strict-harness`
- lowest supervisor load mode: `strict-harness`

| Mode | Samples | Median elapsed min | Operational efficiency | Quality adjusted | Quality score | Supervisor ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| supervisor-only | 0 |  |  |  |  |  |
| supervisor-central | 10 | 0.1417 | 65 | 176.4 | 25 | 0.65 |
| normal-harness | 10 | 0.0683 | 81.7 | 380.7 | 26 | 0.35 |
| strict-harness | 10 | 0.0697 | 80.85 | 416.1 | 29 | 0.15 |

## unattended-dispatch

- fastest mode: `normal-harness`
- best operational efficiency mode: `normal-harness`
- best quality-adjusted mode: `strict-harness`
- lowest supervisor load mode: `strict-harness`

| Mode | Samples | Median elapsed min | Operational efficiency | Quality adjusted | Quality score | Supervisor ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| supervisor-only | 0 |  |  |  |  |  |
| supervisor-central | 0 |  |  |  |  |  |
| normal-harness | 10 | 0.0751 | 81.7 | 346.4 | 26 | 0.35 |
| strict-harness | 10 | 0.0751 | 80.85 | 386.4 | 29 | 0.15 |
