# PNH-HARNESS-BENCHMARK-DOCS-20260604 Task Packet

## Objective

Measure whether harness-run coordination recovers time or quality when work naturally separates into documentation, QA checklist, smoke contract, and review lanes.

## Benchmark Pair

### Supervisor-Only Slice

Directly implemented by supervisor agent:

- `ops/templates/PRIVATE_DATA_ADAPTER_BRIEF_TEMPLATE.md`
- `scripts/smoke_check.py` required-file contract update

### Harness-Run Slice

Delegated and integrated:

- Implementer subagent: `ops/templates/PRIVATE_DATA_ADAPTER_SECURITY_GATE_TEMPLATE.md`
- QA subagent: `ops/checklists/PRIVATE_DATA_ADAPTER_QA_CHECKLIST.md`
- Reviewer subagent: diff review after integration

## Success Criteria

- Both slices create useful real-data adapter governance assets.
- Static smoke contract passes.
- Reviewer finds no blocking issue, or findings are resolved.
- Evidence records wall-clock, rework, defect, and harness score.
- No real private data or secret values are introduced.

## Constraints

- Use medium reasoning for benchmark work.
- Do not add dependencies.
- Do not connect real adapters.
- Do not store or request real secrets.
