"""
Optional Apple Health export + Screen Time imports (macOS, read-only).

Health: parse Apple Health export.xml (Export All Health Data).
Screen Time: best-effort read from Knowledge database (may require Full Disk Access).
"""

from __future__ import annotations

import json
import os
import sqlite3
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import eel

import daily_checklist

SLEEP_TYPE = "HKCategoryTypeIdentifierSleepAnalysis"
STEPS_TYPE = "HKQuantityTypeIdentifierStepCount"
WORKOUT_TAG = "Workout"


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
        try:
            dt = datetime.fromisoformat(start.replace("Z", "+00:00").split("+")[0])
        except (ValueError, TypeError):
            continue
        if dt.replace(tzinfo=None) < cutoff.replace(tzinfo=None):
            continue
        key = _day_key(dt)
        by_day.setdefault(key, {"sleep_hours": 0.0, "steps": 0, "workouts": []})

        if rtype == SLEEP_TYPE and rec.get("value") in ("HKCategoryValueSleepAnalysisAsleep", "Asleep"):
            end = rec.get("endDate") or start
            try:
                end_dt = datetime.fromisoformat(end.replace("Z", "+00:00").split("+")[0])
                hours = max(0.0, (end_dt - dt).total_seconds() / 3600.0)
                by_day[key]["sleep_hours"] = round(by_day[key]["sleep_hours"] + hours, 2)
            except (ValueError, TypeError):
                pass
        elif rtype == STEPS_TYPE:
            try:
                by_day[key]["steps"] += int(float(rec.get("value") or 0))
            except (ValueError, TypeError):
                pass

    for workout in root.iter(WORKOUT_TAG):
        start = workout.get("startDate") or ""
        try:
            dt = datetime.fromisoformat(start.replace("Z", "+00:00").split("+")[0])
        except (ValueError, TypeError):
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


def _try_screen_time_hours(local_date: str) -> Optional[float]:
    """Best-effort Screen Time total (hours) for one day."""
    db = Path.home() / "Library" / "Application Support" / "Knowledge" / "knowledgeC.db"
    if not db.exists():
        return None
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        # Heuristic: sum usage intervals overlapping the day (schema varies by macOS version)
        day_start = datetime.fromisoformat(local_date)
        day_end = day_start + timedelta(days=1)
        start_ts = day_start.timestamp()
        end_ts = day_end.timestamp()
        rows = conn.execute(
            """
            SELECT ZSTARTDATE, ZENDDATE
            FROM ZOBJECT
            WHERE ZSTARTDATE IS NOT NULL AND ZENDDATE IS NOT NULL
              AND ZENDDATE > ? AND ZSTARTDATE < ?
            LIMIT 5000
            """,
            (start_ts, end_ts),
        ).fetchall()
        conn.close()
        total = 0.0
        for r in rows:
            s = max(float(r["ZSTARTDATE"]), start_ts)
            e = min(float(r["ZENDDATE"]), end_ts)
            if e > s:
                total += e - s
        if total <= 0:
            return None
        return round(total / 3600.0, 2)
    except (sqlite3.Error, OSError, KeyError, TypeError):
        return None


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
        st = _try_screen_time_hours(day)
        if st is not None:
            existing["screen_time_hours"] = st
        store[day] = existing
    _save_snapshots(store)
    return {"ok": True, "days_imported": len(parsed), "dates": sorted(parsed.keys(), reverse=True)}


@eel.expose
def refresh_screen_time_for_recent_days(days: int = 7) -> Dict[str, Any]:
    store = _load_snapshots()
    updated = 0
    for i in range(days):
        d = (date.today() - timedelta(days=i)).isoformat()
        st = _try_screen_time_hours(d)
        if st is None:
            continue
        row = store.get(d, {})
        row["screen_time_hours"] = st
        row["screen_time_source"] = "knowledgeC.db"
        row["imported_at"] = datetime.now().isoformat()
        store[d] = row
        updated += 1
    _save_snapshots(store)
    return {
        "ok": True,
        "updated": updated,
        "note": "Screen Time requires Full Disk Access for Kosistenz/Python if reads fail.",
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
