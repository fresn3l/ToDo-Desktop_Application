"""
Workout log — body weight and sessions for a day.

Storage: Application Support/ToDo/workouts.sqlite
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import eel

from paths import data_directory

KINDS = ("running", "legs", "push", "pull", "other")
KIND_LABELS = {
    "running": "Running",
    "legs": "Leg day",
    "push": "Push day",
    "pull": "Pull day",
    "other": "Other",
}


def _data_dir() -> Path:
    return data_directory()


def get_workouts_db_path() -> Path:
    return _data_dir() / "workouts.sqlite"


def _connect() -> sqlite3.Connection:
    path = get_workouts_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS workout_days (
            local_date TEXT PRIMARY KEY,
            body_weight REAL,
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS workout_sessions (
            id TEXT PRIMARY KEY,
            local_date TEXT NOT NULL,
            kind TEXT NOT NULL,
            other_label TEXT NOT NULL DEFAULT '',
            miles REAL,
            minutes REAL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_workout_sessions_date ON workout_sessions(local_date)"
    )
    return conn


def _parse_date(value: Optional[str]) -> str:
    text = str(value or "").strip() or date.today().isoformat()
    try:
        return date.fromisoformat(text[:10]).isoformat()
    except ValueError as exc:
        raise ValueError("Date must be YYYY-MM-DD") from exc


def _parse_optional_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Expected a number") from exc
    if number < 0:
        raise ValueError("Number cannot be negative")
    return number


def _session_dict(row: sqlite3.Row) -> Dict[str, Any]:
    kind = row["kind"]
    label = KIND_LABELS.get(kind, kind)
    other = (row["other_label"] or "").strip()
    if kind == "other" and other:
        label = other
    return {
        "id": row["id"],
        "local_date": row["local_date"],
        "kind": kind,
        "kind_label": KIND_LABELS.get(kind, kind),
        "other_label": other,
        "label": label,
        "miles": row["miles"],
        "minutes": row["minutes"],
        "created_at": row["created_at"],
    }


def _day_payload(local_date: str, conn: sqlite3.Connection) -> Dict[str, Any]:
    day = conn.execute(
        "SELECT * FROM workout_days WHERE local_date = ?",
        (local_date,),
    ).fetchone()
    sessions = [
        _session_dict(row)
        for row in conn.execute(
            "SELECT * FROM workout_sessions WHERE local_date = ? ORDER BY created_at ASC",
            (local_date,),
        ).fetchall()
    ]
    miles = sum(float(s["miles"] or 0) for s in sessions)
    return {
        "local_date": local_date,
        "body_weight": None if day is None else day["body_weight"],
        "notes": "" if day is None else (day["notes"] or ""),
        "sessions": sessions,
        "session_count": len(sessions),
        "miles": round(miles, 2),
        "done": len(sessions) > 0,
    }


@eel.expose
def get_workouts_db_path_exposed() -> str:
    return str(get_workouts_db_path())


@eel.expose
def get_workout_day(local_date: str = "") -> Dict[str, Any]:
    target = _parse_date(local_date)
    with _connect() as conn:
        return _day_payload(target, conn)


@eel.expose
def save_body_weight(local_date: str, body_weight: Any, notes: str = "") -> Dict[str, Any]:
    target = _parse_date(local_date)
    weight = _parse_optional_float(body_weight)
    now = datetime.now().isoformat()
    with _connect() as conn:
        existing = conn.execute(
            "SELECT created_at FROM workout_days WHERE local_date = ?",
            (target,),
        ).fetchone()
        created = existing["created_at"] if existing else now
        conn.execute(
            """
            INSERT INTO workout_days (local_date, body_weight, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(local_date) DO UPDATE SET
                body_weight = excluded.body_weight,
                notes = excluded.notes,
                updated_at = excluded.updated_at
            """,
            (target, weight, (notes or "").strip(), created, now),
        )
        return _day_payload(target, conn)


@eel.expose
def add_workout_session(
    local_date: str,
    kind: str,
    other_label: str = "",
    miles: Any = None,
    minutes: Any = None,
) -> Dict[str, Any]:
    target = _parse_date(local_date)
    key = str(kind or "").strip().lower()
    if key not in KINDS:
        raise ValueError("Unknown workout type")
    label = (other_label or "").strip()
    if key == "other" and not label:
        raise ValueError("Name the other activity (pickleball, hill sprints, …)")
    mile_val = _parse_optional_float(miles)
    minute_val = _parse_optional_float(minutes)
    if key == "running" and mile_val is None:
        raise ValueError("Add miles for a run")
    now = datetime.now().isoformat()
    session_id = str(uuid.uuid4())
    with _connect() as conn:
        existing = conn.execute(
            "SELECT created_at FROM workout_days WHERE local_date = ?",
            (target,),
        ).fetchone()
        if existing is None:
            conn.execute(
                """
                INSERT INTO workout_days (local_date, body_weight, notes, created_at, updated_at)
                VALUES (?, NULL, '', ?, ?)
                """,
                (target, now, now),
            )
        conn.execute(
            """
            INSERT INTO workout_sessions (
                id, local_date, kind, other_label, miles, minutes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (session_id, target, key, label, mile_val, minute_val, now),
        )
        return _day_payload(target, conn)


@eel.expose
def delete_workout_session(session_id: str) -> Dict[str, Any]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT local_date FROM workout_sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        if row is None:
            raise ValueError("Session not found")
        target = row["local_date"]
        conn.execute("DELETE FROM workout_sessions WHERE id = ?", (session_id,))
        return _day_payload(target, conn)


@eel.expose
def list_recent_workout_days(limit: int = 14) -> List[Dict[str, Any]]:
    limit = max(1, min(int(limit or 14), 90))
    with _connect() as conn:
        dates = [
            row["local_date"]
            for row in conn.execute(
                """
                SELECT local_date FROM workout_days
                ORDER BY local_date DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        ]
        extra = [
            row["local_date"]
            for row in conn.execute(
                """
                SELECT DISTINCT local_date FROM workout_sessions
                ORDER BY local_date DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        ]
        ordered = []
        seen = set()
        for value in dates + extra:
            if value in seen:
                continue
            seen.add(value)
            ordered.append(value)
        ordered.sort(reverse=True)
        return [_day_payload(day, conn) for day in ordered[:limit]]


def count_workouts_by_date(start_date: str, end_date: str) -> Dict[str, int]:
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT local_date, COUNT(*) AS n
            FROM workout_sessions
            WHERE local_date >= ? AND local_date <= ?
            GROUP BY local_date
            """,
            (start, end),
        ).fetchall()
    return {row["local_date"]: int(row["n"] or 0) for row in rows}


def list_all_workout_sessions() -> List[Dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM workout_sessions ORDER BY local_date DESC, created_at DESC"
        ).fetchall()
        return [_session_dict(row) for row in rows]


def list_all_workout_days() -> List[Dict[str, Any]]:
    with _connect() as conn:
        dates = [
            row["local_date"]
            for row in conn.execute(
                """
                SELECT local_date FROM workout_days
                UNION
                SELECT DISTINCT local_date FROM workout_sessions
                ORDER BY 1 DESC
                """
            ).fetchall()
        ]
        return [_day_payload(day, conn) for day in dates]


def list_workout_dates() -> List[str]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT DISTINCT local_date FROM workout_sessions ORDER BY local_date DESC"
        ).fetchall()
    return [row["local_date"] for row in rows]


def workout_metrics(days: int = 30) -> Dict[str, Any]:
    days = max(1, min(int(days or 30), 3650))
    end = date.today()
    start = end - timedelta(days=days - 1)
    with _connect() as conn:
        sessions = conn.execute(
            """
            SELECT * FROM workout_sessions
            WHERE local_date >= ? AND local_date <= ?
            ORDER BY local_date ASC
            """,
            (start.isoformat(), end.isoformat()),
        ).fetchall()
        weights = conn.execute(
            """
            SELECT local_date, body_weight FROM workout_days
            WHERE local_date >= ? AND local_date <= ?
              AND body_weight IS NOT NULL
            ORDER BY local_date ASC
            """,
            (start.isoformat(), end.isoformat()),
        ).fetchall()
    by_kind: Dict[str, int] = {k: 0 for k in KINDS}
    miles = 0.0
    session_days = set()
    for row in sessions:
        by_kind[row["kind"]] = by_kind.get(row["kind"], 0) + 1
        miles += float(row["miles"] or 0)
        session_days.add(row["local_date"])
    return {
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "days": days,
        "sessions": len(sessions),
        "days_trained": len(session_days),
        "miles": round(miles, 2),
        "by_kind": {KIND_LABELS.get(k, k): n for k, n in by_kind.items() if n},
        "by_kind_raw": by_kind,
        "weight_log": [
            {"date": row["local_date"], "weight": row["body_weight"]} for row in weights
        ],
    }
