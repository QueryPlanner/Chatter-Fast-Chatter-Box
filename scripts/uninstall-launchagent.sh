#!/usr/bin/env bash
set -euo pipefail

AGENT_DIR="${HOME}/Library/LaunchAgents"
INSTALLED_PLIST="${AGENT_DIR}/com.fastchatterbox.server.plist"
LABEL="com.fastchatterbox.server"
UID_NUM="$(id -u)"
GUI_DOMAIN="gui/${UID_NUM}/${LABEL}"
LOG_DIR="${HOME}/Library/Logs/fast-chatterbox"

PURGE_LOGS=0
for arg in "$@"; do
  case "${arg}" in
    --purge-logs)
      PURGE_LOGS=1
      ;;
    -h|--help)
      echo "Usage: $0 [--purge-logs]"
      echo "  --purge-logs  Also remove ${LOG_DIR}"
      exit 0
      ;;
    *)
      echo "Unknown option: ${arg}" >&2
      exit 1
      ;;
  esac
done

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "uninstall-launchagent: This script is for macOS only." >&2
  exit 1
fi

echo "Stopping and unloading ${LABEL} from your login session..."

launchctl bootout "${GUI_DOMAIN}" 2>/dev/null || true

if [[ -f "${INSTALLED_PLIST}" ]]; then
  rm -f "${INSTALLED_PLIST}"
  echo "Removed ${INSTALLED_PLIST}"
else
  echo "No plist at ${INSTALLED_PLIST} (already removed?)"
fi

if [[ "${PURGE_LOGS}" -eq 1 ]]; then
  rm -rf "${LOG_DIR}"
  echo "Removed log directory ${LOG_DIR}"
else
  echo "Logs kept at ${LOG_DIR} (pass --purge-logs to delete)"
fi
