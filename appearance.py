"""
Appearance settings — theme, typography, layout, and writing preferences.

Stored as JSON next to other Kosistenz data under Application Support.
"""

from __future__ import annotations

import copy
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List

import eel

COLOR_SLOTS = (
    "pageBg",
    "widgetBg",
    "widgetBorder",
    "titles",
    "accent",
    "done",
    "openNext",
    "sidebar",
)

INK_LIGHT = "#f7fafc"
INK_DARK = "#1a1814"

# Built-in palettes. CSS theme blocks stay in sync; tests check the hexes.
THEME_PALETTES: Dict[str, Dict[str, str]] = {
    "ocean": {
        "pageBg": "#121c26",
        "widgetBg": "#1d2c3b",
        "widgetBorder": "#2c3d4e",
        "titles": "#eef3f7",
        "accent": "#4f8fcf",
        "done": "#5ebb8e",
        "openNext": "#d4a054",
        "sidebar": "#0e1620",
    },
    "midnight": {
        "pageBg": "#111113",
        "widgetBg": "#1f1f23",
        "widgetBorder": "#2a2a30",
        "titles": "#f4f4f5",
        "accent": "#4f8fcf",
        "done": "#5ebb8e",
        "openNext": "#d4a054",
        "sidebar": "#0c0c0e",
    },
    "slate": {
        "pageBg": "#171e2b",
        "widgetBg": "#243044",
        "widgetBorder": "#2c3848",
        "titles": "#eef2f6",
        "accent": "#4f8fcf",
        "done": "#5ebb8e",
        "openNext": "#d4a054",
        "sidebar": "#121824",
    },
    "paper": {
        "pageBg": "#f7f3eb",
        "widgetBg": "#f1ebe0",
        "widgetBorder": "#d8d0c2",
        "titles": "#1b1814",
        "accent": "#4f8fcf",
        "done": "#2f7d57",
        "openNext": "#b5791f",
        "sidebar": "#f3eee4",
    },
    "forest": {
        "pageBg": "#141e1a",
        "widgetBg": "#20312b",
        "widgetBorder": "#2a3c36",
        "titles": "#eef4f0",
        "accent": "#4f8fcf",
        "done": "#6bc49a",
        "openNext": "#d4a054",
        "sidebar": "#101816",
    },
    "dusk": {
        "pageBg": "#1b1824",
        "widgetBg": "#2b2738",
        "widgetBorder": "#3a3548",
        "titles": "#f2eef6",
        "accent": "#4f8fcf",
        "done": "#5ebb8e",
        "openNext": "#d4a054",
        "sidebar": "#16131e",
    },
}

ACCENT_HEX = {
    "sky": "#4f8fcf",
    "teal": "#2a9a8c",
    "amber": "#c8892c",
    "rose": "#c45c6a",
    "violet": "#7a6cb5",
    "lime": "#6a9a6e",
}

DEFAULTS: Dict[str, Any] = {
    "theme": "ocean",
    "accent": "sky",
    "customAccent": "#4F8FCF",
    "font": "system",
    "density": "comfortable",
    "radius": "soft",
    "width": "standard",
    "sidebar": "expanded",
    "todayLayout": "split",
    "todayOrder": "todo,workout,journal",
    "todayTodo": True,
    "todayWorkout": True,
    "todayJournal": True,
    "journalFontSize": 17,
    "timerMinutes": 10,
    "autoFocus": False,
    "reducedMotion": False,
    "highContrast": False,
    "colorOverrides": {},
    "widgetBorderWidth": 1,
    "inkAuto": True,
    "ink": "",
    "activePresetId": "",
    "userPresets": [],
}

ALLOWED = {
    "theme": {"ocean", "midnight", "slate", "paper", "forest", "dusk"},
    "accent": {"sky", "teal", "amber", "rose", "violet", "lime", "custom"},
    "font": {"sans", "serif", "mono", "system"},
    "density": {"comfortable", "compact"},
    "radius": {"sharp", "soft", "round"},
    "width": {"narrow", "standard", "wide"},
    "sidebar": {"expanded", "compact"},
    "todayLayout": {"split", "stack", "columns"},
}

