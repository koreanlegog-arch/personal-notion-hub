# Evidence Log: PNH Discord/OpenClaw Dispatch Rehearsal

Date: 2026-06-05

## Results

- `openclaw status`: gateway reachable in fast status; Discord configured.
- `openclaw security audit`: 0 critical, 4 warn, 1 info before hardening.
- `chmod 700 /home/koreanlego/.openclaw`: applied to remove group-writable state dir warning.
- `openclaw message thread create --dry-run`: passed with gateway SecretRef warning.
- Direct Discord API rehearsal using ambient `DISCORD_BOT_TOKEN`: failed with HTTP 401.
  - Interpretation: ambient shell token is stale or not the approved current bot token.
  - Token value was not printed.
- `~/.config/openclaw/openclaw-gateway.env`: exists and contains approved local variable names.
  - Values were not printed.
- OpenClaw live thread create after sourcing gateway env: passed.
  - Discord thread ID: `1512255836360151070`
  - Parent channel: `#command-center`
  - GitHub issue: https://github.com/koreanlegog-arch/personal-notion-hub/issues/1
- OpenClaw lifecycle messages posted:
  - `/task create`: `1512255933336780880`
  - `/task assign`: `1512255950638026783`
  - `/review`: `1512255967730077898`
  - `/qa`: `1512255982703476887`
  - `/task done`: `1512255996989407283`
- Audit-log message posted:
  - `1512256011233132574`
- GitHub issue comment posted:
  - https://github.com/koreanlegog-arch/personal-notion-hub/issues/1#issuecomment-4627177556
- Final local validation:
  - `python3 -m py_compile scripts/github_ledger_bridge.py scripts/github_ledger_bridge_smoke_check.py`: passed
  - `python3 scripts/github_ledger_bridge_smoke_check.py`: passed
  - `python3 scripts/smoke_check.py`: passed
  - `git diff --check`: passed
- Secret pattern scan:
  - matches were existing synthetic fixture text, companion runtime pairing-code print location, and prior evidence command text
  - no GitHub token, Discord bot token, OpenClaw gateway token, or raw private command value was identified in this change

## Security Notes

- No token value was printed.
- Raw private command packet body was not posted to GitHub or Discord.
- OpenClaw live path required sourcing the approved local gateway env file.
- Ambient `DISCORD_BOT_TOKEN` in the shell failed with 401 and should be treated as stale until refreshed.
- Remaining OpenClaw warnings still need runtime hardening:
  - gateway auth SecretRef resolution mismatch in some command paths
  - gateway HTTP auth mode warning while loopback-only
  - multi-user/sandbox heuristic warning

## Verdict

PNH ledger-to-Discord/OpenClaw routing rehearsal is complete.

This is not yet full automatic worker execution. The next gate is converting PNH command packets into repeatable dispatch jobs with dedupe, ledger updates, and OpenClaw worker-session result capture.
