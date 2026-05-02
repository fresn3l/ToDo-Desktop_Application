"""
Journal + Daily Checklist — Python (Eel) + web UI.

Set CLUNY_SQLITE_PATH or CLUNY_INGEST_URL (see cluny_sync.py) to sync journal entries to Cluny.
Daily checklist responses live in daily_checklist.sqlite (see daily_checklist.py).
"""

import eel

import daily_checklist  # noqa: F401 — registers eel endpoints
import journal

eel.init("web")

if __name__ == "__main__":
    eel.start("index.html", size=(900, 700), port=0, mode="chrome-app")
