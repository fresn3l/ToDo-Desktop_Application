"""Switchable year heatmap: streaks, journaling intensity, or one repeating series."""

from __future__ import annotations

import json
import os
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

import eel

import journal
import timeline
import work
import workouts
from paths import data_directory

SOURCES = ("show_up", "writing", "workout", "checkin", "journal", "series")
JOURNAL_FILTERS = ("all", "journal", "morning_brief", "evening_review", "reading")
SOURCE_LABELS = {
    "show_up": "Show up",
    "writing": "Writing streak",
    "workout": "Workout",
    "checkin": "Check-in",
    "journal": "Journaling",
    "series": "Repeating to do",
}


def _today() -> date:
    return date.today()


def _path():
    return data_directory() / "heatmap.json"


def _parse_day(raw: Any) -> Optional[date]:
    try:
        return date.fromisoformat(str(raw or "")[:10])
    except (TypeError, ValueError):
        return None


def _default_settings() -> Dict[str, str]:
    return {"source": "writing", "series_id": "", "journal_filter": "all"}


def _load_settings() -> Dict[str, str]:
    packed = _default_settings()
    path = _path()
    if not path.exists():
        return packed
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return packed
    if not isinstance(data, dict):
        return packed
    source = str(data.get("source") or "writing").strip()
    packed["source"] = source if source in SOURCES else "writing"
    packed["series_id"] = str(data.get("series_id") or "").strip()
    filt = str(data.get("journal_filter") or "all").strip()
    packed["journal_filter"] = filt if filt in JOURNAL_FILTERS else "all"
    return packed


def _save_settings(settings: Dict[str, str]) -> Dict[str, str]:
    path = _path()
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(settings, handle, indent=2)
    os.replace(tmp, path)
    return settings


def _monday_on_or_before(day: date) -> date:
    return day - timedelta(days=day.weekday())


def _grid_range(days: int, today: date) -> tuple[date, date]:
    days = max(14, min(int(days or 365), 400))
    start = _monday_on_or_before(today - timedelta(days=days - 1))
    return start, today


def _empty_days(start: date, end: date) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    cursor = start
    while cursor <= end:
        rows.append(
            {
                "date": cursor.isoformat(),
                "weekday": cursor.strftime("%a"),
                "value": 0,
                "state": "none",
                "kinds": {},
            }
        )
        cursor += timedelta(days=1)
    return rows


def _journal_dates(span: int) -> Dict[str, Dict[str, int]]:
    by_day: Dict[str, Dict[str, int]] = {}
    for entry in journal.get_recent_entries(days=span):
        day = _parse_day(entry.get("date") or entry.get("created_at") or "")
        if not day:
            continue
        kind = journal.normalize_journal_kind(entry.get("kind"))
        iso = day.isoformat()
        bucket = by_day.setdefault(iso, {})
        bucket[kind] = bucket.get(kind, 0) + 1
        bucket["all"] = bucket.get("all", 0) + 1
    return by_day


def _workout_dates() -> set:
    out = set()
    for iso in workouts.list_workout_dates():
        day = _parse_day(iso)
        if day:
            out.add(day.isoformat())
    return out


def _checkin_dates() -> set:
    import daily_checklist

    out = set()
    for iso in daily_checklist.list_submission_dates():
        day = _parse_day(iso)
        if day:
            out.add(day.isoformat())
    return out


def _fill_binary(rows: List[Dict[str, Any]], hits: set) -> None:
    for row in rows:
        if row["date"] in hits:
            row["value"] = 1
            row["state"] = "hit"


def _series_streak(rows: List[Dict[str, Any]], today: date) -> int:
    by_date = {row["date"]: row for row in rows}

    def state_of(day: date) -> str:
        row = by_date.get(day.isoformat())
        return (row or {}).get("state") or "none"

    cursor = today
    today_state = state_of(today)
    if today_state in ("none", "pending", "skip"):
        cursor = today - timedelta(days=1)
    n = 0
    while True:
        iso = cursor.isoformat()
        row = by_date.get(iso)
        if row is None:
            break
        state = row.get("state")
        if state == "skip" or state == "none":
            cursor -= timedelta(days=1)
            continue
        if state != "hit":
            break
        n += 1
        cursor -= timedelta(days=1)
    return n


