#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_DIR"

if [ -f .env ]; then
  set -a
  # shellcheck source=/dev/null
  . ./.env
  set +a
fi

export DEVICE="${DEVICE:-auto}"
export HF_HOME="${HF_HOME:-$HOME/.cache/huggingface}"

resolve_uv() {
  if [ -n "${UV_BIN:-}" ] && [ -x "${UV_BIN}" ]; then
    echo "${UV_BIN}"
    return 0
  fi
  local candidate="${HOME}/.local/bin/uv"
  if [ -x "${candidate}" ]; then
    echo "${candidate}"
    return 0
  fi
  if command -v uv >/dev/null 2>&1; then
    command -v uv
    return 0
  fi
  echo "start-prod: uv not found. Install uv or set UV_BIN in the LaunchDaemon EnvironmentVariables." >&2
  return 1
}

UV_EXE="$(resolve_uv)"

exec "${UV_EXE}" run --frozen \
  uvicorn app.main:app \
  --host "${HOST:-0.0.0.0}" \
  --port "${PORT:-8000}"
