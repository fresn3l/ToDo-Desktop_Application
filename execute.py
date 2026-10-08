"""Home as a go circuit: Execute, Aim, Close.

Not a widget board. Phase comes from the calendar awake window. One 12-week
aim. Habits follow the clock in a 21-day block. Calendar stays the planner.
"""

from __future__ import annotations

import json
import os
import random
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import eel

from paths import data_directory

BOUT_MINUTES = (45, 70, 90)
DEFAULT_BOUT = 70
VISUAL_SECONDS = 60
DEFOCUS_MINUTES = 15
AIM_WEEKS = 12
MAX_WEEKLY_MINUTES = 80 * 60
HABIT_BLOCK_DAYS = 21
HABIT_CAP = 6
HABIT_SUCCESS_MIN = 4
MAX_TEXT = 400
MAX_RECAP = 8_000
DIFFICULTY = ("too_easy", "about_right", "too_hard")
BUCKETS = ("hard", "easy")
BOUT_STATES = ("idle", "target", "work", "review", "defocus", "done")
PHASE_LABELS = {
    "hard": "Hard window",
    "easy": "Easy window",
    "wind_down": "Wind down",
}


def _now() -> datetime:
    return datetime.now()


def _today() -> date:
    return _now().date()


def _path():
    return data_directory() / "execute.json"


def _read() -> Dict[str, Any]:
    path = _path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _write(data: Dict[str, Any]) -> None:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
    os.replace(tmp, path)


def _clip(raw: Any, limit: int) -> str:
    return str(raw or "").strip()[:limit]


def _iso(stamp: Optional[datetime] = None) -> str:
    return (stamp or _now()).isoformat(timespec="seconds")


def _parse_stamp(raw: Any) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(str(raw or "")[:19])
    except ValueError:
        return None


def _parse_hhmm(raw: str) -> Tuple[int, int]:
    text = str(raw or "05:30").strip()
    if ":" not in text and len(text) >= 3:
        text = f"{text[:-2]}:{text[-2:]}"
    parts = text.split(":")
    try:
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
    except (TypeError, ValueError):
        return 5, 30
    return max(0, min(23, hour)), max(0, min(59, minute))


def _week_key(day: Optional[date] = None) -> str:
    current = day or _today()
    return (current - timedelta(days=current.weekday())).isoformat()


def day_phase(now: Optional[datetime] = None, day_start: str = "05:30") -> Dict[str, Any]:
    """Hard for the first 8 hours after waking, easy until 15, then wind down."""
    current = now or _now()
    hour, minute = _parse_hhmm(day_start)
    wake = current.replace(hour=hour, minute=minute, second=0, microsecond=0)
    hours = (current - wake).total_seconds() / 3600
    if 0 <= hours < 8:
        name = "hard"
    elif 8 <= hours < 15:
        name = "easy"
    else:
        name = "wind_down"
    return {
        "name": name,
        "label": PHASE_LABELS[name],
        "hours_awake": round(hours, 2),
        "day_start": f"{hour:02d}:{minute:02d}",
        "close": name == "wind_down",
    }


def _empty_bout() -> Dict[str, Any]:
    return {
        "status": "idle",
        "minutes": DEFAULT_BOUT,
        "started_at": "",
        "resume": "",
        "coin": "",
        "happened": None,
    }


def _empty_today(day: str) -> Dict[str, Any]:
    return {
        "date": day,
        "priority_id": "",
        "first_bout": "",
        "micro_suck": "",
        "micro_suck_done": False,
        "bout": _empty_bout(),
        "bouts_done": 0,
        "close_recap": "",
        "closed": False,
        "tomorrow_bout": "",
    }


def _load() -> Dict[str, Any]:
    raw = _read()
    today = _today().isoformat()
    day = raw.get("today") if isinstance(raw.get("today"), dict) else {}
    if str(day.get("date") or "") != today:
        # Last night's tomorrow line is this morning's first hard bout.
        carry = _clip(day.get("tomorrow_bout"), MAX_TEXT)
        day = _empty_today(today)
        if carry:
            day["first_bout"] = carry
    bout = day.get("bout") if isinstance(day.get("bout"), dict) else _empty_bout()
    if str(bout.get("status") or "idle") not in BOUT_STATES:
        bout["status"] = "idle"
    try:
        minutes = int(bout.get("minutes") or DEFAULT_BOUT)
    except (TypeError, ValueError):
        minutes = DEFAULT_BOUT
    bout["minutes"] = minutes if minutes in BOUT_MINUTES else DEFAULT_BOUT
    day["bout"] = bout
    day["date"] = today
    aim = raw.get("aim") if isinstance(raw.get("aim"), dict) else {}
    block = raw.get("habits_block") if isinstance(raw.get("habits_block"), dict) else {}
    return {"aim": aim, "today": day, "habits_block": block}


