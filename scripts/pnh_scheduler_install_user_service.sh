#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_NAME="pnh-scheduler.service"
TIMER_NAME="pnh-scheduler.timer"
SYSTEMD_USER_DIR="${HOME}/.config/systemd/user"
INTERVAL_MINUTES="10"
APPLY="false"
START_NOW="true"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply)
      APPLY="true"
      shift
      ;;
    --no-start)
      START_NOW="false"
      shift
      ;;
    --interval-minutes)
      INTERVAL_MINUTES="${2:-}"
      shift 2
      ;;
    *)
      echo "unknown_arg=$1" >&2
      exit 2
      ;;
  esac
done

echo "# PNH Scheduler User Service Installer"
echo "root=${ROOT}"
echo "service=${SERVICE_NAME}"
echo "timer=${TIMER_NAME}"
echo "apply=${APPLY}"

if ! command -v systemctl >/dev/null 2>&1; then
  echo "systemctl_available=false"
  exit 2
fi

if ! systemctl --user show-environment >/dev/null 2>&1; then
  echo "systemd_user_available=false"
  echo "hint=Enable WSL systemd or start a user systemd session, then rerun this script."
  exit 2
fi

PLAN_JSON="$(python3 "${ROOT}/scripts/pnh_scheduler_service_plan.py" --interval-minutes "${INTERVAL_MINUTES}")"
SERVICE_TEXT="$(printf '%s\n' "${PLAN_JSON}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["serviceText"], end="")')"
TIMER_TEXT="$(printf '%s\n' "${PLAN_JSON}" | python3 -c 'import json,sys; print(json.load(sys.stdin)["timerText"], end="")')"

if [[ "${APPLY}" != "true" ]]; then
  echo "mode=dry-run"
  printf '%s\n' "${PLAN_JSON}"
  exit 0
fi

mkdir -p "${SYSTEMD_USER_DIR}"
printf '%s' "${SERVICE_TEXT}" > "${SYSTEMD_USER_DIR}/${SERVICE_NAME}"
printf '%s' "${TIMER_TEXT}" > "${SYSTEMD_USER_DIR}/${TIMER_NAME}"
chmod 0644 "${SYSTEMD_USER_DIR}/${SERVICE_NAME}" "${SYSTEMD_USER_DIR}/${TIMER_NAME}"

systemctl --user daemon-reload
systemctl --user enable "${TIMER_NAME}" >/dev/null
if [[ "${START_NOW}" == "true" ]]; then
  systemctl --user start "${TIMER_NAME}"
  systemctl --user start "${SERVICE_NAME}"
fi

echo "installed=true"
systemctl --user --no-pager --full status "${TIMER_NAME}" || true
