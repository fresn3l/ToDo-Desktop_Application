"""Execute, Aim, Close — Home's first page."""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import date, datetime, time, timedelta
from pathlib import Path
from unittest import mock

import execute
import glance
import work


class ExecuteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.tmp.name)
        self.env = mock.patch.dict(os.environ, {"KOSISTENZ_DATA_DIR": str(self.data_dir)})
        self.env.start()
        self.work_dir = mock.patch.object(work, "_data_dir", lambda: self.data_dir)
        self.work_dir.start()
        work.invalidate_work_board_cache()
        self.clock = datetime.combine(date.today(), time(9, 0))
        self.now = mock.patch.object(execute, "_now", side_effect=lambda: self.clock)
        self.now.start()
        self.glance_today = mock.patch.object(glance, "_today", side_effect=lambda: self.clock.date())
        self.glance_today.start()

    def tearDown(self) -> None:
        self.glance_today.stop()
        self.now.stop()
        work.cancel_heavy_snapshot_side_effects()
        self.work_dir.stop()
        self.env.stop()
        self.tmp.cleanup()

    def _advance(self, **delta) -> None:
        self.clock = self.clock + timedelta(**delta)

    def test_phase_follows_the_awake_start(self) -> None:
        day = date(2026, 9, 7)
        at = lambda h, m=0: datetime.combine(day, time(h, m))
        self.assertEqual(execute.day_phase(at(5, 30), "05:30")["name"], "hard")
        self.assertEqual(execute.day_phase(at(13, 29), "05:30")["name"], "hard")
        self.assertEqual(execute.day_phase(at(13, 30), "05:30")["name"], "easy")
        self.assertEqual(execute.day_phase(at(20, 30), "05:30")["name"], "wind_down")
        self.assertTrue(execute.day_phase(at(21, 0), "0530")["close"])
        self.assertEqual(execute.day_phase(at(4, 0), "05:30")["name"], "wind_down")

    def test_one_thing_prefers_pin_then_line_then_first_open_todo(self) -> None:
        today = work._today().isoformat()
        first = work.create_work_item("Answer email", scheduled_date=today)
        memo = work.create_work_item("Board memo", scheduled_date=today)
        with mock.patch.object(execute, "_clock_focus", return_value={"kind": "none"}):
            self.assertEqual(execute.get_execute_home()["one_thing"]["title"], "Answer email")
            execute.save_first_bout("After coffee, 70 minutes on the memo")
            self.assertEqual(execute.get_execute_home()["one_thing"]["kind"], "intention")
            pinned = execute.pin_execute_priority(memo["id"])
        self.assertEqual(pinned["one_thing"]["title"], "Board memo")
        self.assertIn(first["id"], [row["id"] for row in pinned["todos"]])

    def test_calendar_assignments_are_not_todos(self) -> None:
        today = work._today().isoformat()
        work.create_work_item("Mine", scheduled_date=today)
        with mock.patch.object(work, "get_work_board", return_value={
            "today": [
                {"id": "a", "title": "Mine", "status": "open", "source": "manual"},
                {"id": "b", "title": "Problem set 3", "status": "open", "source": "calendar"},
            ],
        }):
            titles = [row["title"] for row in execute.get_execute_home()["todos"]]
        self.assertEqual(titles, ["Mine"])

    def test_bout_walks_through_target_work_review_defocus_done(self) -> None:
        execute.save_execute_aim("Ship the memo series", 300)
        state = execute.start_execute_bout(45, True)
        self.assertEqual(state["bout"]["status"], "target")
        self.assertEqual(state["bout"]["remaining_seconds"], execute.VISUAL_SECONDS)
        self._advance(seconds=execute.VISUAL_SECONDS + 5)
        state = execute.get_execute_home()
        self.assertEqual(state["bout"]["status"], "work")
        self.assertEqual(state["bout"]["remaining_seconds"], 45 * 60 - 5)
        with self.assertRaises(ValueError):
            execute.start_execute_bout(70)
        self._advance(minutes=46)
        self.assertEqual(execute.get_execute_home()["bout"]["status"], "review")
        state = execute.set_execute_outcome(True, "")
        self.assertEqual(state["bout"]["status"], "defocus")
        self.assertEqual(state["aim"]["spent_minutes"], 45)
        self.assertEqual(state["bouts_done"], 1)
        self._advance(minutes=execute.DEFOCUS_MINUTES)
        state = execute.get_execute_home()
        self.assertEqual(state["bout"]["status"], "done")
        self.assertIn(state["bout"]["coin"], ("heads", "tails"))
        self.assertEqual(execute.start_execute_bout(70)["bout"]["status"], "target")

    def test_stopping_early_credits_only_the_minutes_worked(self) -> None:
        execute.save_execute_aim("Ship the memo series", 300)
        execute.start_execute_bout(90, False)
        self._advance(minutes=20)
        state = execute.set_execute_outcome(True, "")
        self.assertEqual(state["aim"]["spent_minutes"], 20)

    def test_still_open_keeps_the_resume_line_and_skips_the_reward(self) -> None:
        execute.start_execute_bout(70, False)
        state = execute.set_execute_outcome(False, "Section 3, second paragraph")
        self.assertEqual(state["bout"]["status"], "done")
        self.assertEqual(state["bout"]["coin"], "")
        self.assertEqual(state["first_bout"], "Section 3, second paragraph")
        self.assertEqual(state["aim"]["spent_minutes"], 0)

    def test_outcome_needs_a_bout(self) -> None:
        with self.assertRaises(ValueError):
            execute.set_execute_outcome(True)

    def test_aim_needs_minutes_and_runs_twelve_weeks(self) -> None:
        with self.assertRaises(ValueError):
            execute.save_execute_aim("Ship the memo series", 0)
        state = execute.save_execute_aim("Ship the memo series", 300)
        aim = state["aim"]
        self.assertTrue(aim["set"])
        self.assertEqual(aim["remaining_weeks"], 12)
        start = date.fromisoformat(aim["started_on"])
        self.assertEqual(date.fromisoformat(aim["end_date"]), start + timedelta(weeks=12))
        self.assertFalse(aim["ask_difficulty"])
        self.assertFalse(execute.save_execute_aim("", 0)["aim"]["set"])

    def test_difficulty_rates_last_week(self) -> None:
        with self.assertRaises(ValueError):
            execute.set_aim_difficulty("about_right")
        execute.save_execute_aim("Ship the memo series", 300)
        self._advance(days=8)
        state = execute.get_execute_home()
        self.assertTrue(state["aim"]["ask_difficulty"])
        self.assertEqual(state["aim"]["remaining_weeks"], 11)
        state = execute.set_aim_difficulty("too_easy")
        self.assertEqual(state["aim"]["difficulty"], "too_easy")
        with self.assertRaises(ValueError):
            execute.set_aim_difficulty("meh")

    def test_tomorrow_line_becomes_the_first_bout(self) -> None:
        execute.close_execute_day("Memo moved; email ate an hour.", "After coffee, 70 on section 4")
        self._advance(days=1)
        state = execute.get_execute_home()
        self.assertEqual(state["first_bout"], "After coffee, 70 on section 4")
        self.assertFalse(state["closed"])
        self.assertEqual(state["close_recap"], "")

    def test_close_parks_and_dates_leftovers(self) -> None:
        today = work._today().isoformat()
        park = work.create_work_item("Park me", scheduled_date=today)
        move = work.create_work_item("Move me", scheduled_date=today)
        tomorrow = (work._today() + timedelta(days=1)).isoformat()
        state = execute.close_execute_day("ok", "", [park["id"]], {move["id"]: tomorrow})
        self.assertTrue(state["closed"])
        self.assertEqual(state["leftovers"], [])
        rows = {row["id"]: row for row in work.get_work_items_by_ids([park["id"], move["id"]])}
        self.assertIsNone(rows[park["id"]]["scheduled_date"])
        self.assertEqual(rows[move["id"]]["scheduled_date"], tomorrow)
        with self.assertRaises(ValueError):
            execute.close_execute_day("ok", "", ["gone"], {})
        self.assertTrue(execute.get_execute_home()["closed"])

    def test_habits_cap_bucket_and_test_window(self) -> None:
        state = execute.add_execute_habit("Cold shower", "hard")
        self.assertEqual(state["habits"]["mode"], "form")
        self.assertEqual(state["habits"]["started_on"], self.clock.date().isoformat())
        habit = state["habits"]["habits"][0]
        self.assertEqual(habit["bucket"], "hard")
        state = execute.set_habit_bucket(habit["id"], "easy")
        self.assertEqual(state["habits"]["habits"][0]["bucket"], "easy")
        self.assertEqual(glance.load_habits()["habits"][0]["bucket"], "easy")
        for name in ("Walk", "Read", "Stretch", "Journal", "No phone"):
            execute.add_execute_habit(name, "easy")
        with self.assertRaises(ValueError):
            execute.add_execute_habit("Seventh", "hard")
        ids = [row["id"] for row in execute.get_execute_home()["habits"]["habits"]]
        for hid in ids[:4]:
            state = execute.toggle_execute_habit(hid)
        self.assertTrue(state["habits"]["success"])
        execute.remove_execute_habit(ids[-1])
        self._advance(days=execute.HABIT_BLOCK_DAYS)
        state = execute.get_execute_home()
        self.assertEqual(state["habits"]["mode"], "test")
        self.assertFalse(state["habits"]["can_add"])
        with self.assertRaises(ValueError):
            execute.add_execute_habit("Sneak one in", "hard")
        self._advance(days=execute.HABIT_BLOCK_DAYS)
        self.assertEqual(execute.get_execute_home()["habits"]["mode"], "form")

    def test_micro_suck_needs_a_name(self) -> None:
        with self.assertRaises(ValueError):
            execute.toggle_micro_suck()
        execute.save_micro_suck("No phone until noon")
        self.assertTrue(execute.toggle_micro_suck()["micro_suck_done"])
        self.assertFalse(execute.save_micro_suck("")["micro_suck_done"])

    def test_reading_does_not_rewrite_the_file(self) -> None:
        execute.get_execute_home()
        path = self.data_dir / "execute.json"
        before = path.stat().st_mtime_ns
        os.utime(path, ns=(before - 10_000_000, before - 10_000_000))
        stamped = path.stat().st_mtime_ns
        execute.get_execute_home()
        self.assertEqual(path.stat().st_mtime_ns, stamped)


if __name__ == "__main__":
    unittest.main()
