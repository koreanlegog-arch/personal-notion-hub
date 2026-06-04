# Harness Retrospective: Browser Companion Bridge

## Verdict

This run is a meaningful multi-agent harness run.

The split was justified because the task crossed security, CORS/session design, browser UI, server auth, documentation, and verification. A single supervisor-only implementation would likely have mixed those concerns and increased the chance of missing a boundary.

## What Worked

- Read-only architect, security, and QA sidecars shaped the implementation before file edits.
- Server and browser write sets were mostly disjoint, reducing merge friction.
- Static smoke checks now enforce that `fetch` only appears in `assets/js/companion-bridge.js`.
- Browser token handling is isolated from the main app state and browser persistence.
- Screenshot redaction was added as a concrete UI control instead of remaining only a policy note.

## Bottlenecks

- Supervisor integration still carried documentation updates, final consistency checks, and evidence writing.
- The local harness cannot measure true speedup against an unrun supervisor-only counterfactual.
- Browser QA is still script/static heavy; no automated browser screenshot validation exists yet.
- Pairing code usability is manual because a safer long-term mobile pairing flow is not implemented.

## Efficiency Measurement Notes

The current efficiency score is a run-quality proxy, not a true elapsed-time A/B comparison.

Useful measurements available now:

- implementer slice count
- supervisor direct implementation ratio
- write-set conflict count
- replan count
- duplicate work count
- unverified claim count
- acceptance pass rate
- evidence completeness

Measurements not available without deliberate experiment design:

- exact token consumption per agent
- exact wall-clock speedup versus supervisor-only implementation
- model-by-model cost comparison
- thinking token distribution by task type

For future comparisons, keep a small baseline set:

- one supervisor-only run for a similar medium-risk feature
- one harness run for a similar medium-risk feature
- same acceptance criteria, similar write scope, same verification depth
- compare elapsed time, rework count, defect count, and supervisor direct implementation ratio

## Improvements To Apply

- Add a standard `slice_result.md` format for implementer sidecars.
- Add a `browser-qa` packet that can run after implementation without requiring the supervisor to design the scenario again.
- Add a lightweight counterfactual estimate section to each harness score, explicitly labeled as estimate.
- Keep model routing pragmatic: high-reasoning sidecars for security/architecture, standard implementers for bounded file edits, and lightweight agents for docs/evidence drafts when available.
