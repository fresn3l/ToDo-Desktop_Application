"""One Home round-trip: layout, glance payloads, and the check-in slot."""

from __future__ import annotations

import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Set

import eel

import home_layout
import lazy_eel
import work
from paths import data_directory

CACHE_NAME = "home_boot_cache.json"
WAVE1_KINDS = frozenset({"today_calendar", "cluny"})
WORK_PACK_SLICES = frozenset({"today", "unplaced", "due", "backlog"})
WORK_PACK_TASK = "__work_pack"

_supervisor_lock = threading.Lock()
_supervisor_started = False
_rate_voice_lock = threading.Lock()
_rate_voice_thread: Optional[threading.Thread] = None
_rollover_lock = threading.Lock()
_rollover_thread: Optional[threading.Thread] = None
_cache_lock = threading.Lock()


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


def _work_slice_of(key: str) -> Optional[str]:
    kind, settings = home_layout.split_key(str(key or "").strip())
    if kind != "work":
        return None
    return settings.get("slice") or "today"


def _is_wave1_key(key: str) -> bool:
    kind, settings = home_layout.split_key(str(key or "").strip())
    if kind in WAVE1_KINDS:
        return True
    if kind == "work" and (settings.get("slice") or "today") == "today":
        return True
    return False


def _slim_today_board(board: Dict[str, Any]) -> Dict[str, Any]:
    """The Today tile paints titles, status, clock time, leftover minutes."""
    raw_rows = [row for row in (board.get("today") or []) if isinstance(row, dict)]
    starts: Dict[str, str] = {}
    leftovers: Dict[str, int] = {}
    ids = [str(row.get("id") or "") for row in raw_rows if row.get("id")]
    if ids:
        try:
            import calclock

            starts = calclock.first_open_bar_starts(ids)
            leftovers = calclock.leftover_minutes_for(raw_rows)
        except Exception:
            starts = {}
            leftovers = {}
    today_items: List[Dict[str, Any]] = []
    for row in raw_rows:
        packed: Dict[str, Any] = {
            "id": row.get("id"),
            "title": row.get("title") or "",
            "status": row.get("status") or "",
        }
        start = starts.get(str(row.get("id") or ""))
        if start:
            packed["start_at"] = start
        leftover = leftovers.get(str(row.get("id") or ""), 0)
        if leftover:
            packed["remaining_minutes"] = leftover
        estimate = row.get("estimate_minutes")
        if estimate:
            packed["estimate_minutes"] = int(estimate)
        today_items.append(packed)
    return {
        "local_date": board.get("local_date"),
        "today": today_items,
        "counts": board.get("counts") or {},
    }


def _build_work_pack(slices: Set[str]) -> Dict[str, Any]:
    """Today, Unplaced, Due, and All work share one SQLite walk per boot.

    Parallel readers on the same file fight the lock. One thread builds the
    pack; each tile still gets its own answer.
    """
    wanted = {name for name in slices if name in WORK_PACK_SLICES}
    out: Dict[str, Any] = {}
    board: Optional[Dict[str, Any]] = None
    if "today" in wanted or "backlog" in wanted:
        try:
            board = work.get_work_board(_today_iso())
        except Exception as exc:
            board = {"ok": False, "error": str(exc), "today": [], "counts": {}, "backlog": []}
    if "today" in wanted:
        out["today"] = _slim_today_board(board or {})
    if "backlog" in wanted:
        if isinstance(board, dict) and "backlog" in board:
            out["backlog"] = board.get("backlog") or []
        else:
            try:
                out["backlog"] = work.list_backlog()
            except Exception as exc:
                out["backlog"] = {"ok": False, "error": str(exc)}
    if "unplaced" in wanted:
        out["unplaced"] = _safe_call("home_glances", "unplaced_glance")
    if "due" in wanted:
        out["due"] = _safe_call("home_glances", "dues_this_week")
    return out


def _work_glance(slice_name: str) -> Any:
    """Four cuts of one list. Today and Due come off the dated board; All work
    and Unplaced come off the backlog."""
    pack = _build_work_pack({slice_name})
    if slice_name in pack:
        return pack[slice_name]
    return {"ok": False, "error": "unknown work slice", "today": [], "counts": {}}


