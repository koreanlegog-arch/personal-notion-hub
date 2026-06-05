# Evidence Log: PNH Single Command Packet

Date: 2026-06-05T07:57:50+00:00

## Result

- mode: `apply`
- selected capture: `assistant-capture-capture-mq0mgu4q-uvzyzm0s`
- external writes performed: `true`
- worker run performed: `true`
- private values printed: `false`
- token values printed: `false`
- raw private body read: `false`
- Discord reply delivered: `false`

## Commands Run

- `queue_plan` returnCode=`0`
- `readiness` returnCode=`0`
- `dispatch_pilot` returnCode=`0`
- `github_status_refresh` returnCode=`0`
- `discord_thread_refresh` returnCode=`0`
- `github_status_refresh_after_discord` returnCode=`0`
- `worker_capture_dry_run` returnCode=`0`
- `worker_capture_apply` returnCode=`0`
- `github_status_refresh` returnCode=`0`
- `discord_thread_refresh` returnCode=`0`
- `github_status_refresh_after_discord` returnCode=`0`
- `label_plan` returnCode=`0`
- `label_apply_dry_run` returnCode=`0`
- `label_apply` returnCode=`0`
- `github_status_refresh_after_label` returnCode=`0`
- `post_label_plan` returnCode=`0`
- `dispatch_state_status` returnCode=`0`
- `evidence_summary` returnCode=`0`
- `supervisor_review` returnCode=`0`

## Safety

- Worker prompts are generated from dispatch metadata only.
- Subcommand stdout/stderr byte counts are recorded; raw output bodies are not embedded here.
- Secret values and raw private command bodies are not printed or stored in tracked evidence.
