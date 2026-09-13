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
        # Boot finishes the rate-goal nudge off the round-trip; let it land
        # before the data directory disappears out from under it.
        import home_boot

        home_boot.wait_for_boot_background()
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

    def test_settings_feature_does_not_import_brain(self) -> None:
        import lazy_eel

        self.assertEqual(lazy_eel.FEATURE_MODULES["settings"], ())
        self.assertEqual(lazy_eel.FEATURE_MODULES["today"], ("insights", "calclock", "home_glances"))

    def test_home_boot_does_not_probe_cluny_health(self) -> None:
        import home_boot
        import work

        work.create_work_item("Write the paper", scheduled_date=work._today().isoformat())
        with (
            mock.patch.object(home_boot, "_ensure_cluny_supervisor"),
            mock.patch.object(home_boot, "_call", wraps=home_boot._call) as called,
        ):
            home_boot.get_home_boot()
        names = [row.args[1] for row in called.call_args_list if row.args]
        self.assertNotIn("get_cluny_health", names)
        self.assertIn("get_cluny_inbox", names)
        self.assertNotIn("get_today_home", names)
        self.assertIn("now_next_glance", names)

    def test_get_home_boot_is_one_payload(self) -> None:
        import home_boot
        import work

        work.create_work_item("Write the paper", scheduled_date=work._today().isoformat())
        with mock.patch.object(home_boot, "_ensure_cluny_supervisor"):
            boot = home_boot.get_home_boot()
        self.assertIn("layout", boot)
        self.assertIn("glances", boot)
        # Tiles come back keyed by widget key, so two Work slices on one page
        # each get their own answer instead of sharing one.
        self.assertIn("work:slice=today", boot["glances"])
        self.assertIn("today_calendar", boot["glances"])
        todo = boot["glances"]["work:slice=today"]
        titles = [row.get("title") for row in (todo.get("today") or [])]
        self.assertIn("Write the paper", titles)
        self.assertIsNotNone(boot.get("checkin"))
        # The check-in runs beside the tiles but is not one of them.
        self.assertNotIn(home_boot.CHECKIN_TASK, boot["glances"])

    def test_each_work_slice_fetches_its_own_list(self) -> None:
        """Four slices of one tile, four different questions. Sharing one
        answer between them would show the backlog under a Due heading."""
        import home_boot

        calls = []

        def record(module, func, *args):
            calls.append(func)
            return {"ok": True}

        with mock.patch.object(home_boot, "_safe_call", side_effect=record):
            with mock.patch.object(home_boot.work, "list_backlog", return_value=[]) as backlog:
                home_boot.fetch_glance("work:slice=backlog")
            home_boot.fetch_glance("work:slice=unplaced")
            home_boot.fetch_glance("work:slice=due")
        self.assertEqual(backlog.call_count, 1)
        self.assertEqual(calls, ["unplaced_glance", "dues_this_week"])

    def test_a_work_tile_with_no_slice_shows_today(self) -> None:
        import home_boot
        import work

        work.create_work_item("Write the paper", scheduled_date=work._today().isoformat())
        board = home_boot.fetch_glance("work")
        titles = [row.get("title") for row in (board.get("today") or [])]
        self.assertIn("Write the paper", titles)

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

    def test_stubs_then_real_import_replaces_and_loads(self) -> None:
        """Opening Calendar/Home after launch used to AssertionError on @eel.expose."""
        code = r"""
import json
import os
import sys
import tempfile
sys.path.insert(0, %r)
tmp = tempfile.TemporaryDirectory()
os.environ["KOSISTENZ_DATA_DIR"] = tmp.name
import eel
import lazy_eel
lazy_eel.register_lazy_exposes()
for name in lazy_eel.LAZY_MODULES:
    lazy_eel.load_module(name)
week = lazy_eel.invoke_exposed("get_week", [""])
assert len(week["days"]) == 7, week
today = lazy_eel.invoke_exposed("get_today_home", [])
assert "beat" in today and "local_date" in today, today
flow = lazy_eel.invoke_exposed("get_daily_checklist", [])
assert isinstance(flow.get("nodes"), dict), flow
json.dumps(week)
json.dumps(today)
json.dumps(flow)
import home_boot
from unittest import mock
with mock.patch.object(home_boot, "_ensure_cluny_supervisor"):
    boot = home_boot.get_home_boot()
json.dumps(boot)
assert boot["glances"]["today_calendar"].get("ok") is not False
assert "beat" in boot["glances"]["today_calendar"]
assert boot.get("checkin") and boot["checkin"].get("ok") is not False
print("ok")
""" % (str(ROOT),)
        out = subprocess.check_output([sys.executable, "-c", code], cwd=str(ROOT), text=True)
        self.assertIn("ok", out)

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

    def test_home_boot_skips_insights_for_today_tile(self) -> None:
        code = r"""
import sys
sys.path.insert(0, %r)
import os
import tempfile
from unittest import mock
tmp = tempfile.TemporaryDirectory()
os.environ["KOSISTENZ_DATA_DIR"] = tmp.name
import home_boot
with mock.patch.object(home_boot, "_ensure_cluny_supervisor"):
    boot = home_boot.get_home_boot()
blocked = [name for name in ("insights", "workouts", "timeline") if name in sys.modules]
assert not blocked, blocked
assert boot["glances"]["today_calendar"].get("ok") is not False
assert "beat" in boot["glances"]["today_calendar"]
print("ok")
""" % (str(ROOT),)
        out = subprocess.check_output([sys.executable, "-c", code], cwd=str(ROOT), text=True)
        self.assertIn("ok", out)
