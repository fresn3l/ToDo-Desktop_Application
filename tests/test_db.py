"""SQLite connections must close. Python's ``with conn`` does not."""

from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import db
import work


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


class ConnectCloseTests(unittest.TestCase):
    def test_context_closes_even_when_the_body_raises(self) -> None:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        path = Path(folder.name) / "fail.sqlite"
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
        self.patcher = mock.patch.object(work, "_data_dir", lambda: self.data_dir)
        self.patcher.start()

    def tearDown(self) -> None:
        self.patcher.stop()
        self._tmp.cleanup()

    def test_work_connect_closes(self) -> None:
        with work._connect() as conn:
            held = conn
            conn.execute("SELECT COUNT(*) FROM work_items")
        with self.assertRaises(sqlite3.ProgrammingError):
            _closed_error(held)

    def test_repeated_board_reads_do_not_leave_sqlite_open(self) -> None:
        today = date.today().isoformat()
        work.create_work_item("Leak check", scheduled_date=today)
        for _ in range(40):
            work.get_work_board(today)
        work_db = work.get_work_db_path()
        self.assertIn(_open_fd_count(work_db), (-1, 0))
        board = work.get_work_board(today)
        self.assertIn("Leak check", [row["title"] for row in board["today"]])