_TODAY_MODULES = ("todo", "workout", "journal")
_HEX_RE = re.compile(r"^#?[0-9a-fA-F]{3}([0-9a-fA-F]{3})?$")
_PRESET_ID_RE = re.compile(r"^up-[a-zA-Z0-9_-]{2,36}$")
_MAX_PRESETS = 32


def _as_today_order(raw: Any) -> str:
    parts: list[str] = []
    if isinstance(raw, str):
        parts = [p.strip() for p in raw.split(",")]
    elif isinstance(raw, (list, tuple)):
        parts = [str(p).strip() for p in raw]
    seen: list[str] = []
    for part in parts:
        if part in _TODAY_MODULES and part not in seen:
            seen.append(part)
    for part in _TODAY_MODULES:
        if part not in seen:
            seen.append(part)
    return ",".join(seen)


def _app_data_dir() -> Path:
    from paths import data_directory

    return data_directory()


def _settings_path() -> Path:
    return _app_data_dir() / "appearance.json"


def _as_bool(raw: Any, default: bool) -> bool:
    if raw is None:
        return default
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, (int, float)):
        return bool(raw)
    if isinstance(raw, str):
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    return default


def _clamp_int(value: Any, lo: int, hi: int, fallback: int) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return fallback
    return max(lo, min(hi, n))


def _as_hex(raw: Any, fallback: str = "") -> str:
    if not isinstance(raw, str):
        return fallback
    text = raw.strip()
    if not text:
        return fallback
    if not text.startswith("#"):
        text = "#" + text
    if not _HEX_RE.match(text):
        return fallback
    body = text[1:]
    if len(body) == 3:
        body = "".join(ch * 2 for ch in body)
    return "#" + body.lower()


def _srgb_to_linear(channel: float) -> float:
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_color: str) -> float:
    hx = _as_hex(hex_color, "")
    if not hx:
        return 0.0
    r = int(hx[1:3], 16) / 255.0
    g = int(hx[3:5], 16) / 255.0
    b = int(hx[5:7], 16) / 255.0
    return 0.2126 * _srgb_to_linear(r) + 0.7152 * _srgb_to_linear(g) + 0.0722 * _srgb_to_linear(b)


def ink_for_hex(hex_color: str) -> str:
    """Light ink on dark fills, dark ink on light fills."""
    return INK_DARK if relative_luminance(hex_color) > 0.45 else INK_LIGHT


def palette_for(theme: str) -> Dict[str, str]:
    return dict(THEME_PALETTES.get(theme, THEME_PALETTES["ocean"]))


def _sanitize_overrides(raw: Any) -> Dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    out: Dict[str, str] = {}
    for slot in COLOR_SLOTS:
        hx = _as_hex(raw.get(slot), "")
        if hx:
            out[slot] = hx
    return out


def _sanitize_colors(raw: Any, base_theme: str) -> Dict[str, str]:
    out = palette_for(base_theme)
    if isinstance(raw, dict):
        for slot in COLOR_SLOTS:
            hx = _as_hex(raw.get(slot), "")
            if hx:
                out[slot] = hx
    return out


def _sanitize_preset(raw: Any) -> Dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    ident = raw.get("id")
    if not isinstance(ident, str) or not _PRESET_ID_RE.match(ident.strip()):
        return None
    name = raw.get("name")
    if not isinstance(name, str):
        return None
    label = " ".join(name.strip().split())
    if not label or len(label) > 40:
        return None
    base = raw.get("baseTheme")
    if not isinstance(base, str) or base not in ALLOWED["theme"]:
        base = "ocean"
    return {
        "id": ident.strip(),
        "name": label,
        "baseTheme": base,
        "colors": _sanitize_colors(raw.get("colors"), base),
        "widgetBorderWidth": _clamp_int(raw.get("widgetBorderWidth"), 0, 8, 1),
        "inkAuto": _as_bool(raw.get("inkAuto"), True),
        "ink": _as_hex(raw.get("ink"), ""),
    }


