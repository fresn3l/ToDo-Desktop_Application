"""
Work items — dated To Do tasks, undated All Work backlog, and timer sessions.

Storage: Application Support/ToDo/work_items.sqlite
Widget snapshot: Application Support/ToDo/widget_snapshot.json
  (a future Mac widget can read open_count for today without opening the app)
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import eel

import daily_checklist

STATUSES = ("open", "active", "done")


def _data_dir() -> Path:
    override = os.environ.get("KOSISTENZ_DATA_DIR")
    if override:
        path = Path(override)
        path.mkdir(parents=True, exist_ok=True)
        return path
    return daily_checklist.get_data_directory()


def get_work_db_path() -> Path:
    return _data_dir() / "work_items.sqlite"


def get_widget_snapshot_path() -> Path:
    return _data_dir() / "widget_snapshot.json"


def _connect() -> sqlite3.Connection:
    path = get_work_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS work_items (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT '',
            scheduled_date TEXT,
            status TEXT NOT NULL DEFAULT 'open',
            active_started_at TEXT,
            finished_at TEXT,
            duration_seconds INTEGER NOT NULL DEFAULT 0,
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'manual'
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_work_scheduled ON work_items(scheduled_date)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_work_status ON work_items(status)")
    return conn


def _now() -> datetime:
    return datetime.now()


def _today() -> date:
    return date.today()


def _parse_date(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10]).isoformat()
    except ValueError as exc:
        raise ValueError("Date must be YYYY-MM-DD") from exc


def _elapsed_seconds(row: sqlite3.Row | Dict[str, Any], now: Optional[datetime] = None) -> int:
    stored = int(row["duration_seconds"] or 0)
    started = row["active_started_at"]
    status = row["status"]
    if status != "active" or not started:
        return max(0, stored)
    now = now or _now()
    try:
        start = datetime.fromisoformat(str(started))
    except ValueError:
        return max(0, stored)
    return max(0, stored + int((now - start).total_seconds()))


def _row_to_dict(row: sqlite3.Row, now: Optional[datetime] = None) -> Dict[str, Any]:
    now = now or _now()
    elapsed = _elapsed_seconds(row, now)
    scheduled = row["scheduled_date"]
    today = _today().isoformat()
    return {
        "id": row["id"],
        "title": row["title"],
        "notes": row["notes"] or "",
        "scheduled_date": scheduled,
        "status": row["status"],
        "active_started_at": row["active_started_at"],
        "finished_at": row["finished_at"],
        "duration_seconds": elapsed,
        "stored_duration_seconds": int(row["duration_seconds"] or 0),
        "sort_order": int(row["sort_order"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "source": row["source"] or "manual",
        "is_today": scheduled == today,
        "is_overdue": bool(scheduled and scheduled < today and row["status"] != "done"),
        "is_backlog": scheduled is None,
    }


def _fetch(conn: sqlite3.Connection, item_id: str) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT * FROM work_items WHERE id = ?", (item_id,)).fetchone()


def _pause_active(conn: sqlite3.Connection, except_id: Optional[str] = None) -> None:
    now = _now()
    rows = conn.execute(
        "SELECT * FROM work_items WHERE status = 'active'"
    ).fetchall()
    for row in rows:
        if except_id and row["id"] == except_id:
            continue
        elapsed = _elapsed_seconds(row, now)
        conn.execute(
            """
            UPDATE work_items
            SET status = 'open',
                active_started_at = NULL,
                duration_seconds = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (elapsed, now.isoformat(), row["id"]),
        )


def _write_widget_snapshot() -> Dict[str, Any]:
    today = _today().isoformat()
    with _connect() as conn:
        today_rows = conn.execute(
            "SELECT * FROM work_items WHERE scheduled_date = ?",
            (today,),
        ).fetchall()
        backlog = conn.execute(
            "SELECT COUNT(*) AS n FROM work_items WHERE scheduled_date IS NULL AND status != 'done'"
        ).fetchone()["n"]
    open_items = []
    done_count = 0
    active_count = 0
    now = _now()
    for row in today_rows:
        item = _row_to_dict(row, now)
        if item["status"] == "done":
            done_count += 1
        else:
            open_items.append(item)
            if item["status"] == "active":
                active_count += 1
    snapshot = {
        "date": today,
        "updated_at": now.isoformat(),
        "open_count": len(open_items),
        "active_count": active_count,
        "done_count": done_count,
        "backlog_count": int(backlog or 0),
        "titles": [item["title"] for item in open_items[:12]],
    }
    path = get_widget_snapshot_path()
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(snapshot, handle, indent=2, ensure_ascii=False)
    os.replace(tmp, path)
    return snapshot


def _next_sort(conn: sqlite3.Connection, scheduled_date: Optional[str]) -> int:
    if scheduled_date is None:
        row = conn.execute(
            "SELECT MAX(sort_order) AS m FROM work_items WHERE scheduled_date IS NULL"
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT MAX(sort_order) AS m FROM work_items WHERE scheduled_date = ?",
            (scheduled_date,),
        ).fetchone()
    return int(row["m"] or 0) + 10


