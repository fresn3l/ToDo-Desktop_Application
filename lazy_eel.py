"""Register Eel stubs so the UI can call later features before those modules load.

Launch only imports Home. Calendar, Journal, Brain, and the rest are imported
on first use. Eel builds JS proxies from whatever is exposed at page load, so
each lazy function needs a name here even before the real module is imported.
"""

from __future__ import annotations

import importlib
import importlib.util
import re
import sys
import threading
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import eel

ROOT = Path(__file__).resolve().parent
_EXPOSE_RE = re.compile(
    r"@eel\.expose(?:\([^)]*\))?\s*\ndef ([A-Za-z_][A-Za-z0-9_]*)",
    re.MULTILINE,
)
_lock = threading.Lock()
_loaded: Dict[str, bool] = {}

LAZY_MODULES: Tuple[str, ...] = (
    "brain",
    "library",
    "cluny_brain",
    "cluny_ask",
    "cluny_snapshot",
    "cluny_sync",
    "calclock",
    "schedule",
    "icloud_sync",
    "health_import",
    "export_data",
    "glance",
    "heatmap",
    "reading",
    "tap_counters",
    "goals",
    "day_brief",
    "timeline",
    "reminders",
    "insights",
    "home_glances",
    "weather",
    "word_of_the_day",
    "journal",
    "daily_checklist",
)

FEATURE_MODULES: Dict[str, Tuple[str, ...]] = {
    "calendar": ("calclock", "schedule"),
    "journal": ("journal",),
    "brain": ("brain", "cluny_brain"),
    "library": ("library",),
    "settings": ("export_data", "health_import", "icloud_sync", "cluny_sync", "cluny_brain"),
    "icloud": ("icloud_sync",),
    "today": ("insights", "day_brief", "timeline", "workouts", "calclock", "home_glances"),
    "todo": ("work", "goals"),
    "workout": ("workouts",),
    "goals": ("goals",),
    "analytics": ("insights", "timeline"),
    "timeline": ("timeline",),
    "weather": ("weather",),
    "glance": ("glance",),
    "heatmap": ("heatmap",),
    "day_brief": ("day_brief",),
    "counters": ("tap_counters",),
    "reading": ("reading",),
    "word": ("word_of_the_day",),
    "cluny": ("cluny_ask", "cluny_brain", "cluny_sync"),
    "allwork": ("work",),
    "checklist": ("daily_checklist", "day_brief"),
}


