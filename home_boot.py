"""One Home round-trip: layout, glance payloads, and the check-in slot."""

from __future__ import annotations

import threading
from datetime import date
from typing import Any, Dict, List, Optional

import eel

import home_layout
import lazy_eel
import work

_supervisor_lock = threading.Lock()
_supervisor_started = False


def _today_iso() -> str:
    return date.today().isoformat()


def _active_page(layout: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    pages = layout.get("pages") or []
    if not pages:
        return None
    aid = layout.get("active_page_id")
    return next((page for page in pages if page.get("id") == aid), pages[0])


def _first_page(layout: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    pages = layout.get("pages") or []
    return pages[0] if pages else None


def _call(module: str, func_name: str, *args):
    loaded = lazy_eel.load_module(module)
    return getattr(loaded, func_name)(*args)


def _safe_call(module: str, func_name: str, *args):
    try:
        return _call(module, func_name, *args)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _cluny_glance() -> Dict[str, Any]:
    inbox = _safe_call("cluny_ask", "get_cluny_inbox") or {}
    health = _safe_call("cluny_ask", "get_cluny_health") or {}
    if not isinstance(inbox, dict):
        inbox = {}
    if not isinstance(health, dict):
        health = {}
    return {**inbox, **health}


def fetch_glance(kind: str) -> Any:
    key = str(kind or "").strip()
    if key == "weather":
        return _safe_call("weather", "get_weather_forecast", False)
    if key == "word":
        return _safe_call("word_of_the_day", "get_word_of_the_day")
    if key == "today_calendar":
        return _safe_call("insights", "get_today_home")
    if key == "todo":
        try:
            return work.get_work_board(_today_iso())
        except Exception as exc:
            return {"ok": False, "error": str(exc), "today": [], "counts": {}}
    if key == "focus":
        return _safe_call("glance", "get_daily_focus")
    if key == "countdown":
        return _safe_call("glance", "get_countdowns")
    if key == "habits":
        return _safe_call("glance", "get_habits")
    if key == "reading":
        return _safe_call("reading", "get_reading")
    if key == "counters":
        return _safe_call("tap_counters", "get_tap_counters")
    if key == "workout":
        return _safe_call("insights", "get_today_status")
    if key == "goals":
        return _safe_call("goals", "list_goals")
    if key == "allwork":
        try:
            return work.list_backlog()
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
    if key == "day_brief":
        return _safe_call("day_brief", "get_day_brief")
    if key == "heatmap":
        return _safe_call("heatmap", "get_heatmap")
    if key == "analytics":
        return _safe_call("insights", "get_analytics", 7)
    if key == "timeline":
        return _safe_call("timeline", "get_timeline_day", _today_iso())
    if key == "cluny":
        return _cluny_glance()
    if key == "now_next":
        return _safe_call("home_glances", "now_next_glance")
    if key == "unplaced":
        return _safe_call("home_glances", "unplaced_glance")
    if key == "dues":
        return _safe_call("home_glances", "dues_this_week")
    if key == "free_today":
        return _safe_call("home_glances", "free_today_glance")
    return None


def _ensure_cluny_supervisor() -> None:
    """Start the brain watcher after Home data is ready, not at process boot."""
    global _supervisor_started
    with _supervisor_lock:
        if _supervisor_started:
            return
        _supervisor_started = True

    def _run() -> None:
        try:
            cluny_brain = lazy_eel.load_module("cluny_brain")
            cluny_brain.start_supervisor()
        except Exception:
            pass

    threading.Thread(target=_run, daemon=True, name="cluny-supervisor").start()


@eel.expose
def get_home_boot(page_id: str = "") -> Dict[str, Any]:
    """Layout plus every glance on the active page, in one Eel call."""
    wanted = str(page_id or "").strip()
    if wanted:
        layout = home_layout.set_active_home_page(wanted)
    else:
        layout = home_layout.get_home_layout()
    page = _active_page(layout) or {}
    kinds: List[str] = []
    seen = set()
    for widget in page.get("widgets") or []:
        kind = str(widget.get("kind") or "").strip()
        if not kind or kind in seen:
            continue
        seen.add(kind)
        kinds.append(kind)
    glances = {kind: fetch_glance(kind) for kind in kinds}
    first = _first_page(layout)
    checkin = None
    if first and page.get("id") == first.get("id"):
        checkin = _safe_call("daily_checklist", "get_home_checkin")
    _ensure_cluny_supervisor()
    return {
        "layout": layout,
        "glances": glances,
        "checkin": checkin,
        "page_id": page.get("id") or "",
    }
