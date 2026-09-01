"""Currently reading book, pages today, and reading journal."""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest import mock

import journal
import reading


class ReadingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"KOSISTENZ_DATA_DIR": self.tmp.name})
        self.env.start()

    def tearDown(self) -> None:
        self.env.stop()
        self.tmp.cleanup()

    def test_book_and_pages_today(self) -> None:
        reading.set_reading_book("The Dispossessed", 40)
        payload = reading.add_reading_pages(5)
        self.assertEqual(payload["title"], "The Dispossessed")
        self.assertEqual(payload["page"], 45)
        self.assertEqual(payload["pages_today"], 5)
        payload = reading.add_reading_pages(10)
        self.assertEqual(payload["page"], 55)
        self.assertEqual(payload["pages_today"], 15)

    def test_pages_today_reset_on_new_day(self) -> None:
        reading.set_reading_book("Dune", 10)
        with mock.patch.object(reading, "_today") as today:
            from datetime import date

            today.return_value = date(2026, 9, 1)
            reading.add_reading_pages(3)
            self.assertEqual(reading.get_reading()["pages_today"], 3)
            today.return_value = date(2026, 9, 2)
            payload = reading.get_reading()
            self.assertEqual(payload["pages_today"], 0)
            self.assertEqual(payload["page"], 13)

    def test_reading_journal_is_separate_kind(self) -> None:
        reading.set_reading_book("Dune", 12)
        result = reading.save_reading_journal("Power is a trap; desert is the teacher.")
        self.assertEqual(result["entry"]["kind"], "reading")
        self.assertEqual(result["entry"]["brief"]["book"], "Dune")
        entries = journal.get_all_entries()
        self.assertEqual(entries[0]["kind"], "reading")
        self.assertIn("desert", entries[0]["content"])
        with self.assertRaises(ValueError):
            reading.save_reading_journal("  ")
        reading.set_reading_book("", 0)
        with self.assertRaises(ValueError):
            reading.add_reading_pages(1)


if __name__ == "__main__":
    unittest.main()
