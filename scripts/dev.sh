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

exec uv run uvicorn app.main:app \
  --reload \
  --host "${HOST:-0.0.0.0}" \
  --port "${PORT:-8000}"
