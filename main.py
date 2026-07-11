"""
Kosistenz — Python (Eel) + web UI (journal + daily checklist).

Set CLUNY_SQLITE_PATH or CLUNY_INGEST_URL (see cluny_sync.py) to sync journal entries to Cluny.
Daily checklist responses live in daily_checklist.sqlite (see daily_checklist.py).
"""

import eel

import daily_checklist  # noqa: F401 — registers eel endpoints
import journal
import insights  # noqa: F401 — weekly review endpoints
import timeline  # noqa: F401 — unified timeline endpoints
import export_data  # noqa: F401 — CSV/JSON export endpoints
import recovery  # noqa: F401 — missed-day recovery prompts
import reminders  # noqa: F401 — local launchd reminders
import health_import  # noqa: F401 — Apple Health / Screen Time imports

eel.init("web")

if __name__ == "__main__":
    eel.start("index.html", size=(900, 700), port=0, mode="chrome-app")