@eel.expose
def get_work_db_path_exposed() -> str:
    return str(get_work_db_path())


@eel.expose
def get_widget_snapshot_path_exposed() -> str:
    return str(get_widget_snapshot_path())


@eel.expose
def get_widget_snapshot() -> Dict[str, Any]:
    path = get_widget_snapshot_path()
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict) and data.get("date") == _today().isoformat():
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return _write_widget_snapshot()


@eel.expose
def create_work_item(
    title: str,
    scheduled_date: Optional[str] = None,
    notes: str = "",
    source: str = "manual",
) -> Dict[str, Any]:
    clean = (title or "").strip()
    if not clean:
        raise ValueError("Title is required")
    target = _parse_date(scheduled_date)
    now = _now().isoformat()
    item_id = str(uuid.uuid4())
    src = (source or "manual").strip() or "manual"
    with _connect() as conn:
        sort_order = _next_sort(conn, target)
        conn.execute(
            """
            INSERT INTO work_items (
                id, title, notes, scheduled_date, status,
                active_started_at, finished_at, duration_seconds, sort_order,
                created_at, updated_at, source
            ) VALUES (?, ?, ?, ?, 'open', NULL, NULL, 0, ?, ?, ?, ?)
            """,
            (item_id, clean, (notes or "").strip(), target, sort_order, now, now, src),
        )
        row = _fetch(conn, item_id)
    _write_widget_snapshot()
    assert row is not None
    return _row_to_dict(row)


@eel.expose
def list_work_for_date(local_date: str) -> List[Dict[str, Any]]:
    target = _parse_date(local_date)
    if not target:
        raise ValueError("Date must be YYYY-MM-DD")
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM work_items
            WHERE scheduled_date = ?
            ORDER BY CASE status WHEN 'active' THEN 0 WHEN 'open' THEN 1 ELSE 2 END,
                     sort_order ASC, created_at ASC
            """,
            (target,),
        ).fetchall()
    now = _now()
    return [_row_to_dict(row, now) for row in rows]


@eel.expose
def list_backlog() -> List[Dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM work_items
            WHERE scheduled_date IS NULL AND status != 'done'
            ORDER BY sort_order ASC, created_at ASC
            """
        ).fetchall()
    now = _now()
    return [_row_to_dict(row, now) for row in rows]


@eel.expose
def list_overdue_work() -> List[Dict[str, Any]]:
    today = _today().isoformat()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM work_items
            WHERE scheduled_date IS NOT NULL
              AND scheduled_date < ?
              AND status != 'done'
            ORDER BY scheduled_date ASC, sort_order ASC
            """,
            (today,),
        ).fetchall()
    now = _now()
    return [_row_to_dict(row, now) for row in rows]


@eel.expose
def get_work_board(local_date: str = "") -> Dict[str, Any]:
    today = _today()
    target = _parse_date(local_date) or today.isoformat()
    tomorrow = (today + timedelta(days=1)).isoformat()
    today_items = list_work_for_date(target)
    return {
        "local_date": target,
        "today": today_items,
        "tomorrow": list_work_for_date(tomorrow) if target == today.isoformat() else [],
        "overdue": list_overdue_work() if target == today.isoformat() else [],
        "backlog": list_backlog(),
        "tomorrow_date": tomorrow,
        "counts": {
            "today_open": sum(1 for item in today_items if item["status"] != "done"),
            "today_done": sum(1 for item in today_items if item["status"] == "done"),
            "today_total": len(today_items),
            "overdue": len(list_overdue_work()) if target == today.isoformat() else 0,
            "backlog": len(list_backlog()),
        },
    }


@eel.expose
def assign_work_item(item_id: str, scheduled_date: Optional[str] = None) -> Dict[str, Any]:
    target = _parse_date(scheduled_date)
    now = _now().isoformat()
    with _connect() as conn:
        row = _fetch(conn, item_id)
        if row is None:
            raise ValueError("Work item not found")
        if target is None and row["status"] == "active":
            elapsed = _elapsed_seconds(row)
            conn.execute(
                """
                UPDATE work_items
                SET scheduled_date = NULL,
                    status = 'open',
                    active_started_at = NULL,
                    duration_seconds = ?,
                    updated_at = ?,
                    sort_order = ?
                WHERE id = ?
                """,
                (elapsed, now, _next_sort(conn, None), item_id),
            )
        else:
            conn.execute(
                """
                UPDATE work_items
                SET scheduled_date = ?, updated_at = ?,
                    sort_order = ?
                WHERE id = ?
                """,
                (target, now, _next_sort(conn, target), item_id),
            )
        row = _fetch(conn, item_id)
    _write_widget_snapshot()
    assert row is not None
    return _row_to_dict(row)


@eel.expose
def update_work_item(item_id: str, title: str = "", notes: Optional[str] = None) -> Dict[str, Any]:
    clean = (title or "").strip()
    now = _now().isoformat()
    with _connect() as conn:
        row = _fetch(conn, item_id)
        if row is None:
            raise ValueError("Work item not found")
        new_title = clean or row["title"]
        new_notes = row["notes"] if notes is None else str(notes)
        conn.execute(
            """
            UPDATE work_items SET title = ?, notes = ?, updated_at = ?
            WHERE id = ?
            """,
            (new_title, new_notes, now, item_id),
        )
        row = _fetch(conn, item_id)
    _write_widget_snapshot()
    assert row is not None
    return _row_to_dict(row)


@eel.expose
def delete_work_item(item_id: str) -> Dict[str, Any]:
    with _connect() as conn:
        row = _fetch(conn, item_id)
        if row is None:
            raise ValueError("Work item not found")
        conn.execute("DELETE FROM work_items WHERE id = ?", (item_id,))
    _write_widget_snapshot()
    return {"ok": True, "id": item_id}


@eel.expose
def start_work_item(item_id: str) -> Dict[str, Any]:
    now = _now()
    with _connect() as conn:
        row = _fetch(conn, item_id)
        if row is None:
            raise ValueError("Work item not found")
        if row["status"] == "done":
            raise ValueError("Finished tasks cannot be started. Reopen first.")
        _pause_active(conn, except_id=item_id)
        started = row["active_started_at"] if row["status"] == "active" else now.isoformat()
        conn.execute(
            """
            UPDATE work_items
            SET status = 'active', active_started_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (started, now.isoformat(), item_id),
        )
        row = _fetch(conn, item_id)
    _write_widget_snapshot()
    assert row is not None
    return _row_to_dict(row)


