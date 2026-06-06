#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="pnh-scheduler.service"
TIMER_NAME="pnh-scheduler.timer"
SYSTEMD_USER_DIR="${HOME}/.config/systemd/user"
APPLY="false"

if [[ "${1:-}" == "--apply" ]]; then
  APPLY="true"
fi

echo "# PNH Scheduler User Service Uninstaller"
echo "apply=${APPLY}"

if ! command -v systemctl >/dev/null 2>&1; then
  echo "systemctl_available=false"
  exit 2
fi

if ! systemctl --user show-environment >/dev/null 2>&1; then
  echo "systemd_user_available=false"
  exit 2
fi

if [[ "${APPLY}" != "true" ]]; then
  echo "mode=dry-run"
  echo "would_stop=${TIMER_NAME}"
  echo "would_remove=${SYSTEMD_USER_DIR}/${SERVICE_NAME}"
  echo "would_remove=${SYSTEMD_USER_DIR}/${TIMER_NAME}"
  exit 0
fi

systemctl --user disable --now "${TIMER_NAME}" >/dev/null 2>&1 || true
systemctl --user stop "${SERVICE_NAME}" >/dev/null 2>&1 || true
rm -f "${SYSTEMD_USER_DIR}/${SERVICE_NAME}" "${SYSTEMD_USER_DIR}/${TIMER_NAME}"
systemctl --user daemon-reload
echo "uninstalled=true"
