"""Consistency — planned hours, attendance, and to-do completion."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

import eel

import work

WINDOW_DAYS = {4: 28, 12: 84, 52: 365}
RATE_MEASURES = ("attendance", "hours", "todo_completion")


def coerce_days(days: Any) -> int:
    try:
        value = int(days or 28)
    except (TypeError, ValueError):
        value = 28
    return max(1, min(value, 365))


def coerce_window_weeks(value: Any) -> int:
    try:
        weeks = int(value or 4)
    except (TypeError, ValueError):
        weeks = 4
    if weeks in WINDOW_DAYS:
        return weeks
    if weeks >= 40:
        return 52
    if weeks >= 8:
        return 12
    return 4


def week_monday(day: date) -> date:
    return day - timedelta(days=day.weekday())


def bar_outcome(status: Any) -> str:
    key = str(status or "").strip().lower()
    if key == "done":
        return "done"
    if key in ("missed", "skipped"):
        return "missed"
    return "open"


def _minutes_between(start_at: Any, end_at: Any) -> int:
    try:
        start = datetime.fromisoformat(str(start_at))
        end = datetime.fromisoformat(str(end_at))
    except (TypeError, ValueError):
        return 0
    return max(0, int((end - start).total_seconds() // 60))


def _item_day(item: Dict[str, Any]) -> Optional[date]:
    raw = str(item.get("scheduled_date") or "")[:10] or str(item.get("due_at") or "")[:10]
    if len(raw) != 10:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def collect_bars(start: date, end: date) -> List[Dict[str, Any]]:
    import calclock

    bars: List[Dict[str, Any]] = []
    for item in calclock.expand_hard_events(start, end):
        minutes = int(item.get("minutes") or 0) or _minutes_between(item.get("start_at"), item.get("end_at"))
        day = str(item.get("occurrence_date") or item.get("local_date") or item.get("start_at") or "")[:10]
        bars.append(
            {
                "id": item.get("id"),
                "kind": "hard",
                "title": item.get("title") or "",
                "date": day,
                "minutes": max(0, minutes),
                "status": item.get("status") or "open",
                "outcome": bar_outcome(item.get("status")),
            }
        )
    for block in calclock.list_blocks(start, end):
        minutes = int(block.get("minutes") or 0) or _minutes_between(block.get("start_at"), block.get("end_at"))
        bars.append(
            {
                "id": block.get("id"),
                "kind": block.get("kind") or "work",
                "title": block.get("title") or "",
                "date": str(block.get("local_date") or "")[:10],
                "minutes": max(0, minutes),
                "status": block.get("status") or "open",
                "outcome": bar_outcome(block.get("status")),
            }
        )
    return bars


def dated_todos(start: date, end: date) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for item in work.list_all_work_items():
        day = _item_day(item)
        if day is None or day < start or day > end:
            continue
        packed = dict(item)
        packed["_day"] = day
        rows.append(packed)
    return rows


def _pct(part: int, whole: int) -> Optional[int]:
    if whole <= 0:
        return None
    return int(round(100 * part / whole))


def week_starts(start: date, end: date) -> List[date]:
    cursor = week_monday(start)
    last = week_monday(end)
    out: List[date] = []
    while cursor <= last:
        out.append(cursor)
        cursor += timedelta(days=7)
    return out


def summarize(days: Any = 28, today: Optional[date] = None) -> Dict[str, Any]:
    import calclock

    today = today or work._today()
    span = coerce_days(days)
    start = today - timedelta(days=span - 1)
    calclock.rollover_missed_bars(today)
    bars = collect_bars(start, today)
    todos = dated_todos(start, today)
    closed = [row for row in bars if row["outcome"] != "open"]
    attended = [row for row in closed if row["outcome"] == "done"]
    planned = sum(int(row["minutes"] or 0) for row in bars)
    todo_done = sum(1 for row in todos if str(row.get("status") or "") == "done")
    weeks = []
    for monday in week_starts(start, today):
        sunday = monday + timedelta(days=6)
        wbars = []
        for row in bars:
            try:
                day = date.fromisoformat(str(row.get("date") or ""))
            except ValueError:
                continue
            if monday <= day <= sunday:
                wbars.append(row)
        wtodos = [row for row in todos if monday <= row["_day"] <= sunday]
        wclosed = [row for row in wbars if row["outcome"] != "open"]
        wattended = [row for row in wclosed if row["outcome"] == "done"]
        wdone = sum(1 for row in wtodos if str(row.get("status") or "") == "done")
        wminutes = sum(int(row["minutes"] or 0) for row in wbars)
        weeks.append(
            {
                "week_start": monday.isoformat(),
                "label": f"{monday.strftime('%b')} {monday.day}",
                "minutes": wminutes,
                "hours": round(wminutes / 60, 1),
                "attended": len(wattended),
                "closed": len(wclosed),
                "attendance_pct": _pct(len(wattended), len(wclosed)),
                "todo_done": wdone,
                "todo_total": len(wtodos),
                "todo_pct": _pct(wdone, len(wtodos)),
            }
        )
    return {
        "period_start": start.isoformat(),
        "period_end": today.isoformat(),
        "days": span,
        "planned_minutes": planned,
        "hours": round(planned / 60, 1),
        "attended": len(attended),
        "closed": len(closed),
        "attendance_pct": _pct(len(attended), len(closed)),
        "todo_done": todo_done,
        "todo_total": len(todos),
        "todo_pct": _pct(todo_done, len(todos)),
        "weeks": weeks,
    }


def measure_current(data: Dict[str, Any], measure: str) -> Optional[float]:
    key = str(measure or "").strip().lower()
    if key == "hours":
        return float(data.get("hours") or 0)
    if key == "todo_completion":
        value = data.get("todo_pct")
        return None if value is None else float(value)
    value = data.get("attendance_pct")
    return None if value is None else float(value)


def rate_progress(
    measure: str,
    window_weeks: Any = 4,
    target_value: Any = None,
    today: Optional[date] = None,
    cache: Optional[Dict[int, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    weeks = coerce_window_weeks(window_weeks)
    days = WINDOW_DAYS[weeks]
    data = (cache or {}).get(weeks) or summarize(days, today)
    current = measure_current(data, measure)
    target = None
    if target_value not in (None, ""):
        try:
            target = float(target_value)
        except (TypeError, ValueError):
            target = None
    percent = None
    if target and target > 0 and current is not None:
        percent = min(100, int(round(100 * current / target)))
    return {
        "measure": str(measure or "").strip().lower(),
        "window_weeks": weeks,
        "current": current,
        "target": target,
        "percent": percent,
        "period_start": data.get("period_start"),
        "period_end": data.get("period_end"),
    }


@eel.expose
def get_consistency(days: int = 28) -> Dict[str, Any]:
    """Weekly hours, attendance, and to-do completion for the last N days."""
    return summarize(days)
