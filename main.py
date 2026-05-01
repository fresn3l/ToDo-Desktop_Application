"""
Journal desktop app — Python (Eel) + web UI.

Set CLUNY_SQLITE_PATH or CLUNY_INGEST_URL (see cluny_sync.py) to sync entries to Cluny.
"""

import eel

import journal

eel.init("web")

if __name__ == "__main__":
    eel.start("index.html", size=(900, 700), port=0, mode="chrome-app")
