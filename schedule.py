"""Place study / gym blocks into free gaps. Never move hard events or locked blocks."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import eel

import calclock
import work
import workouts


def _now() -> datetime:
    return datetime.now().replace(microsecond=0)


def chunk_minutes(total: int, chunk_min: int = 50, chunk_max: int = 90) -> List[int]:
    remaining = max(0, int(total))
    if remaining <= 0:
        return []
    chunk_min = max(15, int(chunk_min))
    chunk_max = max(chunk_min, int(chunk_max))
    out: List[int] = []
    while remaining > 0:
        if remaining <= chunk_max:
            out.append(remaining)
            break
        out.append(chunk_max)
        remaining -= chunk_max
    return out


def _as_dt(day: date, hhmm: str) -> datetime:
    hour, minute = calclock.parse_clock(hhmm)
    return datetime.combine(day, datetime.min.time()).replace(hour=hour, minute=minute)


def _busy_intervals(
    day: date,
    *,
    hard: List[Dict[str, Any]],
    blocks: List[Dict[str, Any]],
    day_start: datetime,
    day_end: datetime,
) -> List[Tuple[datetime, datetime]]:
    iso = day.isoformat()
    busy: List[Tuple[datetime, datetime]] = []
    for event in hard:
        if event.get("occurrence_date") != iso:
            continue
        busy.append(
            (calclock.parse_datetime(event["start_at"]), calclock.parse_datetime(event["end_at"]))
        )
    for block in blocks:
        if block.get("local_date") != iso:
            continue
        if block.get("status") == "skipped":
            continue
        busy.append(
            (calclock.parse_datetime(block["start_at"]), calclock.parse_datetime(block["end_at"]))
        )
    clipped: List[Tuple[datetime, datetime]] = []
    for start, end in busy:
        lo = max(start, day_start)
        hi = min(end, day_end)
        if hi > lo:
            clipped.append((lo, hi))
    clipped.sort()
    merged: List[Tuple[datetime, datetime]] = []
    for start, end in clipped:
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
    *,
    minutes: int,
    from_dt: datetime,
    until_dt: datetime,
    hard: List[Dict[str, Any]],
    blocks: List[Dict[str, Any]],
    day_start: str,
    day_end: str,
) -> Optional[Tuple[datetime, datetime]]:
    need = timedelta(minutes=max(1, minutes))
    day = from_dt.date()
    last = until_dt.date()
    while day <= last:
        start_bound = _as_dt(day, day_start)
        end_bound = _as_dt(day, day_end)
        if until_dt.date() == day:
            end_bound = min(end_bound, until_dt)
        window_start = start_bound
        if from_dt.date() == day:
            window_start = max(start_bound, from_dt)
        if end_bound <= window_start:
            day += timedelta(days=1)
            continue
        busy = _busy_intervals(
            day,
            hard=hard,
            blocks=blocks,
            day_start=start_bound,
            day_end=end_bound,
        )
        for gap_start, gap_end in _gaps(busy, window_start, end_bound):
            if gap_end - gap_start >= need:
                return gap_start, gap_start + need
        day += timedelta(days=1)
    return None


def _clear_proposed(week_start: date, week_end: date) -> None:
    with calclock._connect() as conn:
        conn.execute(
            """
            DELETE FROM schedule_blocks
            WHERE status = 'proposed'
              AND local_date >= ?
              AND local_date <= ?
            """,
            (week_start.isoformat(), week_end.isoformat()),
        )
        conn.commit()


@eel.expose
def fill_week(week_start: str = "") -> Dict[str, Any]:
    settings = calclock.load_settings()
    start = date.fromisoformat(week_start) if week_start else calclock.monday_of(date.today())
    start = calclock.monday_of(start)
    end = start + timedelta(days=6)
    _clear_proposed(start, end)

    hard = calclock.expand_hard_events(start, end)
    blocks = calclock.list_blocks(start, end)
    placed = 0
    at_risk: List[str] = []
    now = _now()
    window_begin = max(now, datetime.combine(start, datetime.min.time()))

    for item in calclock.unplaced_work():
        leftover = int(item.get("remaining_minutes") or 0)
        if leftover <= 0:
            continue
        due_raw = item.get("due_at")
        until = datetime.combine(end, datetime.min.time()).replace(hour=23, minute=59)
        if due_raw:
            until = min(until, calclock.parse_datetime(due_raw))
        for chunk in chunk_minutes(leftover, settings["chunk_min"], settings["chunk_max"]):
            slot = find_slot(
                minutes=chunk,
                from_dt=window_begin,
                until_dt=until,
                hard=hard,
                blocks=blocks,
                day_start=settings["day_start"],
                day_end=settings["day_end"],
            )
            if slot is None:
                at_risk.append(item["id"])
                break
            block = calclock.add_block(
                title=item["title"],
                start=slot[0],
                end=slot[1],
                work_item_id=item["id"],
                kind="work",
                status="proposed",
            )
            blocks.append(block)
            placed += 1

    for offset in range(7):
        day = start + timedelta(days=offset)
        if day < date.today():
            continue
        try:
            kinds = workouts.expected_kinds_for_date(day)
        except Exception:
            kinds = []
        if not kinds:
            continue
        already = any(
            block.get("kind") == "workout" and block.get("local_date") == day.isoformat()
            for block in blocks
        )
        try:
            logged = bool((workouts.get_workout_day(day.isoformat()) or {}).get("done"))
        except Exception:
            logged = False
        if already or logged:
            continue
        label = " · ".join(workouts.KIND_LABELS.get(kind, kind) for kind in kinds)
        until = datetime.combine(day, datetime.min.time()).replace(hour=23, minute=59)
        slot = find_slot(
            minutes=60,
            from_dt=max(window_begin, datetime.combine(day, datetime.min.time())),
            until_dt=until,
            hard=hard,
            blocks=blocks,
            day_start=settings["day_start"],
            day_end=settings["day_end"],
        )
        if slot is None:
            continue
        block = calclock.add_block(
            title=f"Gym · {label}",
            start=slot[0],
            end=slot[1],
            work_item_id=None,
            kind="workout",
            status="proposed",
        )
        blocks.append(block)
        placed += 1

    week = calclock.get_week(start.isoformat())
    week["placed"] = placed
    week["at_risk_ids"] = list(dict.fromkeys(at_risk))
    return week
