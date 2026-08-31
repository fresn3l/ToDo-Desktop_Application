"""
Goals — 6 month, year, and 5 year.

Finished to-dos that are attached (picked on add, or matched by keyword)
count minutes toward the goal. Timer time wins; if you only marked it done,
the calendar block minutes count instead.
"""

from __future__ import annotations

import re
import sqlite3
import uuid
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

import eel

import work

HORIZONS = ("six_month", "year", "five_year")
HORIZON_LABELS = {
    "six_month": "6 months",
    "year": "Year",
    "five_year": "5 years",
}
HORIZON_RANK = {"six_month": 0, "year": 1, "five_year": 2}


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS goals (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            horizon TEXT NOT NULL,
            keyword TEXT NOT NULL DEFAULT '',
            target_minutes INTEGER,
            end_date TEXT,
            notes TEXT NOT NULL DEFAULT '',
            archived INTEGER NOT NULL DEFAULT 0,
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    cols = {row[1] for row in conn.execute("PRAGMA table_info(work_items)")}
    if "goal_id" not in cols:
        conn.execute("ALTER TABLE work_items ADD COLUMN goal_id TEXT")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_work_goal_id ON work_items(goal_id)")
    series_cols = {row[1] for row in conn.execute("PRAGMA table_info(work_series)")}
    if "goal_id" not in series_cols:
        conn.execute("ALTER TABLE work_series ADD COLUMN goal_id TEXT")


def _horizon(value: Any) -> str:
    key = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "6": "six_month",
        "6m": "six_month",
        "6_month": "six_month",
        "6month": "six_month",
        "sixmonth": "six_month",
        "six_months": "six_month",
        "month": "six_month",
        "months": "six_month",
        "1y": "year",
        "1_year": "year",
        "yr": "year",
        "5": "five_year",
        "5y": "five_year",
        "5_year": "five_year",
        "5year": "five_year",
        "fiveyear": "five_year",
        "five_years": "five_year",
    }
    key = aliases.get(key, key)
    if key not in HORIZONS:
        raise ValueError("Horizon must be 6 months, year, or 5 years")
    return key


