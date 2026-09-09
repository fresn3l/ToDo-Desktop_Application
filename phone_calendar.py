"""Phone week clock helpers. Keep lockstep with ios/Kosistenz/PhoneCalendar.swift."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple


def parse_hhmm(raw: Optional[str], fallback: str = "05:30") -> Tuple[int, int]:
    text = str(raw or fallback).strip().replace(".", ":").replace(" ", "")
    if text.isdigit() and 3 <= len(text) <= 4:
        text = text.zfill(4)
        text = f"{text[:2]}:{text[2:]}"
    parts = text.split(":")
    try:
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
    except (TypeError, ValueError):
        hour, minute = 5, 30
    hour = max(0, min(23, hour))
    minute = max(0, min(59, minute))
    return hour, minute


def clock_window(day_start: Optional[str], day_end: Optional[str]) -> Tuple[int, int]:
    start_h, start_m = parse_hhmm(day_start, "05:30")
    end_h, end_m = parse_hhmm(day_end, "21:30")
    start_min = start_h * 60 + start_m
    end_min = end_h * 60 + end_m
    if end_min <= start_min:
        end_min = start_min + 60
    return start_min, end_min


def kind_label(kind: Optional[str], status: Optional[str] = None) -> str:
    raw = (kind or "").strip().lower()
    if raw == "hard":
        label = "Event"
    elif raw == "workout":
        label = "Gym"
    else:
        label = "Work"
    state = (status or "").strip().lower()
    if state in {"locked", "done", "skipped"}:
        return f"{label} · {state}"
    return label


def _parse(iso: Optional[str]) -> Optional[datetime]:
    raw = (iso or "").strip()
    if not raw:
        return None
    text = raw.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.replace(tzinfo=None)
    return parsed.replace(microsecond=0)


def expand_hard_event(
    event: Dict[str, Any],
    week_start: str,
    week_end: str,
) -> List[Dict[str, Any]]:
    """Paint one owned event onto the packed week. Overnight spans both days."""
    start = _parse(event.get("start_at"))
    end = _parse(event.get("end_at"))
    if start is None or end is None or end <= start:
        return []
    try:
        first = date.fromisoformat(str(week_start)[:10])
        last = date.fromisoformat(str(week_end)[:10])
    except ValueError:
        return []
    duration = end - start
    raw_days = event.get("weekdays") or []
    allowed = []
    for item in raw_days:
        try:
            day = int(item)
        except (TypeError, ValueError):
            continue
        if 0 <= day <= 6 and day not in allowed:
            allowed.append(day)
    out: List[Dict[str, Any]] = []
    title = (event.get("title") or "").strip()
    event_id = event.get("id") or title
    if allowed:
        cursor = first
        while cursor <= last:
            if cursor.weekday() in set(allowed) and cursor >= start.date():
                occ_start = datetime.combine(cursor, start.time())
                occ_end = occ_start + duration
                out.extend(_split_overnight(event_id, title, occ_start, occ_end, first, last))
            cursor += timedelta(days=1)
        return out
    last_day = end.date()
    if end.time() == datetime.min.time() and last_day > start.date():
        last_day -= timedelta(days=1)
    cursor = max(first, start.date())
    stop = min(last, last_day)
    while cursor <= stop:
        occ = _occurrence_on(event_id, title, start, end, cursor)
        if occ:
            out.append(occ)
        cursor += timedelta(days=1)
    return out


def _occurrence_on(
    event_id: Any,
    title: str,
    start: datetime,
    end: datetime,
    day: date,
) -> Optional[Dict[str, Any]]:
    last_day = end.date()
    if end.time() == datetime.min.time() and last_day > start.date():
        last_day -= timedelta(days=1)
    if day < start.date() or day > last_day:
        return None
    occ_start = start if day == start.date() else datetime.combine(day, datetime.min.time())
    if day < last_day:
        occ_end = datetime.combine(day + timedelta(days=1), datetime.min.time())
    else:
        occ_end = end
    if occ_end <= occ_start:
        return None
    return _clock_item(event_id, title, occ_start, occ_end, day)


def _split_overnight(
    event_id: Any,
    title: str,
    start: datetime,
    end: datetime,
    week_start: date,
    week_end: date,
) -> List[Dict[str, Any]]:
    rows = []
    last_day = end.date()
    if end.time() == datetime.min.time() and last_day > start.date():
        last_day -= timedelta(days=1)
    cursor = start.date()
    while cursor <= last_day:
        if week_start <= cursor <= week_end:
            occ = _occurrence_on(event_id, title, start, end, cursor)
            if occ:
                rows.append(occ)
        cursor += timedelta(days=1)
    return rows


def _clock_item(event_id: Any, title: str, start: datetime, end: datetime, day: date) -> Dict[str, Any]:
    return {
        "id": event_id,
        "title": title,
        "kind": "hard",
        "status": "locked",
        "start_at": start.isoformat(timespec="seconds"),
        "end_at": end.isoformat(timespec="seconds"),
        "occurrence_date": day.isoformat(),
    }


def paint_event_on_days(
    days: Iterable[Dict[str, Any]],
    event: Dict[str, Any],
    week_start: str,
    week_end: str,
) -> List[Dict[str, Any]]:
    painted = [dict(day) for day in days]
    by_date = {str(day.get("date") or ""): day for day in painted}
    for occ in expand_hard_event(event, week_start, week_end):
        day = by_date.get(occ["occurrence_date"])
        if day is None:
            continue
        events = [dict(item) for item in (day.get("events") or [])]
        events = [item for item in events if item.get("id") != occ["id"] or item.get("start_at") != occ["start_at"]]
        events.append(occ)
        events.sort(key=lambda item: str(item.get("start_at") or ""))
        day["events"] = events
    return painted
