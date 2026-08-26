#!/usr/bin/env bash
# Build a standalone Kosistenz.app (WebKit, no Chrome) and install to ~/Applications.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This installer builds a macOS .app. Run it on a Mac." >&2
  exit 1
fi

if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
  echo "Setting up virtualenv first..."
  "$ROOT/setup_venv.sh"
fi

"$ROOT/.venv/bin/python" "$ROOT/build_app.py"

APP_SRC=""
for candidate in "$ROOT/dist/Kosistenz.app" "$ROOT/dist/Kosistenz/Kosistenz.app"; do
  if [[ -d "$candidate" ]]; then
    APP_SRC="$candidate"
    break
  fi
done

if [[ -z "$APP_SRC" ]]; then
  echo "Build succeeded but Kosistenz.app was not found in dist/." >&2
  exit 1
fi

DEST="$HOME/Applications/Kosistenz.app"
mkdir -p "$HOME/Applications"
rm -rf "$DEST"
cp -R "$APP_SRC" "$DEST"
xattr -dr com.apple.quarantine "$DEST" 2>/dev/null || true

echo ""
echo "Installed: $DEST"
echo ""
echo "This is a standalone app. Chrome is not used."
echo "  1. Finder → Go → Home → Applications → Kosistenz"
echo "  2. Drag it to the Dock if you want"
echo "  3. Double-click, or Spotlight (Cmd+Space) and type Kosistenz"
echo ""
echo "First open: right-click → Open, if macOS asks about an unidentified developer."
