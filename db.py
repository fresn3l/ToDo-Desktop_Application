"""SQLite helpers.

``sqlite3.Connection`` as a context manager commits or rolls back, but it does
**not** close the file. Kosistenz used to leak a descriptor on every
``with _connect() as conn`` (Home refresh, widget, menu bar). After a few
dozen Home ticks macOS hits the open-file limit (~256) and every later
``sqlite3.connect`` fails with ``unable to open database file``. Journal
``iterdir`` then fails with ``[Errno 24] Too many open files``.

Always enter this helper — it closes in ``finally``.
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
import sqlite3


@contextmanager
def sqlite_connect(path: Path | str, *, timeout: float = 5.0) -> Iterator[sqlite3.Connection]:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=timeout)
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL").fetchone()
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA foreign_keys=ON")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
