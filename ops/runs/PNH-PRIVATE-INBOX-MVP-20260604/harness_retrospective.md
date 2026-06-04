# Harness Retrospective

Date: 2026-06-04

## What Went Wrong Before

The previous PNH work treated a polished web intake surface as the primary MVP and deferred the most important system proof: whether an input originating outside the workspace could be captured into the local project environment.

That made the report sound like the real automation was still unavailable.

## Updated Supervisor Rule

For automation and assistant projects, the first durable MVP must prove the highest-risk data/control path.

For PNH assistant automation, the critical path is:

```text
phone-like input -> local companion auth -> workspace-local persistence -> redacted evidence
```

Only after that path works should UI polish, dashboard cards, and visual design become priority.

## Harness Implication

Future task packets must explicitly rank:

1. Control/data path proof.
2. Storage/security boundary.
3. Verification and evidence.
4. Operator workflow.
5. UI polish.

If the implementation completes item 5 before items 1-3, the harness should mark the run as mis-sliced.
