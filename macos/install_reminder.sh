#!/usr/bin/env bash
# Install or update the Kosistenz launchd daily reminder (free, offline).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

HOUR="${1:-20}"
MINUTE="${2:-0}"

python3 - <<PY
import reminders
reminders._save_config({"enabled": True, "hour": int("$HOUR"), "minute": int("$MINUTE")})
result = reminders.install_local_reminder()
print(result)
if not result.get("ok"):
    raise SystemExit(1)
PY

echo ""
echo "Local reminder installed for ${HOUR}:$(printf '%02d' "$MINUTE") daily."
echo "Plist: ~/Library/LaunchAgents/com.kosistenz.reminder.plist"
echo "Test now: bash macos/kosistenz-reminder.sh"
