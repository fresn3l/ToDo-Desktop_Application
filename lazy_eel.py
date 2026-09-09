"""Register Eel stubs so the UI can call later features before those modules load.

Launch only imports Home. Calendar, Journal, Brain, and the rest are imported
on first use. Eel builds JS proxies from whatever is exposed at page load, so
each lazy function needs a name here even before the real module is imported.
"""

from __future__ import annotations

import importlib
import re
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
    "settings": ("export_data", "health_import", "icloud_sync"),
    "icloud": ("icloud_sync",),
    "today": ("insights", "day_brief", "timeline", "workouts", "calclock"),
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
    "cluny": ("cluny_ask", "cluny_brain"),
    "allwork": ("work",),
    "checklist": ("daily_checklist", "day_brief"),
}


def _exposed_names(module: str) -> List[str]:
    path = ROOT / f"{module.replace('.', '/')}.py"
    if not path.is_file():
        return []
    return _EXPOSE_RE.findall(path.read_text(encoding="utf-8"))


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