def fetch_glance(key: str) -> Any:
    kind, settings = home_layout.split_key(str(key or "").strip())
    if kind == "work":
        return _work_glance(settings.get("slice") or "today")
    if kind == "weather":
        return _safe_call("weather", "get_weather_forecast", False)
    if kind == "word":
        return _safe_call("word_of_the_day", "get_word_of_the_day")
    if kind == "today_calendar":
        return _today_calendar_glance()
    if kind == "countdown":
        return _safe_call("glance", "get_countdowns")
    if kind == "habits":
        return _safe_call("glance", "get_habits")
    if kind == "reading":
        return _safe_call("reading", "get_reading")
    if kind == "counters":
        return _safe_call("tap_counters", "get_tap_counters")
    if kind == "workout":
        return _safe_call("insights", "get_today_status")
    if kind == "goals":
        return _safe_call("goals", "list_goals")
    if kind == "day_brief":
        return _safe_call("day_brief", "get_day_brief")
    if kind == "analytics":
        return _safe_call("insights", "get_analytics", 7)
    if kind == "cluny":
        return _cluny_glance()
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


def _fetch_glances(keys: List[str], extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Fetch tiles in parallel. Weather cannot hold up Today / Work."""
    pack_keys: Dict[str, List[str]] = {}
    rest: List[str] = []
    for key in keys:
        slice_name = _work_slice_of(key)
        if slice_name in WORK_PACK_SLICES:
            pack_keys.setdefault(slice_name, []).append(key)
        else:
            rest.append(key)
    local: Dict[str, Any] = {
        key: (lambda k=key: fetch_glance(k)) for key in rest if key not in NETWORK_GLANCES
    }
    remote: Dict[str, Any] = {
        key: (lambda k=key: fetch_glance(k)) for key in rest if key in NETWORK_GLANCES
    }
    # Anything else Home needs on open rides along with the tiles rather than
    # waiting for them to finish first.
    local.update(extra or {})
    if pack_keys:
        wanted = set(pack_keys)
        local[WORK_PACK_TASK] = lambda: _build_work_pack(wanted)
    out = _run_together(local, 8.0)
    out.update(_run_together(remote, NETWORK_GLANCE_TIMEOUT_SEC))
    packed = out.pop(WORK_PACK_TASK, None)
    if isinstance(packed, dict):
        pack_failed = packed.get("ok") is False and not any(name in packed for name in WORK_PACK_SLICES)
        for slice_name, slice_keys in pack_keys.items():
            payload = packed if pack_failed else packed.get(slice_name)
            for key in slice_keys:
                out[key] = payload
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


def _rollover_later() -> None:
    """Missed-bar marks are a write. First launch of the day used to do that
    before seven readers asked for the same file. Kick it; do not wait."""
    global _rollover_thread

    def _run() -> None:
        _safe_call("calclock", "rollover_missed_bars")
        _safe_call("calclock", "maybe_purge_stale_imports")

    with _rollover_lock:
        if _rollover_thread is not None and _rollover_thread.is_alive():
            return
        _rollover_thread = threading.Thread(target=_run, daemon=True, name="cal-rollover")
        _rollover_thread.start()


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
        voice = _rate_voice_thread
    with _rollover_lock:
        rollover = _rollover_thread
    for thread in (voice, rollover):
        if thread is not None:
            thread.join(timeout=timeout)


def _cache_path():
    return data_directory() / CACHE_NAME


def _read_boot_cache() -> Optional[Dict[str, Any]]:
    path = _cache_path()
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
    except (OSError, ValueError, TypeError):
        return None
    return raw if isinstance(raw, dict) else None


def _write_boot_cache(payload: Dict[str, Any]) -> None:
    path = _cache_path()
    tmp = str(path) + ".tmp"
    packed = {
        "layout": payload.get("layout"),
        "glances": payload.get("glances") or {},
        "checkin": payload.get("checkin"),
        "page_id": payload.get("page_id") or "",
        "saved_at": datetime.now().isoformat(timespec="seconds"),
    }
    try:
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(packed, handle)
        os.replace(tmp, path)
    except (OSError, TypeError, ValueError):
        try:
            os.remove(tmp)
        except OSError:
            pass


def _save_boot_cache(payload: Dict[str, Any], *, merge: bool) -> None:
    with _cache_lock:
        if merge:
            existing = _read_boot_cache() or {}
            glances = dict(existing.get("glances") or {})
            glances.update(payload.get("glances") or {})
            checkin = payload.get("checkin")
            if checkin is None:
                checkin = existing.get("checkin")
            packed = {
                "layout": payload.get("layout") or existing.get("layout"),
                "glances": glances,
                "checkin": checkin,
                "page_id": payload.get("page_id") or existing.get("page_id") or "",
            }
            _write_boot_cache(packed)
            return
        _write_boot_cache(payload)


def _merge_boot_cache_glances(glances: Dict[str, Any]) -> None:
    if not glances:
        return
    with _cache_lock:
        existing = _read_boot_cache() or {}
        merged = dict(existing.get("glances") or {})
        merged.update(glances)
        existing["glances"] = merged
        _write_boot_cache(existing)


def _normalize_wave(wave: Any) -> str:
    text = str(wave or "all").strip().lower()
    if text in ("1", "wave1"):
        return "1"
    if text in ("2", "wave2"):
        return "2"
    return "all"


def _page_widget_keys(page: Dict[str, Any]) -> List[str]:
    keys: List[str] = []
    seen = set()
    for widget in page.get("widgets") or []:
        kind = str(widget.get("kind") or "").strip()
        if not kind:
            continue
        key = home_layout.widget_key(kind, widget.get("settings"))
        if key in seen:
            continue
        seen.add(key)
        keys.append(key)
    return keys


@eel.expose
def peek_home_boot(page_id: str = "") -> Dict[str, Any]:
    """Last successful boot from disk. Cheap enough to paint before live data."""
    packed = _read_boot_cache()
    if not packed:
        return {
            "ok": False,
            "stale": True,
            "layout": None,
            "glances": {},
            "checkin": None,
            "page_id": "",
        }
    wanted = str(page_id or "").strip()
    cached_page = str(packed.get("page_id") or "")
    glances = packed.get("glances") or {}
    checkin = packed.get("checkin")
    if wanted and cached_page and wanted != cached_page:
        glances = {}
        checkin = None
    return {
        "ok": True,
        "stale": True,
        "layout": packed.get("layout"),
        "glances": glances if isinstance(glances, dict) else {},
        "checkin": checkin,
        "page_id": cached_page,
    }


@eel.expose
def get_home_glances(keys: Optional[List[str]] = None) -> Dict[str, Any]:
    """Refresh only the tiles a change actually touched."""
    wanted: List[str] = []
    seen = set()
    for raw in keys or []:
        key = str(raw or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        wanted.append(key)
    glances = _fetch_glances(wanted)
    _merge_boot_cache_glances(glances)
    return {"ok": True, "glances": glances}


@eel.expose
def get_home_boot(page_id: str = "", wave: str = "all") -> Dict[str, Any]:
    """Layout plus glances on the active page.

    wave "all" is the original one-payload path. "1" is Today / Work / Cluny
    and the check-in; "2" is everything else. Tests and older clients keep
    calling this with no wave and still get the full board.
    """
    wanted = str(page_id or "").strip()
    if wanted:
        layout = home_layout.set_active_home_page(wanted)
    else:
        layout = home_layout.get_home_layout()
    page = _active_page(layout) or {}
    # Keyed by widget key, not by kind: two Work tiles on one page ask two
    # different questions and each needs its own answer.
    keys = _page_widget_keys(page)
    wave_name = _normalize_wave(wave)
    if wave_name == "1":
        keys = [key for key in keys if _is_wave1_key(key)]
    elif wave_name == "2":
        keys = [key for key in keys if not _is_wave1_key(key)]
    if wave_name != "2":
        _rollover_later()
    first = _first_page(layout)
    extra: Dict[str, Any] = {}
    if wave_name != "2" and first and page.get("id") == first.get("id"):
        extra[CHECKIN_TASK] = lambda: _safe_call("daily_checklist", "get_home_checkin")
    glances = _fetch_glances(keys, extra)
    checkin = glances.pop(CHECKIN_TASK, None)
    if wave_name != "2":
        _ensure_cluny_supervisor()
        _nudge_rate_voice_later()
    payload = {
        "layout": layout,
        "glances": glances,
        "checkin": checkin,
        "page_id": page.get("id") or "",
        "wave": wave_name,
        "stale": False,
    }
    _save_boot_cache(payload, merge=wave_name != "all")
    return payload