def _save(store: Dict[str, Any]) -> None:
    _write(
        {
            "aim": store.get("aim") or {},
            "today": store.get("today") or _empty_today(_today().isoformat()),
            "habits_block": store.get("habits_block") or {},
        }
    )


def _flip() -> str:
    return "heads" if random.random() < 0.5 else "tails"


def _advance_bout(store: Dict[str, Any], now: Optional[datetime] = None) -> bool:
    """Timed states roll forward on their own. Returns True when anything moved."""
    current = now or _now()
    bout = store["today"]["bout"]
    start = _parse_stamp(bout.get("started_at"))
    if start is None:
        return False
    status = str(bout.get("status") or "idle")
    moved = False
    if status == "target" and current >= start + timedelta(seconds=VISUAL_SECONDS):
        start = start + timedelta(seconds=VISUAL_SECONDS)
        bout["status"] = status = "work"
        bout["started_at"] = _iso(start)
        moved = True
    if status == "work" and current >= start + timedelta(minutes=int(bout["minutes"])):
        bout["status"] = "review"
        moved = True
    elif status == "defocus" and current >= start + timedelta(minutes=DEFOCUS_MINUTES):
        bout["status"] = "done"
        if not bout.get("coin"):
            bout["coin"] = _flip()
        moved = True
    return moved


def _remaining_seconds(bout: Dict[str, Any], now: Optional[datetime] = None) -> int:
    current = now or _now()
    start = _parse_stamp(bout.get("started_at"))
    status = bout.get("status")
    if start is None or status not in ("target", "work", "defocus"):
        return 0
    if status == "target":
        span = VISUAL_SECONDS
    elif status == "work":
        span = int(bout["minutes"]) * 60
    else:
        span = DEFOCUS_MINUTES * 60
    return max(0, span - int((current - start).total_seconds()))


def _aim_payload(aim: Dict[str, Any]) -> Dict[str, Any]:
    title = _clip(aim.get("title"), MAX_TEXT)
    try:
        weekly = int(aim.get("weekly_minutes") or 0)
    except (TypeError, ValueError):
        weekly = 0
    weekly = max(0, min(weekly, MAX_WEEKLY_MINUTES))
    week = _week_key()
    spent_map = aim.get("week_spent") if isinstance(aim.get("week_spent"), dict) else {}
    try:
        spent = max(0, int(spent_map.get(week) or 0))
    except (TypeError, ValueError):
        spent = 0
    last_week = _week_key(_today() - timedelta(days=7))
    diff_map = aim.get("difficulty") if isinstance(aim.get("difficulty"), dict) else {}
    difficulty = str(diff_map.get(last_week) or "")
    started = str(aim.get("started_on") or "")
    remaining = AIM_WEEKS
    if started:
        try:
            elapsed_weeks = (_today() - date.fromisoformat(started[:10])).days // 7
            remaining = max(0, AIM_WEEKS - elapsed_weeks)
        except ValueError:
            pass
    return {
        "title": title,
        "weekly_minutes": weekly,
        "started_on": started,
        "end_date": str(aim.get("end_date") or ""),
        "spent_minutes": spent,
        "remaining_weeks": remaining,
        "difficulty": difficulty if difficulty in DIFFICULTY else "",
        "ask_difficulty": bool(title and weekly and started and started[:10] < week),
        "week_start": week,
        "set": bool(title and weekly),
    }


def _credit_aim(store: Dict[str, Any], minutes: int) -> None:
    aim = store.get("aim") if isinstance(store.get("aim"), dict) else {}
    if minutes <= 0 or not _clip(aim.get("title"), MAX_TEXT):
        return
    spent_map = aim.get("week_spent") if isinstance(aim.get("week_spent"), dict) else {}
    week = _week_key()
    try:
        current = int(spent_map.get(week) or 0)
    except (TypeError, ValueError):
        current = 0
    spent_map[week] = current + int(minutes)
    aim["week_spent"] = spent_map
    store["aim"] = aim


def _day_start() -> str:
    try:
        import calclock

        return str(calclock.load_settings().get("day_start") or "05:30")
    except Exception:
        return "05:30"


