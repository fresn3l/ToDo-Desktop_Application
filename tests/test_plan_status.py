"""One status path: finish, park, skip, attend, last chunk."""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import calclock
import glance
import schedule
import work


class PlanStatusTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self._tmp.name)
        self.env = mock.patch.dict(os.environ, {"KOSISTENZ_DATA_DIR": str(self.data_dir)})
        self.env.start()
        self.patcher = mock.patch.object(work, "_data_dir", lambda: self.data_dir)
        self.kinds = mock.patch.object(schedule.workouts, "expected_kinds_for_date", return_value=[])
        self.patcher.start()
        self.kinds.start()
        self.today = mock.patch.object(work, "_today", return_value=date(2026, 9, 7))
        self.today.start()
        self.habit_day = mock.patch.object(glance, "_today", return_value=date(2026, 9, 7))
        self.habit_day.start()
        calclock.reset_purge_cache()
        work.invalidate_work_board_cache()

    def tearDown(self) -> None:
        work.cancel_heavy_snapshot_side_effects()
        self.habit_day.stop()
        self.kinds.stop()
        self.patcher.stop()
        self.today.stop()
        self.env.stop()
        self._tmp.cleanup()

    def test_done_on_work_closes_open_bars_and_leaves_event_marks(self) -> None:
        item = work.create_work_item("Board memo", scheduled_date="2026-09-07", estimate_minutes=60)
        bar = calclock.schedule_work_at(
            item["id"], "2026-09-07T10:00:00", "2026-09-07T11:00:00"
        )["block"]
        event = calclock.create_calendar_event(
            "Standup", "2026-09-07T09:00:00", "2026-09-07T09:30:00"
        )
        calclock.set_bar_outcome(event["id"], "attended", "2026-09-07")
        finished = work.finish_work_item(item["id"])
        self.assertEqual(finished["status"], "done")
        closed = calclock.load_block(bar["id"])
        self.assertEqual(closed["status"], "done")
        week = calclock.get_week("2026-09-07")
        monday = next(day for day in week["days"] if day["date"] == "2026-09-07")
        marked = next(row for row in monday["events"] if row["id"] == event["id"])
        self.assertEqual(marked["status"], "done")

    def test_park_clears_date_and_deletes_bars(self) -> None:
        item = work.create_work_item("Board memo", scheduled_date="2026-09-07", estimate_minutes=45)
        bar = calclock.schedule_work_at(
            item["id"], "2026-09-07T11:00:00", "2026-09-07T11:45:00"
        )["block"]
        parked = work.assign_work_item(item["id"], "")
        self.assertIsNone(parked["scheduled_date"])
        self.assertEqual(parked["estimate_minutes"], 45)
        self.assertIsNone(calclock.load_block(bar["id"]))
        self.assertEqual(calclock.blocks_for_item(item["id"]), [])

    def test_park_detaches_focus_so_minutes_stay_unplaced(self) -> None:
        item = work.create_work_item("Board memo", scheduled_date="2026-09-07", estimate_minutes=30)
        focus = calclock.create_focus_block(
            "Deep work",
            "2026-09-07T13:00:00",
            "2026-09-07T14:00:00",
            [item["id"]],
        )
        work.assign_work_item(item["id"], "")
        packed = calclock._enrich_focus_blocks([calclock._load_block(focus["id"])])[0]
        self.assertEqual(packed["items"], [])
        unplaced = {row["id"] for row in calclock.unplaced_work()}
        self.assertIn(item["id"], unplaced)

    def test_skip_bar_keeps_work_dated_and_puts_leftover_in_unplaced(self) -> None:
        item = work.create_work_item("Board memo", scheduled_date="2026-09-07", estimate_minutes=60)
        bar = calclock.schedule_work_at(
            item["id"], "2026-09-07T10:00:00", "2026-09-07T11:00:00"
        )["block"]
        skipped = calclock.set_block_status(bar["id"], "skipped")
        self.assertEqual(skipped["status"], "skipped")
        still = work.get_work_items_by_ids([item["id"]])[0]
        self.assertEqual(still["scheduled_date"], "2026-09-07")
        self.assertEqual(still["status"], "open")
        leftover = {row["id"]: row for row in calclock.unplaced_work()}
        self.assertIn(item["id"], leftover)
        self.assertEqual(leftover[item["id"]]["remaining_minutes"], 60)

    def test_attended_event_does_not_finish_work_or_bars(self) -> None:
        item = work.create_work_item("Board memo", scheduled_date="2026-09-07", estimate_minutes=45)
        bar = calclock.schedule_work_at(
            item["id"], "2026-09-07T11:00:00", "2026-09-07T11:45:00"
        )["block"]
        event = calclock.create_calendar_event(
            "Standup", "2026-09-07T09:00:00", "2026-09-07T09:30:00"
        )
        calclock.set_bar_outcome(event["id"], "attended", "2026-09-07")
        still = work.get_work_items_by_ids([item["id"]])[0]
        self.assertEqual(still["status"], "open")
        self.assertEqual(calclock.load_block(bar["id"])["status"], "proposed")

    def test_finish_last_chunk_marks_work_done(self) -> None:
        item = work.create_work_item("Board memo", scheduled_date="2026-09-07", estimate_minutes=60)
        bar = calclock.schedule_work_at(
            item["id"], "2026-09-07T10:00:00", "2026-09-07T11:00:00"
        )["block"]
        packed = calclock.set_block_status(bar["id"], "done")
        self.assertEqual(packed["status"], "done")
        self.assertEqual(work.get_work_items_by_ids([item["id"]])[0]["status"], "done")

    def test_glance_park_uses_the_same_path(self) -> None:
        import home_glances

        item = work.create_work_item("Gym film", scheduled_date="2026-09-07", estimate_minutes=30)
        bar = calclock.schedule_work_at(
            item["id"], "2026-09-07T07:00:00", "2026-09-07T07:30:00"
        )["block"]
        parked = home_glances.glance_park_work(item["id"])
        self.assertIsNone(parked["scheduled_date"])
        self.assertIsNone(calclock.load_block(bar["id"]))


class FocusHabitTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self._tmp.name)
        self.env = mock.patch.dict(os.environ, {"KOSISTENZ_DATA_DIR": str(self.data_dir)})
        self.env.start()
        self.patcher = mock.patch.object(work, "_data_dir", lambda: self.data_dir)
        self.kinds = mock.patch.object(schedule.workouts, "expected_kinds_for_date", return_value=[])
        self.patcher.start()
        self.kinds.start()
        self.today = mock.patch.object(work, "_today", return_value=date(2026, 9, 7))
        self.today.start()
        self.habit_day = mock.patch.object(glance, "_today", return_value=date(2026, 9, 7))
        self.habit_day.start()
        calclock.reset_purge_cache()
        work.invalidate_work_board_cache()

    def tearDown(self) -> None:
        work.cancel_heavy_snapshot_side_effects()
        self.habit_day.stop()
        self.kinds.stop()
        self.patcher.stop()
        self.today.stop()
        self.env.stop()
        self._tmp.cleanup()

    def test_habit_minutes_in_the_title_count_as_overflow(self) -> None:
        glance.add_habit("15 mins of yoga nidra")
        hid = glance.get_habits()["habits"][0]["id"]
        item = work.create_work_item("Board memo", scheduled_date="2026-09-07", estimate_minutes=60)
        focus = calclock.create_focus_block(
            "Morning",
            "2026-09-07T06:00:00",
            "2026-09-07T07:00:00",
            [item["id"]],
        )
        packed = calclock.attach_focus_item(focus["id"], hid, "habit")
        kinds = {row["kind"] for row in packed["items"]}
        self.assertEqual(kinds, {"work", "habit"})
        self.assertEqual(packed["planned_minutes"], 75)
        self.assertEqual(packed["overflow_minutes"], 15)
        habit = next(row for row in packed["items"] if row["kind"] == "habit")
        self.assertEqual(habit["minutes"], 15)
        self.assertFalse(habit["done"])

    def test_tick_habit_on_focus_is_the_habits_tick(self) -> None:
        glance.add_habit("15 mins of yoga nidra")
        hid = glance.get_habits()["habits"][0]["id"]
        focus = calclock.create_focus_block(
            "Morning",
            "2026-09-07T06:00:00",
            "2026-09-07T07:00:00",
            [],
        )
        calclock.attach_focus_item(focus["id"], hid, "habit")
        packed = calclock.toggle_focus_row(focus["id"], hid, "habit")
        habit = packed["items"][0]
        self.assertTrue(habit["done"])
        self.assertTrue(glance.get_habits()["habits"][0]["done"])

    def test_done_on_focus_work_finishes_the_work_item(self) -> None:
        item = work.create_work_item("Board memo", scheduled_date="2026-09-07", estimate_minutes=30)
        focus = calclock.create_focus_block(
            "Deep work",
            "2026-09-07T13:00:00",
            "2026-09-07T14:00:00",
            [item["id"]],
        )
        packed = calclock.toggle_focus_row(focus["id"], item["id"], "work")
        self.assertTrue(packed["items"][0]["done"])
        self.assertEqual(work.get_work_items_by_ids([item["id"]])[0]["status"], "done")

    def test_legacy_focus_rows_migrate_to_work_kind(self) -> None:
        item = work.create_work_item("Board memo", scheduled_date="2026-09-07", estimate_minutes=30)
        focus = calclock.create_focus_block(
            "Hold",
            "2026-09-07T13:00:00",
            "2026-09-07T14:00:00",
            [item["id"]],
        )
        path = self.data_dir / "calendar.sqlite"
        import sqlite3

        conn = sqlite3.connect(path)
        conn.execute("DROP TABLE focus_block_items")
        conn.execute(
            """
            CREATE TABLE focus_block_items (
                block_id TEXT NOT NULL,
                work_item_id TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (block_id, work_item_id)
            )
            """
        )
        conn.execute(
            "INSERT INTO focus_block_items (block_id, work_item_id, sort_order) VALUES (?, ?, 0)",
            (focus["id"], item["id"]),
        )
        conn.commit()
        conn.close()
        calclock.reset_purge_cache()
        packed = calclock._enrich_focus_blocks([calclock._load_block(focus["id"])])[0]
        self.assertEqual(len(packed["items"]), 1)
        self.assertEqual(packed["items"][0]["kind"], "work")
        self.assertEqual(packed["items"][0]["id"], item["id"])