@eel.expose
def get_heatmap_settings() -> Dict[str, Any]:
    settings = _load_settings()
    return {
        **settings,
        "sources": [{"id": key, "label": SOURCE_LABELS[key]} for key in SOURCES],
        "series": work.list_repeating_series(),
        "journal_filters": list(JOURNAL_FILTERS),
    }


@eel.expose
def save_heatmap_settings(
    source: str = "",
    series_id: str = "",
    journal_filter: str = "",
) -> Dict[str, Any]:
    settings = _load_settings()
    key = str(source or "").strip()
    if key in SOURCES:
        settings["source"] = key
    sid = str(series_id or "").strip()
    if sid or key == "series" or source:
        settings["series_id"] = sid
    filt = str(journal_filter or "").strip()
    if filt in JOURNAL_FILTERS:
        settings["journal_filter"] = filt
    _save_settings(settings)
    return get_heatmap()


@eel.expose
def get_heatmap(
    source: str = "",
    series_id: str = "",
    journal_filter: str = "",
    days: int = 365,
) -> Dict[str, Any]:
    settings = _load_settings()
    key = str(source or "").strip() or settings["source"]
    if key not in SOURCES:
        key = "writing"
    sid = str(series_id if series_id is not None else settings.get("series_id") or "").strip()
    if source and key != "series":
        sid = ""
    filt = str(journal_filter or "").strip() or settings.get("journal_filter") or "all"
    if filt not in JOURNAL_FILTERS:
        filt = "all"
    today = _today()
    start, end = _grid_range(days, today)
    span = (today - start).days + 2
    rows = _empty_days(start, end)
    streak = 0
    series_title = ""
    cadence_label = ""

    journal_days = _journal_dates(span)
    workout_days = _workout_dates()
    checkin_days = _checkin_dates()
    writing_hits = set(journal_days)
    show_up = writing_hits | workout_days | checkin_days
    streaks = timeline.compute_streaks(today)

    if key == "show_up":
        _fill_binary(rows, show_up)
        streak = int(streaks.get("show_up") or 0)
    elif key == "writing":
        _fill_binary(rows, writing_hits)
        streak = int(streaks.get("writing") or 0)
    elif key == "workout":
        _fill_binary(rows, workout_days)
        streak = int(streaks.get("workout") or 0)
    elif key == "checkin":
        _fill_binary(rows, checkin_days)
        streak = int(streaks.get("checkin") or 0)
    elif key == "journal":
        max_val = 1
        for row in rows:
            bucket = journal_days.get(row["date"]) or {}
            if filt == "all":
                value = int(bucket.get("all") or 0)
                kinds = {k: v for k, v in bucket.items() if k != "all"}
            else:
                value = int(bucket.get(filt) or 0)
                kinds = {filt: value} if value else {}
            row["value"] = value
            row["kinds"] = kinds
            row["state"] = "hit" if value else "none"
            max_val = max(max_val, value)
        streak = int(streaks.get("writing") or 0)
        for row in rows:
            row["max"] = max_val
    else:
        series_days = work.series_heatmap_days(sid, start, end, today) if sid else []
        by_date = {row["date"]: row for row in series_days}
        for row in rows:
            match = by_date.get(row["date"])
            if not match:
                continue
            row["state"] = match["state"]
            row["value"] = int(match.get("value") or 0)
        for item in work.list_repeating_series():
            if item["id"] == sid:
                series_title = item.get("title") or ""
                cadence_label = item.get("cadence_label") or ""
                break
        streak = _series_streak(rows, today)

    return {
        "source": key,
        "source_label": SOURCE_LABELS.get(key, key),
        "series_id": sid,
        "series_title": series_title,
        "cadence_label": cadence_label,
        "journal_filter": filt,
        "streak": streak,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "today": today.isoformat(),
        "days": rows,
        "sources": [{"id": name, "label": SOURCE_LABELS[name]} for name in SOURCES],
        "series": work.list_repeating_series(),
        "journal_filters": list(JOURNAL_FILTERS),
    }