@eel.expose
def stop_work_item(item_id: str) -> Dict[str, Any]:
    """Pause the timer without marking the task done."""
    now = _now()
    with _connect() as conn:
        row = _fetch(conn, item_id)
        if row is None:
            raise ValueError("Work item not found")
        elapsed = _elapsed_seconds(row, now)
        conn.execute(
            """
            UPDATE work_items
            SET status = 'open',
                active_started_at = NULL,
                duration_seconds = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (elapsed, now.isoformat(), item_id),
        )
        row = _fetch(conn, item_id)
    _write_widget_snapshot()
    assert row is not None
    return _row_to_dict(row)


@eel.expose
def finish_work_item(item_id: str) -> Dict[str, Any]:
    now = _now()
    with _connect() as conn:
        row = _fetch(conn, item_id)
        if row is None:
            raise ValueError("Work item not found")
        elapsed = _elapsed_seconds(row, now)
        conn.execute(
            """
            UPDATE work_items
            SET status = 'done',
                active_started_at = NULL,
                duration_seconds = ?,
                finished_at = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (elapsed, now.isoformat(), now.isoformat(), item_id),
        )
        row = _fetch(conn, item_id)
    _write_widget_snapshot()
    assert row is not None
    return _row_to_dict(row)


@eel.expose
def reopen_work_item(item_id: str) -> Dict[str, Any]:
    now = _now().isoformat()
    with _connect() as conn:
        row = _fetch(conn, item_id)
        if row is None:
            raise ValueError("Work item not found")
        conn.execute(
            """
            UPDATE work_items
            SET status = 'open',
                active_started_at = NULL,
                finished_at = NULL,
                updated_at = ?
            WHERE id = ?
            """,
            (now, item_id),
        )
        row = _fetch(conn, item_id)
    _write_widget_snapshot()
    assert row is not None
    return _row_to_dict(row)


def apply_evening_plan(answers: Dict[str, Any]) -> Dict[str, Any]:
    """Create/assign tomorrow's work from an evening checklist answers payload."""
    tomorrow = (_today() + timedelta(days=1)).isoformat()
    created: List[Dict[str, Any]] = []
    assigned: List[Dict[str, Any]] = []
    if not isinstance(answers, dict):
        return {"tomorrow": tomorrow, "created": created, "assigned": assigned}
    for value in answers.values():
        if not isinstance(value, dict):
            continue
        if "created_titles" not in value and "assign_ids" not in value:
            continue
        target = _parse_date(value.get("tomorrow")) or tomorrow
        for title in value.get("created_titles") or []:
            text = str(title).strip()
            if not text:
                continue
            created.append(create_work_item(text, scheduled_date=target, source="evening"))
        for item_id in value.get("assign_ids") or []:
            try:
                assigned.append(assign_work_item(str(item_id), target))
            except ValueError:
                continue
    return {"tomorrow": tomorrow, "created": created, "assigned": assigned}


def list_work_dates() -> List[str]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT scheduled_date FROM work_items
            WHERE scheduled_date IS NOT NULL
            ORDER BY scheduled_date DESC
            """
        ).fetchall()
    return [str(row["scheduled_date"]) for row in rows if row["scheduled_date"]]


def count_work_by_date(start_date: str, end_date: str) -> Dict[str, int]:
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    if not start or not end:
        return {}
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT scheduled_date, COUNT(*) AS n
            FROM work_items
            WHERE scheduled_date IS NOT NULL
              AND scheduled_date >= ?
              AND scheduled_date <= ?
            GROUP BY scheduled_date
            """,
            (start, end),
        ).fetchall()
    return {str(row["scheduled_date"]): int(row["n"] or 0) for row in rows}
