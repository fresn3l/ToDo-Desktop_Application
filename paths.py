"""Resolve bundled resource paths and the on-disk data directory."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def resource_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def resource_path(*parts: str) -> Path:
    return resource_root().joinpath(*parts)


def data_directory() -> Path:
    """Application Support folder (legacy name ToDo). Honors KOSISTENZ_DATA_DIR."""
    override = os.environ.get("KOSISTENZ_DATA_DIR")
    if override:
        path = Path(override).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        return path
    if sys.platform == "win32":
        base = Path.home() / "AppData" / "Local" / "ToDo"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "ToDo"
    else:
        base = Path.home() / ".local" / "share" / "ToDo"
    base.mkdir(parents=True, exist_ok=True)
    return base
