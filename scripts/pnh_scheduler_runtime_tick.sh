#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

python3 scripts/pnh_scheduler_tick.py \
  --out "${PNH_SCHEDULER_RUNTIME_OUT:-companion/private/scheduler/scheduler_tick.json}" \
  --runtime-dir "${PNH_SCHEDULER_RUNTIME_DIR:-companion/private/scheduler/jobs}"
