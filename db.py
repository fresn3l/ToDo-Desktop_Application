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
import threading

# journal_mode=WAL needs an exclusive lock. Home boot opens eight connections
# at once, and eight of those pragmas on a fresh file lose to each other with
# "database is locked". After the first success the file is already WAL.
_wal_ready: set[str] = set()
_wal_lock = threading.Lock()


@contextmanager
def sqlite_connect(path: Path | str, *, timeout: float = 5.0) -> Iterator[sqlite3.Connection]:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    key = str(path)
    conn = sqlite3.connect(str(path), timeout=timeout)
    try:
        conn.row_factory = sqlite3.Row
        with _wal_lock:
            if key not in _wal_ready:
                conn.execute("PRAGMA journal_mode=WAL").fetchone()
                _wal_ready.add(key)
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA foreign_keys=ON")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
