"""Attendance, midnight miss, planned hours, and rate goals."""

from __future__ import annotations

import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest import mock

import calclock
import consistency
import goals
import insights
import work


class ConsistencyTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self._tmp.name)
        self.patcher = mock.patch.object(work, "_data_dir", lambda: self.data_dir)
        self.today = mock.patch.object(work, "_today", return_value=date(2026, 9, 11))
        self.patcher.start()
        self.today.start()
        calclock.reset_purge_cache()

    def tearDown(self) -> None:
        self.today.stop()
        self.patcher.stop()
        self._tmp.cleanup()

    def _event(self, title: str, day: date, hour: int = 9, minutes: int = 60):
        start = datetime(day.year, day.month, day.day, hour, 0, 0)
        end = start + timedelta(minutes=minutes)
        return calclock.create_calendar_event(
            title,
            start.isoformat(timespec="seconds"),
            end.isoformat(timespec="seconds"),
        )

    def _block(self, title: str, day: date, hour: int = 14, minutes: int = 45, status: str = "proposed"):
        start = datetime(day.year, day.month, day.day, hour, 0, 0)
        end = start + timedelta(minutes=minutes)
        return calclock.add_block(title=title, start=start, end=end, kind="work", status=status)

    def test_rollover_marks_yesterday_open_bars_missed(self) -> None:
        yesterday = date(2026, 9, 10)
        event = self._event("Standup", yesterday)
        block = self._block("Spanish", yesterday, status="locked")
        today_event = self._event("Today meeting", date(2026, 9, 11), hour=11)
        result = calclock.rollover_missed_bars(date(2026, 9, 11), force=True)
        self.assertGreaterEqual(result["events"], 1)
        self.assertEqual(result["blocks"], 1)
        marks = calclock.event_mark_map()
        self.assertEqual(marks[calclock.event_mark_key(event["id"], "2026-09-10")], "missed")
        self.assertNotIn(calclock.event_mark_key(today_event["id"], "2026-09-11"), marks)
        again = calclock._load_block(block["id"])
        self.assertEqual(again["status"], "missed")
        second = calclock.rollover_missed_bars(date(2026, 9, 11), force=True)
        self.assertEqual(second["blocks"], 0)

    def test_set_bar_outcome_for_event_and_block(self) -> None:
        event = self._event("Review", date(2026, 9, 10))
        block = self._block("Write", date(2026, 9, 10))
        calclock.set_bar_outcome(event["id"], "attended", "2026-09-10")
        calclock.set_bar_outcome(block["id"], "missed")
        marks = calclock.event_mark_map()
        self.assertEqual(marks[calclock.event_mark_key(event["id"], "2026-09-10")], "done")
        self.assertEqual(calclock._load_block(block["id"])["status"], "missed")

    def test_attendance_counts_done_against_miss_and_skip(self) -> None:
        day = date(2026, 9, 10)
        event = self._event("A", day, hour=9, minutes=60)
        self._event("B", day, hour=11, minutes=60)
        block = self._block("C", day, hour=14, minutes=60, status="skipped")
        calclock.set_bar_outcome(event["id"], "attended", day.isoformat())
        calclock.rollover_missed_bars(date(2026, 9, 11), force=True)
        data = consistency.summarize(7, date(2026, 9, 11))
        self.assertEqual(data["attended"], 1)
        self.assertEqual(data["closed"], 3)
        self.assertEqual(data["attendance_pct"], 33)
        self.assertEqual(data["planned_minutes"], 180)
        self.assertEqual(data["hours"], 3.0)
        self.assertEqual(calclock._load_block(block["id"])["status"], "skipped")

    def test_todo_completion_uses_dated_items(self) -> None:
        work.create_work_item("Done one", scheduled_date="2026-09-10")
        work.create_work_item("Open one", scheduled_date="2026-09-10")
        later = work.create_work_item("Also done", scheduled_date="2026-09-10")
        work.finish_work_item(later["id"])
        first = [row for row in work.list_all_work_items() if row["title"] == "Done one"][0]
        work.finish_work_item(first["id"])
        data = consistency.summarize(7, date(2026, 9, 11))
        self.assertEqual(data["todo_total"], 3)
        self.assertEqual(data["todo_done"], 2)
        self.assertEqual(data["todo_pct"], 67)

    def test_analytics_payload_includes_consistency(self) -> None:
        with mock.patch.object(insights, "_journal_entries_in_range", return_value=[]):
            data = insights.get_analytics(28)
        self.assertIn("consistency", data)
        self.assertEqual(data["consistency"]["days"], 28)
        self.assertIn("weeks", data["consistency"])

    def test_rate_goal_tracks_attendance(self) -> None:
        day = date(2026, 9, 10)
        event = self._event("A", day)
        self._event("B", day, hour=11)
        calclock.set_bar_outcome(event["id"], "attended", day.isoformat())
        calclock.rollover_missed_bars(date(2026, 9, 11), force=True)
        goal = goals.create_rate_goal("Show up", "attendance", 80, 4)
        self.assertTrue(goal["is_rate"])
        self.assertEqual(goal["measure"], "attendance")
        self.assertEqual(goal["window_weeks"], 4)
        self.assertEqual(goal["current_value"], 50)
        self.assertEqual(goal["percent"], 62)
        board = goals.get_goals_board()
        self.assertEqual(len(board["rates"]["goals"]), 1)
        self.assertEqual(len(board["horizons"][0]["goals"]), 0)


if __name__ == "__main__":
    unittest.main()