# Used when .py source is not on disk (frozen .app). Keep in sync with @eel.expose.
EXPOSE_FALLBACK: Dict[str, Tuple[str, ...]] = {
    "brain": (
        "brain_ensure_serve",
        "brain_health",
        "brain_stats",
        "brain_library",
        "brain_library_filters",
        "brain_delete_doc",
        "brain_ingest_file_b64",
        "brain_new_session",
        "brain_list_sessions",
        "brain_load_session",
        "brain_get_session_id",
        "brain_chat",
        "brain_chat_stream",
        "brain_propose",
        "brain_config_get",
        "brain_config_save",
        "brain_config_reset",
        "brain_user_config_get",
        "brain_user_config_save",
        "brain_export_config",
        "brain_import_config",
        "brain_sync_analytics",
        "brain_accept_proposal",
        "brain_context_preview",
    ),
    "library": (
        "library_list",
        "library_filters",
        "library_get",
        "library_update",
        "library_delete_doc",
        "library_search",
        "library_create_collection",
        "library_delete_collection",
        "library_upload_b64",
        "library_stats",
        "library_open_data_dir",
        "library_reveal_path",
    ),
    "cluny_brain": ("get_cluny_brain_supervisor", "restart_cluny_brain"),
    "cluny_ask": (
        "get_cluny_health",
        "probe_cluny_connection",
        "get_cluny_inbox",
        "ask_cluny",
        "suggest_cluny_work",
        "accept_cluny_proposal",
        "dismiss_cluny_proposal",
    ),
    "cluny_snapshot": ("get_cluny_life_snapshot", "get_cluny_snapshot_status"),
    "cluny_sync": (
        "get_cluny_settings",
        "save_cluny_settings",
        "backfill_cluny_journals",
        "backfill_cluny_life",
    ),
    "calclock": (
        "set_calendar_feed_enabled",
        "get_calendar_settings",
        "save_calendar_settings",
        "import_ics_url",
        "import_pasted_calendar",
        "ingest_calendar_events",
        "list_calendar_feeds",
        "unsubscribe_calendar_feed",
        "delete_undated_imported_assignments",
        "create_calendar_event",
        "delete_calendar_event",
        "update_calendar_event",
        "get_week",
        "get_month",
        "get_year",
        "get_day_agenda",
        "set_block_status",
        "delete_schedule_block",
        "update_schedule_block",
        "park_schedule_block",
        "schedule_work_at",
        "place_work_after_lecture",
    ),
    "schedule": ("place_work_item", "add_todo_to_calendar", "fill_week"),
    "icloud_sync": (
        "get_icloud_sync_status",
        "save_icloud_sync_settings",
        "push_icloud_pack",
        "pull_icloud_pack",
        "maybe_pull_icloud_on_open",
    ),
    "health_import": ("import_health_export", "get_health_snapshot"),
    "export_data": (
        "export_journal_json",
        "export_journal_csv",
        "export_work_json",
        "export_work_csv",
        "export_workouts_json",
        "export_workouts_csv",
        "get_exports_directory",
        "get_app_data_directory",
        "export_week_markdown",
    ),
    "glance": (
        "get_daily_focus",
        "set_daily_focus",
        "keep_daily_focus",
        "get_countdowns",
        "add_home_countdown",
        "remove_home_countdown",
        "get_habits",
        "add_home_habit",
        "remove_home_habit",
        "toggle_home_habit",
    ),
    "heatmap": ("get_heatmap_settings", "save_heatmap_settings", "get_heatmap"),
    "reading": ("get_reading", "set_reading_book", "add_reading_pages", "save_reading_journal"),
    "tap_counters": (
        "get_tap_counters",
        "add_tap_counter",
        "update_tap_counter",
        "remove_tap_counter",
        "tap_counter",
    ),
    "goals": (
        "list_goals",
        "get_goals_board",
        "create_goal",
        "update_goal",
        "delete_goal",
        "attach_work_item_goal",
    ),
    "day_brief": (
        "get_day_brief",
        "set_day_brief_override",
        "save_morning_brief",
        "save_evening_review",
        "roll_brief_item_to_tomorrow",
    ),
    "timeline": ("get_timeline_day", "list_timeline_dates", "get_week_overview"),
    "reminders": (
        "get_reminder_config",
        "set_reminder_config",
        "uninstall_local_reminder",
        "test_local_reminder",
    ),
    "insights": (
        "save_weekly_pattern_note",
        "get_today_status",
        "get_today_home",
        "get_analytics",
        "get_time_allocation",
    ),
    "home_glances": (
        "get_now_next_glance",
        "get_unplaced_glance",
        "get_dues_week_glance",
        "get_free_today_glance",
        "glance_skip_block",
        "glance_finish_work",
        "glance_park_work",
        "glance_plus15",
        "glance_do_today",
        "glance_place_unplaced",
        "glance_log_expected_workout",
    ),
    "weather": (
        "get_weather_settings",
        "search_weather_places",
        "set_weather_place",
        "set_weather_units",
        "get_weather_forecast",
    ),
    "word_of_the_day": ("get_word_of_the_day",),
    "journal": (
        "get_journal_tag_presets",
        "save_journal_entry",
        "get_recent_entries",
        "get_all_entries",
    ),
    "daily_checklist": (
        "get_custom_checklist_items",
        "add_custom_checklist_item",
        "remove_custom_checklist_item",
        "get_daily_checklist",
        "list_bundled_checklists",
        "get_active_checklist_stem",
        "set_active_checklist_stem",
        "get_daily_checklist_db_path_exposed",
        "submit_daily_checklist_response",
        "list_daily_checklist_submissions",
        "get_home_checkin",
    ),
}


def _module_source(module: str) -> str:
    rel = f"{module.replace('.', '/')}.py"
    candidates = [ROOT / rel]
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / rel)
    try:
        spec = importlib.util.find_spec(module)
    except (ImportError, ValueError, ModuleNotFoundError):
        spec = None
    origin = getattr(spec, "origin", None) if spec else None
    if origin:
        candidates.append(Path(origin))
    for path in candidates:
        if path.is_file() and path.suffix == ".py":
            try:
                return path.read_text(encoding="utf-8")
            except OSError:
                continue
    return ""


def _exposed_names(module: str) -> List[str]:
    source = _module_source(module)
    names = _EXPOSE_RE.findall(source) if source else []
    if names:
        return names
    return list(EXPOSE_FALLBACK.get(module, ()))


def load_module(name: str) -> object:
    with _lock:
        mod = importlib.import_module(name)
        _loaded[name] = True
        return mod


def _stub(module: str, func_name: str):
    def wrapper(*args, **kwargs):
        loaded = load_module(module)
        fn = getattr(loaded, func_name)
        return fn(*args, **kwargs)

    wrapper.__name__ = func_name
    wrapper.__qualname__ = func_name
    wrapper.__doc__ = f"Lazy stub for {module}.{func_name}"
    return wrapper


def register_lazy_exposes(modules: Iterable[str] = LAZY_MODULES) -> List[str]:
    """Expose one stub per @eel.expose in modules that are not loaded yet."""
    registered: List[str] = []
    exposed = getattr(eel, "_exposed_functions", {})
    for module in modules:
        for name in _exposed_names(module):
            if name in exposed:
                continue
            eel.expose(_stub(module, name))
            registered.append(name)
    return registered


@eel.expose
def boot_feature(name: str) -> Dict[str, object]:
    """Import the Python modules for one screen or widget overlay."""
    key = str(name or "").strip().lower()
    mods = FEATURE_MODULES.get(key) or ()
    loaded = []
    for module in mods:
        load_module(module)
        loaded.append(module)
    return {"ok": True, "feature": key, "loaded": loaded}


def loaded_modules() -> List[str]:
    with _lock:
        return sorted(_loaded)
