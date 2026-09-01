"""Pinned countdown dates."""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import countdown


class CountdownTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"KOSISTENZ_DATA_DIR": self.tmp.name})
        self.env.start()

    def tearDown(self) -> None:
        self.env.stop()
        self.tmp.cleanup()

    def test_future_date_counts_days_remaining(self) -> None:
        today = date(2026, 9, 1)
        with mock.patch.object(countdown, "_today", return_value=today):
            payload = countdown.add_countdown("Trip", "2026-09-11", False)
        item = payload["items"][0]
        self.assertEqual(item["days"], 10)
        self.assertEqual(item["label"], "10 days")
        self.assertEqual(payload["next"]["title"], "Trip")

    def test_past_non_yearly_is_days_ago(self) -> None:
        today = date(2026, 9, 1)
        with mock.patch.object(countdown, "_today", return_value=today):
            payload = countdown.add_countdown("Deadline", "2026-08-28", False)
        self.assertEqual(payload["items"][0]["days"], -4)
        self.assertEqual(payload["items"][0]["label"], "4 days ago")

    def test_yearly_birthday_rolls_to_next_year(self) -> None:
        today = date(2026, 9, 1)
        with mock.patch.object(countdown, "_today", return_value=today):
            payload = countdown.add_countdown("Ada", "1990-03-10", True)
        item = payload["items"][0]
        self.assertEqual(item["next_date"], "2027-03-10")
        self.assertTrue(item["yearly"])
        self.assertGreater(item["days"], 0)

    def test_today_is_zero_days(self) -> None:
        today = date(2026, 9, 1)
        with mock.patch.object(countdown, "_today", return_value=today):
            payload = countdown.add_countdown("Launch", "2026-09-01", False)
        self.assertEqual(payload["items"][0]["days"], 0)
        self.assertEqual(payload["items"][0]["label"], "today")

    def test_remove_and_persist(self) -> None:
        countdown.add_countdown("Trip", "2026-12-01", False)
        item_id = countdown.get_countdowns()["items"][0]["id"]
        countdown.remove_countdown(item_id)
        self.assertEqual(countdown.get_countdowns()["items"], [])
        self.assertTrue((Path(self.tmp.name) / "countdowns.json").exists())


if __name__ == "__main__":
    unittest.main()
