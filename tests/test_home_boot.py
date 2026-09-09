"""Home boot payload and launch-time imports."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


class HomeBootTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"KOSISTENZ_DATA_DIR": self.tmp.name})
        self.env.start()

    def tearDown(self) -> None:
        self.env.stop()
        self.tmp.cleanup()

    def test_bridge_import_does_not_load_calendar_or_brain(self) -> None:
        code = r"""
import sys
sys.path.insert(0, %r)
import bridge  # noqa: F401
blocked = [name for name in ("calclock", "brain", "library", "icloud_sync", "schedule") if name in sys.modules]
assert not blocked, blocked
assert "home_boot" in sys.modules
assert "work" in sys.modules
print("ok")
""" % (str(ROOT),)
        out = subprocess.check_output([sys.executable, "-c", code], cwd=str(ROOT), text=True)
        self.assertIn("ok", out)

    def test_get_home_boot_is_one_payload(self) -> None:
        import home_boot
        import work

        work.create_work_item("Write the paper", scheduled_date=work._today().isoformat())
        with mock.patch.object(home_boot, "_ensure_cluny_supervisor"):
            boot = home_boot.get_home_boot()
        self.assertIn("layout", boot)
        self.assertIn("glances", boot)
        self.assertIn("todo", boot["glances"])
        self.assertIn("today_calendar", boot["glances"])
        todo = boot["glances"]["todo"]
        titles = [row.get("title") for row in (todo.get("today") or [])]
        self.assertIn("Write the paper", titles)
        self.assertIsNotNone(boot.get("checkin"))

    def test_week_clock_items_are_slim(self) -> None:
        import calclock

        calclock.create_calendar_event(
            "Office hours",
            "2026-09-08T14:00:00",
            "2026-09-08T15:00:00",
            weekdays=[1],
        )
        week = calclock.get_week("2026-09-07")
        tuesday = next(day for day in week["days"] if day["date"] == "2026-09-08")
        event = tuesday["events"][0]
        self.assertEqual(event["title"], "Office hours")
        self.assertEqual(event["kind"], "hard")
        self.assertIn("weekdays", event.get("recurrence") or {})
        self.assertNotIn("created_at", event)
        self.assertNotIn("source_uid", event)
        self.assertNotIn("updated_at", event)
        self.assertNotIn("at_risk", week)
        self.assertIn("day_start", week["settings"])
        self.assertNotIn("feeds", week["settings"])

    def test_cluny_modules_are_lazy_and_packaged(self) -> None:
        import lazy_eel

        self.assertIn("cluny_sync", lazy_eel.LAZY_MODULES)
        self.assertIn("cluny_sync", lazy_eel.FEATURE_MODULES["cluny"])
        names = lazy_eel._exposed_names("cluny_sync")
        self.assertIn("backfill_cluny_life", names)
        self.assertIn("get_cluny_settings", names)
        build = (ROOT / "build_app.py").read_text(encoding="utf-8")
        self.assertIn('"cluny_brain"', build)
        self.assertIn('"brain"', build)
        self.assertIn('"library"', build)
