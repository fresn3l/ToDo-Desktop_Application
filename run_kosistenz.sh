#!/usr/bin/env bash
# Run Kosistenz from the repo virtualenv (used by Kosistenz.app).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
  echo "Virtualenv missing. Run: ./setup_venv.sh" >&2
  exit 1
fi

export PATH="$ROOT/.venv/bin:$PATH"
exec "$ROOT/.venv/bin/python" "$ROOT/main.py"
