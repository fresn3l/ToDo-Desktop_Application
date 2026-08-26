"""
Unified timeline — journal entries + checklist submissions by date.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

import eel

import daily_checklist
import journal


def _parse_date(s: str) -> Optional[date]:
    if not s:
        return None
    try:
        return date.fromisoformat(s[:10])
    except (ValueError, TypeError):
        pass
    try:
        return datetime.fromisoformat(s).date()
    except (ValueError, TypeError):
        return None


@eel.expose
def get_timeline_day(local_date: str) -> Dict[str, Any]:
    """Everything recorded on one calendar day (YYYY-MM-DD)."""
    target = _parse_date(local_date)
    if not target:
        raise ValueError("Invalid date; use YYYY-MM-DD")

    submissions: List[Dict[str, Any]] = []
    for row in daily_checklist.fetch_submissions(local_date=target.isoformat()):
        submissions.append(
            {
                "id": row["id"],
                "created_at": row["created_at"],
                "checklist_id": row.get("checklist_id"),
                "title": row.get("title") or row.get("checklist_id") or "Checklist",
                "answers": row.get("answers") or {},
                "answers_formatted": row.get("answers_formatted") or [],
                "summary": row.get("summary") or "",
            }
        )

    entries: List[Dict[str, Any]] = []
    span = max(1, (date.today() - target).days + 2)
    for e in journal.get_recent_entries(days=span):
        ed = _parse_date(e.get("date") or e.get("created_at") or "")
        if ed == target:
            dur = int(e.get("duration_seconds") or 0)
            entries.append(
                {
                    "id": e.get("id"),
                    "content": e.get("content", ""),
                    "date": e.get("date") or e.get("created_at"),
                    "duration_seconds": dur,
                    "duration_label": f"{dur // 60}m {dur % 60}s" if dur else "",
                    "tags": e.get("tags") or [],
                    "continued": bool(e.get("continued")),
                }
            )

    entries.sort(key=lambda x: x.get("date", ""), reverse=True)
    submissions.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    total_writing = sum(int(e.get("duration_seconds") or 0) for e in entries)

    return {
        "local_date": target.isoformat(),
        "submissions": submissions,
        "journal_entries": entries,
        "submission_count": len(submissions),
        "journal_count": len(entries),
        "total_writing_seconds": total_writing,
    }


@eel.expose
def list_timeline_dates(limit: int = 60) -> List[str]:
    """Recent dates that have journal or checklist activity."""
    limit = max(1, min(int(limit or 60), 365))
    dates_set = set()
    for iso in daily_checklist.list_submission_dates():
        d = _parse_date(iso)
        if d:
            dates_set.add(d.isoformat())
    for e in journal.get_all_entries():
        d = _parse_date(e.get("date") or e.get("created_at") or "")
        if d:
            dates_set.add(d.isoformat())
    sorted_dates = sorted(dates_set, reverse=True)
    return sorted_dates[:limit]


@eel.expose
def get_week_overview(end_date: str = "") -> Dict[str, Any]:
    """Rolling 7 days ending at end_date (defaults to today, never in the future)."""
    end = _parse_date(end_date) or date.today()
    today = date.today()
    if end > today:
        end = today
    start = end - timedelta(days=6)

    checklist_counts: Dict[str, int] = {}
    for row in daily_checklist.fetch_submissions(
        start_date=start.isoformat(),
        end_date=end.isoformat(),
        decorate=False,
    ):
        iso = row.get("local_date")
        if iso:
            checklist_counts[iso] = checklist_counts.get(iso, 0) + 1

    journal_counts: Dict[str, int] = {}
    span = max(14, (today - start).days + 1)
    for e in journal.get_recent_entries(days=span):
        d = _parse_date(e.get("date") or e.get("created_at") or "")
        if d and start <= d <= end:
            iso = d.isoformat()
            journal_counts[iso] = journal_counts.get(iso, 0) + 1

    days: List[Dict[str, Any]] = []
    for i in range(6, -1, -1):
        d = end - timedelta(days=i)
        iso = d.isoformat()
        c_count = checklist_counts.get(iso, 0)
        j_count = journal_counts.get(iso, 0)
        days.append(
            {
                "date": iso,
                "weekday": d.strftime("%a"),
                "day": d.day,
                "is_today": d == today,
                "checklist_count": c_count,
                "journal_count": j_count,
                "filled": (c_count + j_count) > 0,
            }
        )

    return {
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "days": days,
        "streaks": compute_streaks(today),
    }


def compute_streaks(today: Optional[date] = None) -> Dict[str, int]:
    """Consecutive days of activity, always measured from today.

    If today is still empty, the streak continues from yesterday until a
    missed past day. Used by the week strip so browsing older weeks does
    not change the live streak.
    """
    today = today or date.today()

    checkin_dates = set()
    for iso in daily_checklist.list_submission_dates():
        d = _parse_date(iso)
        if d:
            checkin_dates.add(d)

    journal_dates = set()
    for entry in journal.get_recent_entries(days=400):
        d = _parse_date(entry.get("date") or entry.get("created_at") or "")
        if d:
            journal_dates.add(d)

    return {
        "show_up": _count_streak(checkin_dates | journal_dates, today),
        "writing": _count_streak(journal_dates, today),
        "checkin": _count_streak(checkin_dates, today),
    }


def _count_streak(dates: set, today: date) -> int:
    if not dates:
        return 0
    cursor = today if today in dates else today - timedelta(days=1)
    n = 0
    while cursor in dates:
        n += 1
        cursor -= timedelta(days=1)
    return n
