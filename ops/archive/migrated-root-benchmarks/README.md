# Migrated Root Benchmarks

Status: archived local copies.

The active benchmark owner is now the workspace root at `/home/koreanlego/projects`.
PNH benchmark evidence was copied to:

- `../ops/runs/project-personal-notion-hub/` in the workspace root
- `../ops/runs/harness_operation_mode_measurements.jsonl` in the workspace root

PNH keeps these archived copies only for rollback and historical traceability.
Do not run benchmark analysis from this project archive. Use the root benchmark
scripts and the root project adapter instead:

```bash
cd /home/koreanlego/projects
python3 scripts/harness_four_mode_benchmark.py \
  --project-adapter ops/benchmarks/projects/personal_notion_hub.json
```
