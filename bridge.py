"""
Local UI server (Eel) — no browser. The native window loads this over localhost.
The menu bar, widget, and Services use a separate 127.0.0.1 API on port 18741.
"""

from __future__ import annotations

import os

import eel

import appearance  # noqa: F401
import calclock  # noqa: F401
import home_layout  # noqa: F401
import export_data  # noqa: F401
import goals  # noqa: F401
import icloud_sync  # noqa: F401
import health_import  # noqa: F401
import insights  # noqa: F401
import journal  # noqa: F401
import local_api
import reminders  # noqa: F401
import schedule  # noqa: F401
import timeline  # noqa: F401
import work  # noqa: F401
import workouts  # noqa: F401


def run_bridge(port: int, web_dir: str) -> None:
    os.environ["KOSISTENZ_UI_PORT"] = str(int(port))
    api_port = local_api.start_background_server()
    print(f"KOSISTENZ_API_PORT={api_port}", flush=True)
    eel.init(web_dir)
    eel.start(
        "index.html",
        host="127.0.0.1",
        port=port,
        mode=None,
        block=True,
        close_callback=lambda *_args: None,
    )