def _clock_focus() -> Dict[str, Any]:
    try:
        from home_glances import now_next_glance

        beat = now_next_glance()
    except Exception:
        return {"kind": "none"}
    item = beat.get("now") or beat.get("next")
    if not item or not item.get("title"):
        return {"kind": "none"}
    return {
        "kind": "clock",
        "id": item.get("work_item_id") or "",
        "title": item.get("title") or "",
        "start_at": item.get("start_at") or "",
        "end_at": item.get("end_at") or "",
        "when": "now" if beat.get("now") else "next",
    }


def _today_todos() -> List[Dict[str, Any]]:
    """To Dos dated today. Calendar assignments are Due, not To Do."""
    try:
        import work

        board = work.get_work_board()
    except Exception:
        return []
    rows = []
    for item in board.get("today") or []:
        if str(item.get("source") or "") == "calendar":
            continue
        rows.append(
            {
                "id": item.get("id"),
                "title": item.get("title") or "",
                "open": str(item.get("status") or "") != "done",
            }
        )
    return rows


def _one_thing(store: Dict[str, Any], todos: List[Dict[str, Any]]) -> Dict[str, Any]:
    day = store["today"]
    first = _clip(day.get("first_bout"), MAX_TEXT)
    priority = str(day.get("priority_id") or "")
    if priority:
        hit = next((row for row in todos if row["id"] == priority), None)
        if hit:
            return {"kind": "todo", "title": hit["title"], "id": hit["id"], "open": hit["open"]}
    if first:
        return {"kind": "intention", "title": first, "id": ""}
    clock = _clock_focus()
    if clock.get("kind") == "clock":
        return clock
    open_todo = next((row for row in todos if row["open"]), None)
    if open_todo:
        return {"kind": "todo", "title": open_todo["title"], "id": open_todo["id"], "open": True}
    return {"kind": "empty", "title": "Name the hard thing", "id": ""}


def _habit_block(store: Dict[str, Any]) -> Dict[str, Any]:
    """21 days of forming, then 21 days with no new habits, then repeat."""
    block = store.get("habits_block") if isinstance(store.get("habits_block"), dict) else {}
    started = str(block.get("started_on") or "")
    mode = str(block.get("mode") or "form")
    if mode not in ("form", "test"):
        mode = "form"
    if started:
        try:
            anchor = block.get("test_started_on") if mode == "test" else started
            elapsed = (_today() - date.fromisoformat(str(anchor or started)[:10])).days
        except ValueError:
            elapsed = 0
        if elapsed >= HABIT_BLOCK_DAYS:
            if mode == "form":
                block = {"started_on": started, "mode": "test", "test_started_on": _today().isoformat()}
            else:
                block = {"started_on": _today().isoformat(), "mode": "form"}
            store["habits_block"] = block
            mode = block["mode"]
    return {
        "started_on": str(block.get("started_on") or ""),
        "mode": mode,
        "can_add": mode == "form",
        "days": HABIT_BLOCK_DAYS,
    }


def _habits_payload(store: Dict[str, Any]) -> Dict[str, Any]:
    import glance

    block = _habit_block(store)
    rows = []
    for row in (glance.load_habits().get("habits") or [])[:HABIT_CAP]:
        bucket = str(row.get("bucket") or "hard")
        rows.append({**row, "bucket": bucket if bucket in BUCKETS else "hard"})
    done = sum(1 for row in rows if row.get("done"))
    need = min(HABIT_SUCCESS_MIN, len(rows))
    return {
        **block,
        "habits": rows,
        "done": done,
        "total": len(rows),
        "success": bool(rows) and done >= need,
        "cap": HABIT_CAP,
        "need": need,
    }


def _payload(store: Dict[str, Any]) -> Dict[str, Any]:
    day = store["today"]
    bout = day["bout"]
    todos = _today_todos()
    return {
        "phase": day_phase(_now(), _day_start()),
        "one_thing": _one_thing(store, todos),
        "todos": todos,
        "priority_id": day.get("priority_id") or "",
        "first_bout": day.get("first_bout") or "",
        "micro_suck": day.get("micro_suck") or "",
        "micro_suck_done": bool(day.get("micro_suck_done")),
        "bout": {
            **bout,
            "remaining_seconds": _remaining_seconds(bout),
            "visual_seconds": VISUAL_SECONDS,
            "defocus_minutes": DEFOCUS_MINUTES,
            "options": list(BOUT_MINUTES),
        },
        "bouts_done": int(day.get("bouts_done") or 0),
        "aim": _aim_payload(store.get("aim") or {}),
        "habits": _habits_payload(store),
        "leftovers": [row for row in todos if row["open"]],
        "close_recap": day.get("close_recap") or "",
        "closed": bool(day.get("closed")),
        "tomorrow_bout": day.get("tomorrow_bout") or "",
    }


