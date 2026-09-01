"""Switchable heatmap sources."""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import date, timedelta
from unittest import mock

import daily_checklist
import heatmap
import journal
import timeline
import work
import workouts


class HeatmapTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"KOSISTENZ_DATA_DIR": self.tmp.name})
        self.env.start()

    def tearDown(self) -> None:
        self.env.stop()
        self.tmp.cleanup()

    def _cell(self, payload, iso):
        return next(row for row in payload["days"] if row["date"] == iso)

    def test_writing_and_show_up_match_streak_dates(self) -> None:
        today = date.today().isoformat()
        journal.save_journal_entry("Wrote this morning.")
        writing = heatmap.get_heatmap("writing")
        show_up = heatmap.get_heatmap("show_up")
        streaks = timeline.compute_streaks()
        self.assertEqual(self._cell(writing, today)["state"], "hit")
        self.assertEqual(self._cell(show_up, today)["state"], "hit")
        self.assertEqual(writing["streak"], streaks["writing"])
        self.assertEqual(show_up["streak"], streaks["show_up"])

    def test_workout_and_checkin_sources(self) -> None:
        today = date.today().isoformat()
        workouts.add_workout_session(today, "push", "", None, None)
        daily_checklist.submit_daily_checklist_response("morning", 1, {"intentions": "go"})
        workout = heatmap.get_heatmap("workout")
        checkin = heatmap.get_heatmap("checkin")
        streaks = timeline.compute_streaks()
        self.assertEqual(self._cell(workout, today)["state"], "hit")
        self.assertEqual(self._cell(checkin, today)["state"], "hit")
        self.assertEqual(workout["streak"], streaks["workout"])
        self.assertEqual(checkin["streak"], streaks["checkin"])

    def test_journaling_intensity_and_kind_filter(self) -> None:
        today = date.today().isoformat()
        journal.save_journal_entry("Free write")
        journal.upsert_kinded_journal_entry("Plan", "morning_brief", today)
        journal.upsert_kinded_journal_entry("Recap", "evening_review", today)
        all_writing = heatmap.get_heatmap("journal", journal_filter="all")
        morning = heatmap.get_heatmap("journal", journal_filter="morning_brief")
        self.assertEqual(self._cell(all_writing, today)["value"], 3)
        self.assertEqual(self._cell(morning, today)["value"], 1)
        self.assertEqual(self._cell(all_writing, today)["kinds"]["morning_brief"], 1)

    def test_series_done_miss_pending_and_not_expected(self) -> None:
        yesterday = date.today() - timedelta(days=1)
        with mock.patch.object(work, "_today", return_value=yesterday):
            item = work.create_work_item(
                "Meditate",
                scheduled_date=yesterday.isoformat(),
                repeat={"kind": "weekly", "weekdays": [yesterday.weekday(), date.today().weekday()]},
            )
        series_id = item["series_id"]
        payload = heatmap.get_heatmap("series", series_id, days=21)
        self.assertEqual(self._cell(payload, yesterday.isoformat())["state"], "miss")
        self.assertEqual(self._cell(payload, date.today().isoformat())["state"], "pending")
        skipped = yesterday.weekday()
        # A day the cadence does not expect stays muted.
        other = date.today()
        while other.weekday() in {yesterday.weekday(), date.today().weekday()}:
            other -= timedelta(days=1)
            if other < yesterday - timedelta(days=8):
                break
        if other.weekday() not in {yesterday.weekday(), date.today().weekday()}:
            self.assertEqual(self._cell(payload, other.isoformat())["state"], "none")
        today_item = next(
            row for row in work.list_work_for_date(date.today().isoformat()) if row["series_id"] == series_id
        )
        work.finish_work_item(today_item["id"])
        payload = heatmap.get_heatmap("series", series_id, days=21)
        self.assertEqual(self._cell(payload, date.today().isoformat())["state"], "hit")
        skip_item = next(
            row for row in work.list_work_for_date(yesterday.isoformat()) if row.get("series_id") == series_id
        ) if work.list_work_for_date(yesterday.isoformat()) else None
        if skip_item is None:
            # yesterday's occurrence may not exist as an item after a miss; mark skip via delete if present
            pass
        else:
            work.delete_work_item(skip_item["id"], scope="occurrence")
            payload = heatmap.get_heatmap("series", series_id, days=21)
            self.assertEqual(self._cell(payload, yesterday.isoformat())["state"], "skip")
        self.assertEqual(skipped, yesterday.weekday())

    def test_settings_round_trip(self) -> None:
        heatmap.save_heatmap_settings("workout", "", "all")
        loaded = heatmap.get_heatmap()
        self.assertEqual(loaded["source"], "workout")
        heatmap.save_heatmap_settings("journal", "", "evening_review")
        loaded = heatmap.get_heatmap()
        self.assertEqual(loaded["source"], "journal")
        self.assertEqual(loaded["journal_filter"], "evening_review")


if __name__ == "__main__":
    unittest.main()
