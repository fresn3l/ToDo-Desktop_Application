"""Morning brief and evening review snapshots, separate journal kinds."""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import date, timedelta
from unittest import mock

import day_brief
import insights
import journal
import work


class DayBriefTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.env_patch = mock.patch.dict(os.environ, {"KOSISTENZ_DATA_DIR": self.tmp.name})
        self.env_patch.start()

    def tearDown(self) -> None:
        self.env_patch.stop()
        self.tmp.cleanup()

    def test_morning_and_evening_journals_are_separate(self) -> None:
        today = work._today().isoformat()
        a = work.create_work_item("Essay", scheduled_date=today)
        b = work.create_work_item("Spanish", scheduled_date=today)
        work.create_work_item("Gym bag", scheduled_date=today)
        morning = day_brief.save_morning_brief("Finish the essay and a Spanish block.", [a["id"], b["id"]])
        self.assertEqual(morning["slot"], "morning")
        self.assertEqual(morning["morning"]["intention_text"], "Finish the essay and a Spanish block.")
        self.assertEqual(morning["morning"]["focus_work_ids"], [a["id"], b["id"]])
        evening = day_brief.save_evening_review("Essay done. Spanish slipped.")
        kinds = {entry["kind"]: entry["content"] for entry in journal.get_all_entries()}
        self.assertEqual(kinds["morning_brief"], "Finish the essay and a Spanish block.")
        self.assertEqual(kinds["evening_review"], "Essay done. Spanish slipped.")
        self.assertNotEqual(morning["morning"]["journal_id"], evening["evening"]["journal_id"])
        morning2 = day_brief.save_morning_brief("Still the essay.", [a["id"]])
        briefs = [entry for entry in journal.get_all_entries() if entry["kind"] == "morning_brief"]
        self.assertEqual(len(briefs), 1)
        self.assertEqual(briefs[0]["content"], "Still the essay.")
        self.assertEqual(morning2["morning"]["journal_id"], briefs[0]["id"])

    def test_empty_saves_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            day_brief.save_morning_brief("  ", [])
        with self.assertRaises(ValueError):
            day_brief.save_evening_review("")

    def test_evening_done_leftover_and_roll_to_tomorrow(self) -> None:
        today = work._today().isoformat()
        done = work.create_work_item("Done item", scheduled_date=today)
        leftover = work.create_work_item("Leftover item", scheduled_date=today)
        day_brief.save_morning_brief("Two things.", [done["id"], leftover["id"]])
        work.finish_work_item(done["id"])
        payload = day_brief.get_day_brief()
        done_ids = [row["id"] for row in payload["review"]["done"]]
        leftover_ids = [row["id"] for row in payload["review"]["leftover"]]
        self.assertIn(done["id"], done_ids)
        self.assertIn(leftover["id"], leftover_ids)
        rolled = day_brief.roll_brief_item_to_tomorrow(leftover["id"])
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        moved = work.get_work_items_by_ids([leftover["id"]])[0]
        self.assertEqual(moved["scheduled_date"], tomorrow)
        self.assertEqual([row["id"] for row in rolled["review"]["rolled"]], [leftover["id"]])
        self.assertNotIn(leftover["id"], [row["id"] for row in rolled["review"]["leftover"]])
        day_brief.save_evening_review("Rolled Spanish.")
        cap = insights.get_analytics(7)["capacity"]
        self.assertEqual(cap["days_planned"], 1)
        self.assertEqual(cap["focus_count"], 2)
        self.assertEqual(cap["done_count"], 1)
        self.assertEqual(cap["rolled_count"], 1)
        self.assertEqual(cap["completion_pct"], 50)

    def test_override_switches_slot(self) -> None:
        evening = day_brief.set_day_brief_override("evening")
        self.assertEqual(evening["slot"], "evening")
        self.assertEqual(evening["override_slot"], "evening")
        morning = day_brief.set_day_brief_override("morning")
        self.assertEqual(morning["slot"], "morning")


if __name__ == "__main__":
    unittest.main()
