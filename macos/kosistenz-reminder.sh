#!/usr/bin/env bash
# Free local notification — no network, no Twilio.
set -euo pipefail

osascript <<'APPLESCRIPT'
display notification "Open Kosistenz and complete your check-in." with title "Kosistenz" subtitle "Daily reminder"
APPLESCRIPT
