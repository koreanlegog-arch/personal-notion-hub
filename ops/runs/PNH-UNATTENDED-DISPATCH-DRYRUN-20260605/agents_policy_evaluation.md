# Evaluation: PNH Project AGENTS.md Policy

Date: 2026-06-05

## Question

Did the project-scoped `AGENTS.md` reduce unnecessary approval gates while still
preserving material gates?

## Observations

- Routine local dry-run commands were executed without asking for approval.
- Smoke checks were executed without asking for approval.
- A potentially unsafe evidence overwrite was detected and corrected without
  supervisor approval because it was a local reversible fix caused by this run.
- Existing historical apply evidence was restored before writing new dry-run
  evidence.
- A separate run directory was used for this dry-run evidence.
- No external write was performed.

## Policy Fit

The policy worked as intended for:

- local evidence generation
- local verification
- Git-safe reversible correction of the agent's own intermediate changes
- avoiding micro-approval during a bounded PNH phase

The policy also preserved the correct material gate:

- live unattended pilot apply remains gated because it writes to GitHub,
  Discord, and OpenClaw.

## Residual Issue

The scripts still use historical default evidence directories. Running them
without `--out` or `--run-dir` can overwrite previous tracked evidence. The
agent caught this during the run, but the tooling should make the safe path
easier.

## Recommended Follow-up

Add a small guard or convention so dry-run commands default to a fresh run
directory when the target evidence file already exists, or document that
operators must provide explicit `--out` and `--run-dir` for repeat rehearsals.

This follow-up is local tooling work and does not require a material approval
gate unless it changes external dispatch behavior.
