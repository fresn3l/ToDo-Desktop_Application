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
        self.assertIn("get_daily_checklist", lazy_eel.EXPOSE_FALLBACK["daily_checklist"])

    def test_expose_fallback_matches_source_and_survives_missing_files(self) -> None:
        import lazy_eel

        for module in lazy_eel.LAZY_MODULES:
            path = ROOT / f"{module.replace('.', '/')}.py"
            from_file = lazy_eel._EXPOSE_RE.findall(path.read_text(encoding="utf-8"))
            self.assertEqual(
                list(lazy_eel.EXPOSE_FALLBACK[module]),
                from_file,
                module,
            )
        with mock.patch.object(lazy_eel, "_module_source", return_value=""):
            names = lazy_eel._exposed_names("daily_checklist")
        self.assertIn("get_daily_checklist", names)
        self.assertIn("get_home_checkin", names)
        build = (ROOT / "build_app.py").read_text(encoding="utf-8")
        self.assertIn('"cluny_brain"', build)
        self.assertIn('"brain"', build)
        self.assertIn('"library"', build)

    def test_invoke_exposed_runs_today_and_week(self) -> None:
        import lazy_eel

        today = lazy_eel.invoke_exposed("get_today_home", [])
        self.assertIn("beat", today)
        self.assertIn("local_date", today)
        week = lazy_eel.invoke_exposed("get_week", [""])
        self.assertEqual(len(week["days"]), 7)
        with self.assertRaises(ValueError):
            lazy_eel.invoke_exposed("os_system", [])

    def test_home_boot_returns_today_when_weather_hangs(self) -> None:
        import threading
        import time

        import home_boot

        real = home_boot.fetch_glance
        release = threading.Event()

        def hang(kind: str):
            if kind == "weather":
                release.wait(timeout=30)
                return {"ok": True}
            return real(kind)

        with mock.patch.object(home_boot, "NETWORK_GLANCE_TIMEOUT_SEC", 0.2):
            with mock.patch.object(home_boot, "fetch_glance", side_effect=hang):
                with mock.patch.object(home_boot, "_ensure_cluny_supervisor"):
                    started = time.monotonic()
                    boot = home_boot.get_home_boot()
                    elapsed = time.monotonic() - started
        release.set()
        self.assertLess(elapsed, 2)
        self.assertIn("today_calendar", boot["glances"])
        self.assertIn("beat", boot["glances"]["today_calendar"])
        self.assertFalse(boot["glances"]["weather"].get("ok"))
