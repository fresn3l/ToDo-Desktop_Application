"""Phone Work sheet filters. Keep lockstep with ios/Kosistenz/PhoneWork.swift."""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional

_TITLE_HOURS = re.compile(r"(?P<n>\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h)\b", re.I)
_TITLE_MINS = re.compile(r"(?P<n>\d+(?:\.\d+)?)\s*(?:minutes?|mins?|min|m)\b", re.I)


def parse_minutes_from_title(title: str) -> Optional[int]:
    """Read '45 mins memo' or '1h reading' from the to-do text."""
    text = str(title or "")
    if not text.strip():
        return None
    hours = 0.0
    mins = 0.0
    found = False
    for match in _TITLE_HOURS.finditer(text):
        hours += float(match.group("n"))
        found = True
    rest = _TITLE_HOURS.sub(" ", text)
    for match in _TITLE_MINS.finditer(rest):
        mins += float(match.group("n"))
        found = True
    if not found:
        return None
    total = int(round(hours * 60 + mins))
    if total <= 0:
        return None
    return min(total, 24 * 60)


def normalize_filter(raw: str) -> str:
    key = str(raw or "").strip().lower()
    if key in {"backlog", "allwork", "all"}:
        return "all"
    if key in {"unplaced", "due"}:
        return key
    return "today"


def filter_items(
    items: Iterable[Dict[str, Any]],
    kind: str,
    today: str,
    unplaced_ids: Optional[Iterable[str]] = None,
) -> List[Dict[str, Any]]:
    wanted = normalize_filter(kind)
    today_iso = str(today or "")[:10]
    held = {str(item) for item in (unplaced_ids or [])}
    out: List[Dict[str, Any]] = []
    for item in items:
        status = str(item.get("status") or "").strip().lower()
        scheduled = str(item.get("scheduled_date") or "")[:10]
        due = str(item.get("due_at") or "")[:10]
        item_id = str(item.get("id") or "")
        if wanted == "today":
            if status == "done":
                continue
            if scheduled != today_iso:
                continue
            out.append(item)
        elif wanted == "all":
            if status == "done":
                continue
            if scheduled:
                continue
            out.append(item)
        elif wanted == "unplaced":
            if item_id and item_id in held:
                out.append(item)
        elif wanted == "due":
            if status == "done" or not due:
                continue
            out.append(item)
    if wanted == "due":
        out.sort(key=lambda row: str(row.get("due_at") or ""))
    elif wanted == "all":
        out.sort(key=lambda row: str(row.get("updated_at") or ""), reverse=True)
    else:
        out.sort(key=lambda row: (str(row.get("scheduled_date") or ""), str(row.get("title") or "")))
    return out
