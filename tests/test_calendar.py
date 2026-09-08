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

    def test_ics_import_writes_widget_snapshot_once(self) -> None:
        events = [
            {
                "title": f"HW {i}",
                "uid": f"uid-{i}",
                "start_at": datetime(2026, 9, 10, 23, 59),
                "all_day": False,
            }
            for i in range(80)
        ]
        with mock.patch.object(work, "_write_widget_snapshot", wraps=work._write_widget_snapshot) as snap:
            counts = calclock.ingest_events(events, calendar_id="canvas", role="deadlines")
        self.assertEqual(counts["created"], 80)
        self.assertEqual(counts["skipped"], 0)
        self.assertEqual(snap.call_count, 1)
        self.assertEqual(len(work.list_all_work_items()), 80)

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

    def test_normalize_ics_url_accepts_webcal_wrappers_and_uri_lists(self) -> None:
        self.assertEqual(
            calclock.normalize_ics_url("<webcal://cal.example.edu/x.ics>"),
            "https://cal.example.edu/x.ics",
        )
        self.assertEqual(
            calclock.normalize_ics_url("# comment\nhttps://cal.example.edu/x.ics?token=1\n"),
            "https://cal.example.edu/x.ics?token=1",
        )
        self.assertEqual(
            calclock.normalize_ics_url('Copy this: https://cal.example.edu/feed.ics'),
            "https://cal.example.edu/feed.ics",
        )
        self.assertEqual(
            calclock.normalize_ics_url("http://cal.example.edu/feed.ics"),
            "http://cal.example.edu/feed.ics",
        )
        self.assertEqual(calclock.normalize_ics_url("  ", allow_empty=True), "")
        with self.assertRaises(ValueError):
            calclock.normalize_ics_url("javascript:alert(1)")
        with self.assertRaises(ValueError):
            calclock.normalize_ics_url("")

    def test_import_ics_url_fetches_normalized_https_link(self) -> None:
        ics = """BEGIN:VCALENDAR
BEGIN:VEVENT
UID:essay-paste
SUMMARY:Essay pasted
DTSTART;VALUE=DATE:20260904
END:VEVENT
END:VCALENDAR
"""
        resp = mock.MagicMock()
        resp.read.return_value = ics.encode("utf-8")
        cm = mock.MagicMock()
        cm.__enter__.return_value = resp
        cm.__exit__.return_value = False
        with mock.patch.object(calclock, "urlopen", return_value=cm) as opener:
            result = calclock.import_ics_url("<webcal://cal.example.edu/class.ics>")
        self.assertGreaterEqual(result["created"], 1)
        req = opener.call_args[0][0]
        self.assertEqual(req.full_url, "https://cal.example.edu/class.ics")
        self.assertEqual(calclock.load_settings()["ics_url"], "https://cal.example.edu/class.ics")

    def test_rename_and_move_lecture(self) -> None:
        event = calclock.create_calendar_event(
            "CHEM 109",
            "2026-09-07T09:30:00",
            "2026-09-07T10:20:00",
            weekdays=[0],
        )
        updated = calclock.update_calendar_event(
            event["id"],
            "CHEM 109 lecture",
            "2026-09-07T14:00:00",
            "2026-09-07T14:50:00",
            [0, 2],
        )
        self.assertEqual(updated["title"], "CHEM 109 lecture")
        self.assertEqual(updated["start_at"], "2026-09-07T14:00:00")
        self.assertEqual(updated["recurrence"]["weekdays"], [0, 2])

    def test_drag_recurring_lecture_swaps_weekday(self) -> None:
        event = calclock.create_calendar_event(
            "Lab",
            "2026-09-07T13:00:00",
            "2026-09-07T15:00:00",
            weekdays=[0],
        )
        moved = calclock.update_calendar_event(
            event["id"],
            "",
            "2026-09-08T16:00:00",
            "2026-09-08T18:00:00",
            None,
            "2026-09-07",
        )
        self.assertEqual(moved["recurrence"]["weekdays"], [1])
        self.assertEqual(moved["start_at"][11:19], "16:00:00")
        self.assertTrue(moved["start_at"].startswith("2026-09-07"))

    def test_rename_move_and_park_work_block(self) -> None:
        item = work.create_work_item("Study essay", estimate_minutes=60)
        placed = calclock.schedule_work_at(
            item["id"],
            "2026-09-08T11:00:00",
            "2026-09-08T12:00:00",
        )
        block = placed["block"]
        self.assertEqual(block["start_at"], "2026-09-08T11:00:00")
        self.assertEqual(placed["item"]["scheduled_date"], "2026-09-08")
        renamed = calclock.update_schedule_block(
            block["id"],
            "Study essay 2",
            "2026-09-09T15:00:00",
            "2026-09-09T16:30:00",
            "locked",
        )
        self.assertEqual(renamed["title"], "Study essay 2")
        self.assertEqual(renamed["local_date"], "2026-09-09")
        self.assertEqual(renamed["status"], "locked")
        self.assertEqual(work.get_work_items_by_ids([item["id"]])[0]["title"], "Study essay 2")
        self.assertEqual(work.get_work_items_by_ids([item["id"]])[0]["scheduled_date"], "2026-09-09")
        calclock.park_schedule_block(block["id"])
        parked = work.get_work_items_by_ids([item["id"]])[0]
        self.assertIsNone(parked["scheduled_date"])
        week = calclock.get_week("2026-09-07")
        self.assertEqual([b for day in week["days"] for b in day["blocks"]], [])

    def test_delete_locked_block_requires_force(self) -> None:
        item = work.create_work_item("Problem set", estimate_minutes=50)
        block = calclock.schedule_work_at(item["id"], "2026-09-08T09:00:00", "2026-09-08T09:50:00")["block"]
        calclock.set_block_status(block["id"], "locked")
        with self.assertRaises(ValueError):
            calclock.delete_schedule_block(block["id"])
        calclock.delete_schedule_block(block["id"], True)
        week = calclock.get_week("2026-09-07")
        self.assertEqual([b for day in week["days"] for b in day["blocks"]], [])

    def test_awake_window_defaults_to_0530_2130(self) -> None:
        settings = calclock.load_settings()
        self.assertEqual(settings["day_start"], "05:30")
        self.assertEqual(settings["day_end"], "21:30")

    def test_awake_window_accepts_military_hhmm(self) -> None:
        saved = calclock.save_calendar_settings({"day_start": "0530", "day_end": "2130"})
        self.assertEqual(saved["day_start"], "05:30")
        self.assertEqual(saved["day_end"], "21:30")
        again = calclock.save_calendar_settings({"day_start": "5:30", "day_end": "21:30"})
        self.assertEqual(again["day_start"], "05:30")
        with self.assertRaises(ValueError):
            calclock.save_calendar_settings({"day_start": "25:00"})

    def test_packer_stays_inside_awake_window(self) -> None:
        calclock.save_calendar_settings({"day_start": "05:30", "day_end": "21:30"})
        monday = date(2026, 9, 7)
        work.create_work_item(
            "Study",
            due_at="2026-09-11T23:59:00",
            estimate_minutes=90,
        )
        week = self._fill(monday.isoformat(), datetime(2026, 9, 7, 6, 0, 0))
        blocks = [b for day in week["days"] for b in day["blocks"] if b["kind"] == "work"]
        self.assertTrue(blocks)
        for block in blocks:
            start = calclock.parse_datetime(block["start_at"])
            end = calclock.parse_datetime(block["end_at"])
            self.assertGreaterEqual(start.hour * 60 + start.minute, 5 * 60 + 30)
            self.assertLessEqual(end.hour * 60 + end.minute, 21 * 60 + 30)

    def test_import_pasted_calendar_accepts_ics_blob(self) -> None:
        ics = """BEGIN:VCALENDAR
BEGIN:VEVENT
UID:paste-blob
SUMMARY:Quiz pasted
DTSTART;VALUE=DATE:20260904
END:VEVENT
END:VCALENDAR
"""
        result = calclock.import_pasted_calendar(ics)
        self.assertTrue(result["ok"])
        self.assertEqual(result["created"], 1)
        titles = [row["title"] for row in work.list_all_work_items()]
        self.assertIn("Quiz pasted", titles)

    def test_import_pasted_calendar_treats_url_as_ics_url(self) -> None:
        with mock.patch.object(
            calclock,
            "import_ics_url",
            return_value={"ok": True, "created": 2, "updated": 0},
        ) as mocked:
            result = calclock.import_pasted_calendar("https://canvas.example/calendar.ics")
        mocked.assert_called_once_with("https://canvas.example/calendar.ics")
        self.assertEqual(result["created"], 2)

    def test_default_packer_leaves_nights_empty(self) -> None:
        monday = date(2026, 9, 7)
        work.create_work_item(
            "Study",
            due_at="2026-09-11T23:59:00",
            estimate_minutes=90,
        )
        week = self._fill(monday.isoformat(), datetime(2026, 9, 7, 6, 0, 0))
        blocks = [b for day in week["days"] for b in day["blocks"] if b["kind"] == "work"]
        self.assertTrue(blocks)
        for block in blocks:
            start = calclock.parse_datetime(block["start_at"])
            end = calclock.parse_datetime(block["end_at"])
            self.assertGreaterEqual(start.hour * 60 + start.minute, 5 * 60 + 30)
            self.assertLessEqual(end.hour * 60 + end.minute, 21 * 60 + 30)

    def test_unplaced_subtracts_placed_minutes_without_per_item_queries(self) -> None:
        item = work.create_work_item(
            "Study",
            due_at="2026-09-11T23:59:00",
            estimate_minutes=90,
        )
        calclock.add_block(
            title="Study",
            start=datetime(2026, 9, 8, 9, 0, 0),
            end=datetime(2026, 9, 8, 9, 50, 0),
            work_item_id=item["id"],
            kind="work",
        )
        with mock.patch.object(calclock, "blocks_for_item", side_effect=AssertionError("per-item query")):
            rows = calclock.unplaced_work()
        match = next(row for row in rows if row["id"] == item["id"])
        self.assertEqual(match["remaining_minutes"], 40)

    def test_calendar_payload_caps_unplaced_and_skips_per_todo_block_queries(self) -> None:
        extra = 25
        count = calclock.UNPLACED_UI_LIMIT + extra
        for i in range(count):
            work.create_work_item(
                f"Quiz {i}",
                due_at="2026-12-01T23:59:00",
                estimate_minutes=60,
            )
        with mock.patch.object(calclock, "blocks_for_item", side_effect=AssertionError("per-item query")):
            month = calclock.get_month(2026, 9)
            week = calclock.get_week("2026-09-07")
        self.assertEqual(month["unplaced_total"], count)
        self.assertEqual(len(month["unplaced"]), calclock.UNPLACED_UI_LIMIT)
        self.assertEqual(week["unplaced_total"], count)
        self.assertEqual(len(week["unplaced"]), calclock.UNPLACED_UI_LIMIT)

    def test_day_agenda_does_not_scan_unplaced_work(self) -> None:
        with mock.patch.object(calclock, "unplaced_work", side_effect=AssertionError("unplaced on agenda")):
            agenda = calclock.get_day_agenda("2026-09-08")
        self.assertEqual(agenda["local_date"], "2026-09-08")
        self.assertEqual(agenda["unplaced"], [])


if __name__ == "__main__":
    unittest.main()
