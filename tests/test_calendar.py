"""Calendar clock: deadline ingest, hard lectures, and the packer."""

from __future__ import annotations

import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest import mock

import calclock
import schedule
import work


class CalendarStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self._tmp.name)
        self.patcher = mock.patch.object(work, "_data_dir", lambda: self.data_dir)
        self.kinds = mock.patch.object(schedule.workouts, "expected_kinds_for_date", return_value=[])
        self.patcher.start()
        self.kinds.start()

    def tearDown(self) -> None:
        self.kinds.stop()
        self.patcher.stop()
        self._tmp.cleanup()

    def _fill(self, monday: str, now: datetime) -> dict:
        with mock.patch.object(schedule, "_now", return_value=now):
            return schedule.fill_week(monday)

    def test_all_day_and_1159_are_deadlines_not_busy(self) -> None:
        start = datetime(2026, 9, 4, 0, 0, 0)
        self.assertTrue(
            calclock.is_deadline_event(all_day=True, start_at=start, end_at=start + timedelta(days=1))
        )
        due = datetime(2026, 9, 4, 23, 59, 0)
        self.assertTrue(
            calclock.is_deadline_event(all_day=False, start_at=due, end_at=due)
        )
        lecture = datetime(2026, 9, 4, 9, 30, 0)
        self.assertFalse(
            calclock.is_deadline_event(
                all_day=False,
                start_at=lecture,
                end_at=lecture + timedelta(minutes=50),
                role="busy",
            )
        )

    def test_all_day_due_is_end_of_that_day(self) -> None:
        start = datetime(2026, 9, 4, 0, 0, 0)
        end = datetime(2026, 9, 5, 0, 0, 0)
        due = calclock.due_at_for_imported(all_day=True, start_at=start, end_at=end)
        self.assertEqual(due, "2026-09-04T23:59:00")

    def test_ics_import_dedupes_uid(self) -> None:
        ics = """BEGIN:VCALENDAR
BEGIN:VEVENT
UID:essay-2
SUMMARY:Essay 2 due
DTSTART;VALUE=DATE:20260904
DTEND;VALUE=DATE:20260905
END:VEVENT
BEGIN:VEVENT
UID:quiz-1
SUMMARY:Quiz 1 due
DTSTART:20260903T235900
END:VEVENT
END:VCALENDAR
"""
        first = calclock.import_ics_text(ics, calendar_id="class")
        self.assertEqual(first["created"], 2)
        second = calclock.import_ics_text(ics, calendar_id="class")
        self.assertEqual(second["created"], 0)
        self.assertEqual(second["updated"], 2)
        items = work.list_all_work_items()
        self.assertEqual(len(items), 2)
        by_title = {row["title"]: row for row in items}
        self.assertEqual(by_title["Essay 2 due"]["due_at"], "2026-09-04T23:59:00")
        self.assertEqual(by_title["Quiz 1 due"]["due_at"], "2026-09-03T23:59:00")
        self.assertEqual(by_title["Essay 2 due"]["estimate_minutes"], 60)
        self.assertIsNone(by_title["Essay 2 due"]["scheduled_date"])
        self.assertEqual(by_title["Essay 2 due"]["source_uid"], "essay-2")

    def test_second_import_does_not_reopen_done(self) -> None:
        ics = """BEGIN:VCALENDAR
BEGIN:VEVENT
UID:essay-2
SUMMARY:Essay 2 due
DTSTART;VALUE=DATE:20260904
END:VEVENT
END:VCALENDAR
"""
        calclock.import_ics_text(ics, calendar_id="class")
        item = work.list_all_work_items()[0]
        work.finish_work_item(item["id"])
        calclock.import_ics_text(
            ics.replace("Essay 2 due", "Essay 2 due (updated)"), calendar_id="class"
        )
        again = work.list_all_work_items()[0]
        self.assertEqual(again["status"], "done")
        self.assertEqual(again["title"], "Essay 2 due (updated)")

    def test_chunks_split_long_estimates(self) -> None:
        self.assertEqual(schedule.chunk_minutes(180), [90, 90])
        self.assertEqual(schedule.chunk_minutes(100), [90, 10])
        self.assertEqual(schedule.chunk_minutes(40), [40])

    def test_packer_places_around_lecture(self) -> None:
        monday = date(2026, 9, 7)
        calclock.create_calendar_event(
            "CHEM 109",
            "2026-09-07T09:30:00",
            "2026-09-07T10:20:00",
            weekdays=[0],
        )
        work.create_work_item(
            "Study essay 2",
            due_at="2026-09-11T23:59:00",
            estimate_minutes=180,
        )
        week = self._fill(monday.isoformat(), datetime(2026, 9, 7, 8, 0, 0))
        monday_row = next(day for day in week["days"] if day["date"] == "2026-09-07")
        self.assertEqual(monday_row["events"][0]["title"], "CHEM 109")
        work_blocks = [b for day in week["days"] for b in day["blocks"] if b["kind"] == "work"]
        self.assertEqual(sum(b["minutes"] for b in work_blocks), 180)
        lecture_start = datetime(2026, 9, 7, 9, 30, 0)
        lecture_end = datetime(2026, 9, 7, 10, 20, 0)
        for block in monday_row["blocks"]:
            start = calclock.parse_datetime(block["start_at"])
            end = calclock.parse_datetime(block["end_at"])
            overlaps = start < lecture_end and end > lecture_start
            self.assertFalse(overlaps)

    def test_locked_block_survives_refill(self) -> None:
        monday = date(2026, 9, 7)
        work.create_work_item(
            "Problem set",
            due_at="2026-09-11T23:59:00",
            estimate_minutes=90,
        )
        week = self._fill(monday.isoformat(), datetime(2026, 9, 7, 8, 0, 0))
        work_blocks = [b for day in week["days"] for b in day["blocks"] if b["kind"] == "work"]
        self.assertEqual(len(work_blocks), 1)
        block_id = work_blocks[0]["id"]
        calclock.set_block_status(block_id, "locked")
        week = self._fill(monday.isoformat(), datetime(2026, 9, 7, 8, 0, 0))
        locked = [b for day in week["days"] for b in day["blocks"] if b["status"] == "locked"]
        self.assertEqual(len(locked), 1)
        self.assertEqual(locked[0]["id"], block_id)


if __name__ == "__main__":
    unittest.main()
