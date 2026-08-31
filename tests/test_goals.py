"""Goals: attach to-dos, count finish minutes, fall back to calendar blocks."""

from __future__ import annotations

import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest import mock

import goals
import schedule
import work


class GoalsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self._tmp.name)
        self.patcher = mock.patch.object(work, "_data_dir", lambda: self.data_dir)
        self.patcher.start()

    def tearDown(self) -> None:
        self.patcher.stop()
        self._tmp.cleanup()

    def test_keyword_matches_title_word(self) -> None:
        self.assertTrue(goals.keyword_matches("45 mins spanish", "spanish"))
        self.assertTrue(goals.keyword_matches("Spend 45 mins doing Spanish", "spanish"))
        self.assertFalse(goals.keyword_matches("calculus homework", "spanish"))

    def test_create_attaches_by_keyword(self) -> None:
        goal = goals.create_goal("Learn to speak Spanish", "six_month", "spanish")
        item = work.create_work_item("45 mins spanish", scheduled_date=date.today().isoformat())
        self.assertEqual(item["goal_id"], goal["id"])

    def test_explicit_goal_wins_over_keyword(self) -> None:
        spanish = goals.create_goal("Learn Spanish", "six_month", "spanish")
        calc = goals.create_goal("Pass calculus", "year", "calculus")
        item = work.create_work_item(
            "45 mins spanish",
            scheduled_date=date.today().isoformat(),
            goal_id=calc["id"],
        )
        self.assertEqual(item["goal_id"], calc["id"])
        self.assertNotEqual(item["goal_id"], spanish["id"])

    def test_finish_timer_counts_not_the_block(self) -> None:
        goal = goals.create_goal("Learn Spanish", "six_month", "spanish", target_hours=10)
        with mock.patch.object(schedule, "_now", return_value=datetime(2026, 9, 3, 8, 0, 0)):
            placed = schedule.add_todo_to_calendar(
                "45 mins spanish",
                on_date="2026-09-03",
                goal_id=goal["id"],
            )
        self.assertEqual(placed["placed"], 1)
        item_id = placed["item"]["id"]
        t0 = datetime(2026, 9, 3, 10, 0, 0)
        with mock.patch.object(work, "_now", return_value=t0):
            work.start_work_item(item_id)
        with mock.patch.object(work, "_now", return_value=t0 + timedelta(minutes=20)):
            work.finish_work_item(item_id)
        board = goals.get_goals_board()
        six = next(col for col in board["horizons"] if col["id"] == "six_month")
        row = six["goals"][0]
        self.assertEqual(row["spent_minutes"], 20)
        self.assertEqual(row["percent"], 3)
        self.assertTrue(row["has_target"])

    def test_finish_without_timer_uses_block_minutes(self) -> None:
        goal = goals.create_goal("Learn Spanish", "six_month", "spanish")
        with mock.patch.object(schedule, "_now", return_value=datetime(2026, 9, 3, 8, 0, 0)):
            placed = schedule.add_todo_to_calendar("45 mins spanish", on_date="2026-09-03")
        self.assertEqual(placed["item"]["goal_id"], goal["id"])
        work.finish_work_item(placed["item"]["id"])
        row = goals.list_goals()[0]
        self.assertEqual(row["spent_minutes"], 45)
        self.assertFalse(row["has_target"])
        self.assertIsNone(row["percent"])

    def test_running_total_without_hour_target(self) -> None:
        goal = goals.create_goal("Read more", "year", "reading")
        item = work.create_work_item("30 mins reading", scheduled_date=date.today().isoformat())
        t0 = datetime(2026, 9, 1, 9, 0, 0)
        with mock.patch.object(work, "_now", return_value=t0):
            work.start_work_item(item["id"])
        with mock.patch.object(work, "_now", return_value=t0 + timedelta(minutes=30)):
            work.finish_work_item(item["id"])
        row = next(g for g in goals.list_goals() if g["id"] == goal["id"])
        self.assertFalse(row["has_target"])
        self.assertEqual(row["spent_minutes"], 30)
        self.assertIsNone(row["percent"])

    def test_horizons_are_separate_columns(self) -> None:
        goals.create_goal("Spanish", "six_month", "spanish")
        goals.create_goal("Degree", "five_year")
        board = goals.get_goals_board()
        labels = [col["label"] for col in board["horizons"]]
        self.assertEqual(labels, ["1 week", "6 months", "Year", "5 years"])
        self.assertEqual(len(board["horizons"][1]["goals"]), 1)
        self.assertEqual(len(board["horizons"][3]["goals"]), 1)

    def test_delete_goal_unlinks_todos(self) -> None:
        goal = goals.create_goal("Spanish", "six_month", "spanish")
        item = work.create_work_item("45 mins spanish")
        self.assertEqual(item["goal_id"], goal["id"])
        goals.delete_goal(goal["id"])
        again = work.list_all_work_items()[0]
        self.assertIsNone(again["goal_id"])
        self.assertEqual(goals.list_goals(), [])

    def _freeze(self, day: date, hour: int = 10):
        now = datetime(day.year, day.month, day.day, hour, 0, 0)
        return mock.patch.multiple(
            work,
            _today=lambda: day,
            _now=lambda: now,
        )

    def test_weekly_goal_lands_on_today_midweek(self) -> None:
        wednesday = date(2026, 9, 2)
        with self._freeze(wednesday):
            goal = goals.create_goal("Speak Spanish", "week", "spanish", target_hours=3)
            items = work.list_all_work_items()
        weekly = [row for row in items if row.get("source") == "weekly_goal"]
        self.assertEqual(len(weekly), 1)
        self.assertEqual(weekly[0]["scheduled_date"], "2026-09-02")
        self.assertEqual(weekly[0]["goal_id"], goal["id"])
        self.assertEqual(weekly[0]["title"], "3h spanish")
        self.assertEqual(weekly[0]["source_uid"], f"weekly:{goal['id']}:2026-08-31")
        self.assertFalse(weekly[0]["is_overdue"])

    def test_sunday_assigns_upcoming_week_without_duplicating(self) -> None:
        sunday = date(2026, 9, 6)
        with self._freeze(sunday):
            goal = goals.create_goal("Speak Spanish", "week", "spanish", target_hours=3)
            again = goals.ensure_weekly_goal_todos()
        self.assertEqual(again, [])
        items = [
            row
            for row in work.list_all_work_items()
            if row.get("source") == "weekly_goal"
        ]
        dates = sorted(row["scheduled_date"] for row in items)
        self.assertEqual(dates, ["2026-09-06", "2026-09-07"])
        uids = {row["source_uid"] for row in items}
        self.assertEqual(
            uids,
            {
                f"weekly:{goal['id']}:2026-08-31",
                f"weekly:{goal['id']}:2026-09-07",
            },
        )

    def test_monday_assigns_the_week_if_sunday_was_missed(self) -> None:
        monday = date(2026, 9, 7)
        with self._freeze(monday):
            goal = goals.create_goal("Gym", "weekly")
            work.get_work_board(monday.isoformat())
        items = [row for row in work.list_all_work_items() if row.get("source") == "weekly_goal"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["scheduled_date"], "2026-09-07")
        self.assertEqual(items[0]["source_uid"], f"weekly:{goal['id']}:2026-09-07")
        self.assertEqual(items[0]["title"], "Gym")

    def test_ended_weekly_goal_skips_future_weeks(self) -> None:
        sunday = date(2026, 9, 6)
        with self._freeze(sunday):
            goals.create_goal(
                "Wrap Spanish",
                "week",
                "spanish",
                end_date="2026-09-04",
            )
        items = [row for row in work.list_all_work_items() if row.get("source") == "weekly_goal"]
        dates = sorted(row["scheduled_date"] for row in items)
        self.assertEqual(dates, ["2026-09-06"])

    def test_week_progress_only_counts_this_week(self) -> None:
        wednesday = date(2026, 9, 2)
        with self._freeze(wednesday):
            goal = goals.create_goal("Speak Spanish", "week", "spanish", target_hours=3)
        last_week = work.create_work_item(
            "45 mins spanish",
            scheduled_date="2026-08-26",
            goal_id=goal["id"],
        )
        this_week = work.create_work_item(
            "30 mins spanish",
            scheduled_date="2026-09-02",
            goal_id=goal["id"],
        )
        t0 = datetime(2026, 8, 26, 9, 0, 0)
        with mock.patch.object(work, "_now", return_value=t0):
            work.start_work_item(last_week["id"])
        with mock.patch.object(work, "_now", return_value=t0 + timedelta(minutes=45)):
            work.finish_work_item(last_week["id"])
        t1 = datetime(2026, 9, 2, 9, 0, 0)
        with mock.patch.object(work, "_now", return_value=t1):
            work.start_work_item(this_week["id"])
        with mock.patch.object(work, "_now", return_value=t1 + timedelta(minutes=30)):
            work.finish_work_item(this_week["id"])
        with self._freeze(wednesday):
            row = next(g for g in goals.list_goals() if g["id"] == goal["id"])
        self.assertEqual(row["spent_minutes"], 30)
        self.assertEqual(row["percent"], 17)

    def test_horizon_aliases_include_week(self) -> None:
        goal = goals.create_goal("Run", "1w")
        self.assertEqual(goal["horizon"], "week")
        self.assertEqual(goal["horizon_label"], "1 week")
