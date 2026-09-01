"""Word of the day pick, persistence, and evening-check-in interpolation."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import daily_checklist
import home_layout
import word_of_the_day
import work


class WordOfTheDayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.env = mock.patch.dict(os.environ, {"KOSISTENZ_DATA_DIR": str(self.root)})
        self.env.start()
        self.today = mock.patch.object(word_of_the_day, "_today", return_value="2026-09-01")
        self.today.start()

    def tearDown(self) -> None:
        self.today.stop()
        self.env.stop()
        self.tmp.cleanup()

    def test_catalog_has_german_and_english(self) -> None:
        langs = {row["language"] for row in word_of_the_day.WORDS}
        self.assertEqual(langs, {"de", "en"})
        ids = [row["id"] for row in word_of_the_day.WORDS]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(word_of_the_day.WORDS), 40)
        for row in word_of_the_day.WORDS:
            self.assertTrue(row["word"])
            self.assertTrue(row["meaning"])
            self.assertIn(row["language"], ("de", "en"))

    def test_pick_is_stable_for_a_date(self) -> None:
        a = word_of_the_day.pick_word("2026-09-01", [])
        b = word_of_the_day.pick_word("2026-09-01", [])
        self.assertEqual(a["id"], b["id"])
        other = word_of_the_day.pick_word("2026-09-02", [])
        self.assertNotEqual(a["id"], other["id"])

    def test_skips_recent_ids(self) -> None:
        first = word_of_the_day.pick_word("2026-09-01", [])
        second = word_of_the_day.pick_word("2026-09-01", [first["id"]])
        self.assertNotEqual(first["id"], second["id"])

    def test_today_word_stays_put(self) -> None:
        first = word_of_the_day.ensure_today_word()
        again = word_of_the_day.ensure_today_word()
        self.assertEqual(first["id"], again["id"])
        self.assertEqual(first["date"], "2026-09-01")
        self.assertTrue((self.root / "word_of_the_day.json").exists())
        if first["article"]:
            self.assertEqual(first["display"], f"{first['article']} {first['word']}")
        else:
            self.assertEqual(first["display"], first["word"])

    def test_fill_text_and_evening_flow(self) -> None:
        word = {
            "word": "Fernweh",
            "display": "das Fernweh",
            "meaning": "a longing to be far away",
            "language_label": "German",
            "example": "",
            "article": "das",
            "pos": "noun",
        }
        text = word_of_the_day.fill_text(
            "Today’s word is {display} ({language}): {meaning}.",
            word,
        )
        self.assertEqual(
            text,
            "Today’s word is das Fernweh (German): a longing to be far away.",
        )
        flow = json.loads((Path(__file__).resolve().parents[1] / "checklists" / "evening.json").read_text(encoding="utf-8"))
        self.assertIn("word_use", flow["nodes"])
        self.assertEqual(flow["nodes"]["journal_reflect"]["next"], "word_use")
        self.assertEqual(flow["nodes"]["word_use"]["next"], "tomorrow_prep")
        decorated = word_of_the_day.decorate_flow(flow, word)
        question = decorated["nodes"]["word_use"]["question"]
        self.assertIn("das Fernweh", question)
        self.assertNotIn("{display}", question)
        self.assertNotIn("{word}", decorated["nodes"]["word_use"]["placeholder"])

    def test_get_daily_checklist_fills_evening_word(self) -> None:
        daily_checklist.set_selected_checklist_stem("evening")
        packed = word_of_the_day.ensure_today_word()
        flow = daily_checklist.get_daily_checklist()
        question = flow["nodes"]["word_use"]["question"]
        self.assertIn(packed["display"], question)
        self.assertIn(packed["meaning"], question)
        self.assertNotIn("{meaning}", question)

    def test_word_use_history_label(self) -> None:
        rows = daily_checklist.format_submission_answers(
            "evening",
            {"word_use": "I felt Fernweh on the train."},
        )
        self.assertEqual(rows[0]["label"], "Today’s word")
        self.assertEqual(rows[0]["value"], "I felt Fernweh on the train.")

    def test_home_catalog_includes_word_and_checklist(self) -> None:
        kinds = {row["kind"] for row in home_layout.catalog()}
        self.assertIn("word", kinds)
        self.assertIn("checklist", kinds)

    def test_submit_evening_plan_still_creates_tomorrow(self) -> None:
        parked = work.create_work_item("Call dentist")
        result = daily_checklist.submit_daily_checklist_response(
            "evening",
            3,
            {
                "word_use": "Feierabend came early.",
                "tomorrow_prep": {
                    "created_titles": ["Pay electricity bill"],
                    "assign_ids": [parked["id"]],
                },
            },
        )
        self.assertEqual(result["checklist_id"], "evening")
        self.assertIn("Feierabend", result["answers"]["word_use"])
        titles = {row["title"] for row in work.list_work_for_date(result["local_date"])}
        # apply_evening_plan schedules for tomorrow, not today
        from datetime import date, timedelta

        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        titles = {row["title"] for row in work.list_work_for_date(tomorrow)}
        self.assertEqual(titles, {"Pay electricity bill", "Call dentist"})


if __name__ == "__main__":
    unittest.main()
