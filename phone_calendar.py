"""Phone week clock helpers. Keep lockstep with ios/Kosistenz/PhoneCalendar.swift."""

from __future__ import annotations

import re
import uuid
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple

WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
CHUNK_MIN = 50
CHUNK_MAX = 90
DEFAULT_ESTIMATE = 60
ICS_BYDAY = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}


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


def monday_of(iso: str) -> str:
    day = date.fromisoformat(str(iso)[:10])
    return (day - timedelta(days=day.weekday())).isoformat()


def empty_week(week_start: str, today: str) -> List[Dict[str, Any]]:
    start = date.fromisoformat(monday_of(week_start))
    today_iso = str(today or "")[:10]
    days: List[Dict[str, Any]] = []
    for offset in range(7):
        day = start + timedelta(days=offset)
        iso = day.isoformat()
        days.append(
            {
                "date": iso,
                "weekday": WEEKDAY_LABELS[offset],
                "is_today": iso == today_iso,
                "events": [],
                "blocks": [],
                "dues": [],
            }
        )
    return days


def remaining_minutes(estimate: Any, placed: Any, status: Any = None) -> int:
    if str(status or "").strip().lower() == "done":
        return 0
    try:
        total = int(estimate or 0)
    except (TypeError, ValueError):
        total = 0
    if total <= 0:
        return 0
    try:
        used = int(placed or 0)
    except (TypeError, ValueError):
        used = 0
    return max(0, total - used)


