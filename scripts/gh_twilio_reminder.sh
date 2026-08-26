#!/usr/bin/env bash
# Used by GitHub Actions: if checkins/YYYY-MM-DD.json is missing for "today"
# in CHECKIN_TIMEZONE, send one SMS via Twilio.
set -euo pipefail

if [[ -n "${CHECKIN_TIMEZONE:-}" ]]; then
  export TZ="${CHECKIN_TIMEZONE}"
else
  export TZ="America/Denver"
fi
TODAY="$(date +%Y-%m-%d)"

if [[ -f "checkins/${TODAY}.json" ]]; then
  echo "Check-in file exists for ${TODAY} — no reminder."
  exit 0
fi

if [[ -z "${TWILIO_ACCOUNT_SID:-}" || -z "${TWILIO_AUTH_TOKEN:-}" ]]; then
  echo "Twilio secrets missing — skipping SMS."
  exit 0
fi

if [[ -z "${TWILIO_FROM_NUMBER:-}" || -z "${TWILIO_TO_NUMBER:-}" ]]; then
  echo "TWILIO_FROM_NUMBER or TWILIO_TO_NUMBER missing — skipping SMS."
  exit 0
fi

BODY="${REMINDER_BODY:-Kosistenz: Daily checklist not logged for ${TODAY}.}"

curl -sS -X POST \
  "https://api.twilio.com/2010-04-01/Accounts/${TWILIO_ACCOUNT_SID}/Messages.json" \
  --data-urlencode "From=${TWILIO_FROM_NUMBER}" \
  --data-urlencode "To=${TWILIO_TO_NUMBER}" \
  --data-urlencode "Body=${BODY}" \
  -u "${TWILIO_ACCOUNT_SID}:${TWILIO_AUTH_TOKEN}"

echo ""
echo "Reminder SMS sent for missing check-in on ${TODAY} (${TZ})."