def _fresh() -> Dict[str, Any]:
    store = _load()
    before = json.dumps(store, sort_keys=True)
    _advance_bout(store)
    _habit_block(store)
    if json.dumps(store, sort_keys=True) != before or not _path().exists():
        _save(store)
    return store


@eel.expose
def get_execute_home() -> Dict[str, Any]:
    return _payload(_fresh())


@eel.expose
def pin_execute_priority(work_id: str = "") -> Dict[str, Any]:
    store = _fresh()
    store["today"]["priority_id"] = _clip(work_id, 80)
    _save(store)
    return _payload(store)


@eel.expose
def save_first_bout(text: str = "") -> Dict[str, Any]:
    store = _fresh()
    store["today"]["first_bout"] = _clip(text, MAX_TEXT)
    _save(store)
    return _payload(store)


@eel.expose
def start_execute_bout(minutes: int = DEFAULT_BOUT, visual: bool = True) -> Dict[str, Any]:
    store = _fresh()
    if store["today"]["bout"].get("status") in ("target", "work", "review"):
        raise ValueError("Finish this bout first.")
    try:
        span = int(minutes)
    except (TypeError, ValueError):
        span = DEFAULT_BOUT
    bout = _empty_bout()
    bout["minutes"] = span if span in BOUT_MINUTES else DEFAULT_BOUT
    bout["started_at"] = _iso()
    bout["status"] = "target" if visual else "work"
    store["today"]["bout"] = bout
    _save(store)
    return _payload(store)


@eel.expose
def skip_execute_visual() -> Dict[str, Any]:
    store = _fresh()
    bout = store["today"]["bout"]
    if bout.get("status") == "target":
        bout["status"] = "work"
        bout["started_at"] = _iso()
        _save(store)
    return _payload(store)


