"""
Optional Apple Health export + Screen Time imports (macOS, read-only).

Health: parse Apple Health export.xml (Export All Health Data).
Screen Time: best-effort read from Knowledge database (may require Full Disk Access).
"""

from __future__ import annotations

import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

import eel

import daily_checklist

SLEEP_TYPE = "HKCategoryTypeIdentifierSleepAnalysis"
STEPS_TYPE = "HKQuantityTypeIdentifierStepCount"
WORKOUT_TAG = "Workout"
ASLEEP_MARKERS = (
    "HKCategoryValueSleepAnalysisAsleep",
    "HKCategoryValueSleepAnalysisAsleepUnspecified",
    "HKCategoryValueSleepAnalysisAsleepCore",
    "HKCategoryValueSleepAnalysisAsleepDeep",
    "HKCategoryValueSleepAnalysisAsleepREM",
)


def _parse_health_datetime(raw: str) -> datetime | None:
    """Parse Apple Health export timestamps such as '2024-12-01 23:15:30 -0800'."""
    if not raw:
        return None
    s = raw.strip().replace("Z", "+0000").replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M:%S %z", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    try:
        core = s.split("+")[0].rsplit(" ", 1)[0] if " " in s[19:] else s[:19]
        return datetime.strptime(core[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def _is_asleep_value(value: str) -> bool:
    v = value or ""
    if "Awake" in v or "InBed" in v:
        return False
    if v in ASLEEP_MARKERS or v == "Asleep":
        return True
    return "Asleep" in v


def _workout_duration_minutes(workout: ET.Element) -> float:
    raw = workout.get("duration")
    if raw is None or raw == "":
        return 0.0
    try:
        value = float(raw)
    except (ValueError, TypeError):
        return 0.0
    unit = (workout.get("durationUnit") or "s").strip().lower()
    if unit in ("min", "hr", "h"):
        if unit == "hr" or unit == "h":
            return round(value * 60.0, 1)
        return round(value, 1)
    return round(value / 60.0, 1)


def _snapshots_path() -> Path:
    return daily_checklist.get_data_directory() / "health_snapshots.json"


def _load_snapshots() -> Dict[str, Any]:
    path = _snapshots_path()
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_snapshots(data: Dict[str, Any]) -> None:
    path = _snapshots_path()
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    os.replace(tmp, path)


def _day_key(dt: datetime) -> str:
    return dt.date().isoformat()


def _parse_health_export_xml(path: str, days: int = 14) -> Dict[str, Dict[str, Any]]:
    root = ET.parse(path).getroot()
    cutoff = datetime.now() - timedelta(days=days)
    by_day: Dict[str, Dict[str, Any]] = {}

    for rec in root.iter("Record"):
        rtype = rec.get("type", "")
        start = rec.get("startDate") or rec.get("creationDate") or ""
        dt = _parse_health_datetime(start)
        if dt is None:
            continue
        if dt.replace(tzinfo=None) < cutoff.replace(tzinfo=None):
            continue
        key = _day_key(dt)
        by_day.setdefault(key, {"sleep_hours": 0.0, "steps": 0, "workouts": []})

        if rtype == SLEEP_TYPE and _is_asleep_value(rec.get("value") or ""):
            end = rec.get("endDate") or start
            end_dt = _parse_health_datetime(end)
            if end_dt is None:
                continue
            hours = max(0.0, (end_dt.replace(tzinfo=None) - dt.replace(tzinfo=None)).total_seconds() / 3600.0)
            by_day[key]["sleep_hours"] = round(by_day[key]["sleep_hours"] + hours, 2)
        elif rtype == STEPS_TYPE:
            try:
                by_day[key]["steps"] += int(float(rec.get("value") or 0))
            except (ValueError, TypeError):
                pass

    for workout in root.iter(WORKOUT_TAG):
        start = workout.get("startDate") or ""
        dt = _parse_health_datetime(start)
        if dt is None:
            continue
        if dt.replace(tzinfo=None) < cutoff.replace(tzinfo=None):
            continue
        key = _day_key(dt)
        by_day.setdefault(key, {"sleep_hours": 0.0, "steps": 0, "workouts": []})
        by_day[key]["workouts"].append(
            {
                "type": workout.get("workoutActivityType", "workout"),
                "duration_min": _workout_duration_minutes(workout),
            }
        )

    return by_day


@eel.expose
def import_health_export(export_path: str, days: int = 14) -> Dict[str, Any]:
    path = (export_path or "").strip()
    if not path or not os.path.isfile(path):
        raise ValueError("Valid path to export.xml required")
    parsed = _parse_health_export_xml(path, days=days)
    store = _load_snapshots()
    for day, metrics in parsed.items():
        existing = store.get(day, {})
        existing.update(metrics)
        existing["source"] = "health_export"
        existing["imported_at"] = datetime.now().isoformat()
        store[day] = existing
    _save_snapshots(store)
    return {"ok": True, "days_imported": len(parsed), "dates": sorted(parsed.keys(), reverse=True)}


@eel.expose
def refresh_screen_time_for_recent_days(days: int = 7) -> Dict[str, Any]:
    """Disabled — prior Knowledge DB heuristic was unreliable."""
    return {
        "ok": False,
        "updated": 0,
        "note": (
            "Screen Time import is experimental and currently disabled. "
            "Apple does not expose reliable Screen Time data to third-party apps on macOS."
        ),
    }


@eel.expose
def get_health_snapshot(local_date: str) -> Dict[str, Any]:
    store = _load_snapshots()
    return store.get(local_date, {})


@eel.expose
def get_health_snapshots_recent(limit: int = 14) -> List[Dict[str, Any]]:
    store = _load_snapshots()
    items = []
    for k in sorted(store.keys(), reverse=True)[: max(1, min(limit, 90))]:
        row = dict(store[k])
        row["local_date"] = k
        items.append(row)
    return items
