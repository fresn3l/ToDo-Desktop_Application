"""SQLite connections must close. Python's ``with conn`` does not."""

from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import daily_checklist
import day_brief
import db
import tap_counters
import work
import workouts


def _closed_error(conn: sqlite3.Connection) -> None:
    conn.execute("SELECT 1")


def _open_fd_count(path: Path) -> int:
    """Count descriptors whose target is this sqlite file (Linux)."""
    fd_dir = Path("/proc/self/fd")
    if not fd_dir.is_dir():
        return -1
    targets = {str(path), str(path) + "-wal", str(path) + "-shm"}
    try:
        resolved = path.resolve()
        targets.update({str(resolved), str(resolved) + "-wal", str(resolved) + "-shm"})
    except OSError:
        pass
    count = 0
    for name in os.listdir(fd_dir):
        try:
            dest = os.readlink(fd_dir / name)
        except OSError:
            continue
        if dest in targets:
            count += 1
    return count


class SqliteConnectTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_stdlib_connection_context_does_not_close(self) -> None:
        path = self.dir / "stdlib.sqlite"
        conn = sqlite3.connect(str(path))
        with conn:
            conn.execute("CREATE TABLE t (id INTEGER)")
        conn.execute("INSERT INTO t VALUES (1)")
        conn.commit()
        conn.close()

    def test_helper_closes_and_commits(self) -> None:
        path = self.dir / "ours.sqlite"
        with db.sqlite_connect(path) as conn:
            conn.execute("CREATE TABLE t (id INTEGER)")
            conn.execute("INSERT INTO t VALUES (1)")
            held = conn
        with self.assertRaises(sqlite3.ProgrammingError):
            _closed_error(held)
        with db.sqlite_connect(path) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM t").fetchone()[0], 1)
        self.assertIn(_open_fd_count(path), (-1, 0))

    def test_helper_closes_after_error(self) -> None:
        path = self.dir / "fail.sqlite"
        with self.assertRaises(RuntimeError):
            with db.sqlite_connect(path) as conn:
                conn.execute("CREATE TABLE t (id INTEGER)")
                held = conn
                raise RuntimeError("boom")
        with self.assertRaises(sqlite3.ProgrammingError):
            _closed_error(held)
        self.assertIn(_open_fd_count(path), (-1, 0))


class StoreConnectCloseTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self._tmp.name)
        self.patches = [
            mock.patch.object(work, "_data_dir", lambda: self.data_dir),
            mock.patch.object(workouts, "_data_dir", lambda: self.data_dir),
            mock.patch.object(daily_checklist, "data_directory", lambda: self.data_dir),
            mock.patch.object(day_brief, "_db_path", lambda: self.data_dir / "day_briefs.sqlite"),
            mock.patch.object(tap_counters, "_db_path", lambda: self.data_dir / "tap_counters.sqlite"),
        ]
        for patcher in self.patches:
            patcher.start()

    def tearDown(self) -> None:
        for patcher in self.patches:
            patcher.stop()
        self._tmp.cleanup()

    def test_work_connect_closes(self) -> None:
        with work._connect() as conn:
            held = conn
            conn.execute("SELECT COUNT(*) FROM work_items")
        with self.assertRaises(sqlite3.ProgrammingError):
            _closed_error(held)

    def test_repeated_home_reads_do_not_leave_sqlite_open(self) -> None:
        today = date.today().isoformat()
        work.create_work_item("Leak check", scheduled_date=today)
        workouts.save_body_weight(today, 180)
        for _ in range(40):
            work.get_work_board(today)
            workouts.get_workout_day(today)
            daily_checklist.fetch_submissions(limit=5)
        work_db = work.get_work_db_path()
        workout_db = workouts.get_workouts_db_path()
        checklist_db = daily_checklist.get_daily_checklist_db_path()
        for path in (work_db, workout_db, checklist_db):
            self.assertIn(_open_fd_count(path), (-1, 0), msg=path.name)
        board = work.get_work_board(today)
        self.assertIn("Leak check", [row["title"] for row in board["today"]])
        day = workouts.get_workout_day(today)
        self.assertEqual(day["body_weight"], 180)

    def test_day_brief_and_counters_connect_close(self) -> None:
        with day_brief._connect() as conn:
            held_brief = conn
            conn.execute("SELECT COUNT(*) FROM briefs")
        with tap_counters._connect() as conn:
            held_counters = conn
            conn.execute("SELECT COUNT(*) FROM counters")
        with self.assertRaises(sqlite3.ProgrammingError):
            _closed_error(held_brief)
        with self.assertRaises(sqlite3.ProgrammingError):
            _closed_error(held_counters)
