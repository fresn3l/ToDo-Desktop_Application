"""Read-only life snapshot for Cluny: file, HTTP, Ask context."""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest import mock

import calclock
import cluny_ask
import cluny_client
import cluny_snapshot
import cluny_sync
import journal
import local_api
import work
import workouts


class ClunySnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"KOSISTENZ_DATA_DIR": self.tmp.name}, clear=False)
        self.env.start()
        for key in (
            "CLUNY_SQLITE_PATH",
            "CLUNY_DATABASE_PATH",
            "CLUNY_INGEST_URL",
            "CLUNY_BRAIN_URL",
            "CLUNY_CHECKLIST_INGEST_URL",
            "CLUNY_API_KEY",
        ):
            os.environ.pop(key, None)

    def tearDown(self) -> None:
        self.env.stop()
        self.tmp.cleanup()

    def _seed_life(self) -> date:
        today = date.today()
        today_iso = today.isoformat()
        journal.save_journal_entry(
            "Spanish vocab felt slow tonight.",
            tags=["spanish"],
            kind="evening_review",
        )
        item = work.create_work_item("Essay outline", scheduled_date=today_iso, notes="Need two sources")
        work.start_work_item(item["id"])
        work.finish_work_item(item["id"])
        start = datetime(today.year, today.month, today.day, 9, 0)
        end = datetime(today.year, today.month, today.day, 10, 0)
        calclock.create_calendar_event("CHEM 109 lecture", start.isoformat(), end.isoformat())
        workouts.add_workout_session(today_iso, "push", "", None, None)
        return today

    def test_snapshot_shape_and_write(self) -> None:
        self._seed_life()
        payload = cluny_snapshot.write_life_snapshot()
        self.assertEqual(payload["date"], date.today().isoformat())
        self.assertIn("Never pick a clock time", payload["instruction"])
        self.assertIn("journal", payload)
        self.assertIn("work", payload)
        self.assertIn("calendar", payload)
        self.assertIn("workouts", payload)
        self.assertIn("goals", payload)
        self.assertIn("briefs", payload)
        self.assertIsInstance(payload["free_minutes"], int)
        excerpts = [row.get("excerpt") for row in payload["journal"]]
        self.assertTrue(any("Spanish vocab felt slow" in (text or "") for text in excerpts))
        kinds = [row.get("kind") for row in payload["journal"]]
        self.assertIn("evening_review", kinds)
        logged_titles = [row.get("title") for row in payload["work"]["logged"]]
        self.assertIn("Essay outline", logged_titles)
        logged = next(row for row in payload["work"]["logged"] if row["title"] == "Essay outline")
        self.assertIn("duration_seconds", logged)
        event_titles = [event.get("title") for day in payload["calendar"]["days"] for event in day.get("events") or []]
        self.assertIn("CHEM 109 lecture", event_titles)
        self.assertTrue(any(row.get("content") and "Spanish vocab felt slow" in row["content"] for row in payload["journal"]))
        digest = cluny_snapshot.snapshot_as_text(payload)
        self.assertIn("Spanish vocab felt slow", digest)
        self.assertIn("Need two sources", digest)
        self.assertIn("workout_plan", payload)
        self.assertTrue(any(row.get("kind") == "push" for row in payload["workouts"]))
        path = Path(self.tmp.name) / "cluny_life_snapshot.json"
        self.assertTrue(path.exists())
        status = cluny_snapshot.snapshot_public_status()
        self.assertEqual(status["snapshot_path"], str(path))
        self.assertEqual(status["snapshot_updated_at"], payload["generated_at"])

    def test_loopback_get_life(self) -> None:
        self._seed_life()
        status, payload = local_api.handle_request("GET", "/api/cluny/life")
        self.assertEqual(status, 200)
        self.assertEqual(payload["date"], date.today().isoformat())
        self.assertTrue(any("Spanish vocab" in (row.get("excerpt") or "") for row in payload["journal"]))

    def test_ask_context_includes_logged_event_journal_workout(self) -> None:
        self._seed_life()
        ctx = cluny_ask.build_context()
        self.assertIn("Never pick a clock time", ctx["instruction"])
        excerpts = [row.get("excerpt") for row in ctx["journal"]]
        self.assertTrue(any("Spanish vocab felt slow" in (text or "") for text in excerpts))
        logged_titles = [row.get("title") for row in ctx["work"]["logged"]]
        self.assertIn("Essay outline", logged_titles)
        event_titles = [event.get("title") for day in ctx["calendar"]["days"] for event in day.get("events") or []]
        self.assertIn("CHEM 109 lecture", event_titles)
        self.assertTrue(any(row.get("kind") == "push" for row in ctx["workouts"]))
        self.assertTrue(any(row.get("title") == "CHEM 109 lecture" for row in ctx["events_today"]))

    def test_settings_expose_snapshot_path(self) -> None:
        cluny_snapshot.write_life_snapshot()
        packed = cluny_sync.public_cluny_settings()
        self.assertTrue(packed["configured"])
        self.assertTrue(str(packed["snapshot_path"]).endswith("cluny_life_snapshot.json"))
        self.assertTrue(packed["snapshot_updated_at"])

    def test_refresh_does_not_raise_when_calendar_is_down(self) -> None:
        with mock.patch.object(calclock, "get_week", side_effect=RuntimeError("no clock")):
            payload = cluny_snapshot.refresh_life_snapshot_safe()
        self.assertIsNotNone(payload)
        self.assertEqual(payload["calendar"]["days"], [])


if __name__ == "__main__":
    unittest.main()
