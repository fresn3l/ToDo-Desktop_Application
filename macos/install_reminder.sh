#!/usr/bin/env bash
# Install or update the Kosistenz launchd daily reminder (free, offline).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export KOSISTENZ_REMINDER_HOUR="${1:-20}"
export KOSISTENZ_REMINDER_MINUTE="${2:-0}"

python3 - <<'PY'
import os
import reminders

hour = int(os.environ["KOSISTENZ_REMINDER_HOUR"])
minute = int(os.environ["KOSISTENZ_REMINDER_MINUTE"])
reminders._save_config({"enabled": True, "hour": hour, "minute": minute})
result = reminders.install_local_reminder()
print(result)
if not result.get("ok"):
    raise SystemExit(1)
PY

echo ""
echo "Local reminder installed for ${KOSISTENZ_REMINDER_HOUR}:$(printf '%02d' "${KOSISTENZ_REMINDER_MINUTE}") daily."
echo "Plist: ~/Library/LaunchAgents/com.kosistenz.reminder.plist"
echo "Test now: bash macos/kosistenz-reminder.sh"
