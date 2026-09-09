"""Today's clock for the iPhone companion.

Keep lockstep with ios/Kosistenz/DayTimeline.swift
(tests/test_iphone_today_timeline.py).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional


def _parse(iso: Optional[str]) -> Optional[datetime]:
    raw = (iso or "").strip()
    if not raw:
        return None
    text = raw.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def duration_minutes(start_at: Optional[str], end_at: Optional[str]) -> int:
    start = _parse(start_at)
    end = _parse(end_at)
    if start is None:
        return 30
    if end is None or end <= start:
        return 30
    return max(1, int((end - start).total_seconds() // 60))


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


def _sort_key(item: Dict[str, Any]) -> tuple:
    start = item.get("start_at") or ""
    title = (item.get("title") or "").lower()
    missing = 1 if not start else 0
    return (missing, start, title)


def timeline_items(
    events: Iterable[Dict[str, Any]],
    blocks: Iterable[Dict[str, Any]],
    now: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """Events and packed blocks, earliest start first. No unplaced."""
    rows = [dict(item) for item in list(events or []) + list(blocks or []) if item]
    rows.sort(key=_sort_key)
    clock = now
    out: List[Dict[str, Any]] = []
    for item in rows:
        start_at = item.get("start_at")
        end_at = item.get("end_at")
        start = _parse(start_at)
        end = _parse(end_at)
        is_now = False
        if clock is not None and start is not None:
            if end is None:
                is_now = start <= clock
            else:
                is_now = start <= clock < end
        out.append(
            {
                "id": item.get("id") or f"{item.get('title')}-{start_at}",
                "title": item.get("title") or "",
                "kind": item.get("kind") or "",
                "status": item.get("status") or "",
                "start_at": start_at,
                "end_at": end_at,
                "minutes": duration_minutes(start_at, end_at),
                "label": kind_label(item.get("kind"), item.get("status")),
                "is_now": is_now,
            }
        )
    return out


def unplaced_titles(items: Iterable[Dict[str, Any]]) -> List[str]:
    titles = []
    for item in items or []:
        title = (item.get("title") or "").strip()
        if title:
            titles.append(title)
    return titles
