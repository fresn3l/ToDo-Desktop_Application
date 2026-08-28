"""
Weekly review and insights — aggregates checklist + journal data.
"""

from __future__ import annotations

import json
import os
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Set

import eel

import daily_checklist
import journal
import work
import workouts


def _data_dir() -> Path:
    return daily_checklist.get_data_directory()


def _pattern_notes_path() -> Path:
    return _data_dir() / "weekly_pattern_notes.json"


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


def _submissions_in_range(start: date, end: date) -> List[Dict[str, Any]]:
    return daily_checklist.fetch_submissions(
        start_date=start.isoformat(),
        end_date=end.isoformat(),
        decorate=False,
    )


def _journal_entries_in_range(start: date, end: date) -> List[Dict[str, Any]]:
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


def _is_exercise_yes(answers: Dict[str, Any]) -> bool:
    """Completed exercise only — excludes morning planned_workout intentions."""
    for key in ("exercise_done", "exercise_yn"):
        if answers.get(key) is True:
            return True
    return False


def _workout_types(answers: Dict[str, Any]) -> List[str]:
    wt = answers.get("workout_type")
    if isinstance(wt, dict):
        if wt.get("value") == "other":
            return [f"other:{wt.get('otherText', '')}"]
        return [str(wt.get("value", ""))]
    return []


def _custom_trends(
    submissions: List[Dict[str, Any]], custom_items: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    stats: Dict[str, Dict[str, Any]] = {}
    for item in custom_items:
        cid = item.get("id")
        if not cid:
            continue
        stats[cid] = {
            "question": item.get("question", cid),
            "type": item.get("type"),
            "responses": 0,
            "yes_count": 0,
            "choice_counts": Counter(),
        }
    for sub in submissions:
        answers = sub.get("answers") or {}
        for cid, meta in stats.items():
            if cid not in answers:
                continue
            meta["responses"] += 1
            val = answers[cid]
            if meta["type"] == "yes_no":
                ans = val.get("answer") if isinstance(val, dict) else val
                if ans is True:
                    meta["yes_count"] += 1
            elif meta["type"] == "choice" and isinstance(val, dict):
                v = val.get("value", "")
                if v == "other":
                    v = f"other: {val.get('otherText', '')}"
                meta["choice_counts"][v] += 1
    trends = []
    for cid, meta in stats.items():
        row: Dict[str, Any] = {
            "id": cid,
            "question": meta["question"],
            "type": meta["type"],
            "responses": meta["responses"],
        }
        if meta["type"] == "yes_no" and meta["responses"]:
            row["yes_rate"] = round(meta["yes_count"] / meta["responses"], 2)
            row["yes_count"] = meta["yes_count"]
        elif meta["type"] == "choice" and meta["choice_counts"]:
            row["choices"] = dict(meta["choice_counts"])
        trends.append(row)
    return trends


@eel.expose
def get_weekly_review(days: int = 7) -> Dict[str, Any]:
    """Summary for the last N days (default 7)."""
    days = max(1, min(int(days or 7), 90))
    end = date.today()
    start = end - timedelta(days=days - 1)
    week_key = _week_key(end)

    submissions = _submissions_in_range(start, end)
    journal_entries = _journal_entries_in_range(start, end)
    custom_items = daily_checklist.get_custom_checklist_items()
    workout = workouts.workout_metrics(days)

    days_with_checkin: Set[str] = set()
    checklist_ids: Counter = Counter()

    for sub in submissions:
        ld = sub.get("local_date")
        if ld:
            days_with_checkin.add(ld)
        checklist_ids[sub.get("checklist_id", "unknown")] += 1

    completion_pct = round(len(days_with_checkin) / days * 100, 1)
    total_writing = sum(int(e.get("duration_seconds") or 0) for e in journal_entries)
    pattern_notes = _load_pattern_notes()

    return {
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "days": days,
        "week_key": week_key,
        "checklist_completion_pct": completion_pct,
        "days_with_checkin": len(days_with_checkin),
        "total_submissions": len(submissions),
        "checklist_breakdown": dict(checklist_ids),
        "exercise_sessions": workout.get("sessions") or 0,
        "exercise_days": workout.get("days_trained") or 0,
        "workout_types": workout.get("by_kind") or {},
        "workout_miles": workout.get("miles") or 0,
        "journal_entry_count": len(journal_entries),
        "journal_writing_seconds": total_writing,
        "journal_writing_minutes": round(total_writing / 60, 1),
        "custom_question_trends": _custom_trends(submissions, custom_items),
        "pattern_prompt": "What pattern do you notice?",
        "pattern_note": pattern_notes.get(week_key, ""),
    }


@eel.expose
def save_weekly_pattern_note(note: str) -> None:
    week_key = _week_key(date.today())
    _save_pattern_note(week_key, (note or "").strip())


def _title_for_checklist(checklist_id: str) -> str:
    for bundle in daily_checklist.list_bundled_checklists():
        if bundle.get("id") == checklist_id:
            return bundle.get("title") or checklist_id
    fallback = {
        "morning": "Morning check-in",
        "evening": "Evening check-in",
        "default": "Daily check-in",
    }
    return fallback.get(checklist_id, checklist_id.replace("_", " ").title())


@eel.expose
def get_today_status() -> Dict[str, Any]:
    """Workout, to-do, and journal counts for today."""
    today = date.today()
    iso = today.isoformat()
    hour = datetime.now().hour

    journal_count = 0
    for entry in journal.get_recent_entries(days=2):
        raw = entry.get("date") or entry.get("created_at") or ""
        try:
            ed = datetime.fromisoformat(raw).date()
        except (ValueError, TypeError):
            continue
        if ed == today:
            journal_count += 1

    work_board = work.get_work_board(iso)
    work_open = int(work_board.get("counts", {}).get("today_open") or 0)
    work_done = int(work_board.get("counts", {}).get("today_done") or 0)
    work_total = int(work_board.get("counts", {}).get("today_total") or 0)
    workout = workouts.get_workout_day(iso)

    return {
        "local_date": iso,
        "hour": hour,
        "journal_count": journal_count,
        "workout": {
            "done": bool(workout.get("done")),
            "session_count": int(workout.get("session_count") or 0),
            "miles": workout.get("miles") or 0,
        },
        "work": {
            "open": work_open,
            "done": work_done,
            "total": work_total,
        },
    }
