"""Notes: storage vs one focus span."""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import calclock
import notes
import schedule
import work


class NotesTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self._tmp.name)
        self.env = mock.patch.dict(os.environ, {"KOSISTENZ_DATA_DIR": str(self.data_dir)})
        self.work_dir = mock.patch.object(work, "_data_dir", lambda: self.data_dir)
        self.kinds = mock.patch.object(schedule.workouts, "expected_kinds_for_date", return_value=[])
        self.today = mock.patch.object(work, "_today", return_value=date(2026, 9, 7))
        self.env.start()
        self.work_dir.start()
        self.kinds.start()
        self.today.start()
        calclock.reset_purge_cache()
        work.invalidate_work_board_cache()

    def tearDown(self) -> None:
        work.cancel_heavy_snapshot_side_effects()
        self.today.stop()
        self.kinds.stop()
        self.work_dir.stop()
        self.env.stop()
        self._tmp.cleanup()

    def _focus(self, title: str = "Friday deep work") -> dict:
        return calclock.create_focus_block(
            title,
            "2026-09-11T14:00:00",
            "2026-09-11T16:00:00",
            [],
        )

    def test_save_lands_in_storage_until_attached(self) -> None:
        saved = notes.save_note("Talking points", "- budget\n- hiring")
        self.assertIsNone(saved["focus_id"])
        self.assertEqual(saved["title"], "Talking points")
        listed = notes.list_notes()
        self.assertEqual(listed[0]["id"], saved["id"])

    def test_title_falls_back_to_first_line(self) -> None:
        saved = notes.save_note("", "Board memo\nSecond line")
        self.assertEqual(saved["title"], "Board memo")

    def test_attach_and_detach_one_focus(self) -> None:
        focus = self._focus()
        saved = notes.save_note("Agenda", "- one\n- two")
        attached = notes.attach_note(saved["id"], focus["id"])
        self.assertEqual(attached["focus_id"], focus["id"])
        week = calclock.get_week("2026-09-07")
        friday = next(day for day in week["days"] if day["date"] == "2026-09-11")
        block = next(row for row in friday["blocks"] if row["id"] == focus["id"])
        self.assertEqual(block["notes"][0]["id"], saved["id"])
        self.assertEqual(block["notes"][0]["body"], "- one\n- two")
        detached = notes.detach_note(saved["id"])
        self.assertIsNone(detached["focus_id"])
        week = calclock.get_week("2026-09-07")
        friday = next(day for day in week["days"] if day["date"] == "2026-09-11")
        block = next(row for row in friday["blocks"] if row["id"] == focus["id"])
        self.assertEqual(block["notes"], [])

    def test_moving_note_leaves_the_old_span(self) -> None:
        first = self._focus("First")
        second = calclock.create_focus_block(
            "Second",
            "2026-09-11T16:00:00",
            "2026-09-11T17:00:00",
            [],
        )
        saved = notes.save_note("Shared", "pin me")
        notes.attach_note(saved["id"], first["id"])
        notes.attach_note(saved["id"], second["id"])
        by_focus = notes.notes_by_focus_ids([first["id"], second["id"]])
        self.assertEqual(by_focus[first["id"]], [])
        self.assertEqual(by_focus[second["id"]][0]["id"], saved["id"])

    def test_deleting_focus_returns_note_to_storage(self) -> None:
        focus = self._focus()
        saved = notes.save_note("Keep", "still needed")
        notes.attach_note(saved["id"], focus["id"])
        calclock.delete_schedule_block(focus["id"], force=True)
        listed = notes.list_notes()
        self.assertEqual(listed[0]["id"], saved["id"])
        self.assertIsNone(listed[0]["focus_id"])

    def test_cannot_attach_to_a_work_bar(self) -> None:
        item = work.create_work_item("Essay", scheduled_date="2026-09-11", estimate_minutes=45)
        bar = calclock.add_block(
            title="Essay",
            start=calclock.parse_datetime("2026-09-11T10:00:00"),
            end=calclock.parse_datetime("2026-09-11T11:00:00"),
            kind="work",
            work_item_id=item["id"],
        )
        saved = notes.save_note("Nope", "not a hold")
        with self.assertRaises(ValueError):
            notes.attach_note(saved["id"], bar["id"])

    def test_list_focus_spans_this_week(self) -> None:
        focus = self._focus()
        spans = notes.list_focus_spans()
        self.assertTrue(any(row["id"] == focus["id"] for row in spans))


if __name__ == "__main__":
    unittest.main()