@eel.expose
def set_execute_outcome(happened: bool = True, resume: str = "") -> Dict[str, Any]:
    """Happened earns the minutes and a defocus. Still open keeps a resume line."""
    store = _fresh()
    bout = store["today"]["bout"]
    status = bout.get("status")
    if status not in ("work", "review"):
        raise ValueError("Finish a bout first.")
    bout["happened"] = bool(happened)
    bout["resume"] = _clip(resume, MAX_TEXT)
    if happened:
        if status == "work":
            start = _parse_stamp(bout.get("started_at")) or _now()
            minutes = max(1, int((_now() - start).total_seconds() // 60))
            minutes = min(minutes, int(bout["minutes"]))
        else:
            minutes = int(bout["minutes"])
        _credit_aim(store, minutes)
        store["today"]["bouts_done"] = int(store["today"].get("bouts_done") or 0) + 1
        bout["status"] = "defocus"
        bout["started_at"] = _iso()
    else:
        bout["status"] = "done"
        bout["coin"] = ""
        if bout["resume"]:
            store["today"]["first_bout"] = bout["resume"]
    _save(store)
    return _payload(store)


@eel.expose
def finish_execute_defocus() -> Dict[str, Any]:
    store = _fresh()
    bout = store["today"]["bout"]
    if bout.get("status") == "defocus":
        bout["status"] = "done"
        if not bout.get("coin"):
            bout["coin"] = _flip()
        _save(store)
    return _payload(store)


@eel.expose
def save_execute_aim(title: str = "", weekly_minutes: int = 0) -> Dict[str, Any]:
    store = _fresh()
    named = _clip(title, MAX_TEXT)
    if not named:
        store["aim"] = {}
        _save(store)
        return _payload(store)
    try:
        weekly = int(weekly_minutes)
    except (TypeError, ValueError):
        weekly = 0
    weekly = max(0, min(weekly, MAX_WEEKLY_MINUTES))
    if weekly <= 0:
        raise ValueError("Set weekly minutes for the aim.")
    existing = store.get("aim") if isinstance(store.get("aim"), dict) else {}
    try:
        start_day = date.fromisoformat(str(existing.get("started_on") or "")[:10])
    except ValueError:
        start_day = _today()
    store["aim"] = {
        "title": named,
        "weekly_minutes": weekly,
        "started_on": start_day.isoformat(),
        "end_date": (start_day + timedelta(days=AIM_WEEKS * 7)).isoformat(),
        "week_spent": existing.get("week_spent") if isinstance(existing.get("week_spent"), dict) else {},
        "difficulty": existing.get("difficulty") if isinstance(existing.get("difficulty"), dict) else {},
    }
    _save(store)
    return _payload(store)


@eel.expose
def set_aim_difficulty(level: str = "") -> Dict[str, Any]:
    """Rates last week. Too easy or too hard is the cue to change weekly minutes."""
    key = str(level or "").strip()
    if key not in DIFFICULTY:
        raise ValueError("Was last week too easy, about right, or too hard?")
    store = _fresh()
    aim = store.get("aim") if isinstance(store.get("aim"), dict) else {}
    if not _clip(aim.get("title"), MAX_TEXT):
        raise ValueError("Set the 12-week aim first.")
    diff = aim.get("difficulty") if isinstance(aim.get("difficulty"), dict) else {}
    diff[_week_key(_today() - timedelta(days=7))] = key
    aim["difficulty"] = diff
    store["aim"] = aim
    _save(store)
    return _payload(store)


@eel.expose
def save_micro_suck(text: str = "") -> Dict[str, Any]:
    store = _fresh()
    store["today"]["micro_suck"] = _clip(text, MAX_TEXT)
    if not store["today"]["micro_suck"]:
        store["today"]["micro_suck_done"] = False
    _save(store)
    return _payload(store)


@eel.expose
def toggle_micro_suck() -> Dict[str, Any]:
    store = _fresh()
    if not store["today"].get("micro_suck"):
        raise ValueError("Name one hard extra first.")
    store["today"]["micro_suck_done"] = not bool(store["today"].get("micro_suck_done"))
    _save(store)
    return _payload(store)


@eel.expose
def close_execute_day(
    recap: str = "",
    tomorrow_bout: str = "",
    park_ids: Optional[List[str]] = None,
    date_ids: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """After-action: what happened, tomorrow's first bout, and where leftovers go."""
    store = _fresh()
    store["today"]["close_recap"] = _clip(recap, MAX_RECAP)
    store["today"]["tomorrow_bout"] = _clip(tomorrow_bout, MAX_TEXT)
    store["today"]["closed"] = True
    _save(store)
    moves: List[Tuple[str, Optional[str]]] = []
    for item_id in list(park_ids or []):
        key = _clip(item_id, 80)
        if key:
            moves.append((key, None))
    if isinstance(date_ids, dict):
        for item_id, day in date_ids.items():
            key = _clip(item_id, 80)
            if key:
                moves.append((key, str(day or "") or None))
    if moves:
        import work

        failed = 0
        for key, day in moves:
            try:
                work.assign_work_item(key, day)
            except ValueError:
                failed += 1
        if failed:
            raise ValueError("Some leftovers were already gone. Close saved.")
    return _payload(store)


@eel.expose
def add_execute_habit(title: str = "", bucket: str = "hard") -> Dict[str, Any]:
    import glance

    store = _fresh()
    if not _habit_block(store)["can_add"]:
        raise ValueError("No new habits in the test window.")
    if len(glance.load_habits().get("habits") or []) >= HABIT_CAP:
        raise ValueError("Six habits is the cap.")
    glance.add_habit(title, bucket if bucket in BUCKETS else "hard")
    if not store["habits_block"].get("started_on"):
        store["habits_block"] = {"started_on": _today().isoformat(), "mode": "form"}
        _save(store)
    return _payload(store)


@eel.expose
def set_habit_bucket(habit_id: str = "", bucket: str = "hard") -> Dict[str, Any]:
    import glance

    glance.set_bucket(_clip(habit_id, 80), bucket)
    return get_execute_home()


@eel.expose
def start_habits_block() -> Dict[str, Any]:
    store = _fresh()
    store["habits_block"] = {"started_on": _today().isoformat(), "mode": "form"}
    _save(store)
    return _payload(store)


@eel.expose
def toggle_execute_habit(habit_id: str = "") -> Dict[str, Any]:
    import glance

    glance.toggle_habit(habit_id)
    return get_execute_home()


@eel.expose
def remove_execute_habit(habit_id: str = "") -> Dict[str, Any]:
    import glance

    glance.remove_habit(habit_id)
    return get_execute_home()
