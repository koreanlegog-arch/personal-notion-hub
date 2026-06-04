# Harness Retrospective

## Hypothesis

Harness-run should outperform supervisor-only when the task has independent documentation, QA, and review lanes.

## Early Result

Partially supported. The harness-run did not reduce first smoke-pass wall-clock relative to the narrower supervisor-only slice, but it produced broader delivery assets in the same run window.

The stronger result is quality-related: reviewer review caught a High governance issue and a Medium smoke-contract weakness after the initial smoke pass. This is exactly the class of defect that a direct path can miss because "file exists and smoke passes" is not the same as "policy-safe artifact is ready."

## Measurement Caveat

The two slices were similar in theme but not identical in scope. A fairer future test should fix output count and complexity, then compare:

- direct serial implementation plus self-review
- delegated implementation plus parallel QA/review

## Rework

- Defect count found by reviewer: `2`
- Blocking defects before review: `1`
- Rework required: yes
- Rework type: policy wording plus stronger smoke contract

## Efficiency Score

- Score: `68.9`
- Band: `partial`
- Classification: `multi-agent-harness`
- Penalty: `10` for one replan/rework loop

Interpretation: the harness improved quality and caught a blocking policy defect, but did not yet prove wall-clock speedup. The useful lesson is that reviewer lanes should be launched earlier against drafted acceptance criteria or template policy constraints, not only after initial integration.

## Operational Lesson

Use harness when at least two of these are true:

- implementation and QA artifacts are separate files
- reviewer can inspect without blocking implementation
- output has client/security significance
- acceptance criteria are likely to be forgotten in a direct path
