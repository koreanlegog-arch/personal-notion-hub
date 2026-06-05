# Evidence Log: PNH Final Report Gate Diet

Date: 2026-06-05

## Finding

The prior workflow treated routine end-of-slice reports like implicit approval
gates even when the next PNH task was scoped, reversible, and already delegated.

## Rule Update

Final-style reports should be limited to:

- active phase complete with no immediate scoped next task
- material approval gate
- blocker requiring supervisor-only action or external state
- explicit supervisor request for status, summary, or review

For ordinary PNH implementation slices, continue through smoke checks, browser
QA, evidence, commit, push, and the next obvious scoped task without opening a
human gate.

## Verification

- `python3 scripts/smoke_check.py`: pass
- `git diff --check`: pass

## Gate Review

This change did not require a human approval gate. It clarifies an already
delegated PNH operating rule and adds static contract coverage.
