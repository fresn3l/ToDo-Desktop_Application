"""
Local UI server (Eel) — no browser. The native window loads this over localhost.
"""

from __future__ import annotations

import eel

import appearance  # noqa: F401
import export_data  # noqa: F401
import health_import  # noqa: F401
import insights  # noqa: F401
import journal  # noqa: F401
import reminders  # noqa: F401
import timeline  # noqa: F401
import work  # noqa: F401
import workouts  # noqa: F401


def run_bridge(port: int, web_dir: str) -> None:
    eel.init(web_dir)
    eel.start(
        "index.html",
        host="127.0.0.1",
        port=port,
        mode=None,
        block=True,
        close_callback=lambda *_args: None,
    )
