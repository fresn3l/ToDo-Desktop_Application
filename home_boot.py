"""One Home round-trip: layout, glance payloads, and the check-in slot."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from typing import Any, Dict, List, Optional

import eel

import home_layout
import lazy_eel
import work

_supervisor_lock = threading.Lock()
_supervisor_started = False
_rate_voice_lock = threading.Lock()
_rate_voice_thread: Optional[threading.Thread] = None


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
    # Inbox is local JSON. Health probes the brain over HTTP and must stay
    # off the Home click path.
    inbox = _safe_call("cluny_ask", "get_cluny_inbox") or {}
    return inbox if isinstance(inbox, dict) else {}


def _today_calendar_glance() -> Dict[str, Any]:
    """Clock beat only. Full Today (workouts, streak, brief) stays on the overlay."""
    beat = _safe_call("home_glances", "now_next_glance")
    if isinstance(beat, dict) and beat.get("ok") is False:
        return beat
    packed = beat if isinstance(beat, dict) else {}
    return {
        "ok": True,
        "beat": packed,
        "local_date": packed.get("local_date") or _today_iso(),
    }


def fetch_glance(kind: str) -> Any:
    key = str(kind or "").strip()
    if key == "weather":
        return _safe_call("weather", "get_weather_forecast", False)
    if key == "word":
        return _safe_call("word_of_the_day", "get_word_of_the_day")
    if key == "today_calendar":
        return _today_calendar_glance()
    if key == "todo":
        try:
            return work.get_work_board(_today_iso())
        except Exception as exc:
            return {"ok": False, "error": str(exc), "today": [], "counts": {}}
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
    if key == "analytics":
        return _safe_call("insights", "get_analytics", 7)
    if key == "cluny":
        return _cluny_glance()
    if key == "unplaced":
        return _safe_call("home_glances", "unplaced_glance")
    if key == "dues":
        return _safe_call("home_glances", "dues_this_week")
    return None


NETWORK_GLANCES = frozenset({"weather"})
NETWORK_GLANCE_TIMEOUT_SEC = 3.0
# Not a widget kind. Rides in the glance pool so the check-in does not wait.
CHECKIN_TASK = "__checkin"


def _run_together(tasks: Dict[str, Any], timeout: float) -> Dict[str, Any]:
    """Run named zero-argument calls at once; one slow call cannot hold the rest."""
    out: Dict[str, Any] = {}
    if not tasks:
        return out
    pool = ThreadPoolExecutor(max_workers=min(8, len(tasks)))
    try:
        futs = {name: pool.submit(fn) for name, fn in tasks.items()}
        for name, fut in futs.items():
            try:
                out[name] = fut.result(timeout=timeout)
            except Exception as exc:
                out[name] = {"ok": False, "error": str(exc)}
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
    return out


def _fetch_glances(kinds: List[str], extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Fetch tiles in parallel. Weather cannot hold up Today / To Do."""
    local: Dict[str, Any] = {
        kind: (lambda k=kind: fetch_glance(k)) for kind in kinds if kind not in NETWORK_GLANCES
    }
    remote: Dict[str, Any] = {
        kind: (lambda k=kind: fetch_glance(k)) for kind in kinds if kind in NETWORK_GLANCES
    }
    # Anything else Home needs on open rides along with the tiles rather than
    # waiting for them to finish first.
    local.update(extra or {})
    out = _run_together(local, 8.0)
    out.update(_run_together(remote, NETWORK_GLANCE_TIMEOUT_SEC))
    return out


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


def _nudge_rate_voice_later() -> None:
    """Rate-goal voice reads every goal across three windows. Nothing on the
    board needs it this round-trip, so it runs after Home already has its data
    and the nudge lands on the next refresh."""
    global _rate_voice_thread

    def _run() -> None:
        _safe_call("cluny_voice", "refresh_rate_voice_safe")

    with _rate_voice_lock:
        # Home refreshes on every data change; one pass at a time is plenty.
        if _rate_voice_thread is not None and _rate_voice_thread.is_alive():
            return
        _rate_voice_thread = threading.Thread(target=_run, daemon=True, name="cluny-rate-voice")
        _rate_voice_thread.start()


def wait_for_boot_background(timeout: float = 5.0) -> None:
    """Join whatever the last boot kicked off. For shutdown and for tests."""
    with _rate_voice_lock:
        thread = _rate_voice_thread
    if thread is not None:
        thread.join(timeout=timeout)


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
    _safe_call("calclock", "rollover_missed_bars")
    first = _first_page(layout)
    extra: Dict[str, Any] = {}
    if first and page.get("id") == first.get("id"):
        extra[CHECKIN_TASK] = lambda: _safe_call("daily_checklist", "get_home_checkin")
    glances = _fetch_glances(kinds, extra)
    checkin = glances.pop(CHECKIN_TASK, None)
    _ensure_cluny_supervisor()
    _nudge_rate_voice_later()
    return {
        "layout": layout,
        "glances": glances,
        "checkin": checkin,
        "page_id": page.get("id") or "",
    }
