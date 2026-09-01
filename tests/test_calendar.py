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

    def test_todo_title_duration_lands_on_chosen_day_around_lecture(self) -> None:
        thursday = date(2026, 9, 3)
        calclock.create_calendar_event(
            "CHEM 109",
            "2026-09-03T09:30:00",
            "2026-09-03T10:20:00",
            weekdays=[3],
        )
        with mock.patch.object(schedule, "_now", return_value=datetime(2026, 9, 3, 9, 0, 0)):
            result = schedule.add_todo_to_calendar(
                "spend 45 mins doing calculus",
                on_date=thursday.isoformat(),
            )
        self.assertEqual(result["placed"], 1)
        self.assertEqual(result["date"], "2026-09-03")
        self.assertEqual(result["item"]["estimate_minutes"], 45)
        self.assertEqual(result["item"]["scheduled_date"], "2026-09-03")
        start = calclock.parse_datetime(result["start_at"])
        self.assertEqual(start, datetime(2026, 9, 3, 10, 20, 0))
        lecture_start = datetime(2026, 9, 3, 9, 30, 0)
        lecture_end = datetime(2026, 9, 3, 10, 20, 0)
        end = start + timedelta(minutes=45)
        self.assertFalse(start < lecture_end and end > lecture_start)
        week = calclock.get_week("2026-08-31")
        work_blocks = [b for day in week["days"] for b in day["blocks"] if b["kind"] == "work"]
        self.assertEqual(len(work_blocks), 1)
        self.assertEqual(work_blocks[0]["local_date"], "2026-09-03")
        self.assertEqual(work_blocks[0]["minutes"], 45)

    def test_add_todo_without_minutes_stays_on_todo(self) -> None:
        with mock.patch.object(schedule, "_now", return_value=datetime(2026, 9, 3, 8, 0, 0)):
            result = schedule.add_todo_to_calendar("Read the chapter", on_date="2026-09-03")
        self.assertEqual(result["placed"], 0)
        self.assertEqual(result["item"]["scheduled_date"], "2026-09-03")
        self.assertIsNone(result["item"]["estimate_minutes"])
        self.assertEqual(calclock.list_blocks(date(2026, 9, 3), date(2026, 9, 3)), [])

    def test_repeating_todo_is_not_auto_placed(self) -> None:
        result = schedule.add_todo_to_calendar(
            "15 mins meditate",
            on_date="2026-09-03",
            repeat={"kind": "daily"},
        )
        self.assertEqual(result["placed"], 0)
        self.assertTrue(result["item"]["is_repeating"])
        self.assertEqual(calclock.list_blocks(date(2026, 9, 3), date(2026, 9, 3)), [])

    def test_fill_week_keeps_scheduled_item_on_that_day(self) -> None:
        monday = date(2026, 9, 7)
        work.create_work_item("45 mins calculus", scheduled_date="2026-09-10")
        week = self._fill(monday.isoformat(), datetime(2026, 9, 7, 8, 0, 0))
        work_blocks = [b for day in week["days"] for b in day["blocks"] if b["kind"] == "work"]
        self.assertEqual(len(work_blocks), 1)
        self.assertEqual(work_blocks[0]["local_date"], "2026-09-10")
        self.assertEqual(work_blocks[0]["minutes"], 45)

    def test_place_parses_title_without_clearing_due(self) -> None:
        item = work.create_work_item(
            "calculus",
            scheduled_date="2026-09-03",
            due_at="2026-09-04",
        )
        self.assertIsNone(item["estimate_minutes"])
        work.update_work_item(item["id"], "45 mins calculus")
        with mock.patch.object(schedule, "_now", return_value=datetime(2026, 9, 3, 8, 0, 0)):
            result = schedule.place_work_item(item["id"], "2026-09-03")
        self.assertEqual(result["placed"], 1)
        self.assertEqual(result["item"]["due_at"], "2026-09-04T23:59:00")
        self.assertEqual(result["item"]["estimate_minutes"], 45)

    def test_get_month_is_six_weeks_of_seven(self) -> None:
        payload = calclock.get_month(2026, 9)
        self.assertEqual(payload["year"], 2026)
        self.assertEqual(payload["month"], 9)
        self.assertEqual(payload["label"], "September 2026")
        self.assertEqual(len(payload["weeks"]), 6)
        for week in payload["weeks"]:
            self.assertEqual(len(week), 7)
        first = payload["weeks"][0][0]
        self.assertEqual(first["date"], "2026-08-31")
        self.assertFalse(first["in_month"])
        sept1 = payload["weeks"][0][1]
        self.assertEqual(sept1["date"], "2026-09-01")
        self.assertTrue(sept1["in_month"])
        sept30 = next(
            cell
            for week in payload["weeks"]
            for cell in week
            if cell["date"] == "2026-09-30"
        )
        self.assertTrue(sept30["in_month"])

    def test_get_month_marks_today_and_counts_items(self) -> None:
        today = date.today()
        payload = calclock.get_month(today.year, today.month)
        flagged = [cell for week in payload["weeks"] for cell in week if cell["is_today"]]
        self.assertEqual(len(flagged), 1)
        self.assertEqual(flagged[0]["date"], today.isoformat())
        self.assertTrue(flagged[0]["in_month"])

        calclock.create_calendar_event(
            "CHEM 109",
            "2026-09-07T09:30:00",
            "2026-09-07T10:20:00",
            weekdays=[0],
        )
        work.create_work_item("Essay 2", due_at="2026-09-11T23:59:00")
        work.create_work_item("45 mins calculus", scheduled_date="2026-09-10")
        with mock.patch.object(schedule, "_now", return_value=datetime(2026, 9, 7, 8, 0, 0)):
            schedule.fill_week("2026-09-07")
        month = calclock.get_month(2026, 9)
        lecture = next(
            cell for week in month["weeks"] for cell in week if cell["date"] == "2026-09-07"
        )
        due = next(
            cell for week in month["weeks"] for cell in week if cell["date"] == "2026-09-11"
        )
        placed = next(
            cell for week in month["weeks"] for cell in week if cell["date"] == "2026-09-10"
        )
        self.assertGreaterEqual(lecture["event_count"], 1)
        self.assertGreaterEqual(due["due_count"], 1)
        self.assertGreaterEqual(placed["block_count"], 1)
        self.assertTrue(lecture["has_items"])

    def test_get_month_clamps_junk_year_and_month(self) -> None:
        today = date.today()
        junk = calclock.get_month("nope", 99)
        self.assertEqual(junk["year"], today.year)
        self.assertEqual(junk["month"], today.month)
        far = calclock.get_month(3000, 0)
        self.assertEqual(far["year"], today.year)
        self.assertEqual(far["month"], today.month)

    def test_get_year_has_twelve_month_grids(self) -> None:
        payload = calclock.get_year(2026)
        self.assertEqual(payload["year"], 2026)
        self.assertEqual(payload["label"], "2026")
        self.assertEqual(len(payload["months"]), 12)
        self.assertEqual([row["month"] for row in payload["months"]], list(range(1, 13)))
        for month in payload["months"]:
            self.assertEqual(len(month["weeks"]), 6)
            self.assertEqual(len(month["weeks"][0]), 7)
        junk = calclock.get_year("later")
        self.assertEqual(junk["year"], date.today().year)


if __name__ == "__main__":
    unittest.main()