def _keyword(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    if len(text) > 40:
        raise ValueError("Keyword is too long")
    return text


def _target_minutes(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        minutes = int(round(float(value)))
    except (TypeError, ValueError) as exc:
        raise ValueError("Target must be hours or minutes") from exc
    if minutes < 0:
        raise ValueError("Target cannot be negative")
    if minutes > 20 * 365 * 24 * 60:
        raise ValueError("Target is too long")
    return minutes or None


def _end_date(value: Any) -> Optional[str]:
    if value is None or str(value).strip() == "":
        return None
    return work._parse_date(str(value))


def keyword_matches(title: str, keyword: str) -> bool:
    kw = _keyword(keyword)
    if len(kw) < 2:
        return False
    text = str(title or "").lower()
    if " " in kw:
        return kw in text
    return re.search(r"(?<![a-z0-9])" + re.escape(kw) + r"(?![a-z0-9])", text) is not None


def _fetch_goal(conn: sqlite3.Connection, goal_id: str) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM goals WHERE id = ? AND archived = 0",
        (goal_id,),
    ).fetchone()


def resolve_goal_id(title: str, explicit: Any = None, conn: Any = None) -> Optional[str]:
    """Explicit pick wins. Otherwise the longest keyword that appears in the title."""

    def _run(db: sqlite3.Connection) -> Optional[str]:
        if explicit:
            row = _fetch_goal(db, str(explicit).strip())
            if row is None:
                raise ValueError("Goal not found")
            return row["id"]
        matches: List[Tuple[int, int, str]] = []
        for row in db.execute(
            "SELECT id, keyword, horizon FROM goals WHERE archived = 0 AND keyword != ''"
        ).fetchall():
            if not keyword_matches(title, row["keyword"]):
                continue
            matches.append(
                (
                    -len(row["keyword"] or ""),
                    HORIZON_RANK.get(row["horizon"], 9),
                    row["id"],
                )
            )
        if not matches:
            return None
        matches.sort()
        return matches[0][2]

    if conn is not None:
        return _run(conn)
    with work._connect() as db:
        return _run(db)


def contributing_minutes(item: Dict[str, Any]) -> int:
    """Timer minutes if you worked it; otherwise the calendar block if you only finished it."""
    if item.get("status") != "done":
        return 0
    stored = int(item.get("stored_duration_seconds") or item.get("duration_seconds") or 0)
    if stored > 0:
        return max(1, int(round(stored / 60)))
    item_id = item.get("id")
    if not item_id:
        return 0
    try:
        import calclock

        return int(calclock.placed_minutes(str(item_id)) or 0)
    except Exception:
        return 0


def _row_goal(row: sqlite3.Row) -> Dict[str, Any]:
    target = row["target_minutes"]
    return {
        "id": row["id"],
        "title": row["title"],
        "horizon": row["horizon"],
        "horizon_label": HORIZON_LABELS.get(row["horizon"], row["horizon"]),
        "keyword": row["keyword"] or "",
        "target_minutes": None if target is None else int(target),
        "end_date": row["end_date"],
        "notes": row["notes"] or "",
        "archived": bool(row["archived"]),
        "sort_order": int(row["sort_order"] or 0),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _enrich(goal: Dict[str, Any], items: List[Dict[str, Any]]) -> Dict[str, Any]:
    contribs = []
    spent = 0
    for item in items:
        if item.get("goal_id") != goal["id"]:
            continue
        minutes = contributing_minutes(item)
        if minutes <= 0:
            continue
        spent += minutes
        contribs.append(
            {
                "id": item["id"],
                "title": item["title"],
                "minutes": minutes,
                "finished_at": item.get("finished_at"),
                "scheduled_date": item.get("scheduled_date"),
            }
        )
    contribs.sort(key=lambda row: row.get("finished_at") or "", reverse=True)
    target = goal.get("target_minutes")
    percent = None
    if target:
        percent = min(100, int(round(100 * spent / target)))
    end = goal.get("end_date")
    overdue = bool(end and end < work._today().isoformat() and (percent is None or percent < 100))
    packed = dict(goal)
    packed.update(
        {
            "spent_minutes": spent,
            "percent": percent,
            "has_target": bool(target),
            "overdue": overdue,
            "contributions": contribs[:12],
            "contrib_count": len(contribs),
        }
    )
    return packed


@eel.expose
def list_goals() -> List[Dict[str, Any]]:
    with work._connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM goals
            WHERE archived = 0
            ORDER BY CASE horizon
                WHEN 'six_month' THEN 0 WHEN 'year' THEN 1 ELSE 2 END,
                sort_order ASC, created_at ASC
            """
        ).fetchall()
    items = work.list_all_work_items()
    return [_enrich(_row_goal(row), items) for row in rows]


@eel.expose
def get_goals_board() -> Dict[str, Any]:
    goals = list_goals()
    groups = {key: [] for key in HORIZONS}
    for goal in goals:
        groups.setdefault(goal["horizon"], []).append(goal)
    return {
        "horizons": [
            {
                "id": key,
                "label": HORIZON_LABELS[key],
                "goals": groups.get(key) or [],
            }
            for key in HORIZONS
        ],
        "goals": goals,
    }


@eel.expose
def create_goal(
    title: str,
    horizon: str = "six_month",
    keyword: str = "",
    target_hours: Any = None,
    end_date: str = "",
    notes: str = "",
) -> Dict[str, Any]:
    clean = (title or "").strip()
    if not clean:
        raise ValueError("Name the goal first")
    if len(clean) > 200:
        raise ValueError("Title is too long")
    hz = _horizon(horizon)
    kw = _keyword(keyword)
    minutes = None
    if target_hours not in (None, ""):
        try:
            hours = float(target_hours)
        except (TypeError, ValueError) as exc:
            raise ValueError("Hours must be a number") from exc
        minutes = _target_minutes(hours * 60)
    now = work._now().isoformat()
    goal_id = str(uuid.uuid4())
    with work._connect() as conn:
        sort_row = conn.execute(
            "SELECT MAX(sort_order) AS m FROM goals WHERE horizon = ?",
            (hz,),
        ).fetchone()
        sort_order = int(sort_row["m"] or 0) + 10
        conn.execute(
            """
            INSERT INTO goals (
                id, title, horizon, keyword, target_minutes, end_date, notes,
                archived, sort_order, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
            """,
            (
                goal_id,
                clean,
                hz,
                kw,
                minutes,
                _end_date(end_date),
                (notes or "").strip(),
                sort_order,
                now,
                now,
            ),
        )
        row = _fetch_goal(conn, goal_id)
    assert row is not None
    return _enrich(_row_goal(row), work.list_all_work_items())


@eel.expose
def update_goal(
    goal_id: str,
    title: str = "",
    keyword: Any = None,
    target_hours: Any = None,
    end_date: Any = None,
    horizon: str = "",
) -> Dict[str, Any]:
    now = work._now().isoformat()
    with work._connect() as conn:
        row = _fetch_goal(conn, goal_id)
        if row is None:
            raise ValueError("Goal not found")
        clean = (title or "").strip() or row["title"]
        kw = row["keyword"] if keyword is None else _keyword(keyword)
        hz = _horizon(horizon) if str(horizon or "").strip() else row["horizon"]
        if target_hours is None:
            minutes = row["target_minutes"]
        elif target_hours == "":
            minutes = None
        else:
            minutes = _target_minutes(float(target_hours) * 60)
        due = row["end_date"] if end_date is None else _end_date(end_date)
        conn.execute(
            """
            UPDATE goals
            SET title = ?, keyword = ?, target_minutes = ?, end_date = ?,
                horizon = ?, updated_at = ?
            WHERE id = ?
            """,
            (clean, kw, minutes, due, hz, now, goal_id),
        )
        row = _fetch_goal(conn, goal_id)
    assert row is not None
    return _enrich(_row_goal(row), work.list_all_work_items())


@eel.expose
def delete_goal(goal_id: str) -> Dict[str, Any]:
    with work._connect() as conn:
        row = conn.execute("SELECT id FROM goals WHERE id = ?", (goal_id,)).fetchone()
        if row is None:
            raise ValueError("Goal not found")
        conn.execute("UPDATE work_items SET goal_id = NULL WHERE goal_id = ?", (goal_id,))
        conn.execute("UPDATE work_series SET goal_id = NULL WHERE goal_id = ?", (goal_id,))
        conn.execute("DELETE FROM goals WHERE id = ?", (goal_id,))
    return {"ok": True, "id": goal_id}


@eel.expose
def attach_work_item_goal(item_id: str, goal_id: str = "") -> Dict[str, Any]:
    target = str(goal_id or "").strip() or None
    with work._connect() as conn:
        row = work._fetch(conn, item_id)
        if row is None:
            raise ValueError("Work item not found")
        if target:
            goal = _fetch_goal(conn, target)
            if goal is None:
                raise ValueError("Goal not found")
        conn.execute(
            "UPDATE work_items SET goal_id = ?, updated_at = ? WHERE id = ?",
            (target, work._now().isoformat(), item_id),
        )
        row = work._fetch(conn, item_id)
    work._write_widget_snapshot()
    assert row is not None
    return work._row_to_dict(row)
