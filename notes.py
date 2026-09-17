"""Notes — things to remember, optionally pinned to a focus span.

Not a journal (timed writing on the Mac) and not a To Do (something to do).
A note lives in storage, or on one focus block. Pulling it onto Friday's
span sets that link; pulling it off puts it back in storage. Deleting the
span returns the note to storage.
"""

from __future__ import annotations

import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

import eel

from db import sqlite_connect
from paths import data_directory

MAX_TITLE = 200
MAX_BODY = 80_000
MAX_NOTES = 8_000
MAX_LIST = 400

_schema_lock = threading.Lock()


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def get_notes_db_path() -> Path:
    return data_directory() / "notes.sqlite"


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    with sqlite_connect(get_notes_db_path()) as conn:
        _ensure_schema(conn)
        yield conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    with _schema_lock:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL DEFAULT '',
                body TEXT NOT NULL DEFAULT '',
                focus_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_notes_focus ON notes(focus_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_notes_updated ON notes(updated_at)")


def _export() -> None:
    try:
        import icloud_sync

        icloud_sync.export_if_enabled()
    except Exception:
        pass


def _row(row: sqlite3.Row) -> Dict[str, Any]:
    focus = str(row["focus_id"] or "").strip()
    return {
        "id": row["id"],
        "title": row["title"] or "",
        "body": row["body"] or "",
        "focus_id": focus or None,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _title_from(title: str, body: str) -> str:
    clean = (title or "").strip()
    if clean:
        return clean[:MAX_TITLE]
    first = (body or "").strip().splitlines()[0] if (body or "").strip() else ""
    return (first or "Note")[:MAX_TITLE]


def _require_focus(focus_id: str) -> None:
    import calclock

    block = calclock._load_block(focus_id)
    if str(block.get("kind") or "") != "focus":
        raise ValueError("Notes attach to a focus span.")


def notes_by_focus_ids(block_ids: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    keys = [str(item or "").strip() for item in block_ids if str(item or "").strip()]
    if not keys:
        return {}
    placeholders = ",".join("?" * len(keys))
    with _connect() as conn:
        rows = conn.execute(
            f"""
            SELECT * FROM notes
            WHERE focus_id IN ({placeholders})
            ORDER BY updated_at DESC
            """,
            keys,
        ).fetchall()
    out: Dict[str, List[Dict[str, Any]]] = {key: [] for key in keys}
    for row in rows:
        packed = _row(row)
        focus = packed.get("focus_id")
        if focus:
            out.setdefault(focus, []).append(packed)
    return out


def release_focus(block_id: str) -> int:
    """Put every note on this span back in storage. Used when the span is deleted."""
    key = str(block_id or "").strip()
    if not key:
        return 0
    stamp = _now()
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE notes SET focus_id = NULL, updated_at = ? WHERE focus_id = ?",
            (stamp, key),
        )
        changed = int(cur.rowcount or 0)
    if changed:
        _export()
    return changed


def dump_notes() -> List[Dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM notes ORDER BY updated_at DESC LIMIT ?",
            (MAX_NOTES,),
        ).fetchall()
    return [_row(row) for row in rows]


def import_note(entry: Dict[str, Any], overwrite: bool = False) -> Optional[Dict[str, Any]]:
    if not isinstance(entry, dict):
        return None
    body = str(entry.get("body") or "").strip()
    title = _title_from(str(entry.get("title") or ""), body)
    if not body and not str(entry.get("title") or "").strip():
        return None
    if len(body) > MAX_BODY:
        return None
    note_id = str(entry.get("id") or "").strip() or f"note_{uuid.uuid4().hex[:12]}"
    if len(note_id) > 80 or "/" in note_id or ".." in note_id:
        note_id = f"note_{uuid.uuid4().hex[:12]}"
    focus_raw = str(entry.get("focus_id") or "").strip()
    focus_id = focus_raw[:80] if focus_raw else None
    created = str(entry.get("created_at") or "").strip() or _now()
    updated = str(entry.get("updated_at") or "").strip() or created
    with _connect() as conn:
        existing = conn.execute("SELECT id FROM notes WHERE id = ?", (note_id,)).fetchone()
        if existing and not overwrite:
            return None
        conn.execute(
            """
            INSERT INTO notes (id, title, body, focus_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title = excluded.title,
                body = excluded.body,
                focus_id = excluded.focus_id,
                updated_at = excluded.updated_at
            """,
            (note_id, title, body[:MAX_BODY], focus_id, created, updated),
        )
        row = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
    return _row(row) if row else None


@eel.expose
def list_notes() -> List[Dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM notes ORDER BY updated_at DESC LIMIT ?",
            (MAX_LIST,),
        ).fetchall()
    return [_row(row) for row in rows]


@eel.expose
def save_note(
    title: str = "",
    body: str = "",
    note_id: str = "",
    focus_id: str = "",
) -> Dict[str, Any]:
    text = str(body or "")
    if len(text) > MAX_BODY:
        raise ValueError("That note is too long.")
    named = _title_from(str(title or ""), text)
    if not named.strip() and not text.strip():
        raise ValueError("Write something first.")
    stamp = _now()
    key = str(note_id or "").strip()
    focus = str(focus_id or "").strip()
    if focus:
        _require_focus(focus)
    with _connect() as conn:
        count = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
        if key:
            row = conn.execute("SELECT * FROM notes WHERE id = ?", (key,)).fetchone()
            if row is None:
                raise ValueError("That note is gone.")
            conn.execute(
                """
                UPDATE notes
                SET title = ?, body = ?, focus_id = ?, updated_at = ?
                WHERE id = ?
                """,
                (named, text, focus or None, stamp, key),
            )
        else:
            if int(count or 0) >= MAX_NOTES:
                raise ValueError("Too many notes.")
            key = f"note_{uuid.uuid4().hex[:12]}"
            conn.execute(
                """
                INSERT INTO notes (id, title, body, focus_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (key, named, text, focus or None, stamp, stamp),
            )
        row = conn.execute("SELECT * FROM notes WHERE id = ?", (key,)).fetchone()
    packed = _row(row)
    _export()
    return packed


@eel.expose
def delete_note(note_id: str) -> Dict[str, Any]:
    key = str(note_id or "").strip()
    if not key:
        raise ValueError("That note is gone.")
    with _connect() as conn:
        cur = conn.execute("DELETE FROM notes WHERE id = ?", (key,))
        if not cur.rowcount:
            raise ValueError("That note is gone.")
    _export()
    return {"ok": True, "id": key}


@eel.expose
def attach_note(note_id: str, focus_id: str) -> Dict[str, Any]:
    key = str(note_id or "").strip()
    focus = str(focus_id or "").strip()
    if not key:
        raise ValueError("That note is gone.")
    if not focus:
        return detach_note(key)
    _require_focus(focus)
    stamp = _now()
    with _connect() as conn:
        row = conn.execute("SELECT id FROM notes WHERE id = ?", (key,)).fetchone()
        if row is None:
            raise ValueError("That note is gone.")
        conn.execute(
            "UPDATE notes SET focus_id = ?, updated_at = ? WHERE id = ?",
            (focus, stamp, key),
        )
        packed = conn.execute("SELECT * FROM notes WHERE id = ?", (key,)).fetchone()
    _export()
    return _row(packed)


@eel.expose
def detach_note(note_id: str) -> Dict[str, Any]:
    key = str(note_id or "").strip()
    if not key:
        raise ValueError("That note is gone.")
    stamp = _now()
    with _connect() as conn:
        row = conn.execute("SELECT id FROM notes WHERE id = ?", (key,)).fetchone()
        if row is None:
            raise ValueError("That note is gone.")
        conn.execute(
            "UPDATE notes SET focus_id = NULL, updated_at = ? WHERE id = ?",
            (stamp, key),
        )
        packed = conn.execute("SELECT * FROM notes WHERE id = ?", (key,)).fetchone()
    _export()
    return _row(packed)


@eel.expose
def list_focus_spans() -> List[Dict[str, Any]]:
    """This week's named holds, for the Notes picker."""
    import calclock

    week = calclock.get_week(include_unplaced=False)
    out: List[Dict[str, Any]] = []
    for day in week.get("days") or []:
        for item in day.get("blocks") or []:
            if str(item.get("kind") or "") != "focus":
                continue
            out.append(
                {
                    "id": item.get("id"),
                    "title": item.get("title") or "Focus",
                    "date": day.get("date"),
                    "weekday": day.get("weekday"),
                    "start_at": item.get("start_at"),
                    "end_at": item.get("end_at"),
                }
            )
    return out
