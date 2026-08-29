"""
Local macOS reminder via launchd + osascript (free, offline).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

import eel

import plistlib

from paths import data_directory, resource_root

PLIST_LABEL = "com.kosistenz.reminder"
DEFAULT_CONFIG = {"enabled": False, "hour": 20, "minute": 0}


def _config_path() -> Path:
    return data_directory() / "reminder_config.json"


def _repo_root() -> Path:
    return resource_root()


def _load_config() -> Dict[str, Any]:
    path = _config_path()
    if not path.exists():
        return dict(DEFAULT_CONFIG)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return {**DEFAULT_CONFIG, **data}
    except (json.JSONDecodeError, OSError):
        pass
    return dict(DEFAULT_CONFIG)


def _save_config(cfg: Dict[str, Any]) -> None:
    path = _config_path()
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    path.parent.mkdir(parents=True, exist_ok=True)
    os.replace(tmp, path)


def _launchagents_dir() -> Path:
    return Path.home() / "Library" / "LaunchAgents"


def _plist_path() -> Path:
    return _launchagents_dir() / f"{PLIST_LABEL}.plist"


@eel.expose
def get_reminder_config() -> Dict[str, Any]:
    cfg = _load_config()
    cfg["installed"] = _plist_path().exists()
    cfg["plist_path"] = str(_plist_path())
    return cfg


@eel.expose
def set_reminder_config(enabled: bool, hour: int, minute: int) -> Dict[str, Any]:
    hour = max(0, min(int(hour), 23))
    minute = max(0, min(int(minute), 59))
    cfg = {"enabled": bool(enabled), "hour": hour, "minute": minute}
    _save_config(cfg)
    if sys.platform == "darwin" and cfg["enabled"]:
        return install_local_reminder()
    if sys.platform == "darwin":
        uninstall_local_reminder()
    return get_reminder_config()


def install_local_reminder() -> Dict[str, Any]:
    if sys.platform != "darwin":
        return {"ok": False, "error": "Local reminders are macOS only."}
    cfg = _load_config()
    script = _repo_root() / "macos" / "kosistenz-reminder.sh"
    if not script.exists():
        return {"ok": False, "error": "Missing macos/kosistenz-reminder.sh"}
    _launchagents_dir().mkdir(parents=True, exist_ok=True)
    payload = {
        "Label": PLIST_LABEL,
        "ProgramArguments": ["/bin/bash", str(script)],
        "StartCalendarInterval": {
            "Hour": int(cfg["hour"]),
            "Minute": int(cfg["minute"]),
        },
        "RunAtLoad": False,
    }
    with _plist_path().open("wb") as handle:
        plistlib.dump(payload, handle, sort_keys=False)
    subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}", str(_plist_path())], capture_output=True)
    result = subprocess.run(
        ["launchctl", "bootstrap", f"gui/{os.getuid()}", str(_plist_path())],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return {"ok": False, "error": result.stderr or "launchctl bootstrap failed"}
    return {"ok": True, **get_reminder_config()}


@eel.expose
def uninstall_local_reminder() -> Dict[str, Any]:
    if sys.platform != "darwin":
        return {"ok": True}
    path = _plist_path()
    if path.exists():
        subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}", str(path)], capture_output=True)
        path.unlink(missing_ok=True)
    cfg = _load_config()
    cfg["enabled"] = False
    _save_config(cfg)
    return {"ok": True, **get_reminder_config()}


@eel.expose
def test_local_reminder() -> Dict[str, Any]:
    if sys.platform != "darwin":
        return {"ok": False, "error": "macOS only"}
    script = _repo_root() / "macos" / "kosistenz-reminder.sh"
    result = subprocess.run(["/bin/bash", str(script)], capture_output=True, text=True)
    return {"ok": result.returncode == 0, "stderr": result.stderr}
