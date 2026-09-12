"""Cluny rate-goal voice: Sunday digest and below/above-target to-dos."""

from __future__ import annotations

import os
import re
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest import mock

import calclock
import cluny_ask
import cluny_voice
import goals
import work


CLOCK_RE = re.compile(r"\b\d{1,2}:\d{2}\b")


class ClunyVoiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.tmp.name)
        self.env = mock.patch.dict(os.environ, {"KOSISTENZ_DATA_DIR": self.tmp.name}, clear=False)
        self.env.start()
        self.today = mock.patch.object(work, "_today", return_value=date(2026, 9, 11))
        self.today.start()
        calclock.reset_purge_cache()

    def tearDown(self) -> None:
        self.today.stop()
        self.env.stop()
        self.tmp.cleanup()

    def _event(self, title: str, day: date, hour: int = 9, minutes: int = 60):
        start = datetime(day.year, day.month, day.day, hour, 0, 0)
        end = start + timedelta(minutes=minutes)
        return calclock.create_calendar_event(
            title,
            start.isoformat(timespec="seconds"),
            end.isoformat(timespec="seconds"),
        )

    def _reset_voice(self) -> None:
        cluny_ask._save_inbox({"pending": [], "closed": []})
        cluny_voice._save_state(cluny_voice._empty_state())

    def _seed_attendance(self, target: float = 80) -> dict:
        day = date(2026, 9, 10)
        attended = self._event("Review", day, hour=9)
        self._event("Planning", day, hour=11)
        calclock.set_bar_outcome(attended["id"], "attended", day.isoformat())
        calclock.rollover_missed_bars(date(2026, 9, 11), force=True)
        self._reset_voice()
        goal = goals.create_rate_goal("Show up", "attendance", target, 4)
        self._reset_voice()
        return goal

    def _assert_no_clock(self, row: dict) -> None:
        blob = " ".join(
            str(row.get(key) or "")
            for key in ("title", "message", "due")
        )
        self.assertIsNone(CLOCK_RE.search(blob), blob)
        self.assertNotIn("T", str(row.get("due") or ""))

    def test_sunday_digest_tells_and_proposes_a_dated_todo(self) -> None:
        goal = self._seed_attendance(80)
        sunday = date(2026, 9, 13)
        with mock.patch.object(work, "_today", return_value=sunday):
            result = cluny_voice.refresh_rate_voice(sunday)
        self.assertTrue(result["digest"])
        self.assertEqual(result["added"], 1)
        inbox = cluny_ask.get_cluny_inbox()
        row = inbox["pending"][0]
        self.assertEqual(row["kind"], "rate_voice")
        self.assertEqual(row["reason"], "sunday_digest")
        self.assertEqual(row["goal_id"], goal["id"])
        self.assertIn("below your 80% target", row["message"])
        self.assertIn("Show up", row["title"])
        self.assertEqual(row["due"], "2026-09-13")
        self._assert_no_clock(row)
        again = cluny_voice.refresh_rate_voice(sunday)
        self.assertFalse(again["digest"])
        self.assertEqual(again["added"], 0)
        self.assertEqual(cluny_ask.get_cluny_inbox()["pending_count"], 1)

    def test_weekday_fires_when_a_rate_goes_below_then_above(self) -> None:
        goal = self._seed_attendance(80)
        friday = date(2026, 9, 11)
        first = cluny_voice.refresh_rate_voice(friday)
        self.assertEqual(first["added"], 1)
        self.assertEqual(first["fires"][0]["reason"], "below")
        row = cluny_ask.get_cluny_inbox()["pending"][0]
        self.assertIn("dropped below", row["message"])
        self.assertIn("Protect more attended time", row["title"])
        self._assert_no_clock(row)
        self.assertEqual(cluny_voice.refresh_rate_voice(friday)["added"], 0)

        for hour, title in ((15, "Follow-up"), (16, "Wrap"), (17, "Close"), (18, "Done")):
            extra = self._event(title, date(2026, 9, 10), hour=hour)
            calclock.set_bar_outcome(extra["id"], "attended", "2026-09-10")
        pending = cluny_ask.get_cluny_inbox()["pending"]
        self.assertEqual(len(pending), 2)
        self.assertEqual(pending[-1]["reason"], "above")
        self.assertEqual(pending[-1]["goal_id"], goal["id"])
        self.assertIn("above your 80% target", pending[-1]["message"])
        self.assertEqual(cluny_voice.refresh_rate_voice(friday)["added"], 0)

    def test_on_target_weekday_does_not_nag(self) -> None:
        self._seed_attendance(50)
        result = cluny_voice.refresh_rate_voice(date(2026, 9, 11))
        self.assertEqual(result["added"], 0)
        self.assertEqual(cluny_ask.get_cluny_inbox()["pending_count"], 0)

    def test_accept_lands_in_all_work_without_a_clock_time(self) -> None:
        self._seed_attendance(80)
        cluny_voice.refresh_rate_voice(date(2026, 9, 11))
        uid = cluny_ask.get_cluny_inbox()["pending"][0]["id"]
        result = cluny_ask.accept_cluny_proposal(uid)
        item = result["item"]
        self.assertEqual(item["source"], "cluny_proposal")
        self.assertIsNone(item["scheduled_date"])
        self.assertIsNone(item.get("start_at"))
        self.assertTrue(item["is_backlog"])
        self.assertEqual(item["due_at"], "2026-09-11T23:59:00")

    def test_hours_copy_uses_rate_fields_not_a_clock(self) -> None:
        day = date(2026, 9, 10)
        self._event("Deep work", day, hour=9, minutes=180)
        calclock.rollover_missed_bars(date(2026, 9, 11), force=True)
        self._reset_voice()
        goals.create_rate_goal("Deep work hours", "hours", 10, 4)
        self._reset_voice()
        result = cluny_voice.refresh_rate_voice(date(2026, 9, 11))
        self.assertEqual(result["added"], 1)
        row = cluny_ask.get_cluny_inbox()["pending"][0]
        self.assertIn("hours", row["message"].lower())
        self.assertIn("10 hours", row["message"])
        self.assertIn("4 weeks", row["message"])
        self.assertIn("Put more hours toward", row["title"])
        self._assert_no_clock(row)


if __name__ == "__main__":
    unittest.main()
