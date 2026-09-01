"""User-defined tap counters — water, caffeine, or anything else."""

from __future__ import annotations

import sqlite3
import uuid
from contextlib import contextmanager
from datetime import date
from typing import Any, Dict, Iterator, List, Optional

import eel

from db import sqlite_connect
from paths import data_directory

MAX_COUNTERS = 12
MAX_NAME = 40
MAX_TARGET = 999
ICONS = (
    "💧",
    "☕",
    "🍵",
    "🥤",
    "🚬",
    "💊",
    "🍎",
    "🥗",
    "🚶",
    "🧘",
    "💪",
    "📖",
    "✍️",
    "😴",
    "🧠",
    "⭐",
)


def _today() -> date:
    return date.today()


def _db_path():
    return data_directory() / "tap_counters.sqlite"


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    with sqlite_connect(_db_path()) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS counters (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                icon TEXT NOT NULL,
                target INTEGER,
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS taps (
                counter_id TEXT NOT NULL,
                local_date TEXT NOT NULL,
                count INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (counter_id, local_date)
            )
            """
        )
        yield conn


def _clip_name(raw: Any) -> str:
    return str(raw or "").strip()[:MAX_NAME]


def _icon(raw: Any) -> str:
    text = str(raw or "").strip()
    if text in ICONS:
        return text
    # Allow a single emoji-like token the user typed, else default.
    if text and len(text) <= 8 and " " not in text:
        return text[:8]
    return "⭐"


def _target(raw: Any) -> Optional[int]:
    if raw is None or raw == "":
        return None
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return None
    if n <= 0:
        return None
    return min(n, MAX_TARGET)


def _payload(today: Optional[date] = None) -> Dict[str, Any]:
    today = today or _today()
    iso = today.isoformat()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM counters ORDER BY sort_order ASC, created_at ASC"
        ).fetchall()
        taps = {
            row["counter_id"]: int(row["count"] or 0)
            for row in conn.execute(
                "SELECT counter_id, count FROM taps WHERE local_date = ?",
                (iso,),
            ).fetchall()
        }
    counters = []
    for row in rows:
        count = taps.get(row["id"], 0)
        target = None if row["target"] is None else int(row["target"])
        counters.append(
            {
                "id": row["id"],
                "name": row["name"],
                "icon": row["icon"],
                "target": target,
                "today": count,
                "met": bool(target and count >= target),
            }
        )
    return {"counters": counters, "icons": list(ICONS), "today": iso}


@eel.expose
def get_tap_counters() -> Dict[str, Any]:
    return _payload()


@eel.expose
def add_tap_counter(name: str, icon: str = "", target: Any = None) -> Dict[str, Any]:
    clean = _clip_name(name)
    if not clean:
        raise ValueError("Name the counter")
    with _connect() as conn:
        n = conn.execute("SELECT COUNT(*) AS n FROM counters").fetchone()["n"]
        if int(n or 0) >= MAX_COUNTERS:
            raise ValueError("Too many counters")
        now = _today().isoformat()
        conn.execute(
            """
            INSERT INTO counters (id, name, icon, target, sort_order, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), clean, _icon(icon), _target(target), int(n or 0), now),
        )
        conn.commit()
    return _payload()


@eel.expose
def update_tap_counter(counter_id: str, name: str = "", icon: str = "", target: Any = None) -> Dict[str, Any]:
    key = str(counter_id or "").strip()
    if not key:
        raise ValueError("Counter is required")
    with _connect() as conn:
        row = conn.execute("SELECT * FROM counters WHERE id = ?", (key,)).fetchone()
        if row is None:
            raise ValueError("Counter not found")
        clean = _clip_name(name) or row["name"]
        glyph = _icon(icon) if icon else row["icon"]
        conn.execute(
            "UPDATE counters SET name = ?, icon = ?, target = ? WHERE id = ?",
            (clean, glyph, _target(target if target is not None else row["target"]), key),
        )
        conn.commit()
    return _payload()


@eel.expose
def remove_tap_counter(counter_id: str) -> Dict[str, Any]:
    key = str(counter_id or "").strip()
    with _connect() as conn:
        conn.execute("DELETE FROM taps WHERE counter_id = ?", (key,))
        conn.execute("DELETE FROM counters WHERE id = ?", (key,))
        conn.commit()
    return _payload()


@eel.expose
def tap_counter(counter_id: str, delta: int = 1) -> Dict[str, Any]:
    key = str(counter_id or "").strip()
    try:
        step = int(delta)
    except (TypeError, ValueError):
        step = 1
    if step == 0:
        return _payload()
    today = _today().isoformat()
    with _connect() as conn:
        row = conn.execute("SELECT id FROM counters WHERE id = ?", (key,)).fetchone()
        if row is None:
            raise ValueError("Counter not found")
        current = conn.execute(
            "SELECT count FROM taps WHERE counter_id = ? AND local_date = ?",
            (key, today),
        ).fetchone()
        value = max(0, min(MAX_TARGET * 5, int(current["count"] if current else 0) + step))
        conn.execute(
            """
            INSERT INTO taps (counter_id, local_date, count) VALUES (?, ?, ?)
            ON CONFLICT(counter_id, local_date) DO UPDATE SET count = excluded.count
            """,
            (key, today, value),
        )
        conn.commit()
    return _payload()
