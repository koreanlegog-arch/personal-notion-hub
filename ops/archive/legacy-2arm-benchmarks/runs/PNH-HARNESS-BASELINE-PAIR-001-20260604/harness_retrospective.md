# Harness Retrospective: Baseline Pair 001

## Classification

- comparison type: `supervisor-only` vs `harness-run`
- difficulty band: `M`
- reasoning_effort: `medium`
- reasoning_policy: `fixed-baseline`

## Findings

- `supervisor-only` was faster for this small-medium, low-ambiguity audit script task.
- `harness-run` reduced supervisor direct implementation ratio from `1.0` to about `0.30`.
- `harness-run` added useful checklist coverage around no decrypt/no passphrase/no private output, but the added coordination overhead exceeded the time saved for this task size.
- No defects or rework were observed in either arm.

## Baseline Implication

Do not generalize from one pair. For similar small script tasks, keep measuring before making harness the default. The current evidence suggests that harness-run becomes more attractive when:

- reviewer/QA risk is higher,
- write set is naturally separable,
- implementation size is larger,
- supervisor attention is the bottleneck rather than wall-clock duration.

## Next Test Recommendation

Run another `M` pair, but choose a task with a more naturally separable write set, such as docs/template update plus independent smoke/checklist update.
