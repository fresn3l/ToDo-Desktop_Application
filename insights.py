"""
Weekly review and insights — journal, workouts, and to dos.
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Set

import eel

import journal
import work
import workouts
from paths import data_directory


def _pattern_notes_path() -> Path:
    return data_directory() / "weekly_pattern_notes.json"


def _load_pattern_notes() -> Dict[str, str]:
    path = _pattern_notes_path()
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_pattern_note(week_key: str, note: str) -> None:
    notes = _load_pattern_notes()
    notes[week_key] = note
    path = _pattern_notes_path()
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(notes, f, indent=2, ensure_ascii=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    os.replace(tmp, path)


def _week_key(d: date) -> str:
    iso = d.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _journal_entries_in_range(start: date, end: date) -> list:
    span = max(7, (date.today() - start).days + 1)
    entries = journal.get_recent_entries(days=span)
    out = []
    for e in entries:
        raw = e.get("date") or e.get("created_at") or ""
        try:
            ed = datetime.fromisoformat(raw).date()
        except (ValueError, TypeError):
            continue
        if start <= ed <= end:
            out.append(e)
    return out


@eel.expose
def save_weekly_pattern_note(note: str) -> None:
    week_key = _week_key(date.today())
    _save_pattern_note(week_key, (note or "").strip())


def _journal_count_for(today: date) -> int:
    count = 0
    for entry in journal.get_recent_entries(days=2):
        raw = entry.get("date") or entry.get("created_at") or ""
        try:
            ed = datetime.fromisoformat(raw).date()
        except (ValueError, TypeError):
            continue
        if ed == today:
            count += 1
    return count


def _expected_payload(today: date) -> Dict[str, Any]:
    template = workouts.load_week_template()
    kinds = workouts.expected_kinds_for_date(today, template)
    return {
        "kinds": kinds,
        "labels": [workouts.KIND_LABELS.get(kind, kind) for kind in kinds],
        "template_label": workouts.week_template_label(template),
    }


@eel.expose
def get_today_status() -> Dict[str, Any]:
    """Workout, to-do, and journal counts for today."""
    today = date.today()
    iso = today.isoformat()
    work_board = work.get_work_board(iso)
    work_open = int(work_board.get("counts", {}).get("today_open") or 0)
    work_done = int(work_board.get("counts", {}).get("today_done") or 0)
    work_total = int(work_board.get("counts", {}).get("today_total") or 0)
    workout = workouts.get_workout_day(iso)
    expected = _expected_payload(today)
    agenda = []
    try:
        import calclock

        agenda = calclock.get_day_agenda(iso).get("items") or []
    except Exception:
        agenda = []
    return {
        "local_date": iso,
        "hour": datetime.now().hour,
        "journal_count": _journal_count_for(today),
        "expected": expected,
        "workout": {
            "done": bool(workout.get("done")),
            "session_count": int(workout.get("session_count") or 0),
            "miles": workout.get("miles") or 0,
            "kinds": [s.get("kind") for s in workout.get("sessions") or []],
        },
        "work": {
            "open": work_open,
            "done": work_done,
            "total": work_total,
        },
        "agenda": agenda,
    }


@eel.expose
def get_today_home() -> Dict[str, Any]:
    """Full Today home payload: to-dos, expected workout, journal count."""
    today = date.today()
    iso = today.isoformat()
    status = get_today_status()
    board = work.get_work_board(iso)
    workout = workouts.get_workout_day(iso)
    writing_streak = 0
    try:
        import timeline

        writing_streak = int(timeline.compute_streaks(today).get("writing") or 0)
    except Exception:
        pass
    return {
        **status,
        "today": board.get("today") or [],
        "counts": board.get("counts") or {},
        "workout_day": workout,
        "journal_streak": writing_streak,
    }


@eel.expose
def get_analytics(days: int = 30) -> Dict[str, Any]:
    """Journal, workout, and repeating to-do metrics for the last N days."""
    import timeline

    days = max(1, min(int(days or 30), 365))
    end = date.today()
    start = end - timedelta(days=days - 1)
    journal_entries = _journal_entries_in_range(start, end)
    journal_days: Set[str] = set()
    total_writing = 0
    for entry in journal_entries:
        total_writing += int(entry.get("duration_seconds") or 0)
        raw = entry.get("date") or entry.get("created_at") or ""
        try:
            journal_days.add(datetime.fromisoformat(raw).date().isoformat())
        except (ValueError, TypeError):
            continue

    streaks = timeline.compute_streaks(end)
    workout = workouts.workout_metrics(days)
    plan = workouts.workout_plan_analytics(days)
    work_stats = work.repeating_work_analytics(days)
    week_key = _week_key(end)
    pattern_notes = _load_pattern_notes()
    import day_brief

    capacity = day_brief.capacity_for_range(start, end)
    return {
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "days": days,
        "week_key": week_key,
        "show_up_streak": int(streaks.get("show_up") or 0),
        "journal": {
            "entries": len(journal_entries),
            "days_written": len(journal_days),
            "minutes": round(total_writing / 60, 1),
            "streak": int(streaks.get("writing") or 0),
        },
        "workout": workout,
        "workout_plan": plan,
        "workout_streak": int(streaks.get("workout") or 0),
        "work": work_stats,
        "capacity": capacity,
        "pattern_prompt": "What pattern do you notice?",
        "pattern_note": pattern_notes.get(week_key, ""),
    }


ALLOCATION_LABELS = {
    "hard": "Busy",
    "work": "Work",
    "workout": "Gym",
    "other": "Other",
}


def _minutes_between(start_at: Any, end_at: Any) -> int:
    try:
        start = datetime.fromisoformat(str(start_at))
        end = datetime.fromisoformat(str(end_at))
    except (TypeError, ValueError):
        return 0
    return max(0, int((end - start).total_seconds() // 60))


def allocation_range(period: str = "week", today: Optional[date] = None) -> tuple:
    today = today or date.today()
    key = "month" if str(period or "").strip().lower() == "month" else "week"
    if key == "month":
        from calendar import monthrange

        last = monthrange(today.year, today.month)[1]
        return key, today.replace(day=1), date(today.year, today.month, last)
    this_monday = today - timedelta(days=today.weekday())
    start = this_monday - timedelta(days=7)
    end = this_monday - timedelta(days=1)
    return key, start, end


@eel.expose
def get_time_allocation(period: str = "week") -> Dict[str, Any]:
    """Last ISO week's calendar minutes by category, or the current month."""
    import calclock

    today = date.today()
    key, start, end = allocation_range(period, today)
    totals = {"hard": 0, "work": 0, "workout": 0, "other": 0}
    for item in calclock.expand_hard_events(start, end):
        totals["hard"] += _minutes_between(item.get("start_at"), item.get("end_at"))
    for block in calclock.list_blocks(start, end):
        if block.get("status") == "skipped":
            continue
        kind = str(block.get("kind") or "work")
        if kind not in ("work", "workout"):
            kind = "other"
        totals[kind] += int(block.get("minutes") or _minutes_between(block.get("start_at"), block.get("end_at")))
    total = sum(totals.values())
    rows = []
    for cat in ("hard", "work", "workout", "other"):
        minutes = totals[cat]
        if minutes <= 0 and cat == "other":
            continue
        rows.append(
            {
                "id": cat,
                "label": ALLOCATION_LABELS[cat],
                "minutes": minutes,
                "hours": round(minutes / 60, 1),
                "pct": round((minutes / total) * 100) if total else 0,
            }
        )
    return {
        "period": key,
        "period_label": "Last week" if key == "week" else today.strftime("%B %Y"),
        "start": start.isoformat(),
        "end": end.isoformat(),
        "total_minutes": total,
        "total_hours": round(total / 60, 1),
        "categories": rows,
    }
