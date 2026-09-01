"""Morning brief and evening review — structured snapshots plus journal prose."""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

import eel

import journal
import work
from paths import data_directory

SLOTS = ("morning", "evening")
MAX_FOCUS = 3
MAX_AGENDA = 4
MAX_TEXT = 20_000
DEFAULT_EVENING_AFTER = "17:00"


def _today() -> date:
    return date.today()


def _now() -> datetime:
    return datetime.now()


def _db_path():
    return data_directory() / "day_briefs.sqlite"


def _settings_path():
    return data_directory() / "day_brief.json"


def _connect() -> sqlite3.Connection:
    path = _db_path()
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS briefs (
            local_date TEXT NOT NULL,
            slot TEXT NOT NULL,
            intention_text TEXT,
            recap_text TEXT,
            focus_work_ids TEXT,
            shown_event_ids TEXT,
            done_ids TEXT,
            leftover_ids TEXT,
            rolled_ids TEXT,
            journal_id TEXT,
            saved_at TEXT NOT NULL,
            PRIMARY KEY (local_date, slot)
        )
        """
    )
    return conn


def _parse_ids(raw: Any) -> List[str]:
    if isinstance(raw, list):
        data = raw
    elif isinstance(raw, str) and raw.strip():
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = []
    else:
        data = []
    out: List[str] = []
    seen = set()
    for item in data:
        key = str(item or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def _clip_text(raw: Any) -> str:
    return str(raw or "").strip()[:MAX_TEXT]


def _parse_cutoff(raw: Any) -> tuple[int, int]:
    text = str(raw or DEFAULT_EVENING_AFTER).strip()
    parts = text.split(":")
    try:
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
    except (TypeError, ValueError):
        return 17, 0
    hour = max(0, min(23, hour))
    minute = max(0, min(59, minute))
    return hour, minute


def _load_settings() -> Dict[str, Any]:
    packed = {
        "evening_after": DEFAULT_EVENING_AFTER,
        "override_date": "",
        "override_slot": "",
    }
    path = _settings_path()
    if not path.exists():
        return packed
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return packed
    if not isinstance(data, dict):
        return packed
    hour, minute = _parse_cutoff(data.get("evening_after"))
    packed["evening_after"] = f"{hour:02d}:{minute:02d}"
    packed["override_date"] = str(data.get("override_date") or "").strip()[:10]
    slot = str(data.get("override_slot") or "").strip()
    packed["override_slot"] = slot if slot in SLOTS else ""
    return packed


def _save_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    path = _settings_path()
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(settings, handle, indent=2)
    path.parent.mkdir(parents=True, exist_ok=True)
    import os

    os.replace(tmp, path)
    return settings


def resolve_slot(now: Optional[datetime] = None, settings: Optional[Dict[str, Any]] = None) -> str:
    now = now or _now()
    settings = settings or _load_settings()
    today = now.date().isoformat()
    if settings.get("override_date") == today and settings.get("override_slot") in SLOTS:
        return settings["override_slot"]
    hour, minute = _parse_cutoff(settings.get("evening_after"))
    cutoff = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return "evening" if now >= cutoff else "morning"


def _row_to_dict(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    return {
        "local_date": row["local_date"],
        "slot": row["slot"],
        "intention_text": row["intention_text"] or "",
        "recap_text": row["recap_text"] or "",
        "focus_work_ids": _parse_ids(row["focus_work_ids"]),
        "shown_event_ids": _parse_ids(row["shown_event_ids"]),
        "done_ids": _parse_ids(row["done_ids"]),
        "leftover_ids": _parse_ids(row["leftover_ids"]),
        "rolled_ids": _parse_ids(row["rolled_ids"]),
        "journal_id": row["journal_id"] or "",
        "saved_at": row["saved_at"],
    }


def get_brief(local_date: str, slot: str) -> Optional[Dict[str, Any]]:
    if slot not in SLOTS:
        return None
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM briefs WHERE local_date = ? AND slot = ?",
            (local_date, slot),
        ).fetchone()
    return _row_to_dict(row)


def list_briefs_in_range(start: date, end: date) -> List[Dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM briefs
            WHERE local_date >= ? AND local_date <= ?
            ORDER BY local_date ASC, slot ASC
            """,
            (start.isoformat(), end.isoformat()),
        ).fetchall()
    return [_row_to_dict(row) for row in rows if row is not None]


