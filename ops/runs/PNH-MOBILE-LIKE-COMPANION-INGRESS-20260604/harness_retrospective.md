# Harness Retrospective

## Verdict

This was a partial but useful harness run.

The run did not become a full multi-implementer harness because the actual implementation slice remained supervisor-local. It still improved decision quality: the security sidecar blocked a riskier browser fetch/CORS path before implementation, and the repo-explorer sidecar identified the safer stdin/file CLI path.

## Efficiency Score

- score model: `efficiency`
- score: `60.1 / 100`
- classification: `single-agent-or-partial-harness`
- reason: useful specialist routing and strong evidence, but low implementation parallelism and one replan.

## What Worked

- Specialist fit was meaningful:
  - repo-explorer mapped current entry points quickly.
  - security sidecar correctly flagged browser integration as a separate approval gate.
- Scope became safer before code changes.
- The implementation slice stayed small and reviewable.
- Validation stayed synthetic-only and avoided token/private body output.
- The new command packet made approval gates explicit.

## What Did Not Fully Work

- The first task packet over-scoped browser-to-companion integration before sidecar results arrived.
- The implementer slice was not delegated to a separate implementer agent.
- Critical-path reduction is still an estimate, not an A/B measurement.
- The current local implementation did not exercise a real browser/mobile UI because that remains a separate security design gate.

## Measurement Answer

Can efficiency be checked internally?

Partially.

Directly measurable inside the workspace:

- number of bounded slices
- whether sidecar findings changed scope or caught defects
- rework count
- duplicate work count
- write-set conflicts
- evidence completeness
- security blocker count
- supervisor direct implementation ratio
- commands run and pass/fail results

Not directly measurable without baseline design:

- "faster than no harness"
- actual wall-clock speedup
- cost reduction

Required baseline options:

1. Historical baseline: compare against prior similar tasks with recorded duration, rework, and supervisor implementation ratio.
2. A/B rehearsal: run two similar tasks, one direct and one harness-driven, with same acceptance criteria.
3. Control chart: track repeated task classes over time and compare median lead time and rework.

Current run uses option 1 only as a rough historical estimate, so no hard speedup claim is made.

## Next Run Rule

When a task touches browser-to-local companion integration, run security preflight before writing the task packet's implementation scope.

## Follow-Up

- Browser companion bridge should be a separate approved task with CORS, CSP, pairing/session token, UI token handling, and screenshot redaction design.
- Future harness runs should delegate at least one disjoint implementer slice when file ownership is clear.
