"""
Glance Home widgets — today's focus, named countdowns, and daily habits.

All three stay in small JSON files next to the rest of Kosistenz data.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

import eel

from paths import data_directory

MAX_FOCUS = 240
MAX_COUNTDOWN_TITLE = 60
MAX_COUNTDOWNS = 12
MAX_HABIT_TITLE = 40
MAX_HABITS = 16
HABIT_HISTORY_DAYS = 90


def _path(name: str):
    return data_directory() / name


def _write(path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    os.replace(tmp, path)


def _read(path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _today() -> date:
    return date.today()


def _new_id() -> str:
    return str(uuid.uuid4())


def _clip(raw: Any, limit: int) -> str:
    return str(raw or "").strip()[:limit]


def _parse_date(raw: Any) -> Optional[str]:
    text = str(raw or "").strip()[:10]
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        return None


def countdown_phrase(iso: str, today: Optional[date] = None) -> Dict[str, Any]:
    today = today or _today()
    try:
        target = date.fromisoformat(iso)
    except ValueError:
        return {"days": 0, "phrase": "—", "state": "invalid"}
    delta = (target - today).days
    if delta == 0:
        return {"days": 0, "phrase": "today", "state": "today"}
    if delta == 1:
        return {"days": 1, "phrase": "tomorrow", "state": "upcoming"}
    if delta == -1:
        return {"days": -1, "phrase": "yesterday", "state": "past"}
    if delta > 1:
        return {"days": delta, "phrase": f"in {delta} days", "state": "upcoming"}
    return {"days": delta, "phrase": f"{abs(delta)} days ago", "state": "past"}


def load_focus(today: Optional[date] = None) -> Dict[str, Any]:
    today = today or _today()
    raw = _read(_path("focus.json"))
    stored_date = str(raw.get("date") or "")
    text = _clip(raw.get("text"), MAX_FOCUS)
    if stored_date != today.isoformat():
        return {"date": today.isoformat(), "text": "", "kept": False}
    return {"date": today.isoformat(), "text": text, "kept": bool(raw.get("kept")) and bool(text)}


def save_focus(text: str, today: Optional[date] = None) -> Dict[str, Any]:
    today = today or _today()
    packed = {"date": today.isoformat(), "text": _clip(text, MAX_FOCUS), "kept": False}
    _write(_path("focus.json"), packed)
    return packed


def keep_focus(kept: bool = True, today: Optional[date] = None) -> Dict[str, Any]:
    current = load_focus(today)
    if not current["text"]:
        raise ValueError("Set today’s focus first")
    packed = {"date": current["date"], "text": current["text"], "kept": bool(kept)}
    _write(_path("focus.json"), packed)
    return packed


def load_countdowns(today: Optional[date] = None) -> List[Dict[str, Any]]:
    today = today or _today()
    raw = _read(_path("countdowns.json"))
    incoming = raw.get("items")
    if not isinstance(incoming, list):
        incoming = []
    items: List[Dict[str, Any]] = []
    for row in incoming[:MAX_COUNTDOWNS]:
        if not isinstance(row, dict):
            continue
        iso = _parse_date(row.get("date"))
        title = _clip(row.get("title"), MAX_COUNTDOWN_TITLE)
        if not iso or not title:
            continue
        item = {
            "id": str(row.get("id") or "").strip() or _new_id(),
            "title": title,
            "date": iso,
        }
        item.update(countdown_phrase(iso, today))
        items.append(item)
    items.sort(key=lambda row: (row["date"], row["title"].lower()))
    return items


def save_countdowns(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    packed = [
        {"id": row["id"], "title": row["title"], "date": row["date"]}
        for row in items[:MAX_COUNTDOWNS]
    ]
    _write(_path("countdowns.json"), {"items": packed})
    return load_countdowns()


def add_countdown(title: str, when: str) -> List[Dict[str, Any]]:
    items = load_countdowns()
    if len(items) >= MAX_COUNTDOWNS:
        raise ValueError("Too many countdowns")
    iso = _parse_date(when)
    name = _clip(title, MAX_COUNTDOWN_TITLE)
    if not iso or not name:
        raise ValueError("Need a name and a date")
    items.append({"id": _new_id(), "title": name, "date": iso})
    return save_countdowns(items)


def remove_countdown(item_id: str) -> List[Dict[str, Any]]:
    want = str(item_id or "").strip()
    items = [row for row in load_countdowns() if row["id"] != want]
    return save_countdowns(items)


def _habits_store() -> Dict[str, Any]:
    raw = _read(_path("habits.json"))
    habits_in = raw.get("habits")
    checks_in = raw.get("checks")
    habits: List[Dict[str, Any]] = []
    seen = set()
    if isinstance(habits_in, list):
        for index, row in enumerate(habits_in[:MAX_HABITS]):
            if not isinstance(row, dict):
                continue
            hid = str(row.get("id") or "").strip() or _new_id()
            if hid in seen:
                continue
            title = _clip(row.get("title"), MAX_HABIT_TITLE)
            if not title:
                continue
            seen.add(hid)
            habits.append({"id": hid, "title": title, "sort": index})
    checks: Dict[str, List[str]] = {}
    if isinstance(checks_in, dict):
        cutoff = (_today() - timedelta(days=HABIT_HISTORY_DAYS)).isoformat()
        valid = {row["id"] for row in habits}
        for iso, ids in checks_in.items():
            day = _parse_date(iso)
            if not day or day < cutoff or not isinstance(ids, list):
                continue
            kept = []
            for hid in ids:
                hid = str(hid or "").strip()
                if hid in valid and hid not in kept:
                    kept.append(hid)
            if kept:
                checks[day] = kept
    return {"habits": habits, "checks": checks}


def _save_habits_store(store: Dict[str, Any]) -> Dict[str, Any]:
    packed = {
        "habits": [{"id": row["id"], "title": row["title"]} for row in store["habits"][:MAX_HABITS]],
        "checks": store.get("checks") or {},
    }
    _write(_path("habits.json"), packed)
    return _habits_store()


def load_habits(today: Optional[date] = None) -> Dict[str, Any]:
    today = today or _today()
    store = _habits_store()
    checked = set(store["checks"].get(today.isoformat()) or [])
    rows = []
    for row in store["habits"]:
        rows.append(
            {
                "id": row["id"],
                "title": row["title"],
                "done": row["id"] in checked,
            }
        )
    done = sum(1 for row in rows if row["done"])
    return {
        "date": today.isoformat(),
        "habits": rows,
        "done": done,
        "total": len(rows),
    }


def add_habit(title: str) -> Dict[str, Any]:
    store = _habits_store()
    if len(store["habits"]) >= MAX_HABITS:
        raise ValueError("Too many habits")
    name = _clip(title, MAX_HABIT_TITLE)
    if not name:
        raise ValueError("Name this habit")
    store["habits"].append({"id": _new_id(), "title": name, "sort": len(store["habits"])})
    _save_habits_store(store)
    return load_habits()


def remove_habit(habit_id: str) -> Dict[str, Any]:
    want = str(habit_id or "").strip()
    store = _habits_store()
    store["habits"] = [row for row in store["habits"] if row["id"] != want]
    for iso, ids in list(store["checks"].items()):
        store["checks"][iso] = [hid for hid in ids if hid != want]
        if not store["checks"][iso]:
            del store["checks"][iso]
    _save_habits_store(store)
    return load_habits()


def toggle_habit(habit_id: str, today: Optional[date] = None) -> Dict[str, Any]:
    today = today or _today()
    want = str(habit_id or "").strip()
    store = _habits_store()
    if not any(row["id"] == want for row in store["habits"]):
        raise ValueError("Habit not found")
    iso = today.isoformat()
    current = list(store["checks"].get(iso) or [])
    if want in current:
        current = [hid for hid in current if hid != want]
    else:
        current.append(want)
    if current:
        store["checks"][iso] = current
    else:
        store["checks"].pop(iso, None)
    _save_habits_store(store)
    return load_habits(today)


@eel.expose
def get_daily_focus() -> Dict[str, Any]:
    return load_focus()


@eel.expose
def set_daily_focus(text: str) -> Dict[str, Any]:
    return save_focus(text)


@eel.expose
def keep_daily_focus(kept: bool = True) -> Dict[str, Any]:
    return keep_focus(bool(kept))


@eel.expose
def get_countdowns() -> List[Dict[str, Any]]:
    return load_countdowns()


@eel.expose
def add_home_countdown(title: str, when: str) -> List[Dict[str, Any]]:
    return add_countdown(title, when)


@eel.expose
def remove_home_countdown(item_id: str) -> List[Dict[str, Any]]:
    return remove_countdown(item_id)


@eel.expose
def get_habits() -> Dict[str, Any]:
    return load_habits()


@eel.expose
def add_home_habit(title: str) -> Dict[str, Any]:
    return add_habit(title)


@eel.expose
def remove_home_habit(habit_id: str) -> Dict[str, Any]:
    return remove_habit(habit_id)


@eel.expose
def toggle_home_habit(habit_id: str) -> Dict[str, Any]:
    return toggle_habit(habit_id)
