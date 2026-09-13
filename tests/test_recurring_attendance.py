"""Attendance on a repeating event belongs to one day of it, not the whole series."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest import mock

import calclock
import icloud_sync
import work

ROOT = Path(__file__).resolve().parents[1]

MONDAY = date(2026, 9, 7)
WEEKDAYS = [0, 2, 4]


class RecurringMarkTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self._tmp.name)
        self.patcher = mock.patch.object(work, "_data_dir", lambda: self.data_dir)
        self.today = mock.patch.object(work, "_today", return_value=date(2026, 9, 28))
        self.patcher.start()
        self.today.start()
        calclock.reset_purge_cache()

    def tearDown(self) -> None:
        self.today.stop()
        self.patcher.stop()
        self._tmp.cleanup()

    def _series(self, title: str = "Standup", weekdays=None) -> dict:
        start = datetime(MONDAY.year, MONDAY.month, MONDAY.day, 9, 0, 0)
        return calclock.create_calendar_event(
            title,
            start.isoformat(timespec="seconds"),
            (start + timedelta(minutes=30)).isoformat(timespec="seconds"),
            WEEKDAYS if weekdays is None else weekdays,
        )

    def _statuses(self, days: int = 21) -> dict:
        rows = calclock.expand_hard_events(MONDAY, MONDAY + timedelta(days=days))
        return {row["occurrence_date"]: row["status"] for row in rows}

    def test_marking_one_day_leaves_the_rest_of_the_series_alone(self) -> None:
        event = self._series()
        day = (MONDAY + timedelta(days=14)).isoformat()
        calclock.set_bar_outcome(event["id"], "attended", day)
        statuses = self._statuses()
        self.assertEqual(statuses[day], "done")
        self.assertGreater(len(statuses), 1)
        others = {when: state for when, state in statuses.items() if when != day}
        self.assertNotIn("done", others.values())

    def test_a_repeating_event_will_not_take_a_mark_without_a_day(self) -> None:
        event = self._series()
        with self.assertRaises(ValueError):
            calclock.set_bar_outcome(event["id"], "attended", "")
        self.assertEqual(calclock.event_mark_map(), {})

    def test_a_series_wide_mark_is_refused_at_the_store(self) -> None:
        event = self._series()
        self.assertIsNone(calclock.upsert_event_mark(event["id"], "done"))
        self.assertEqual(calclock.event_mark_map(), {})

    def test_a_one_off_event_still_takes_a_mark_with_no_day(self) -> None:
        event = self._series(title="Board review", weekdays=[])
        self.assertIsNone(event["recurrence"])
        calclock.set_bar_outcome(event["id"], "attended", "")
        self.assertEqual(calclock.event_mark_map(), {event["id"]: "done"})
        self.assertEqual(self._statuses()[MONDAY.isoformat()], "done")

    def test_a_mark_left_over_from_an_older_build_is_cleared(self) -> None:
        series = self._series()
        one_off = self._series(title="Board review", weekdays=[])
        # Written the way older builds wrote them, before the key carried a day.
        with calclock._connect() as conn:
            conn.executemany(
                "INSERT INTO event_marks (id, status, updated_at) VALUES (?, 'done', ?)",
                [(series["id"], "2026-09-10T09:00:00"), (one_off["id"], "2026-09-10T09:00:00")],
            )
            conn.commit()
        # The series never reads as attended off that row, but it should not
        # linger either; it is the row that used to do the damage.
        self.assertEqual(set(self._statuses().values()), {"open", "done"})

        self.assertEqual(calclock.drop_series_wide_marks(), 1)
        self.assertEqual(calclock.event_mark_map(), {one_off["id"]: "done"})

    def test_editing_one_occurrence_keeps_the_earlier_ones(self) -> None:
        event = self._series()
        before = sorted(self._statuses())
        self.assertGreater(len(before), 6)

        edited = MONDAY + timedelta(days=14)
        calclock.update_calendar_event(
            event["id"],
            "Standup",
            f"{edited.isoformat()}T09:00:00",
            f"{edited.isoformat()}T09:30:00",
            WEEKDAYS,
            edited.isoformat(),
        )
        self.assertEqual(sorted(self._statuses()), before)

    def test_editing_one_occurrence_still_moves_the_clock_time(self) -> None:
        event = self._series()
        edited = MONDAY + timedelta(days=14)
        calclock.update_calendar_event(
            event["id"],
            "Standup",
            f"{edited.isoformat()}T11:00:00",
            f"{edited.isoformat()}T11:30:00",
            WEEKDAYS,
            edited.isoformat(),
        )
        rows = calclock.expand_hard_events(MONDAY, MONDAY + timedelta(days=21))
        self.assertTrue(all(row["start_at"].endswith("T11:00:00") for row in rows))

    def test_setting_weekdays_keeps_the_end_date_and_skipped_days(self) -> None:
        event = self._series()
        skipped = (MONDAY + timedelta(days=2)).isoformat()
        recurrence = {
            "kind": "weekly",
            "weekdays": WEEKDAYS,
            "until": (MONDAY + timedelta(days=30)).isoformat(),
            "exdates": [skipped],
        }
        with calclock._connect() as conn:
            conn.execute(
                "UPDATE calendar_events SET recurrence_json = ? WHERE id = ?",
                (json.dumps(recurrence), event["id"]),
            )
            conn.commit()

        updated = calclock.update_calendar_event(
            event["id"],
            "Standup",
            f"{MONDAY.isoformat()}T09:00:00",
            f"{MONDAY.isoformat()}T09:30:00",
            [0, 2],
            MONDAY.isoformat(),
        )
        self.assertEqual(updated["recurrence"]["weekdays"], [0, 2])
        self.assertEqual(updated["recurrence"]["until"], recurrence["until"])
        self.assertEqual(updated["recurrence"]["exdates"], [skipped])


class RecurringPackTests(unittest.TestCase):
    """The sync pack has to carry the day, or the phone hands back a series-wide mark."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.env = mock.patch.dict(os.environ, {"KOSISTENZ_DATA_DIR": str(self.root)})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.addCleanup(self._tmp.cleanup)
        calclock.reset_purge_cache()

    def _series(self) -> dict:
        monday = calclock.monday_of(work._today())
        start = datetime(monday.year, monday.month, monday.day, 9, 0, 0)
        self.monday = monday
        return calclock.create_calendar_event(
            "Standup",
            start.isoformat(timespec="seconds"),
            (start + timedelta(minutes=30)).isoformat(timespec="seconds"),
            WEEKDAYS,
        )

    def test_pack_marks_name_the_day_not_the_series(self) -> None:
        event = self._series()
        calclock.set_bar_outcome(event["id"], "attended", (self.monday + timedelta(days=2)).isoformat())

        pack = icloud_sync._dump_calendar()
        keys = [str(row.get("id") or "") for row in pack["marks"]]
        self.assertTrue(keys)
        self.assertNotIn(event["id"], keys)
        self.assertIn(f"{event['id']}@{(self.monday + timedelta(days=2)).isoformat()}", keys)

    def test_pack_rows_carry_the_day_so_the_phone_can_key_a_check_off(self) -> None:
        self._series()
        pack = icloud_sync._dump_calendar()
        rows = [item for day in pack["days"] for item in day["events"]]
        self.assertTrue(rows)
        for row in rows:
            self.assertEqual(row["occurrence_date"], str(row["start_at"])[:10])

    def test_a_pack_round_trip_leaves_the_other_days_open(self) -> None:
        event = self._series()
        attended = (self.monday + timedelta(days=2)).isoformat()
        calclock.set_bar_outcome(event["id"], "attended", attended)

        pack = icloud_sync._dump_calendar()
        icloud_sync._apply_calendar_marks(pack)

        later = self.monday + timedelta(days=7)
        rows = calclock.expand_hard_events(later, later + timedelta(days=6))
        self.assertTrue(rows)
        self.assertEqual({row["status"] for row in rows}, {"open"})