def _upsert_row(payload: Dict[str, Any]) -> Dict[str, Any]:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO briefs (
                local_date, slot, intention_text, recap_text, focus_work_ids,
                shown_event_ids, done_ids, leftover_ids, rolled_ids, journal_id, saved_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(local_date, slot) DO UPDATE SET
                intention_text = excluded.intention_text,
                recap_text = excluded.recap_text,
                focus_work_ids = excluded.focus_work_ids,
                shown_event_ids = excluded.shown_event_ids,
                done_ids = excluded.done_ids,
                leftover_ids = excluded.leftover_ids,
                rolled_ids = excluded.rolled_ids,
                journal_id = excluded.journal_id,
                saved_at = excluded.saved_at
            """,
            (
                payload["local_date"],
                payload["slot"],
                payload.get("intention_text") or "",
                payload.get("recap_text") or "",
                json.dumps(payload.get("focus_work_ids") or []),
                json.dumps(payload.get("shown_event_ids") or []),
                json.dumps(payload.get("done_ids") or []),
                json.dumps(payload.get("leftover_ids") or []),
                json.dumps(payload.get("rolled_ids") or []),
                payload.get("journal_id") or "",
                payload["saved_at"],
            ),
        )
        conn.commit()
    row = get_brief(payload["local_date"], payload["slot"])
    assert row is not None
    return row


def _focus_sort_key(item: Dict[str, Any]) -> tuple:
    due = str(item.get("due_at") or "9999-12-31")
    return (due, int(item.get("sort_order") or 0), str(item.get("title") or "").lower())


def _open_today(local_date: str) -> List[Dict[str, Any]]:
    items = [item for item in work.list_work_for_date(local_date) if item.get("status") != "done"]
    items.sort(key=_focus_sort_key)
    return items


def _agenda(local_date: str, now: datetime) -> List[Dict[str, Any]]:
    try:
        import calclock

        items = list(calclock.get_day_agenda(local_date).get("items") or [])
    except Exception:
        items = []
    upcoming = []
    earlier = []
    for item in items:
        start = str(item.get("start_at") or "")
        try:
            when = datetime.fromisoformat(start)
        except ValueError:
            earlier.append(item)
            continue
        if when >= now:
            upcoming.append(item)
        else:
            earlier.append(item)
    ordered = upcoming + earlier
    return ordered[:MAX_AGENDA]


def _summarize_item(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": item.get("id"),
        "title": item.get("title") or "",
        "status": item.get("status") or "open",
        "due_at": item.get("due_at"),
        "scheduled_date": item.get("scheduled_date"),
        "goal_id": item.get("goal_id"),
        "estimate_minutes": item.get("estimate_minutes"),
    }


def _review_for(local_date: str, morning: Optional[Dict[str, Any]], evening: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    rolled_ids = _parse_ids((evening or {}).get("rolled_ids"))
    today_items = {_summarize_item(item)["id"]: _summarize_item(item) for item in work.list_work_for_date(local_date)}
    focus_ids = _parse_ids((morning or {}).get("focus_work_ids")) if morning else list(today_items.keys())
    extra = work.get_work_items_by_ids(focus_ids + rolled_ids)
    by_id = {item["id"]: _summarize_item(item) for item in extra}
    by_id.update(today_items)
    done = []
    leftover = []
    rolled = []
    seen = set()
    for item_id in focus_ids + list(today_items.keys()) + rolled_ids:
        if item_id in seen:
            continue
        seen.add(item_id)
        item = by_id.get(item_id)
        if not item:
            continue
        if item_id in rolled_ids:
            rolled.append(item)
            continue
        if morning and item_id not in focus_ids and item_id not in today_items:
            continue
        if morning and item_id not in focus_ids:
            continue
        if item.get("status") == "done":
            done.append(item)
        else:
            leftover.append(item)
    return {"done": done, "leftover": leftover, "rolled": rolled}


def _was_done_on(item: Dict[str, Any], local_date: str) -> bool:
    if item.get("status") != "done":
        return False
    finished = str(item.get("finished_at") or "")[:10]
    if finished:
        return finished == local_date
    return str(item.get("scheduled_date") or "") == local_date


def capacity_for_range(start: date, end: date) -> Dict[str, Any]:
    briefs = list_briefs_in_range(start, end)
    mornings = [row for row in briefs if row["slot"] == "morning"]
    evenings = {(row["local_date"]): row for row in briefs if row["slot"] == "evening"}
    focus_count = 0
    done_count = 0
    rolled_count = 0
    leftover_count = 0
    days_planned = 0
    for morning in mornings:
        ids = morning.get("focus_work_ids") or []
        if not ids and not (morning.get("intention_text") or "").strip():
            continue
        days_planned += 1
        evening = evenings.get(morning["local_date"]) or {}
        rolled = set(_parse_ids(evening.get("rolled_ids")))
        items = {item["id"]: item for item in work.get_work_items_by_ids(ids)}
        focus_count += len(ids)
        for item_id in ids:
            if item_id in rolled:
                rolled_count += 1
                continue
            item = items.get(item_id)
            if item and _was_done_on(item, morning["local_date"]):
                done_count += 1
            else:
                leftover_count += 1
    pct = round((done_count / focus_count) * 100) if focus_count else 0
    return {
        "days_planned": days_planned,
        "focus_count": focus_count,
        "done_count": done_count,
        "rolled_count": rolled_count,
        "leftover_count": leftover_count,
        "completion_pct": pct,
    }


def _payload(slot: Optional[str] = None) -> Dict[str, Any]:
    settings = _load_settings()
    now = _now()
    local_date = now.date().isoformat()
    active = slot if slot in SLOTS else resolve_slot(now, settings)
    morning = get_brief(local_date, "morning")
    evening = get_brief(local_date, "evening")
    candidates = _open_today(local_date)
    selected_ids = (morning or {}).get("focus_work_ids") or [item["id"] for item in candidates[:MAX_FOCUS]]
    agenda = _agenda(local_date, now)
    review = _review_for(local_date, morning, evening)
    tomorrow = (now.date() + timedelta(days=1)).isoformat()
    return {
        "local_date": local_date,
        "slot": active,
        "evening_after": settings["evening_after"],
        "override_slot": settings["override_slot"] if settings.get("override_date") == local_date else "",
        "agenda": agenda,
        "focus_candidates": [_summarize_item(item) for item in candidates],
        "selected_ids": selected_ids,
        "morning": morning,
        "evening": evening,
        "review": review,
        "tomorrow": tomorrow,
        "max_focus": MAX_FOCUS,
    }


@eel.expose
def get_day_brief() -> Dict[str, Any]:
    return _payload()


@eel.expose
def set_day_brief_override(slot: str = "") -> Dict[str, Any]:
    settings = _load_settings()
    key = str(slot or "").strip().lower()
    today = _today().isoformat()
    if key in SLOTS:
        settings["override_date"] = today
        settings["override_slot"] = key
    else:
        settings["override_date"] = ""
        settings["override_slot"] = ""
    _save_settings(settings)
    return _payload(key if key in SLOTS else None)


@eel.expose
def save_morning_brief(intention: str, focus_work_ids: Any = None) -> Dict[str, Any]:
    text = _clip_text(intention)
    if not text:
        raise ValueError("Write what you plan to accomplish today")
    local_date = _today().isoformat()
    candidates = {item["id"] for item in _open_today(local_date)}
    existing = get_brief(local_date, "morning")
    known = set(candidates)
    if existing:
        known.update(existing.get("focus_work_ids") or [])
    ids = [item_id for item_id in _parse_ids(focus_work_ids) if item_id in known][:MAX_FOCUS]
    agenda = _agenda(local_date, _now())
    extra = {
        "slot": "morning",
        "local_date": local_date,
        "focus_work_ids": ids,
        "shown_event_ids": [item.get("id") for item in agenda if item.get("id")],
    }
    entry = journal.upsert_kinded_journal_entry(text, "morning_brief", local_date, extra)
    _upsert_row(
        {
            "local_date": local_date,
            "slot": "morning",
            "intention_text": text,
            "recap_text": (existing or {}).get("recap_text") or "",
            "focus_work_ids": ids,
            "shown_event_ids": extra["shown_event_ids"],
            "done_ids": [],
            "leftover_ids": [],
            "rolled_ids": [],
            "journal_id": entry.get("id") or "",
            "saved_at": _now().isoformat(),
        }
    )
    return _payload("morning")


@eel.expose
def save_evening_review(recap: str) -> Dict[str, Any]:
    text = _clip_text(recap)
    if not text:
        raise ValueError("Write an end-of-day journal entry")
    local_date = _today().isoformat()
    morning = get_brief(local_date, "morning")
    existing = get_brief(local_date, "evening")
    review = _review_for(local_date, morning, existing)
    done_ids = [item["id"] for item in review["done"]]
    leftover_ids = [item["id"] for item in review["leftover"]]
    rolled_ids = [item["id"] for item in review["rolled"]]
    extra = {
        "slot": "evening",
        "local_date": local_date,
        "focus_work_ids": (morning or {}).get("focus_work_ids") or [],
        "done_ids": done_ids,
        "leftover_ids": leftover_ids,
        "rolled_ids": rolled_ids,
    }
    entry = journal.upsert_kinded_journal_entry(text, "evening_review", local_date, extra)
    _upsert_row(
        {
            "local_date": local_date,
            "slot": "evening",
            "intention_text": (existing or {}).get("intention_text") or "",
            "recap_text": text,
            "focus_work_ids": extra["focus_work_ids"],
            "shown_event_ids": (existing or {}).get("shown_event_ids") or [],
            "done_ids": done_ids,
            "leftover_ids": leftover_ids,
            "rolled_ids": rolled_ids,
            "journal_id": entry.get("id") or "",
            "saved_at": _now().isoformat(),
        }
    )
    return _payload("evening")


@eel.expose
def roll_brief_item_to_tomorrow(item_id: str) -> Dict[str, Any]:
    key = str(item_id or "").strip()
    if not key:
        raise ValueError("Work item is required")
    local_date = _today().isoformat()
    tomorrow = (_today() + timedelta(days=1)).isoformat()
    work.assign_work_item(key, tomorrow)
    existing = get_brief(local_date, "evening") or {
        "local_date": local_date,
        "slot": "evening",
        "intention_text": "",
        "recap_text": "",
        "focus_work_ids": [],
        "shown_event_ids": [],
        "done_ids": [],
        "leftover_ids": [],
        "rolled_ids": [],
        "journal_id": "",
    }
    rolled = _parse_ids(existing.get("rolled_ids"))
    if key not in rolled:
        rolled.append(key)
    existing["rolled_ids"] = rolled
    existing["saved_at"] = _now().isoformat()
    _upsert_row(existing)
    return _payload("evening")
