"""Focus, countdown, and habit glance widgets."""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import glance


class GlanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.env = mock.patch.dict(os.environ, {"KOSISTENZ_DATA_DIR": str(self.root)})
        self.env.start()
        self.today = mock.patch.object(glance, "_today", return_value=date(2026, 9, 1))
        self.today.start()

    def tearDown(self) -> None:
        self.today.stop()
        self.env.stop()
        self.tmp.cleanup()

    def test_focus_clears_on_a_new_day(self) -> None:
        glance.set_daily_focus("  Finish the lab report  ")
        packed = glance.get_daily_focus()
        self.assertEqual(packed["text"], "Finish the lab report")
        self.assertEqual(packed["date"], "2026-09-01")
        self.assertFalse(packed["kept"])
        kept = glance.keep_daily_focus(True)
        self.assertTrue(kept["kept"])
        glance.set_daily_focus("Finish the lab report")
        self.assertFalse(glance.get_daily_focus()["kept"])
        with mock.patch.object(glance, "_today", return_value=date(2026, 9, 2)):
            next_day = glance.get_daily_focus()
            self.assertEqual(next_day["text"], "")
            self.assertEqual(next_day["date"], "2026-09-02")
            self.assertFalse(next_day["kept"])
            with self.assertRaises(ValueError):
                glance.keep_daily_focus(True)

    def test_countdown_phrases_and_order(self) -> None:
        glance.add_home_countdown("Trip", "2026-09-15")
        glance.add_home_countdown("Quiz", "2026-09-01")
        rows = glance.get_countdowns()
        self.assertEqual([row["title"] for row in rows], ["Quiz", "Trip"])
        self.assertEqual(rows[0]["phrase"], "today")
        self.assertEqual(rows[1]["phrase"], "in 14 days")
        glance.remove_home_countdown(rows[0]["id"])
        left = glance.get_countdowns()
        self.assertEqual([row["title"] for row in left], ["Trip"])

    def test_countdown_rejects_blank(self) -> None:
        with self.assertRaises(ValueError):
            glance.add_home_countdown("", "2026-09-15")
        with self.assertRaises(ValueError):
            glance.add_home_countdown("Trip", "nope")

    def test_habits_toggle_per_day(self) -> None:
        glance.add_home_habit("Water")
        glance.add_home_habit("Stretch")
        state = glance.get_habits()
        self.assertEqual(state["total"], 2)
        self.assertEqual(state["done"], 0)
        water = state["habits"][0]
        state = glance.toggle_home_habit(water["id"])
        self.assertTrue(state["habits"][0]["done"])
        self.assertEqual(state["done"], 1)
        with mock.patch.object(glance, "_today", return_value=date(2026, 9, 2)):
            next_day = glance.get_habits()
        self.assertFalse(next_day["habits"][0]["done"])
        glance.remove_home_habit(water["id"])
        left = glance.get_habits()
        self.assertEqual([row["title"] for row in left["habits"]], ["Stretch"])

    def test_habit_name_is_required(self) -> None:
        with self.assertRaises(ValueError):
            glance.add_home_habit("   ")
