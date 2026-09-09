#!/usr/bin/env bash
# Build a standalone Kosistenz.app (WebKit, no Chrome) and install to /Applications.
# Then installs Cluny + Ollama unless SKIP_BRAIN=1 or --skip-brain.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This installer builds a macOS .app. Run it on a Mac." >&2
  exit 1
fi

if ! xcrun --find swiftc >/dev/null 2>&1 && ! command -v swiftc >/dev/null 2>&1; then
  echo "Need Xcode Command Line Tools to compile the native window (swiftc)." >&2
  echo "Run: xcode-select --install" >&2
  echo "Then run this installer again." >&2
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

copy_app() {
  local dest="$1"
  local use_sudo="${2:-}"
  if [[ -n "$use_sudo" ]]; then
    sudo rm -rf "$dest"
    sudo cp -R "$APP_SRC" "$dest"
    sudo xattr -dr com.apple.quarantine "$dest" 2>/dev/null || true
  else
    rm -rf "$dest"
    cp -R "$APP_SRC" "$dest"
    xattr -dr com.apple.quarantine "$dest" 2>/dev/null || true
  fi
}

SYSTEM_DEST="/Applications/Kosistenz.app"
HOME_DEST="$HOME/Applications/Kosistenz.app"
DEST=""

if [[ -w /Applications ]]; then
  copy_app "$SYSTEM_DEST"
  DEST="$SYSTEM_DEST"
else
  echo "Installing to /Applications. macOS may ask for your password."
  if sudo -v && copy_app "$SYSTEM_DEST" sudo; then
    DEST="$SYSTEM_DEST"
  else
    echo "Could not write /Applications. Installing to $HOME_DEST instead."
    mkdir -p "$HOME/Applications"
    copy_app "$HOME_DEST"
    DEST="$HOME_DEST"
  fi
fi

# Helps Launchpad / Spotlight pick it up.
touch "$DEST" 2>/dev/null || sudo touch "$DEST" 2>/dev/null || true

echo ""
echo "Installed: $DEST"
echo "Opening that folder in Finder…"
open -R "$DEST"

echo ""
echo "Kosistenz should now be selected in Finder."
echo "Double-click it to launch. First time: right-click → Open if macOS warns."
echo "Quit with Cmd+Q. Closing the window leaves the menu bar running."
echo "Add the Today widget from Notification Center → Edit Widgets → Kosistenz."
echo "If the app fails to launch: ~/Library/Logs/Kosistenz.log"

SKIP_BRAIN="${SKIP_BRAIN:-0}"
for arg in "$@"; do
  case "$arg" in
    --skip-brain) SKIP_BRAIN=1 ;;
    --with-brain) SKIP_BRAIN=0 ;;
  esac
done

if [[ "$SKIP_BRAIN" == "1" ]]; then
  echo ""
  echo "Skipped Cluny + Ollama (SKIP_BRAIN=1 or --skip-brain)."
  echo "To install the local brain later: ./macos/install_brain.sh"
else
  echo ""
  echo "Installing Cluny + Ollama (local brain). App-only: SKIP_BRAIN=1 ./macos/install_app.sh"
  chmod +x "$ROOT/macos/install_brain.sh" 2>/dev/null || true
  "$ROOT/macos/install_brain.sh"
fi
