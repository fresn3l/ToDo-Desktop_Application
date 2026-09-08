"""Read-only Kosistenz life snapshot for Cluny.

Assembled from existing APIs. Never opens Cluny's SQLite. Failures never
block a local save. The widget snapshot stays a thin today-count for the
menu bar; this file is the week + journal + logged work Cluny can read.
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import eel

ASK_INSTRUCTION = (
    "You are Cluny, the local brain. Kosistenz owns the list and the clock. "
    "Answer from this context: journal excerpts (what you wrote), logged work "
    "(done items and workout sessions), the week clock (hard events vs placed "
    "blocks vs unplaced), and goal minutes. When asked what is on today, list "
    "todos_today, events_today, and overdue items. When asked about free time, "
    "recommend open to-dos by title using estimates and free_minutes as capacity. "
    "Never pick a clock time or say to do something at HH:MM. "
    "The user still picks the day; Fill week places the gap."
)

JOURNAL_LIMIT = 40
EXCERPT_CHARS = 400
LOG_DAYS = 14
BRIEF_DAYS = 7


def get_life_snapshot_path() -> Path:
    import work

    return work._data_dir() / "cluny_life_snapshot.json"


def _excerpt(text: Any, limit: int = EXCERPT_CHARS) -> str:
    raw = " ".join(str(text or "").split())
    if len(raw) <= limit:
        return raw
    return raw[: max(1, limit - 1)].rstrip() + "…"


def _hhmm(raw: Any) -> Optional[str]:
    text = str(raw or "").strip()
    if not text:
        return None
    if "T" in text:
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00")[:32])
            return parsed.strftime("%H:%M")
        except ValueError:
            pass
    if len(text) >= 5 and text[2] == ":":
        return text[:5]
    return text[:16]


def _minutes(hhmm: Optional[str]) -> Optional[int]:
    text = str(hhmm or "").strip()
    if len(text) < 5 or text[2] != ":":
        return None
    try:
        return int(text[:2]) * 60 + int(text[3:5])
    except ValueError:
        return None


def free_minutes(events: List[Dict[str, Any]], day_start: str, day_end: str) -> int:
    start = _minutes(day_start) or (5 * 60 + 30)
    end = _minutes(day_end) or (21 * 60 + 30)
    if end <= start:
        return 0
    busy_raw: List[tuple[int, int]] = []
    for event in events:
        begin = _minutes(event.get("start"))
        finish = _minutes(event.get("end"))
        if begin is None or finish is None:
            continue
        begin = max(start, begin)
        finish = min(end, finish)
        if finish <= begin:
            continue
        busy_raw.append((begin, finish))
    busy_raw.sort()
    busy: List[List[int]] = []
    for begin, finish in busy_raw:
        if busy and begin <= busy[-1][1]:
            busy[-1][1] = max(busy[-1][1], finish)
        else:
            busy.append([begin, finish])
    used = sum(finish - begin for begin, finish in busy)
    return max(0, end - start - used)


def _work_slim(item: Dict[str, Any]) -> Dict[str, Any]:
    due = str(item.get("due_at") or "").strip()
    return {
        "id": item.get("id"),
        "title": item.get("title") or "",
        "scheduled_date": item.get("scheduled_date"),
        "status": item.get("status") or "open",
        "duration_seconds": int(item.get("duration_seconds") or 0),
        "finished_at": item.get("finished_at"),
        "due_at": due[:19] or None,
        "estimate_minutes": item.get("estimate_minutes"),
        "goal_id": item.get("goal_id"),
    }


def _ask_work_row(item: Dict[str, Any]) -> Dict[str, Any]:
    due = str(item.get("due_at") or "").strip()
    return {
        "title": item.get("title") or "",
        "due": due[:10] or None,
        "estimate_minutes": item.get("estimate_minutes"),
        "status": item.get("status") or "open",
        "duration_seconds": int(item.get("duration_seconds") or 0),
        "finished_at": item.get("finished_at"),
    }


def _cal_slim(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "title": item.get("title") or "",
        "kind": item.get("kind") or "",
        "status": item.get("status") or "",
        "start": _hhmm(item.get("start_at")),
        "end": _hhmm(item.get("end_at")),
        "start_at": item.get("start_at"),
        "end_at": item.get("end_at"),
    }


def _journal_rows() -> List[Dict[str, Any]]:
    import journal

    try:
        entries = journal.get_recent_entries(days=LOG_DAYS + 16)
    except Exception:
        return []
    rows: List[Dict[str, Any]] = []
    for entry in entries[:JOURNAL_LIMIT]:
        kind = journal.normalize_journal_kind(entry.get("kind"))
        day = str(entry.get("date") or entry.get("created_at") or "")[:10]
        tags = entry.get("tags") if isinstance(entry.get("tags"), list) else []
        rows.append(
            {
                "id": entry.get("id"),
                "date": day or None,
                "kind": kind,
                "tags": [str(t) for t in tags if str(t).strip()][:12],
                "excerpt": _excerpt(entry.get("content")),
                "stem": str(entry.get("id") or ""),
            }
        )
    return rows


def _work_payload(today: date) -> Dict[str, Any]:
    import work

    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    cutoff = (today - timedelta(days=LOG_DAYS)).isoformat()
    week_start = monday.isoformat()
    week_end = sunday.isoformat()
    today_iso = today.isoformat()
    week_items: List[Dict[str, Any]] = []
    logged: List[Dict[str, Any]] = []
    backlog: List[Dict[str, Any]] = []
    overdue: List[Dict[str, Any]] = []
    todos_today: List[Dict[str, Any]] = []
    try:
        items = work.list_all_work_items()
    except Exception:
        items = []
    for item in items:
        scheduled = str(item.get("scheduled_date") or "")[:10]
        status = item.get("status") or "open"
        if scheduled == today_iso:
            todos_today.append(_ask_work_row(item))
        if not scheduled and status != "done":
            backlog.append(_ask_work_row(item))
        if scheduled and week_start <= scheduled <= week_end:
            week_items.append(_work_slim(item))
        finished = str(item.get("finished_at") or "")[:10]
        if status == "done" and (finished >= cutoff or scheduled >= cutoff):
            logged.append(_work_slim(item))
        if item.get("is_overdue") and status != "done":
            overdue.append(_ask_work_row(item))
    week_items.sort(key=lambda row: (row.get("scheduled_date") or "", row.get("title") or ""))
    logged.sort(key=lambda row: str(row.get("finished_at") or ""), reverse=True)
    return {
        "week": week_items[:80],
        "logged": logged[:40],
        "backlog": backlog[:20],
        "overdue": overdue[:20],
        "todos_today": todos_today[:40],
    }


def _calendar_payload(today: date) -> Dict[str, Any]:
    import calclock

    monday = today - timedelta(days=today.weekday())
    try:
        week = calclock.get_week(monday.isoformat())
    except Exception:
        return {
            "week_start": monday.isoformat(),
            "week_end": (monday + timedelta(days=6)).isoformat(),
            "days": [],
            "unplaced": [],
            "events_today": [],
            "settings": {},
        }
    days = []
    events_today: List[Dict[str, Any]] = []
    today_iso = today.isoformat()
    for day in week.get("days") or []:
        events = [_cal_slim(item) for item in day.get("events") or []]
        blocks = [_cal_slim(item) for item in day.get("blocks") or []]
        days.append(
            {
                "date": day.get("date"),
                "weekday": day.get("weekday"),
                "is_today": bool(day.get("is_today")),
                "events": events,
                "blocks": blocks,
            }
        )
        if day.get("date") == today_iso:
            events_today = events + blocks
    unplaced = [
        str(item.get("title") or "").strip()
        for item in (week.get("unplaced") or [])
        if str(item.get("title") or "").strip()
    ][:20]
    return {
        "week_start": week.get("week_start") or monday.isoformat(),
        "week_end": week.get("week_end") or (monday + timedelta(days=6)).isoformat(),
        "days": days,
        "unplaced": unplaced,
        "events_today": events_today[:40],
        "settings": week.get("settings") or {},
    }


def _workout_rows(today: date) -> List[Dict[str, Any]]:
    import workouts

    monday = today - timedelta(days=today.weekday())
    rows: List[Dict[str, Any]] = []
    for offset in range(7):
        day = (monday + timedelta(days=offset)).isoformat()
        try:
            packed = workouts.get_workout_day(day)
        except Exception:
            continue
        for session in packed.get("sessions") or []:
            rows.append(
                {
                    "date": day,
                    "kind": session.get("kind") or "",
                    "label": session.get("other_label") or session.get("kind_label") or "",
                    "miles": session.get("miles"),
                    "minutes": session.get("minutes"),
                    "done": True,
                }
            )
    return rows


def _goal_rows() -> List[Dict[str, Any]]:
    import goals

    try:
        listed = goals.list_goals()
    except Exception:
        return []
    rows = []
    for goal in listed:
        if goal.get("archived"):
            continue
        rows.append(
            {
                "id": goal.get("id"),
                "title": goal.get("title") or "",
                "horizon": goal.get("horizon"),
                "spent_minutes": goal.get("spent_minutes"),
                "target_minutes": goal.get("target_minutes"),
                "percent": goal.get("percent"),
            }
        )
    return rows[:40]


def _brief_rows(today: date) -> List[Dict[str, Any]]:
    import day_brief

    start = today - timedelta(days=BRIEF_DAYS - 1)
    try:
        briefs = day_brief.list_briefs_in_range(start, today)
    except Exception:
        return []
    rows = []
    for brief in briefs:
        rows.append(
            {
                "local_date": brief.get("local_date"),
                "slot": brief.get("slot"),
                "intention_text": _excerpt(brief.get("intention_text"), 240),
                "recap_text": _excerpt(brief.get("recap_text"), 240),
                "journal_id": brief.get("journal_id") or "",
                "done_ids": (brief.get("done_ids") or [])[:12],
                "leftover_ids": (brief.get("leftover_ids") or [])[:12],
                "rolled_ids": (brief.get("rolled_ids") or [])[:12],
            }
        )
    return rows


def _analytics() -> Dict[str, Any]:
    import insights

    try:
        data = insights.get_analytics(7)
    except Exception:
        return {}
    work_stats = data.get("work") or {}
    journal = data.get("journal") or {}
    return {
        "period": data.get("week_key"),
        "tasks_completed": work_stats.get("dated_done"),
        "tasks_slipped": work_stats.get("repeat_missed"),
        "focus_hours": round(float(journal.get("minutes") or 0) / 60.0, 1),
        "journal_streak_days": journal.get("streak"),
        "goal_progress": [
            {
                "goal": row.get("title"),
                "percent": row.get("percent"),
                "spent_minutes": row.get("spent_minutes"),
            }
            for row in _goal_rows()
            if row.get("horizon") == "week"
        ][:20],
    }


def build_life_snapshot() -> Dict[str, Any]:
    today = date.today()
    today_iso = today.isoformat()
    monday = today - timedelta(days=today.weekday())
    work = _work_payload(today)
    calendar = _calendar_payload(today)
    settings = calendar.get("settings") or {}
    day_start = str(settings.get("day_start") or "05:30")
    day_end = str(settings.get("day_end") or "21:30")
    events_today = calendar.get("events_today") or []
    briefs = _brief_rows(today)
    morning = next(
        (row for row in briefs if row.get("local_date") == today_iso and row.get("slot") == "morning"),
        None,
    )
    notes = (morning or {}).get("intention_text") or None
    weekly_goals = [
        row["title"] for row in _goal_rows() if row.get("horizon") == "week" and row.get("title")
    ]
    deadline_todos = [
        {"title": item.get("title") or "", "due": str(item.get("due") or item.get("due_at") or "")[:10]}
        for item in work["todos_today"] + work["overdue"] + work["backlog"]
        if item.get("due") or item.get("due_at")
    ][:40]
    return {
        "generated_at": datetime.now().replace(microsecond=0).isoformat(),
        "date": today_iso,
        "week_start": calendar.get("week_start") or monday.isoformat(),
        "week_end": calendar.get("week_end") or (monday + timedelta(days=6)).isoformat(),
        "instruction": ASK_INSTRUCTION,
        "journal": _journal_rows(),
        "work": work,
        "calendar": {
            "week_start": calendar.get("week_start"),
            "week_end": calendar.get("week_end"),
            "days": calendar.get("days") or [],
            "unplaced": calendar.get("unplaced") or [],
        },
        "workouts": _workout_rows(today),
        "goals": _goal_rows(),
        "briefs": briefs,
        "todos_today": work["todos_today"],
        "overdue": work["overdue"],
        "backlog": work["backlog"],
        "deadline_todos": deadline_todos,
        "events_today": events_today,
        "unplaced": calendar.get("unplaced") or [],
        "free_minutes": free_minutes(events_today, day_start, day_end),
        "weekly_goals": weekly_goals[:20],
        "notes": notes,
        "analytics": _analytics(),
    }


def write_life_snapshot() -> Dict[str, Any]:
    payload = build_life_snapshot()
    path = get_life_snapshot_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    os.replace(tmp, path)
    return payload


def refresh_life_snapshot_safe() -> Optional[Dict[str, Any]]:
    try:
        return write_life_snapshot()
    except Exception as exc:  # noqa: BLE001
        print(f"[Cluny snapshot] Failed (local save still ok): {exc}")
        return None


def snapshot_public_status() -> Dict[str, Any]:
    path = get_life_snapshot_path()
    updated = None
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as handle:
                raw = json.load(handle)
            if isinstance(raw, dict):
                updated = raw.get("generated_at")
        except (OSError, json.JSONDecodeError):
            updated = None
    return {
        "snapshot_path": str(path),
        "snapshot_updated_at": updated,
    }


@eel.expose
def get_cluny_life_snapshot() -> Dict[str, Any]:
    return build_life_snapshot()


@eel.expose
def get_cluny_snapshot_status() -> Dict[str, Any]:
    return snapshot_public_status()
