"""Tests for the loopback menu-bar / widget API."""

from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import local_api
import work
import workouts


class LocalApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        path = Path(self._tmp.name)
        self.patches = [
            mock.patch.object(work, "_data_dir", lambda: path),
            mock.patch.object(workouts, "_data_dir", lambda: path),
            mock.patch.object(work, "_journal_snapshot_bits", return_value={"journal_today": False, "journal_streak": 0}),
        ]
        for patcher in self.patches:
            patcher.start()

    def tearDown(self) -> None:
        for patcher in self.patches:
            patcher.stop()
        self._tmp.cleanup()

    def test_status_says_today_is_empty(self) -> None:
        status, payload = local_api.handle_request("GET", "/api/status")
        self.assertEqual(status, 200)
        self.assertTrue(payload["today_empty"])
        self.assertEqual(payload["summary"], "Today is empty")
        self.assertIsNone(payload["active_id"])

    def test_start_and_finish_active_todo(self) -> None:
        today = date.today().isoformat()
        work.create_work_item("Write report", scheduled_date=today)
        status, started = local_api.handle_request("POST", "/api/todo/start")
        self.assertEqual(status, 200)
        self.assertEqual(started["item"]["status"], "active")
        self.assertEqual(started["item"]["title"], "Write report")
        status, finished = local_api.handle_request("POST", "/api/todo/finish")
        self.assertEqual(status, 200)
        self.assertEqual(finished["item"]["status"], "done")
        status, empty = local_api.handle_request("POST", "/api/todo/finish")
        self.assertEqual(status, 400)
        self.assertIn("active", empty["error"].lower())

    def test_log_push_and_park(self) -> None:
        status, logged = local_api.handle_request("POST", "/api/workout/log", {"kind": "push"})
        self.assertEqual(status, 200)
        self.assertTrue(logged["day"]["done"])
        status, parked = local_api.handle_request("POST", "/api/work/park", {"title": "Call dentist"})
        self.assertEqual(status, 200)
        self.assertTrue(parked["item"]["is_backlog"])
        status, widget = local_api.handle_request("GET", "/api/widget")
        self.assertEqual(status, 200)
        self.assertTrue(widget["workout_logged"])
        self.assertIn("push", widget["workout_kinds"])
        self.assertEqual(widget["backlog_count"], 1)

    def test_unknown_route(self) -> None:
        status, payload = local_api.handle_request("GET", "/nope")
        self.assertEqual(status, 404)
        self.assertFalse(payload["ok"])

    def test_rejects_dns_rebinding_host(self) -> None:
        self.assertFalse(local_api.client_allowed({"Host": "evil.example", "Origin": ""}))
        self.assertTrue(local_api.client_allowed({"Host": "127.0.0.1:18741"}))
        self.assertTrue(local_api.client_allowed({"Host": "localhost:18741"}))

    def test_rejects_website_csrf_origin(self) -> None:
        self.assertFalse(local_api.client_allowed({
            "Host": "127.0.0.1:18741",
            "Origin": "https://evil.example",
        }))
        self.assertFalse(local_api.origin_allowed("null"))
        self.assertTrue(local_api.client_allowed({"Host": "127.0.0.1:18741"}))

    def test_origin_must_match_ui_port(self) -> None:
        with mock.patch.dict("os.environ", {"KOSISTENZ_UI_PORT": "17653"}):
            self.assertTrue(
                local_api.origin_allowed("http://127.0.0.1:17653")
            )
            self.assertFalse(
                local_api.origin_allowed("http://127.0.0.1:9999")
            )


if __name__ == "__main__":
    unittest.main()