def span_minutes(start_at: Optional[str], end_at: Optional[str]) -> int:
    start = _parse(start_at)
    end = _parse(end_at)
    if start is None or end is None or end <= start:
        return 0
    return max(0, int((end - start).total_seconds() // 60))


def placed_minutes(blocks: Iterable[Dict[str, Any]], item_id: str) -> int:
    key = str(item_id or "").strip()
    if not key:
        return 0
    total = 0
    for block in blocks:
        if str(block.get("work_item_id") or "") != key:
            continue
        total += span_minutes(block.get("start_at"), block.get("end_at"))
    return total


def flatten_blocks(days: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for day in days:
        out.extend(list(day.get("blocks") or []))
    return out


def unplaced_from_work(items: Iterable[Dict[str, Any]], blocks: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    clock = list(blocks)
    out: List[Dict[str, Any]] = []
    for item in items:
        if str(item.get("status") or "").strip().lower() == "done":
            continue
        if str(item.get("source") or "").strip().lower() == "calendar":
            continue
        leftover = remaining_minutes(
            item.get("estimate_minutes"),
            placed_minutes(clock, str(item.get("id") or "")),
            item.get("status"),
        )
        if leftover <= 0:
            continue
        packed = dict(item)
        packed["remaining_minutes"] = leftover
        out.append(packed)
    out.sort(key=lambda row: (str(row.get("due_at") or "9999"), str(row.get("created_at") or "")))
    return out


def chunk_minutes(total: int, chunk_min: int = CHUNK_MIN, chunk_max: int = CHUNK_MAX) -> List[int]:
    remaining = max(0, int(total))
    if remaining <= 0:
        return []
    low = max(15, int(chunk_min))
    high = max(low, int(chunk_max))
    out: List[int] = []
    while remaining > 0:
        if remaining <= high:
            out.append(remaining)
            break
        out.append(high)
        remaining -= high
    return out


def _as_dt(day: date, hhmm: Optional[str], fallback: str) -> datetime:
    hour, minute = parse_hhmm(hhmm, fallback)
    return datetime.combine(day, datetime.min.time()).replace(hour=hour, minute=minute)


def _busy_on_day(
    day: Dict[str, Any],
    start_bound: datetime,
    end_bound: datetime,
) -> List[Tuple[datetime, datetime]]:
    busy: List[Tuple[datetime, datetime]] = []
    for item in list(day.get("events") or []) + list(day.get("blocks") or []):
        if str(item.get("kind") or "") != "focus" and str(item.get("status") or "").strip().lower() == "skipped":
            continue
        start = _parse(item.get("start_at"))
        end = _parse(item.get("end_at"))
        if start is None or end is None:
            continue
        lo = max(start, start_bound)
        hi = min(end, end_bound)
        if hi > lo:
            busy.append((lo, hi))
    busy.sort()
    merged: List[Tuple[datetime, datetime]] = []
    for start, end in busy:
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
    return merged


def _gaps(
    busy: List[Tuple[datetime, datetime]],
    window_start: datetime,
    window_end: datetime,
) -> List[Tuple[datetime, datetime]]:
    gaps: List[Tuple[datetime, datetime]] = []
    cursor = window_start
    for start, end in busy:
        if start > cursor:
            gaps.append((cursor, start))
        cursor = max(cursor, end)
    if window_end > cursor:
        gaps.append((cursor, window_end))
    return [(a, b) for a, b in gaps if (b - a).total_seconds() >= 15 * 60]


def find_slot(
    days: Iterable[Dict[str, Any]],
    minutes: int,
    from_dt: datetime,
    until_dt: datetime,
    day_start: Optional[str],
    day_end: Optional[str],
) -> Optional[Tuple[datetime, datetime]]:
    need = timedelta(minutes=max(1, int(minutes)))
    by_date = {str(day.get("date") or ""): day for day in days}
    day = from_dt.date()
    last = until_dt.date()
    while day <= last:
        row = by_date.get(day.isoformat())
        if row is None:
            day += timedelta(days=1)
            continue
        start_bound = _as_dt(day, day_start, "05:30")
        end_bound = _as_dt(day, day_end, "21:30")
        if until_dt.date() == day:
            end_bound = min(end_bound, until_dt)
        window_start = start_bound
        if from_dt.date() == day:
            window_start = max(start_bound, from_dt)
        if end_bound <= window_start:
            day += timedelta(days=1)
            continue
        busy = _busy_on_day(row, start_bound, end_bound)
        for gap_start, gap_end in _gaps(busy, window_start, end_bound):
            if gap_end - gap_start >= need:
                return gap_start, gap_start + need
        day += timedelta(days=1)
    return None


def _clear_proposed(days: Iterable[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    painted = [dict(day) for day in days]
    removed: List[str] = []
    for day in painted:
        kept: List[Dict[str, Any]] = []
        for block in day.get("blocks") or []:
            status = str(block.get("status") or "").strip().lower()
            kind = str(block.get("kind") or "").strip().lower()
            if status == "proposed" and kind != "focus":
                key = str(block.get("id") or "").strip()
                if key:
                    removed.append(key)
                continue
            kept.append(dict(block))
        day["blocks"] = kept
    return painted, removed


def _clock_block(
    *,
    item_id: str,
    title: str,
    start: datetime,
    end: datetime,
    work_item_id: Optional[str],
    kind: str = "work",
) -> Dict[str, Any]:
    return {
        "id": item_id,
        "title": title,
        "kind": kind,
        "status": "proposed",
        "start_at": start.isoformat(timespec="seconds"),
        "end_at": end.isoformat(timespec="seconds"),
        "work_item_id": work_item_id,
        "source": "iphone",
        "occurrence_date": start.date().isoformat(),
        "updated_at": start.replace(microsecond=0).isoformat(timespec="seconds"),
    }


def _append_block(days: List[Dict[str, Any]], block: Dict[str, Any]) -> None:
    iso = str(block.get("start_at") or "")[:10]
    for day in days:
        if str(day.get("date") or "") != iso:
            continue
        blocks = [dict(item) for item in (day.get("blocks") or [])]
        blocks = [item for item in blocks if item.get("id") != block.get("id")]
        blocks.append(dict(block))
        blocks.sort(key=lambda item: str(item.get("start_at") or ""))
        day["blocks"] = blocks
        return


def fill_week(
    days: Iterable[Dict[str, Any]],
    items: Iterable[Dict[str, Any]],
    day_start: Optional[str],
    day_end: Optional[str],
    now: Optional[datetime] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
    """Pack leftover work into free gaps. Same chunk sizes as Mac Fill week."""
    painted, removed = _clear_proposed(days)
    if not painted:
        return painted, [], removed
    start = date.fromisoformat(str(painted[0].get("date") or "")[:10])
    end = date.fromisoformat(str(painted[-1].get("date") or "")[:10])
    clock_now = (now or datetime.now()).replace(microsecond=0)
    window_begin = max(clock_now, datetime.combine(start, datetime.min.time()))
    placed: List[Dict[str, Any]] = []
    clock = flatten_blocks(painted)
    for item in items:
        work_id = str(item.get("id") or "").strip()
        leftover = remaining_minutes(
            item.get("estimate_minutes"),
            placed_minutes(clock, work_id),
            item.get("status"),
        )
        if leftover <= 0:
            leftover = int(item.get("remaining_minutes") or 0)
        if leftover <= 0:
            continue
        until = datetime.combine(end, datetime.min.time()).replace(hour=23, minute=59)
        from_dt = window_begin
        scheduled = str(item.get("scheduled_date") or "")[:10]
        if scheduled:
            try:
                pinned = date.fromisoformat(scheduled)
            except ValueError:
                pinned = None
            if pinned is not None:
                if pinned < start or pinned > end:
                    continue
                from_dt = max(window_begin, datetime.combine(pinned, datetime.min.time()))
                until = min(until, _as_dt(pinned, day_end, "21:30"))
        due = _parse(str(item.get("due_at") or "") or None)
        if due is not None:
            until = min(until, due)
        chunks = [leftover] if leftover <= CHUNK_MAX else chunk_minutes(leftover)
        title = str(item.get("title") or "").strip()
        for chunk in chunks:
            slot = find_slot(painted, chunk, from_dt, until, day_start, day_end)
            if slot is None:
                break
            block = _clock_block(
                item_id=str(uuid.uuid4()),
                title=title,
                start=slot[0],
                end=slot[1],
                work_item_id=work_id or None,
                kind="work",
            )
            _append_block(painted, block)
            clock.append(block)
            placed.append(block)
    return painted, placed, removed


def place_work_at(
    days: Iterable[Dict[str, Any]],
    item: Dict[str, Any],
    start_at: str,
    end_at: str = "",
    day_end: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    start = _parse(start_at)
    if start is None:
        raise ValueError("Use a 24-hour time like 0930 or 09:30.")
    leftover = int(item.get("remaining_minutes") or item.get("estimate_minutes") or DEFAULT_ESTIMATE)
    duration = max(15, min(leftover if leftover > 0 else DEFAULT_ESTIMATE, CHUNK_MAX))
    end = _parse(end_at) if end_at else start + timedelta(minutes=duration)
    if end is None or end <= start:
        end = start + timedelta(minutes=duration)
    hours = (end - start).total_seconds() / 3600
    if hours > 12:
        raise ValueError("Events longer than 12 hours need to be split")
    painted = [dict(day) for day in days]
    block = _clock_block(
        item_id=str(uuid.uuid4()),
        title=str(item.get("title") or "").strip(),
        start=start,
        end=end,
        work_item_id=str(item.get("id") or "").strip() or None,
        kind="work",
    )
    _append_block(painted, block)
    return painted, block


def dues_for_day(items: Iterable[Dict[str, Any]], iso: str) -> List[Dict[str, Any]]:
    day = str(iso or "")[:10]
    out: List[Dict[str, Any]] = []
    for item in items:
        due = str(item.get("due_at") or "")[:10]
        if due != day:
            continue
        if str(item.get("status") or "").strip().lower() == "done":
            continue
        out.append(
            {
                "id": item.get("id"),
                "title": item.get("title") or "",
                "due_at": item.get("due_at"),
                "status": item.get("status") or "open",
                "estimate_minutes": item.get("estimate_minutes"),
            }
        )
    return out


def assemble_week(
    week_start: str,
    today: str,
    packed_days: Iterable[Dict[str, Any]],
    hard_events: Iterable[Dict[str, Any]],
    phone_blocks: Iterable[Dict[str, Any]] = (),
    work_items: Iterable[Dict[str, Any]] = (),
) -> List[Dict[str, Any]]:
    start = monday_of(week_start)
    end = (date.fromisoformat(start) + timedelta(days=6)).isoformat()
    packed_by = {str(day.get("date") or ""): day for day in packed_days or []}
    days = empty_week(start, today)
    packed_this_week = any(str(day.get("date") or "") == start for day in packed_days or [])
    if packed_this_week:
        for day in days:
            src = packed_by.get(str(day.get("date") or ""))
            if src is None:
                day["dues"] = dues_for_day(work_items, day["date"])
                continue
            day["events"] = [dict(item) for item in (src.get("events") or [])]
            day["blocks"] = [dict(item) for item in (src.get("blocks") or [])]
            packed_dues = [dict(item) for item in (src.get("dues") or [])]
            day["dues"] = packed_dues or dues_for_day(work_items, day["date"])
        for block in phone_blocks or []:
            _append_block(days, dict(block))
        return days
    for day in days:
        day["dues"] = dues_for_day(work_items, day["date"])
    for event in hard_events or []:
        days = paint_event_on_days(days, event, start, end)
    for block in phone_blocks or []:
        _append_block(days, dict(block))
    return days


def month_weeks(
    year: int,
    month: int,
    today: str,
    event_dates: Dict[str, int],
    block_dates: Dict[str, int],
    due_dates: Dict[str, int],
) -> List[List[Dict[str, Any]]]:
    first = date(int(year), int(month), 1)
    cursor = first - timedelta(days=first.weekday())
    today_iso = str(today or "")[:10]
    weeks: List[List[Dict[str, Any]]] = []
    for _ in range(6):
        week: List[Dict[str, Any]] = []
        for _offset in range(7):
            iso = cursor.isoformat()
            event_count = int(event_dates.get(iso, 0))
            block_count = int(block_dates.get(iso, 0))
            due_count = int(due_dates.get(iso, 0))
            week.append(
                {
                    "date": iso,
                    "day": cursor.day,
                    "in_month": cursor.month == month,
                    "is_today": iso == today_iso,
                    "event_count": event_count,
                    "block_count": block_count,
                    "due_count": due_count,
                    "has_items": bool(event_count or block_count or due_count),
                }
            )
            cursor += timedelta(days=1)
        weeks.append(week)
    return weeks


def count_dates(items: Iterable[Dict[str, Any]], key: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for item in items:
        iso = str(item.get(key) or item.get("occurrence_date") or item.get("start_at") or "")[:10]
        if len(iso) != 10:
            continue
        counts[iso] = counts.get(iso, 0) + 1
    return counts


def parse_ics_datetime(raw: str) -> Optional[datetime]:
    text = str(raw or "").strip().replace("Z", "")
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) >= 8:
        year = int(digits[0:4])
        month = int(digits[4:6])
        day = int(digits[6:8])
        hour = int(digits[8:10]) if len(digits) >= 10 else 0
        minute = int(digits[10:12]) if len(digits) >= 12 else 0
        second = int(digits[12:14]) if len(digits) >= 14 else 0
        try:
            return datetime(year, month, day, hour, minute, second)
        except ValueError:
            return None
    return _parse(text)


def parse_ics_events(text: str) -> List[Dict[str, Any]]:
    """Phone-sized ICS: SUMMARY, DTSTART, DTEND, weekly BYDAY. Keep lockstep with Swift."""
    unfolded = (
        str(text or "")
        .replace("\r\n ", "")
        .replace("\n ", "")
        .replace("\r\n", "\n")
    )
    chunks = re.split(r"BEGIN:VEVENT", unfolded, flags=re.IGNORECASE)[1:]
    out: List[Dict[str, Any]] = []
    for chunk in chunks:
        body = re.split(r"END:VEVENT", chunk, flags=re.IGNORECASE)[0]
        fields: Dict[str, str] = {}
        for line in body.splitlines():
            if ":" not in line:
                continue
            key, _, val = line.partition(":")
            name = key.split(";")[0].strip().upper()
            fields[name] = val.strip()
        title = (fields.get("SUMMARY") or "").strip()
        start = parse_ics_datetime(fields.get("DTSTART") or "")
        if not title or start is None:
            continue
        end = parse_ics_datetime(fields.get("DTEND") or "")
        if end is None or end <= start:
            end = start + timedelta(minutes=50)
        weekdays: List[int] = []
        rrule = fields.get("RRULE") or ""
        if "FREQ=WEEKLY" in rrule.upper():
            for part in rrule.split(";"):
                if part.upper().startswith("BYDAY="):
                    for token in part.split("=", 1)[1].split(","):
                        day = ICS_BYDAY.get(token.strip().upper()[:2])
                        if day is not None and day not in weekdays:
                            weekdays.append(day)
        hours = (end - start).total_seconds() / 3600
        if hours > 12:
            continue
        out.append(
            {
                "title": title[:200],
                "start_at": start.isoformat(timespec="seconds"),
                "end_at": end.isoformat(timespec="seconds"),
                "weekdays": weekdays,
            }
        )
    return out
