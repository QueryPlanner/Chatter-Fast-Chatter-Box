#!/usr/bin/env bash
# Per-user LaunchAgent (no sudo). Prefer this if install-launchd.sh fails with
# "Bootstrap failed: 5" (often iCloud or launchd quirk on system plists).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATE="${REPO_DIR}/launchd/com.fastchatterbox.server.user.plist"
RENDERED="${SCRIPT_DIR}/com.fastchatterbox.server.user.rendered.plist"
AGENT_DIR="${HOME}/Library/LaunchAgents"
INSTALLED_PLIST="${AGENT_DIR}/com.fastchatterbox.server.plist"
LABEL="com.fastchatterbox.server"
UID_NUM="$(id -u)"
GUI_DOMAIN="gui/${UID_NUM}/${LABEL}"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "install-launchagent: This script is for macOS only." >&2
  exit 1
fi

if [[ ! -f "${TEMPLATE}" ]]; then
  echo "install-launchagent: Missing template: ${TEMPLATE}" >&2
  exit 1
fi

USER_NAME="$(id -un)"
HOME_DIR="${HOME}"
GROUP_NAME="$(id -gn)"
START_PROD_SH="${REPO_DIR}/scripts/start-prod.sh"
LOG_DIR="${HOME_DIR}/Library/Logs/fast-chatterbox"
STDOUT_LOG="${LOG_DIR}/stdout.log"
STDERR_LOG="${LOG_DIR}/stderr.log"

resolve_uv_bin() {
  if [[ -x "${HOME_DIR}/.local/bin/uv" ]]; then
    echo "${HOME_DIR}/.local/bin/uv"
    return 0
  fi
  if command -v uv >/dev/null 2>&1; then
    command -v uv
    return 0
  fi
  echo "install-launchagent: uv not found. Install uv (https://docs.astral.sh/uv/) and re-run." >&2
  return 1
}

UV_BIN="$(resolve_uv_bin)"
PATH_VALUE="/opt/homebrew/bin:/usr/local/bin:${HOME_DIR}/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

if [[ ! -x "${START_PROD_SH}" ]]; then
  echo "install-launchagent: start-prod.sh is not executable: ${START_PROD_SH}" >&2
  exit 1
fi

if [[ ! -x "${UV_BIN}" ]]; then
  echo "install-launchagent: uv is not executable: ${UV_BIN}" >&2
  exit 1
fi

mkdir -p "${LOG_DIR}" "${AGENT_DIR}"

escape_sed_literal() {
  printf '%s' "$1" | sed -e 's/[|&]/\\&/g'
}

# Same substitutions as the LaunchDaemon template (user plist omits User/Group).
render_plist() {
  sed \
    -e "s|@USER_NAME@|$(escape_sed_literal "${USER_NAME}")|g" \
    -e "s|@GROUP_NAME@|$(escape_sed_literal "${GROUP_NAME}")|g" \
    -e "s|@REPO_DIR@|$(escape_sed_literal "${REPO_DIR}")|g" \
    -e "s|@START_PROD_SH@|$(escape_sed_literal "${START_PROD_SH}")|g" \
    -e "s|@STDOUT_LOG@|$(escape_sed_literal "${STDOUT_LOG}")|g" \
    -e "s|@STDERR_LOG@|$(escape_sed_literal "${STDERR_LOG}")|g" \
    -e "s|@HOME_DIR@|$(escape_sed_literal "${HOME_DIR}")|g" \
    -e "s|@PATH_VALUE@|$(escape_sed_literal "${PATH_VALUE}")|g" \
    -e "s|@UV_BIN@|$(escape_sed_literal "${UV_BIN}")|g" \
    "${TEMPLATE}"
}

render_plist > "${RENDERED}"

if ! plutil -lint "${RENDERED}" >/dev/null; then
  echo "install-launchagent: rendered plist failed validation." >&2
  plutil -lint "${RENDERED}" >&2
  exit 1
fi

echo "Rendered plist: ${RENDERED}"
echo "Installing LaunchAgent to ${INSTALLED_PLIST} (no sudo)..."

# Stop a prior user registration, and try to stop the system daemon if it exists (ignores if none).
launchctl bootout "${GUI_DOMAIN}" 2>/dev/null || true
sudo launchctl bootout "system/${LABEL}" 2>/dev/null || true

cp "${RENDERED}" "${INSTALLED_PLIST}"
chmod 644 "${INSTALLED_PLIST}"

if ! launchctl bootstrap "gui/${UID_NUM}" "${INSTALLED_PLIST}"; then
  echo "install-launchagent: bootstrap failed. Try: plutil -lint ${INSTALLED_PLIST}" >&2
  exit 1
fi

launchctl enable "${GUI_DOMAIN}" 2>/dev/null || true
launchctl kickstart -k "${GUI_DOMAIN}" 2>/dev/null || true

echo "LaunchAgent installed. Check health with:"
echo "  curl http://localhost:8000/health"
echo "Status:  launchctl print ${GUI_DOMAIN} | head -20"
