"""
Unified timeline — journal entries + checklist submissions by date.
"""

from __future__ import annotations

from datetime import date, datetime
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


def _format_answer(key: str, val: Any) -> str:
    if val is True:
        return "Yes"
    if val is False:
        return "No"
    if val is None:
        return "—"
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, str):
        return val
    if isinstance(val, dict):
        if "answer" in val:
            return _format_answer(key, val["answer"])
        if val.get("value") == "other":
            return f"Other: {val.get('otherText', '')}"
        if "value" in val:
            base = str(val["value"])
            if val.get("durationMinutes") is not None:
                return f"{base} ({val['durationMinutes']} min)"
            return base
        if val.get("durationMinutes") is not None:
            return f"{val['durationMinutes']} min"
    return str(val)


@eel.expose
def get_timeline_day(local_date: str) -> Dict[str, Any]:
    """Everything recorded on one calendar day (YYYY-MM-DD)."""
    target = _parse_date(local_date)
    if not target:
        raise ValueError("Invalid date; use YYYY-MM-DD")

    submissions: List[Dict[str, Any]] = []
    for row in daily_checklist.list_daily_checklist_submissions(500):
        if _parse_date(row.get("local_date", "")) == target:
            answers = row.get("answers") or {}
            formatted = [
                {"key": k, "label": k.replace("_", " ").title(), "value": _format_answer(k, v)}
                for k, v in answers.items()
            ]
            submissions.append(
                {
                    "id": row["id"],
                    "created_at": row["created_at"],
                    "checklist_id": row.get("checklist_id"),
                    "answers": answers,
                    "answers_formatted": formatted,
                }
            )

    entries: List[Dict[str, Any]] = []
    for e in journal.get_recent_entries(days=365):
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
    for row in daily_checklist.list_daily_checklist_submissions(500):
        d = _parse_date(row.get("local_date", ""))
        if d:
            dates_set.add(d.isoformat())
    for e in journal.get_recent_entries(days=365):
        d = _parse_date(e.get("date") or e.get("created_at") or "")
        if d:
            dates_set.add(d.isoformat())
    sorted_dates = sorted(dates_set, reverse=True)
    return sorted_dates[:limit]
