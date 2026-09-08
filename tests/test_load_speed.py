"""Read-path speed: one board fetch, one event expand, deferred snapshot side effects."""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest import mock

import calclock
import insights
import journal
import work


class LoadSpeedTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.env = mock.patch.dict(os.environ, {"KOSISTENZ_DATA_DIR": str(self.root)})
        self.env.start()
        self.data = mock.patch.object(work, "_data_dir", lambda: self.root)
        self.data.start()
        self.today = mock.patch.object(work, "_today", return_value=date(2026, 9, 8))
        self.today.start()
        calclock.reset_purge_cache()
        work.invalidate_work_board_cache()
        work.cancel_heavy_snapshot_side_effects()

    def tearDown(self) -> None:
        work.cancel_heavy_snapshot_side_effects()
        self.today.stop()
        self.data.stop()
        self.env.stop()
        self.tmp.cleanup()

    def test_ensure_occurrences_skips_snapshot_when_nothing_is_created(self) -> None:
        work.create_work_item("One-off", scheduled_date="2026-09-08")
        with mock.patch.object(work, "_write_widget_snapshot") as snap:
            created = work.ensure_occurrences("2026-09-08")
        self.assertEqual(created, 0)
        snap.assert_not_called()

    def test_work_board_reuses_overdue_and_backlog_lists(self) -> None:
        work.create_work_item("Today", scheduled_date="2026-09-08")
        work.create_work_item("Later", scheduled_date="2026-09-10")
        work.create_work_item("Parked")
        work.invalidate_work_board_cache()
        with (
            mock.patch.object(work, "list_overdue_work", wraps=work.list_overdue_work) as overdue,
            mock.patch.object(work, "list_backlog", wraps=work.list_backlog) as backlog,
            mock.patch.object(work, "list_work_for_date", wraps=work.list_work_for_date) as listed,
        ):
            board = work.get_work_board("2026-09-08")
        self.assertEqual(overdue.call_count, 1)
        self.assertEqual(backlog.call_count, 1)
        listed.assert_not_called()
        self.assertEqual([row["title"] for row in board["today"]], ["Today"])
        self.assertEqual([row["title"] for row in board["upcoming"]], ["Later"])
        self.assertEqual([row["title"] for row in board["backlog"]], ["Parked"])

    def test_work_board_cache_collapses_home_double_fetch(self) -> None:
        work.create_work_item("Today", scheduled_date="2026-09-08")
        work.invalidate_work_board_cache()
        first = work.get_work_board("2026-09-08")
        with mock.patch.object(work, "_list_work_for_dates", side_effect=AssertionError("uncached")):
            second = work.get_work_board("2026-09-08")
        self.assertEqual(first["today"][0]["title"], "Today")
        self.assertEqual(second["today"][0]["title"], "Today")

    def test_widget_snapshot_does_not_export_inline(self) -> None:
        with (
            mock.patch("icloud_sync.export_if_enabled", side_effect=AssertionError("export")) as export,
            mock.patch("cluny_snapshot.refresh_life_snapshot_safe", side_effect=AssertionError("cluny")),
        ):
            snap = work._write_widget_snapshot()
        self.assertEqual(snap["date"], "2026-09-08")
        export.assert_not_called()

    def test_get_week_expands_events_once_and_purges_once(self) -> None:
        calclock.create_calendar_event(
            "CHEM 109",
            "2026-09-08T09:30:00",
            "2026-09-08T10:20:00",
            weekdays=[1],
        )
        with (
            mock.patch.object(calclock, "expand_hard_events", wraps=calclock.expand_hard_events) as expand,
            mock.patch.object(calclock, "purge_stale_imports", wraps=calclock.purge_stale_imports) as purge,
        ):
            week = calclock.get_week("2026-09-07")
            again = calclock.get_week("2026-09-07")
            calclock.get_month(2026, 9)
        self.assertEqual(expand.call_count, 3)
        self.assertEqual(purge.call_count, 1)
        tuesday = next(day for day in week["days"] if day["date"] == "2026-09-08")
        self.assertEqual(tuesday["events"][0]["title"], "CHEM 109")
        self.assertEqual(week["today"]["items"][0]["title"], "CHEM 109")
        self.assertEqual(again["today"]["items"][0]["title"], "CHEM 109")

    def test_expand_skips_ancient_one_shot_events(self) -> None:
        calclock.create_calendar_event(
            "Old lecture",
            "2020-01-14T09:30:00",
            "2020-01-14T10:20:00",
        )
        calclock.create_calendar_event(
            "CHEM 109",
            "2026-09-08T09:30:00",
            "2026-09-08T10:20:00",
        )
        rows = calclock.expand_hard_events(date(2026, 9, 7), date(2026, 9, 13))
        self.assertEqual([row["title"] for row in rows], ["CHEM 109"])

    def test_day_agenda_does_not_rebuild_the_week(self) -> None:
        calclock.create_calendar_event(
            "CHEM 109",
            "2026-09-08T09:30:00",
            "2026-09-08T10:20:00",
        )
        with mock.patch.object(calclock, "get_week", side_effect=AssertionError("week")):
            agenda = calclock.get_day_agenda("2026-09-08")
        self.assertEqual(agenda["items"][0]["title"], "CHEM 109")
        self.assertEqual(agenda["unplaced"], [])

    def test_today_home_fetches_the_board_once(self) -> None:
        work.create_work_item("Write the paper", scheduled_date="2026-09-08")
        work.invalidate_work_board_cache()

        class FrozenDate(date):
            @classmethod
            def today(cls):
                return date(2026, 9, 8)

        with (
            mock.patch("insights.date", FrozenDate),
            mock.patch.object(work, "get_work_board", wraps=work.get_work_board) as board,
        ):
            home = insights.get_today_home()
        self.assertEqual(board.call_count, 1)
        self.assertEqual(home["today"][0]["title"], "Write the paper")

    def test_journal_entry_dates_do_not_parse_bodies(self) -> None:
        journal.save_journal_entry("Rode north.", 60, False, ["health"])
        with mock.patch("journal.json.load", side_effect=AssertionError("parsed")):
            days = journal.entry_dates(days=400)
        self.assertIn(date.today(), days)
        self.assertEqual(journal.count_entries_on(date.today()), 1)
