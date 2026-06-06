# Legacy Non-4-Mode Benchmarks Archive

This archive contains benchmark assets that were not two-arm benchmarks but
still failed the current four-mode-only benchmark contract.

The archived runs used partial mode sets such as:

- `supervisor-only` only smoke checks
- `supervisor-central`, `normal-harness`, `strict-harness`
- `normal-harness`, `strict-harness`

The active benchmark surface must now run all four modes for every benchmark
family and model:

- `supervisor-only`
- `supervisor-central`
- `normal-harness`
- `strict-harness`

Do not use these archived records as current harness decision evidence unless
the report explicitly states that it is reviewing historical partial-mode data.