class RecurringClientTests(unittest.TestCase):
    """The Mac editor and the iPhone both have to speak per-occurrence."""

    def test_the_editor_only_lights_days_the_series_actually_repeats_on(self) -> None:
        source = (ROOT / "web" / "js" / "calendar.js").read_text(encoding="utf-8")
        self.assertIn("setWeekdaySelection(rawDays);", source)
        # A one-off used to arrive with its own weekday lit, and Save made it weekly.
        self.assertNotIn("(d.getDay() + 6) % 7", source)

    def test_the_phone_files_a_check_off_under_the_day(self) -> None:
        pack = (ROOT / "ios" / "Kosistenz" / "SyncPack.swift").read_text(encoding="utf-8")
        self.assertIn("var occurrence_date: String?", pack)
        self.assertIn("var markKey: String", pack)
        self.assertIn('return "\\(base)@\\(day.prefix(10))"', pack)

        listing = (ROOT / "ios" / "Kosistenz" / "TodayList.swift").read_text(encoding="utf-8")
        self.assertIn("item.markKey", listing)
        self.assertNotIn("item.itemId ?? item.id", listing)

        actions = (ROOT / "ios" / "Kosistenz" / "PackActions.swift").read_text(encoding="utf-8")
        self.assertIn("events[eventIndex].markKey == id", actions)
        self.assertIn("blocks[blockIndex].markKey == id", actions)

        calendar = (ROOT / "ios" / "Kosistenz" / "PhoneCalendar.swift").read_text(encoding="utf-8")
        self.assertIn("occurrence_date: dayStamp.string(from: day)", calendar)


if __name__ == "__main__":
    unittest.main()
