#!/usr/bin/env bash
set -euo pipefail

INSTALLED_PLIST="/Library/LaunchDaemons/com.fastchatterbox.server.plist"
LABEL="com.fastchatterbox.server"
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
  echo "uninstall-launchd: This script is for macOS only." >&2
  exit 1
fi

echo "Stopping and unloading ${LABEL} (requires sudo)..."
sudo launchctl bootout "system/${LABEL}" 2>/dev/null || true

if [[ -f "${INSTALLED_PLIST}" ]]; then
  sudo rm -f "${INSTALLED_PLIST}"
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
