# PNH Benchmark Family Comparison

- generated at: `2026-06-05T13:18:25+00:00`
- source log: `ops/runs/harness_operation_mode_measurements.jsonl`
- completed usable records: `12`
- minimum samples per active threshold: `3`

## pnh-local-validation

- fastest mode: `strict-harness`
- best operational efficiency mode: `normal-harness`
- best quality-adjusted mode: `strict-harness`
- lowest supervisor load mode: `strict-harness`

| Mode | Samples | Median elapsed min | Operational efficiency | Quality adjusted | Quality score | Supervisor ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| supervisor-only | 3 | 0.1362 | 47.5 | 154.2 | 21 | 1 |
| supervisor-central | 3 | 0.1317 | 65 | 189.8 | 25 | 0.65 |
| normal-harness | 3 | 0.0654 | 81.7 | 397.6 | 26 | 0.35 |
| strict-harness | 3 | 0.0653 | 80.85 | 444.1 | 29 | 0.15 |
