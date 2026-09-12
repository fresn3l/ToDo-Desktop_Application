"""Home glance beats — now/next, unplaced, dues, free time. No new stores."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

import eel

import work

SKIPPABLE_KINDS = frozenset({"work", "workout"})
SKIPPABLE_STATUSES = frozenset({"proposed", "locked"})


def _parse_dt(raw: Any) -> Optional[datetime]:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")[:19])
    except ValueError:
        return None


def _minutes_between(start: datetime, end: datetime) -> int:
    return max(0, int((end - start).total_seconds() // 60))


def _slim_item(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": item.get("id"),
        "title": item.get("title") or "",
        "start_at": item.get("start_at"),
        "end_at": item.get("end_at"),
        "kind": item.get("kind") or "",
        "status": item.get("status") or "",
        "work_item_id": item.get("work_item_id"),
    }


def clock_beat(
    agenda: List[Dict[str, Any]],
    *,
    now: Optional[datetime] = None,
    day_end: str = "21:30",
) -> Dict[str, Any]:
    """Now / next / gap from today's timed items. Skipped blocks do not occupy."""
    current = now or datetime.now()
    live: List[Dict[str, Any]] = []
    for item in agenda or []:
        if str(item.get("status") or "") in ("skipped", "missed"):
            continue
        start = _parse_dt(item.get("start_at"))
        end = _parse_dt(item.get("end_at"))
        if start is None or end is None or end <= start:
            continue
        packed = dict(item)
        packed["_start"] = start
        packed["_end"] = end
        live.append(packed)
    live.sort(key=lambda row: row["_start"])

    now_item = next((row for row in live if row["_start"] <= current < row["_end"]), None)
    nxt = next((row for row in live if row["_start"] > current), None)
    end_clock = _parse_dt(f"{current.date().isoformat()}T{day_end}:00")
    if now_item and nxt:
        gap = _minutes_between(now_item["_end"], nxt["_start"])
    elif now_item and end_clock:
        gap = _minutes_between(now_item["_end"], end_clock)
    elif nxt:
        gap = _minutes_between(current, nxt["_start"])
    elif end_clock and end_clock > current:
        gap = _minutes_between(current, end_clock)
    else:
        gap = 0

    focus = now_item or nxt
    can_skip = bool(
        focus
        and str(focus.get("kind") or "") in SKIPPABLE_KINDS
        and str(focus.get("status") or "") in SKIPPABLE_STATUSES
        and focus.get("id")
    )
    return {
        "now": _slim_item(now_item) if now_item else None,
        "next": _slim_item(nxt) if nxt else None,
        "gap_minutes": gap,
        "phase": "now" if now_item else ("next" if nxt else "clear"),
        "can_skip": can_skip,
        "focus_id": (focus or {}).get("id") if focus else None,
    }


def week_days(today: Optional[date] = None) -> List[Dict[str, str]]:
    day = today or date.today()
    monday = day - timedelta(days=day.weekday())
    labels = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
    return [
        {"label": labels[offset], "date": (monday + timedelta(days=offset)).isoformat()}
        for offset in range(7)
    ]


def dues_this_week(today: Optional[date] = None) -> Dict[str, Any]:
    import calclock

    day = today or date.today()
    monday = calclock.monday_of(day)
    sunday = monday + timedelta(days=6)
    grouped = calclock._dues_by_day(monday, sunday)
    rows: List[Dict[str, Any]] = []
    for iso in sorted(grouped.keys()):
        for item in grouped[iso]:
            if str(item.get("status") or "") == "done":
                continue
            rows.append(
                {
                    "id": item.get("id"),
                    "title": item.get("title") or "",
                    "due": iso,
                    "status": item.get("status") or "open",
                }
            )
    return {
        "week_start": monday.isoformat(),
        "week_end": sunday.isoformat(),
        "items": rows[:12],
        "count": len(rows),
    }


def unplaced_glance() -> Dict[str, Any]:
    import calclock

    shown, total = calclock._unplaced_ui()
    return {
        "items": shown,
        "count": total,
        "weekdays": week_days(),
    }


def now_next_glance() -> Dict[str, Any]:
    import calclock

    iso = date.today().isoformat()
    settings = calclock.load_settings()
    agenda = calclock.get_day_agenda(iso).get("items") or []
    beat = clock_beat(agenda, day_end=str(settings.get("day_end") or "21:30"))
    beat["local_date"] = iso
    return beat


@eel.expose
def get_now_next_glance() -> Dict[str, Any]:
    return now_next_glance()


@eel.expose
def get_unplaced_glance() -> Dict[str, Any]:
    return unplaced_glance()


@eel.expose
def get_dues_week_glance() -> Dict[str, Any]:
    return dues_this_week()


@eel.expose
def glance_skip_block(block_id: str) -> Dict[str, Any]:
    import calclock

    return calclock.set_block_status(block_id, "skipped")


@eel.expose
def glance_finish_work(item_id: str) -> Dict[str, Any]:
    return work.finish_work_item(item_id)


@eel.expose
def glance_park_work(item_id: str) -> Dict[str, Any]:
    return work.assign_work_item(item_id, "")


@eel.expose
def glance_plus15(item_id: str) -> Dict[str, Any]:
    rows = work.get_work_items_by_ids([item_id])
    if not rows:
        raise ValueError("Work item not found")
    item = rows[0]
    try:
        base = int(item.get("estimate_minutes") or 0)
    except (TypeError, ValueError):
        base = 0
    return work.update_work_plan(item_id, item.get("due_at"), base + 15)


@eel.expose
def glance_do_today(item_id: str) -> Dict[str, Any]:
    return work.assign_work_item(item_id, work._today().isoformat())


@eel.expose
def glance_place_unplaced(item_id: str, scheduled_date: str) -> Dict[str, Any]:
    return work.assign_work_item(item_id, scheduled_date)


@eel.expose
def glance_log_expected_workout(
    kind: str = "",
    miles: Any = None,
    other_label: str = "",
) -> Dict[str, Any]:
    import workouts

    key = str(kind or "").strip().lower()
    iso = date.today().isoformat()
    expected = workouts.expected_kinds_for_date(date.today())
    if not key:
        key = expected[0] if expected else "other"
    if key == "other" and not str(other_label or "").strip():
        other_label = "Session"
    mile_val = 0 if key == "running" and miles in (None, "") else miles
    return workouts.add_workout_session(
        iso,
        key,
        other_label=str(other_label or "").strip(),
        miles=mile_val,
    )
