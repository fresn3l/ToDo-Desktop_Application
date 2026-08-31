"""Tests for dated To Do items, All Work backlog, timers, and evening planning."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

import work


class WorkStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self._tmp.name)
        self.patcher = mock.patch.object(work, "_data_dir", lambda: self.data_dir)
        self.patcher.start()
        self.work = work

    def tearDown(self) -> None:
        self.patcher.stop()
        self._tmp.cleanup()

    def test_due_and_estimate_stay_on_backlog_item(self) -> None:
        item = self.work.create_work_item(
            "Essay 2",
            due_at="2026-09-04",
            estimate_minutes=90,
        )
        self.assertTrue(item["is_backlog"])
        self.assertEqual(item["due_at"], "2026-09-04T23:59:00")
        self.assertEqual(item["estimate_minutes"], 90)
        updated = self.work.update_work_plan(item["id"], "2026-09-04T23:59:00", 120)
        self.assertEqual(updated["estimate_minutes"], 120)

    def test_backlog_stays_undated_until_assigned(self) -> None:
        item = self.work.create_work_item("Pay electricity bill")
        self.assertIsNone(item["scheduled_date"])
        self.assertTrue(item["is_backlog"])
        backlog = self.work.list_backlog()
        self.assertEqual(len(backlog), 1)
        self.assertEqual(backlog[0]["title"], "Pay electricity bill")

        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        assigned = self.work.assign_work_item(item["id"], tomorrow)
        self.assertEqual(assigned["scheduled_date"], tomorrow)
        self.assertEqual(self.work.list_backlog(), [])
        self.assertEqual(len(self.work.list_work_for_date(tomorrow)), 1)

    def test_evening_plan_creates_and_assigns_for_tomorrow(self) -> None:
        parked = self.work.create_work_item("Call dentist")
        result = self.work.apply_evening_plan(
            {
                "tomorrow_prep": {
                    "created_titles": ["Pay electricity bill", ""],
                    "assign_ids": [parked["id"]],
                }
            }
        )
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        self.assertEqual(result["tomorrow"], tomorrow)
        titles = {row["title"] for row in self.work.list_work_for_date(tomorrow)}
        self.assertEqual(titles, {"Pay electricity bill", "Call dentist"})
        self.assertEqual(self.work.list_backlog(), [])

    def test_start_and_finish_timer(self) -> None:
        today = date.today().isoformat()
        item = self.work.create_work_item("Write report", scheduled_date=today)
        started = self.work.start_work_item(item["id"])
        self.assertEqual(started["status"], "active")
        self.assertTrue(started["active_started_at"])
        finished = self.work.finish_work_item(item["id"])
        self.assertEqual(finished["status"], "done")
        self.assertIsNone(finished["active_started_at"])
        self.assertGreaterEqual(finished["duration_seconds"], 0)
        self.assertTrue(finished["finished_at"])

    def test_starting_one_task_pauses_another(self) -> None:
        today = date.today().isoformat()
        a = self.work.create_work_item("A", scheduled_date=today)
        b = self.work.create_work_item("B", scheduled_date=today)
        self.work.start_work_item(a["id"])
        self.work.start_work_item(b["id"])
        board = self.work.get_work_board(today)
        by_id = {row["id"]: row for row in board["today"]}
        self.assertEqual(by_id[a["id"]]["status"], "open")
        self.assertEqual(by_id[b["id"]]["status"], "active")

    def test_widget_snapshot_counts_today_open_tasks(self) -> None:
        today = date.today().isoformat()
        self.work.create_work_item("Pay electricity bill", scheduled_date=today)
        self.work.create_work_item("Later idea")  # backlog
        snap = self.work.get_widget_snapshot()
        self.assertEqual(snap["date"], today)
        self.assertEqual(snap["open_count"], 1)
        self.assertEqual(snap["backlog_count"], 1)
        self.assertEqual(snap["titles"], ["Pay electricity bill"])
        self.assertFalse(snap["workout_logged"])
        self.assertFalse(snap["today_empty"])
        self.assertIn("open", snap["summary"])
        path = self.work.get_widget_snapshot_path()
        self.assertTrue(path.exists())
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["open_count"], 1)

    def test_daily_repeat_spawns_fresh_day_without_carryover(self) -> None:
        friday = date(2026, 8, 28)
        saturday = date(2026, 8, 29)
        with mock.patch.object(self.work, "_today", return_value=friday):
            item = self.work.create_work_item(
                "Meditate 15 mins",
                scheduled_date=friday.isoformat(),
                repeat={"kind": "daily"},
            )
            self.assertTrue(item["is_repeating"])
            self.assertEqual(item["scheduled_date"], friday.isoformat())
        with mock.patch.object(self.work, "_today", return_value=saturday):
            board = self.work.get_work_board(saturday.isoformat())
            self.assertEqual([row["title"] for row in board["today"]], ["Meditate 15 mins"])
            self.assertEqual(board["today"][0]["scheduled_date"], saturday.isoformat())
            self.assertEqual(board["overdue"], [])
            self.assertNotEqual(board["today"][0]["id"], item["id"])

    def test_custom_weekdays_skip_other_days(self) -> None:
        friday = date(2026, 8, 28)  # Friday
        saturday = date(2026, 8, 29)
        with mock.patch.object(self.work, "_today", return_value=friday):
            self.work.create_work_item(
                "Deep work",
                scheduled_date=friday.isoformat(),
                repeat={"kind": "weekly", "weekdays": [0, 4]},  # Mon, Fri
            )
        with mock.patch.object(self.work, "_today", return_value=saturday):
            board = self.work.get_work_board(saturday.isoformat())
            self.assertEqual(board["today"], [])
            self.assertEqual(board["overdue"], [])

    def test_rename_can_be_this_day_or_series(self) -> None:
        friday = date(2026, 8, 28)
        saturday = date(2026, 8, 29)
        with mock.patch.object(self.work, "_today", return_value=friday):
            item = self.work.create_work_item(
                "Meditate 15 mins",
                scheduled_date=friday.isoformat(),
                repeat={"kind": "daily"},
            )
            self.work.update_work_item(item["id"], "Only Friday", scope="occurrence")
        with mock.patch.object(self.work, "_today", return_value=saturday):
            board = self.work.get_work_board(saturday.isoformat())
            self.assertEqual(board["today"][0]["title"], "Meditate 15 mins")
            self.work.update_work_item(board["today"][0]["id"], "Meditate 20 mins", scope="series")
            board = self.work.get_work_board(saturday.isoformat())
            self.assertEqual(board["today"][0]["title"], "Meditate 20 mins")

    def test_delete_this_day_keeps_the_series(self) -> None:
        friday = date(2026, 8, 28)
        saturday = date(2026, 8, 29)
        with mock.patch.object(self.work, "_today", return_value=friday):
            item = self.work.create_work_item(
                "Meditate 15 mins",
                scheduled_date=friday.isoformat(),
                repeat={"kind": "daily"},
            )
            self.work.delete_work_item(item["id"], scope="occurrence")
            self.assertEqual(self.work.list_work_for_date(friday.isoformat()), [])
        with mock.patch.object(self.work, "_today", return_value=saturday):
            board = self.work.get_work_board(saturday.isoformat())
            self.assertEqual([row["title"] for row in board["today"]], ["Meditate 15 mins"])

    def test_missed_repeat_is_logged_without_carryover(self) -> None:
        friday = date(2026, 8, 28)
        saturday = date(2026, 8, 29)
        with mock.patch.object(self.work, "_today", return_value=friday):
            self.work.create_work_item(
                "Meditate 15 mins",
                scheduled_date=friday.isoformat(),
                repeat={"kind": "daily"},
            )
        with mock.patch.object(self.work, "_today", return_value=saturday):
            board = self.work.get_work_board(saturday.isoformat())
            self.assertEqual(board["overdue"], [])
            stats = self.work.repeating_work_analytics(7)
            miss_dates = [row["date"] for row in stats["misses"]]
            self.assertIn(friday.isoformat(), miss_dates)
            self.assertNotIn(saturday.isoformat(), miss_dates)
            self.assertEqual(stats["repeat_missed"], 1)
            self.assertEqual(stats["repeat_skipped"], 0)

    def test_skip_is_not_counted_as_a_miss(self) -> None:
        friday = date(2026, 8, 28)
        saturday = date(2026, 8, 29)
        with mock.patch.object(self.work, "_today", return_value=friday):
            item = self.work.create_work_item(
                "Meditate 15 mins",
                scheduled_date=friday.isoformat(),
                repeat={"kind": "daily"},
            )
            self.work.delete_work_item(item["id"], scope="occurrence")
        with mock.patch.object(self.work, "_today", return_value=saturday):
            stats = self.work.repeating_work_analytics(7)
            self.assertEqual(stats["repeat_skipped"], 1)
            self.assertEqual(stats["repeat_missed"], 0)
            self.assertEqual(stats["misses"], [])

    def test_finished_repeat_is_not_a_miss(self) -> None:
        friday = date(2026, 8, 28)
        saturday = date(2026, 8, 29)
        with mock.patch.object(self.work, "_today", return_value=friday):
            item = self.work.create_work_item(
                "Meditate 15 mins",
                scheduled_date=friday.isoformat(),
                repeat={"kind": "daily"},
            )
            self.work.finish_work_item(item["id"])
        with mock.patch.object(self.work, "_today", return_value=saturday):
            stats = self.work.repeating_work_analytics(7)
            self.assertEqual(stats["repeat_done"], 1)
            self.assertEqual(stats["repeat_missed"], 0)
            self.assertEqual(stats["misses"], [])


if __name__ == "__main__":
    unittest.main()
