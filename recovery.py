"""
Recovery prompt after a missed checklist day.
"""

from __future__ import annotations

import json
import os
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

import eel

import daily_checklist

RECOVERY_OPTIONS = [
    {"value": "too_busy", "label": "Too busy"},
    {"value": "forgot", "label": "Forgot"},
    {"value": "low_energy", "label": "Sick / low energy"},
    {"value": "traveling", "label": "Traveling"},
    {"value": "other", "label": "Other"},
]


def _recovery_path():
    return daily_checklist.get_data_directory() / "recovery_responses.json"


def _load_recovery() -> Dict[str, Any]:
    path = _recovery_path()
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_recovery(data: Dict[str, Any]) -> None:
    path = _recovery_path()
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    os.replace(tmp, path)


def _dates_with_submissions() -> set[str]:
    dates = set()
    for row in daily_checklist.list_daily_checklist_submissions(500):
        ld = row.get("local_date")
        if ld:
            dates.add(ld)
    return dates


def _first_missed_date(lookback: int = 7) -> Optional[str]:
    """Most recent past day (not today) without a submission."""
    today = date.today()
    dates = _dates_with_submissions()
    recovery = _load_recovery()
    for i in range(1, lookback + 1):
        d = today - timedelta(days=i)
        key = d.isoformat()
        if key not in dates and key not in recovery:
            return key
    return None


@eel.expose
def get_recovery_options() -> List[Dict[str, str]]:
    return list(RECOVERY_OPTIONS)


@eel.expose
def get_pending_recovery() -> Dict[str, Any]:
    missed = _first_missed_date()
    if not missed:
        return {"pending": False}
    return {
        "pending": True,
        "missed_date": missed,
        "question": "What got in the way?",
        "options": RECOVERY_OPTIONS,
    }


@eel.expose
def submit_recovery_response(missed_date: str, reason: str) -> Dict[str, Any]:
    missed_date = (missed_date or "").strip()
    reason = (reason or "").strip()
    if not missed_date or not reason:
        raise ValueError("Date and reason required")
    valid = {o["value"] for o in RECOVERY_OPTIONS}
    if reason not in valid:
        raise ValueError("Invalid reason")
    data = _load_recovery()
    data[missed_date] = {"reason": reason, "recorded_at": date.today().isoformat()}
    _save_recovery(data)
    return {"ok": True, "missed_date": missed_date, "reason": reason}
