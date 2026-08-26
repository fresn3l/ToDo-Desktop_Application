#!/usr/bin/env bash
# Build Kosistenz.app and install to ~/Applications for Dock / Spotlight launch.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
  echo "Setting up virtualenv first..."
  "$ROOT/setup_venv.sh"
fi

"$ROOT/macos/build_app.sh"

DEST="$HOME/Applications/Kosistenz.app"
mkdir -p "$HOME/Applications"
rm -rf "$DEST"
cp -R "$ROOT/macos/Kosistenz.app" "$DEST"

echo ""
echo "Installed: $DEST"
echo ""
echo "Next steps:"
echo "  1. Open Finder → Applications (your home folder) → Kosistenz"
echo "  2. Drag Kosistenz to the Dock"
echo "  3. Double-click (or Spotlight: Cmd+Space, type \"Kosistenz\")"
echo ""
echo "If you move the repo, run ./macos/install_app.sh again."
