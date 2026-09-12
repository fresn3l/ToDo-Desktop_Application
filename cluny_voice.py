"""Cluny rate-goal voice: Sunday digest and below/above-target nags.

Templates only — no model. Each fire tells the user and proposes a to-do
with a date, never a clock time.
"""

from __future__ import annotations

import json
import os
from datetime import date
from typing import Any, Dict, List, Optional

from paths import data_directory

STATE_NAME = "cluny_rate_voice.json"
WINDOW_LABELS = {4: "4 weeks", 12: "12 weeks", 52: "the year"}


def _state_path():
    return data_directory() / STATE_NAME


def _empty_state() -> Dict[str, Any]:
    return {"last_digest_sunday": "", "sides": {}}


def _load_state() -> Dict[str, Any]:
    path = _state_path()
    if not path.exists():
        return _empty_state()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _empty_state()
    if not isinstance(raw, dict):
        return _empty_state()
    sides = raw.get("sides") if isinstance(raw.get("sides"), dict) else {}
    return {
        "last_digest_sunday": str(raw.get("last_digest_sunday") or ""),
        "sides": {str(key): str(value) for key, value in sides.items() if str(key)},
    }


def _save_state(state: Dict[str, Any]) -> None:
    packed = {
        "last_digest_sunday": str(state.get("last_digest_sunday") or ""),
        "sides": state.get("sides") or {},
    }
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(packed, handle, indent=2)
    os.replace(tmp, path)


def rate_side(current: Any, target: Any) -> Optional[str]:
    if current is None or target is None:
        return None
    try:
        now = float(current)
        mark = float(target)
    except (TypeError, ValueError):
        return None
    if now < mark:
        return "below"
    if now > mark:
        return "above"
    return "on"


def format_current(measure: str, value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"
    kind = str(measure or "").strip().lower()
    if kind == "hours":
        if abs(number - round(number)) < 0.05:
            return f"{int(round(number))} hours"
        return f"{number:.1f} hours"
    if abs(number - round(number)) < 0.05:
        return f"{int(round(number))}%"
    return f"{number:.1f}%"


def format_target(measure: str, value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "your target"
    kind = str(measure or "").strip().lower()
    if kind == "hours":
        if abs(number - round(number)) < 0.05:
            return f"{int(round(number))} hours"
        return f"{number:.1f} hours"
    if abs(number - round(number)) < 0.05:
        return f"{int(round(number))}%"
    return f"{number:.1f}%"


def window_label(weeks: Any) -> str:
    try:
        key = int(weeks)
    except (TypeError, ValueError):
        key = 4
    return WINDOW_LABELS.get(key, "4 weeks")


def tell_message(goal: Dict[str, Any], reason: str) -> str:
    title = str(goal.get("title") or "This rate").strip() or "This rate"
    measure = str(goal.get("measure") or "attendance")
    current = format_current(measure, goal.get("current_value"))
    target = format_target(measure, goal.get("target_value"))
    window = window_label(goal.get("window_weeks"))
    side = goal.get("side") or "on"
    if reason == "sunday_digest":
        if side == "below":
            return f"{title} is at {current} over {window}, below your {target} target."
        if side == "above":
            return f"{title} is at {current} over {window}, above your {target} target."
        return f"{title} is at {current} over {window}, on your {target} target."
    if side == "below":
        return f"{title} dropped below your {target} target. It is at {current} over {window}."
    return f"{title} is above your {target} target. It is at {current} over {window}."


def proposed_title(goal: Dict[str, Any], reason: str) -> str:
    title = str(goal.get("title") or "this rate").strip() or "this rate"
    measure = str(goal.get("measure") or "attendance")
    side = goal.get("side") or "on"
    if reason == "sunday_digest" and side == "on":
        return f"Keep {title} on target this week"
    if measure == "hours":
        return (
            f"Put more hours toward {title}"
            if side == "below"
            else f"Keep the hours going for {title}"
        )
    if measure == "todo_completion":
        return (
            f"Close more dated to-dos for {title}"
            if side == "below"
            else f"Keep finishing dated to-dos for {title}"
        )
    return (
        f"Protect more attended time for {title}"
        if side == "below"
        else f"Keep showing up for {title}"
    )


def _rate_rows() -> List[Dict[str, Any]]:
    import goals

    rows: List[Dict[str, Any]] = []
    for goal in goals.list_goals():
        if not goal.get("is_rate") or goal.get("archived"):
            continue
        if goal.get("target_value") is None:
            continue
        side = rate_side(goal.get("current_value"), goal.get("target_value"))
        if side is None:
            continue
        packed = dict(goal)
        packed["side"] = side
        rows.append(packed)
    return rows


def _queue(goal: Dict[str, Any], reason: str, today: date) -> bool:
    import cluny_ask

    uid = f"rate-voice:{goal['id']}:{reason}:{today.isoformat()}"
    return cluny_ask.add_local_proposal(
        {
            "id": uid,
            "title": proposed_title(goal, reason),
            "message": tell_message(goal, reason),
            "due": today.isoformat(),
            "keywords": [str(goal.get("measure") or "attendance")],
            "kind": "rate_voice",
            "reason": reason,
            "goal_id": goal.get("id"),
        }
    )


def refresh_rate_voice(today: Optional[date] = None) -> Dict[str, Any]:
    """Sunday digest once a week; otherwise fire when a rate crosses target."""
    import work

    day = today or work._today()
    state = _load_state()
    rows = _rate_rows()
    added = 0
    fires: List[Dict[str, Any]] = []
    sunday = day.weekday() == 6
    sunday_iso = day.isoformat()
    digest_due = sunday and state.get("last_digest_sunday") != sunday_iso
    sides = dict(state.get("sides") or {})
    for goal in rows:
        goal_id = str(goal.get("id") or "")
        side = str(goal.get("side") or "")
        prior = sides.get(goal_id)
        reason = ""
        if digest_due:
            reason = "sunday_digest"
        elif side in ("below", "above") and side != prior:
            reason = side
        if reason and _queue(goal, reason, day):
            added += 1
            fires.append(
                {
                    "goal_id": goal_id,
                    "reason": reason,
                    "side": side,
                    "title": proposed_title(goal, reason),
                    "message": tell_message(goal, reason),
                }
            )
        sides[goal_id] = side
    if digest_due:
        state["last_digest_sunday"] = sunday_iso
    state["sides"] = sides
    _save_state(state)
    return {"ok": True, "added": added, "fires": fires, "digest": digest_due}


def refresh_rate_voice_safe(today: Optional[date] = None) -> Dict[str, Any]:
    try:
        return refresh_rate_voice(today)
    except Exception as exc:  # noqa: BLE001
        print(f"[Cluny voice] Rate check failed: {exc}")
        return {"ok": False, "added": 0, "error": str(exc), "fires": []}
