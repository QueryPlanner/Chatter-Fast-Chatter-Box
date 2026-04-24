#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATE="${REPO_DIR}/launchd/com.fastchatterbox.server.plist"
RENDERED="${SCRIPT_DIR}/com.fastchatterbox.server.rendered.plist"
INSTALLED_PLIST="/Library/LaunchDaemons/com.fastchatterbox.server.plist"
LABEL="com.fastchatterbox.server"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "install-launchd: This script is for macOS only." >&2
  exit 1
fi

if [[ ! -f "${TEMPLATE}" ]]; then
  echo "install-launchd: Missing template: ${TEMPLATE}" >&2
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
  echo "install-launchd: uv not found. Install uv (https://docs.astral.sh/uv/) and re-run." >&2
  return 1
}

UV_BIN="$(resolve_uv_bin)"

PATH_VALUE="/opt/homebrew/bin:/usr/local/bin:${HOME_DIR}/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

if [[ ! -x "${START_PROD_SH}" ]]; then
  echo "install-launchd: start-prod.sh is not executable: ${START_PROD_SH}" >&2
  exit 1
fi

mkdir -p "${LOG_DIR}"

escape_sed_literal() {
  printf '%s' "$1" | sed -e 's/[|&]/\\&/g'
}

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

echo "Rendered plist: ${RENDERED}"
echo "Installing to ${INSTALLED_PLIST} (requires sudo)..."

sudo launchctl bootout "system/${LABEL}" 2>/dev/null || true

sudo cp "${RENDERED}" "${INSTALLED_PLIST}"
sudo chown root:wheel "${INSTALLED_PLIST}"
sudo chmod 644 "${INSTALLED_PLIST}"

sudo launchctl bootstrap system "${INSTALLED_PLIST}"

echo "LaunchDaemon installed. Check health with:"
echo "  curl http://localhost:8000/health"
