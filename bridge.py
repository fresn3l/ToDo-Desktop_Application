"""
Local UI server (Eel) — no browser. The native window loads this over localhost.
The menu bar, widget, and Services use a separate 127.0.0.1 API on port 18741.

Launch imports Home only. Calendar, Journal, Brain, and the rest register as
Eel stubs and load on first use.
"""

from __future__ import annotations

import os

import eel

import appearance  # noqa: F401
import home_layout  # noqa: F401
import home_boot  # noqa: F401
import work  # noqa: F401
import local_api
import lazy_eel

lazy_eel.register_lazy_exposes()


def run_bridge(port: int, web_dir: str) -> None:
    os.environ["KOSISTENZ_UI_PORT"] = str(int(port))
    api_port = local_api.start_background_server()
    print(f"KOSISTENZ_API_PORT={api_port}", flush=True)

    def _on_close(page: str, sockets: list) -> None:  # noqa: ARG001
        try:
            cluny_brain = lazy_eel.load_module("cluny_brain")
            cluny_brain.stop_supervisor()
        except Exception:
            pass

    eel.init(web_dir)
    try:
        eel.start(
            "index.html",
            host="127.0.0.1",
            port=port,
            mode=None,
            block=True,
            close_callback=_on_close,
        )
    finally:
        try:
            cluny_brain = lazy_eel.load_module("cluny_brain")
            cluny_brain.stop_supervisor()
        except Exception:
            pass
