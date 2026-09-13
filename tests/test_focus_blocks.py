"""Focus blocks: named spans, overflow, and Fill week stays off them."""

from __future__ import annotations

import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest import mock

import calclock
import schedule
import work


class FocusBlockTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self._tmp.name)
        self.patcher = mock.patch.object(work, "_data_dir", lambda: self.data_dir)
        self.kinds = mock.patch.object(schedule.workouts, "expected_kinds_for_date", return_value=[])
        self.patcher.start()
        self.kinds.start()
        self.today = mock.patch.object(work, "_today", return_value=date(2026, 9, 7))
        self.today.start()
        calclock.reset_purge_cache()
        work.invalidate_work_board_cache()

    def tearDown(self) -> None:
        work.cancel_heavy_snapshot_side_effects()
        self.kinds.stop()
        self.patcher.stop()
        self.today.stop()
        self._tmp.cleanup()

    def test_overflow_is_allowed_and_visible(self) -> None:
        first = work.create_work_item("Read brief", scheduled_date="2026-09-07", estimate_minutes=45)
        second = work.create_work_item("Draft notes", scheduled_date="2026-09-07", estimate_minutes=45)
        block = calclock.create_focus_block(
            "Deep work",
            "2026-09-07T13:00:00",
            "2026-09-07T14:00:00",
            [first["id"], second["id"]],
        )
        self.assertEqual(block["kind"], "focus")
        self.assertEqual(block["minutes"], 60)
        self.assertEqual(block["planned_minutes"], 90)
        self.assertEqual(block["overflow_minutes"], 30)
        self.assertEqual(len(block["items"]), 2)
        unplaced = {row["id"] for row in calclock.unplaced_work()}
        self.assertNotIn(first["id"], unplaced)
        self.assertNotIn(second["id"], unplaced)

    def test_fill_week_does_not_pack_over_or_delete_focus(self) -> None:
        focus = calclock.create_focus_block(
            "Hold this",
            "2026-09-07T09:00:00",
            "2026-09-07T12:00:00",
            [],
        )
        work.create_work_item(
            "Study essay",
            due_at="2026-09-11T23:59:00",
            estimate_minutes=90,
        )
        with mock.patch.object(schedule, "_now", return_value=datetime(2026, 9, 7, 8, 0, 0)):
            week = schedule.fill_week("2026-09-07")
        monday = next(day for day in week["days"] if day["date"] == "2026-09-07")
        focuses = [row for row in monday["blocks"] if row.get("kind") == "focus"]
        self.assertEqual(len(focuses), 1)
        self.assertEqual(focuses[0]["id"], focus["id"])
        hold_start = datetime(2026, 9, 7, 9, 0, 0)
        hold_end = datetime(2026, 9, 7, 12, 0, 0)
        for block in monday["blocks"]:
            if block.get("kind") == "focus":
                continue
            start = calclock.parse_datetime(block["start_at"])
            end = calclock.parse_datetime(block["end_at"])
            self.assertFalse(start < hold_end and end > hold_start)

    def test_fill_week_does_not_place_attached_todos(self) -> None:
        item = work.create_work_item(
            "Inside focus",
            due_at="2026-09-11T23:59:00",
            estimate_minutes=90,
        )
        calclock.create_focus_block(
            "Morning hold",
            "2026-09-07T14:00:00",
            "2026-09-07T15:00:00",
            [item["id"]],
        )
        with mock.patch.object(schedule, "_now", return_value=datetime(2026, 9, 7, 8, 0, 0)):
            week = schedule.fill_week("2026-09-07")
        work_blocks = [row for day in week["days"] for row in day["blocks"] if row.get("kind") == "work"]
        self.assertEqual(work_blocks, [])

    def test_detach_returns_item_to_unplaced(self) -> None:
        item = work.create_work_item("Parked later", scheduled_date="2026-09-07", estimate_minutes=30)
        block = calclock.create_focus_block(
            "Hold",
            "2026-09-07T16:00:00",
            "2026-09-07T17:00:00",
            [item["id"]],
        )
        calclock.detach_focus_item(block["id"], item["id"])
        unplaced = {row["id"] for row in calclock.unplaced_work()}
        self.assertIn(item["id"], unplaced)

    def test_attach_event_to_focus_makes_a_todo_and_leaves_the_event(self) -> None:
        event = calclock.create_calendar_event(
            "Team sync",
            "2026-09-07T10:00:00",
            "2026-09-07T10:50:00",
        )
        focus = calclock.create_focus_block(
            "Homework",
            "2026-09-07T13:00:00",
            "2026-09-07T15:00:00",
            [],
        )
        packed = calclock.attach_event_to_focus(focus["id"], event["id"], "2026-09-07")
        self.assertEqual(len(packed["items"]), 1)
        self.assertEqual(packed["items"][0]["title"], "Team sync")
        self.assertEqual(packed["items"][0]["estimate_minutes"], 50)
        still = calclock._load_event(event["id"])
        self.assertEqual(still["start_at"], event["start_at"])
        self.assertEqual(still["end_at"], event["end_at"])
        again = calclock.attach_event_to_focus(focus["id"], event["id"], "2026-09-07")
        self.assertEqual([row["id"] for row in again["items"]], [packed["items"][0]["id"]])

    def test_attach_event_to_focus_reuses_imported_work(self) -> None:
        item = work.create_work_item(
            "Essay 2",
            due_at="2026-09-11T23:59:00",
            estimate_minutes=60,
            source_uid="essay-2",
            source_calendar="class",
        )
        stored = calclock.replace_imported_hard_events(
            "class",
            [
                {
                    "title": "Essay 2",
                    "uid": "essay-2",
                    "start_at": datetime(2026, 9, 7, 9, 30, 0),
                    "end_at": datetime(2026, 9, 7, 10, 20, 0),
                }
            ],
        )
        self.assertEqual(stored, 1)
        events = [
            row
            for row in calclock.expand_hard_events(date(2026, 9, 7), date(2026, 9, 7))
            if row.get("source_uid") == "essay-2"
        ]
        self.assertEqual(len(events), 1)
        focus = calclock.create_focus_block(
            "Homework",
            "2026-09-07T13:00:00",
            "2026-09-07T15:00:00",
            [],
        )
        packed = calclock.attach_event_to_focus(focus["id"], events[0]["id"], "2026-09-07")
        self.assertEqual([row["id"] for row in packed["items"]], [item["id"]])
        self.assertEqual(work.get_work_items_by_ids([item["id"]])[0]["scheduled_date"], "2026-09-07")

    def test_due_chip_names_the_focus_that_holds_it(self) -> None:
        item = work.create_work_item(
            "Essay 2",
            due_at="2026-09-07T23:59:00",
            estimate_minutes=60,
        )
        calclock.create_focus_block(
            "Homework",
            "2026-09-07T13:00:00",
            "2026-09-07T15:00:00",
            [item["id"]],
        )
        week = calclock.get_week("2026-09-07")
        monday = next(day for day in week["days"] if day["date"] == "2026-09-07")
        due = next(row for row in monday["dues"] if row["id"] == item["id"])
        self.assertEqual(due["focus_title"], "Homework")
        self.assertTrue(due["focus_id"])
        unplaced = {row["id"] for row in week["unplaced"]}
        self.assertNotIn(item["id"], unplaced)

    def test_move_work_bar_to_focus_parks_the_clock_bar(self) -> None:
        item = work.create_work_item("Read brief", scheduled_date="2026-09-07", estimate_minutes=30)
        bar = calclock.schedule_work_at(item["id"], "2026-09-07T09:00:00", "2026-09-07T09:30:00")["block"]
        focus = calclock.create_focus_block(
            "Homework",
            "2026-09-07T13:00:00",
            "2026-09-07T15:00:00",
            [],
        )
        packed = calclock.move_work_bar_to_focus(bar["id"], focus["id"])
        self.assertEqual([row["id"] for row in packed["items"]], [item["id"]])
        week = calclock.get_week("2026-09-07")
        monday = next(day for day in week["days"] if day["date"] == "2026-09-07")
        work_bars = [row for row in monday["blocks"] if row.get("kind") == "work"]
        self.assertEqual(work_bars, [])
        focuses = [row for row in monday["blocks"] if row.get("kind") == "focus"]
        self.assertEqual([item["id"] for item in focuses[0]["items"]], [item["id"]])

    def test_attach_event_to_focus_rejects_a_work_bar(self) -> None:
        item = work.create_work_item("Read brief", scheduled_date="2026-09-07", estimate_minutes=30)
        block = calclock.schedule_work_at(item["id"], "2026-09-07T09:00:00", "2026-09-07T09:30:00")["block"]
        event = calclock.create_calendar_event("Standup", "2026-09-07T11:00:00", "2026-09-07T11:20:00")
        with self.assertRaises(ValueError):
            calclock.attach_event_to_focus(block["id"], event["id"], "2026-09-07")


if __name__ == "__main__":
    unittest.main()
