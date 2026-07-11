#!/usr/bin/env bash
# Create .venv in this repo and install Kosistenz dependencies.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

PY="${PYTHON:-python3}"
if ! command -v "$PY" >/dev/null 2>&1; then
  echo "Need python3 on PATH (or set PYTHON=/path/to/python3)." >&2
  exit 1
fi

echo "Using: $($PY -c 'import sys; print(sys.executable)')"

if [[ ! -d .venv ]]; then
  "$PY" -m venv .venv
fi

./.venv/bin/python -m pip install -U pip
./.venv/bin/python -m pip install -r requirements.txt

echo ""
echo "Done. Run the app with:"
echo "  ./run_kosistenz.sh"
echo "  python main.py"
echo ""
echo "For Dock / Spotlight launch:"
echo "  ./macos/install_app.sh"
