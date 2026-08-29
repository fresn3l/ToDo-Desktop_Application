"""
Appearance settings — theme, typography, layout, and writing preferences.

Stored as JSON next to other Kosistenz data under Application Support.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict

import eel

DEFAULTS: Dict[str, Any] = {
    "theme": "ocean",
    "accent": "sky",
    "customAccent": "#4F8FCF",
    "font": "system",
    "density": "comfortable",
    "radius": "soft",
    "width": "standard",
    "sidebar": "expanded",
    "journalFontSize": 17,
    "timerMinutes": 10,
    "autoFocus": False,
    "reducedMotion": False,
    "highContrast": False,
}

ALLOWED = {
    "theme": {"ocean", "midnight", "slate", "paper", "forest", "dusk"},
    "accent": {"sky", "teal", "amber", "rose", "violet", "lime", "custom"},
    "font": {"sans", "serif", "mono", "system"},
    "density": {"comfortable", "compact"},
    "radius": {"sharp", "soft", "round"},
    "width": {"narrow", "standard", "wide"},
    "sidebar": {"expanded", "compact"},
}


def _app_data_dir() -> Path:
    from paths import data_directory

    return data_directory()


def _settings_path() -> Path:
    return _app_data_dir() / "appearance.json"


def _clamp_int(value: Any, lo: int, hi: int, fallback: int) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return fallback
    return max(lo, min(hi, n))


def _sanitize(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        return dict(DEFAULTS)
    out = dict(DEFAULTS)
    for key, allowed in ALLOWED.items():
        val = raw.get(key)
        if isinstance(val, str) and val in allowed:
            out[key] = val
    custom = raw.get("customAccent")
    if isinstance(custom, str) and len(custom) <= 16:
        out["customAccent"] = custom.strip() or DEFAULTS["customAccent"]
    out["journalFontSize"] = _clamp_int(raw.get("journalFontSize"), 14, 22, DEFAULTS["journalFontSize"])
    out["timerMinutes"] = _clamp_int(raw.get("timerMinutes"), 5, 30, DEFAULTS["timerMinutes"])
    out["autoFocus"] = bool(raw.get("autoFocus", False))
    out["reducedMotion"] = bool(raw.get("reducedMotion", False))
    out["highContrast"] = bool(raw.get("highContrast", False))
    return out


@eel.expose
def get_appearance_settings() -> Dict[str, Any]:
    path = _settings_path()
    if not path.exists():
        return dict(DEFAULTS)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return _sanitize(json.load(f))
    except (OSError, json.JSONDecodeError):
        return dict(DEFAULTS)


@eel.expose
def save_appearance_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    cleaned = _sanitize(settings)
    path = _settings_path()
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, indent=2)
    os.replace(tmp, path)
    return cleaned


@eel.expose
def reset_appearance_settings() -> Dict[str, Any]:
    return save_appearance_settings(dict(DEFAULTS))