def _sanitize_presets(raw: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: List[Dict[str, Any]] = []
    seen = set()
    for item in raw:
        preset = _sanitize_preset(item)
        if not preset or preset["id"] in seen:
            continue
        seen.add(preset["id"])
        out.append(preset)
        if len(out) >= _MAX_PRESETS:
            break
    return out


def resolve_accent_hex(settings: Dict[str, Any]) -> str:
    overrides = settings.get("colorOverrides") or {}
    if isinstance(overrides, dict):
        hx = _as_hex(overrides.get("accent"), "")
        if hx:
            return hx
    if settings.get("accent") == "custom":
        hx = _as_hex(settings.get("customAccent"), "")
        if hx:
            return hx
    preset = ACCENT_HEX.get(str(settings.get("accent") or "sky"))
    if preset:
        return preset
    return palette_for(str(settings.get("theme") or "ocean"))["accent"]


def resolve_colors(settings: Dict[str, Any]) -> Dict[str, str]:
    theme = str(settings.get("theme") or "ocean")
    out = palette_for(theme)
    overrides = settings.get("colorOverrides") if isinstance(settings.get("colorOverrides"), dict) else {}
    for slot in COLOR_SLOTS:
        if slot == "accent":
            continue
        hx = _as_hex(overrides.get(slot), "")
        if hx:
            out[slot] = hx
    out["accent"] = resolve_accent_hex(settings)
    return out


def resolve_ink(settings: Dict[str, Any]) -> str:
    if _as_bool(settings.get("inkAuto"), True):
        return ink_for_hex(resolve_accent_hex(settings))
    hx = _as_hex(settings.get("ink"), "")
    return hx or ink_for_hex(resolve_accent_hex(settings))


def _sanitize(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        return copy.deepcopy(DEFAULTS)
    out = copy.deepcopy(DEFAULTS)
    for key, allowed in ALLOWED.items():
        val = raw.get(key)
        if isinstance(val, str) and val in allowed:
            out[key] = val
    custom = raw.get("customAccent")
    if isinstance(custom, str) and len(custom) <= 16:
        hx = _as_hex(custom.strip(), "")
        out["customAccent"] = hx or DEFAULTS["customAccent"]
    out["journalFontSize"] = _clamp_int(raw.get("journalFontSize"), 14, 22, DEFAULTS["journalFontSize"])
    out["timerMinutes"] = _clamp_int(raw.get("timerMinutes"), 5, 30, DEFAULTS["timerMinutes"])
    out["autoFocus"] = _as_bool(raw.get("autoFocus"), False)
    out["reducedMotion"] = _as_bool(raw.get("reducedMotion"), False)
    out["highContrast"] = _as_bool(raw.get("highContrast"), False)
    out["todayTodo"] = _as_bool(raw.get("todayTodo"), True)
    out["todayWorkout"] = _as_bool(raw.get("todayWorkout"), True)
    out["todayJournal"] = _as_bool(raw.get("todayJournal"), True)
    out["todayOrder"] = _as_today_order(raw.get("todayOrder"))
    out["colorOverrides"] = _sanitize_overrides(raw.get("colorOverrides"))
    out["widgetBorderWidth"] = _clamp_int(raw.get("widgetBorderWidth"), 0, 8, DEFAULTS["widgetBorderWidth"])
    out["inkAuto"] = _as_bool(raw.get("inkAuto"), True)
    out["ink"] = _as_hex(raw.get("ink"), "")
    out["userPresets"] = _sanitize_presets(raw.get("userPresets"))
    preset_id = raw.get("activePresetId")
    if isinstance(preset_id, str) and any(p["id"] == preset_id.strip() for p in out["userPresets"]):
        out["activePresetId"] = preset_id.strip()
    else:
        out["activePresetId"] = ""
    return out


@eel.expose
def get_appearance_settings() -> Dict[str, Any]:
    path = _settings_path()
    if not path.exists():
        return copy.deepcopy(DEFAULTS)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return _sanitize(json.load(f))
    except (OSError, json.JSONDecodeError):
        return copy.deepcopy(DEFAULTS)


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
    current = get_appearance_settings()
    fresh = copy.deepcopy(DEFAULTS)
    fresh["userPresets"] = current.get("userPresets") or []
    return save_appearance_settings(fresh)
