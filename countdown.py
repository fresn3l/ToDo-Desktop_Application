"""Pinned countdown dates for the Home widget."""

from __future__ import annotations

import json
import os
import uuid
from datetime import date
from typing import Any, Dict, List, Optional

import eel

from paths import data_directory

MAX_COUNTDOWNS = 24
MAX_TITLE = 80


def _path():
    return data_directory() / "countdowns.json"


def _today() -> date:
    return date.today()


def _parse_date(raw: Any) -> Optional[date]:
    text = str(raw or "").strip()[:10]
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def next_occurrence(target: date, yearly: bool, today: Optional[date] = None) -> date:
    today = today or _today()
    if not yearly:
        return target
    year = today.year
    try:
        candidate = target.replace(year=year)
    except ValueError:
        candidate = date(year, 2, 28)
    if candidate < today:
        try:
            candidate = target.replace(year=year + 1)
        except ValueError:
            candidate = date(year + 1, 2, 28)
    return candidate


def _decorate(item: Dict[str, Any], today: Optional[date] = None) -> Dict[str, Any]:
    today = today or _today()
    pinned = _parse_date(item.get("date")) or today
    yearly = bool(item.get("yearly"))
    shown = next_occurrence(pinned, yearly, today)
    delta = (shown - today).days
    if delta == 0:
        label = "today"
    elif delta == 1:
        label = "1 day"
    elif delta == -1:
        label = "1 day ago"
    elif delta > 0:
        label = f"{delta} days"
    else:
        label = f"{abs(delta)} days ago"
    return {
        "id": item.get("id"),
        "title": item.get("title") or "",
        "date": pinned.isoformat(),
        "yearly": yearly,
        "next_date": shown.isoformat(),
        "days": delta,
        "label": label,
        "is_past": delta < 0,
        "is_today": delta == 0,
    }


def _load_raw() -> List[Dict[str, Any]]:
    path = _path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(data, dict):
        data = data.get("items") or []
    if not isinstance(data, list):
        return []
    out: List[Dict[str, Any]] = []
    for item in data[:MAX_COUNTDOWNS]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()[:MAX_TITLE]
        pinned = _parse_date(item.get("date"))
        if not title or pinned is None:
            continue
        out.append(
            {
                "id": str(item.get("id") or "").strip() or str(uuid.uuid4()),
                "title": title,
                "date": pinned.isoformat(),
                "yearly": bool(item.get("yearly")),
            }
        )
    return out


def _write(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    packed = items[:MAX_COUNTDOWNS]
    path = _path()
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump({"items": packed}, handle, indent=2)
    os.replace(tmp, path)
    return packed


def _sorted_payload(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    today = _today()
    rows = [_decorate(item, today) for item in items]
    rows.sort(key=lambda row: (row["days"] < 0, abs(row["days"]), row["title"].lower()))
    return rows


@eel.expose
def get_countdowns() -> Dict[str, Any]:
    rows = _sorted_payload(_load_raw())
    next_up = next((row for row in rows if row["days"] >= 0), rows[0] if rows else None)
    return {"items": rows, "next": next_up, "today": _today().isoformat()}


@eel.expose
def add_countdown(title: str, date_iso: str, yearly: bool = False) -> Dict[str, Any]:
    clean = str(title or "").strip()[:MAX_TITLE]
    pinned = _parse_date(date_iso)
    if not clean:
        raise ValueError("Title is required")
    if pinned is None:
        raise ValueError("Date is required")
    items = _load_raw()
    if len(items) >= MAX_COUNTDOWNS:
        raise ValueError("Too many countdowns")
    items.append(
        {
            "id": str(uuid.uuid4()),
            "title": clean,
            "date": pinned.isoformat(),
            "yearly": bool(yearly),
        }
    )
    _write(items)
    return get_countdowns()


@eel.expose
def remove_countdown(item_id: str) -> Dict[str, Any]:
    key = str(item_id or "").strip()
    items = [item for item in _load_raw() if item["id"] != key]
    _write(items)
    return get_countdowns()
