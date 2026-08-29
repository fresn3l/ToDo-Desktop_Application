"""Tests for shared data dir, Health import path checks, and unloaded eel APIs."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import eel

import daily_checklist
import health_import
import journal
import paths
import recovery
import work
import workouts


class DataDirectoryTests(unittest.TestCase):
    def test_override_applies_to_journal_work_and_workouts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"KOSISTENZ_DATA_DIR": tmp}):
                root = paths.data_directory()
                self.assertEqual(root, Path(tmp))
                journal_dir = journal.get_journal_directory()
                self.assertEqual(journal_dir, Path(tmp) / "Journal")
                self.assertTrue(journal_dir.is_dir())
                self.assertEqual(work._data_dir(), Path(tmp))
                self.assertEqual(workouts._data_dir(), Path(tmp))
                self.assertEqual(daily_checklist.get_data_directory(), Path(tmp))


class HealthPathTests(unittest.TestCase):
    def test_rejects_wrong_name_and_paths_outside_home(self) -> None:
        with self.assertRaises(ValueError):
            health_import._validate_health_export_path("/tmp/not-export.xml")
        with tempfile.TemporaryDirectory() as tmp:
            outside = Path(tmp) / "export.xml"
            outside.write_text("<HealthData/>", encoding="utf-8")
            home = Path.home().resolve()
            try:
                outside.resolve().relative_to(home)
                in_home = True
            except ValueError:
                in_home = False
            if not in_home:
                with self.assertRaises(ValueError):
                    health_import._validate_health_export_path(str(outside))

    def test_accepts_export_xml_under_home(self) -> None:
        folder = Path.home() / ".kosistenz-health-path-test"
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / "export.xml"
        target.write_text("<HealthData/>", encoding="utf-8")
        try:
            path = health_import._validate_health_export_path(str(target))
            self.assertEqual(path, target.resolve())
        finally:
            target.unlink(missing_ok=True)
            try:
                folder.rmdir()
            except OSError:
                pass


class UnloadedApiTests(unittest.TestCase):
    def test_checklist_recovery_and_github_are_not_eel_exposed(self) -> None:
        import checkin_github  # noqa: F401
        import recovery  # noqa: F401

        exposed = getattr(eel, "_exposed_functions", {})
        for name in (
            "submit_daily_checklist_response",
            "get_daily_checklist",
            "get_pending_recovery",
            "submit_recovery_response",
            "get_weekly_review",
            "export_checklist_json",
            "refresh_screen_time_for_recent_days",
            "try_push_checkin",
        ):
            self.assertNotIn(name, exposed)


class PageLockdownTests(unittest.TestCase):
    def test_index_has_csp_and_no_inline_script(self) -> None:
        html = Path(__file__).resolve().parents[1] / "web" / "index.html"
        text = html.read_text(encoding="utf-8")
        self.assertIn('http-equiv="Content-Security-Policy"', text)
        self.assertIn("frame-src 'none'", text)
        self.assertIn("object-src 'none'", text)
        self.assertIn("script-src 'self'", text)
        self.assertNotIn("<script>", text)
        self.assertIn("js/boot-appearance.js", text)

    def test_local_api_does_not_send_wildcard_cors(self) -> None:
        source = Path(__file__).resolve().parents[1] / "local_api.py"
        text = source.read_text(encoding="utf-8")
        self.assertNotIn("Access-Control-Allow-Origin", text)
        self.assertIn("X-Content-Type-Options", text)


class ClunyPathTests(unittest.TestCase):
    def test_sqlite_path_must_stay_in_home(self) -> None:
        import cluny_sync

        with tempfile.TemporaryDirectory() as tmp:
            outside = Path(tmp) / "cluny.sqlite"
            home = Path.home().resolve()
            try:
                outside.resolve().relative_to(home)
                in_home = True
            except ValueError:
                in_home = False
            if not in_home:
                with self.assertRaises(ValueError):
                    cluny_sync._validate_sqlite_path(str(outside))


if __name__ == "__main__":
    unittest.main()
