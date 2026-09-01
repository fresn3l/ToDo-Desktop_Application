"""User-defined tap counters."""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest import mock

import tap_counters


class TapCounterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"KOSISTENZ_DATA_DIR": self.tmp.name})
        self.env.start()

    def tearDown(self) -> None:
        self.env.stop()
        self.tmp.cleanup()

    def test_named_counter_with_icon_and_target(self) -> None:
        payload = tap_counters.add_tap_counter("Water", "💧", 8)
        row = payload["counters"][0]
        self.assertEqual(row["name"], "Water")
        self.assertEqual(row["icon"], "💧")
        self.assertEqual(row["target"], 8)
        self.assertEqual(row["today"], 0)
        self.assertFalse(row["met"])

    def test_tap_and_undo_and_target(self) -> None:
        tap_counters.add_tap_counter("Coffee", "☕", 2)
        item_id = tap_counters.get_tap_counters()["counters"][0]["id"]
        tap_counters.tap_counter(item_id, 1)
        tap_counters.tap_counter(item_id, 1)
        row = tap_counters.get_tap_counters()["counters"][0]
        self.assertEqual(row["today"], 2)
        self.assertTrue(row["met"])
        tap_counters.tap_counter(item_id, -1)
        row = tap_counters.get_tap_counters()["counters"][0]
        self.assertEqual(row["today"], 1)
        self.assertFalse(row["met"])
        tap_counters.tap_counter(item_id, -5)
        self.assertEqual(tap_counters.get_tap_counters()["counters"][0]["today"], 0)

    def test_remove_and_empty_name_rejected(self) -> None:
        tap_counters.add_tap_counter("Smokes", "🚬", None)
        item_id = tap_counters.get_tap_counters()["counters"][0]["id"]
        tap_counters.remove_tap_counter(item_id)
        self.assertEqual(tap_counters.get_tap_counters()["counters"], [])
        with self.assertRaises(ValueError):
            tap_counters.add_tap_counter("  ", "💧", 1)


if __name__ == "__main__":
    unittest.main()
