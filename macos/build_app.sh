#!/usr/bin/env bash
# Build macos/Kosistenz.app (Dock-ready GUI launcher).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$ROOT/macos/Kosistenz.app"
MACOS="$APP/Contents/MacOS"
RES="$APP/Contents/Resources"

rm -rf "$APP"
mkdir -p "$MACOS" "$RES"

cp "$ROOT/macos/Info.plist" "$APP/Contents/Info.plist"
cp "$ROOT/macos/kosistenz-gui" "$MACOS/kosistenz-gui"
chmod +x "$MACOS/kosistenz-gui"

printf '%s\n' "$ROOT" > "$RES/kosistenz_repo.txt"

ICON_SRC=""
for candidate in \
  "$ROOT/macos/app_icon.icns" \
  "$ROOT/app_icon.icns" \
  "$HOME/Applications/Kosistenz.app/Contents/Resources/app_icon.icns" \
  "/Applications/Kosistenz.app/Contents/Resources/app_icon.icns"; do
  if [[ -f "$candidate" ]]; then
    ICON_SRC="$candidate"
    break
  fi
done

if [[ -n "$ICON_SRC" ]]; then
  cp "$ICON_SRC" "$RES/app_icon.icns"
  echo "Using icon: $ICON_SRC"
else
  /usr/libexec/PlistBuddy -c "Delete :CFBundleIconFile" "$APP/Contents/Info.plist" 2>/dev/null || true
  echo "No app_icon.icns found — Kosistenz.app will use the default icon."
fi

echo "Built $APP (repo-linked launcher for development)."
echo "For the standalone Mac app (recommended): ./macos/install_app.sh"
