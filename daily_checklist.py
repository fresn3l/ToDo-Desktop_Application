"""
Daily Checklist (Kosistenz) — branching questionnaire with local SQLite storage.

Checklist flow JSON: see checklists/default.json
Database: Application Support/ToDo/daily_checklist.sqlite (macOS; legacy path preserved for existing data)
"""

from __future__ import annotations

import eel
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import checkin_github


def _resource_base() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def get_checklist_definition_path() -> Path:
    return _resource_base() / "checklists" / "default.json"


def get_data_directory() -> Path:
    if sys.platform == "win32":
        base = Path.home() / "AppData" / "Local" / "ToDo"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "ToDo"
    else:
        base = Path.home() / ".local" / "share" / "ToDo"
    base.mkdir(parents=True, exist_ok=True)
    return base


def get_daily_checklist_db_path() -> Path:
    return get_data_directory() / "daily_checklist.sqlite"


def _init_db(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            checklist_id TEXT NOT NULL,
            flow_version INTEGER NOT NULL,
            local_date TEXT NOT NULL,
            answers_json TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_submissions_created ON submissions (created_at DESC)"
    )
    conn.commit()


def _connect() -> sqlite3.Connection:
    path = get_daily_checklist_db_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    _init_db(conn)
    return conn


@eel.expose
def get_daily_checklist() -> Dict[str, Any]:
    """Return the active checklist flow definition."""
    path = get_checklist_definition_path()
    if not path.exists():
        raise FileNotFoundError(f"Missing checklist definition: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@eel.expose
def get_daily_checklist_db_path_exposed() -> str:
    """Absolute path to the SQLite file (for Cluny / agents)."""
    return str(get_daily_checklist_db_path().resolve())


@eel.expose
def submit_daily_checklist_response(
    checklist_id: str, flow_version: int, answers: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Persist one completed checklist. answers maps node_id -> value from the client.
    """
    now = datetime.now()
    created_at = now.isoformat()
    local_date = now.date().isoformat()
    body = json.dumps(answers, ensure_ascii=False)
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO submissions (created_at, checklist_id, flow_version, local_date, answers_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (created_at, checklist_id, flow_version, local_date, body),
        )
        row_id = cur.lastrowid

    result = {
        "id": row_id,
        "created_at": created_at,
        "local_date": local_date,
        "checklist_id": checklist_id,
    }
    checkin_github.safe_try_push_checkin(
        local_date,
        {
            "localDate": local_date,
            "createdAt": created_at,
            "checklistId": checklist_id,
            "submissionId": row_id,
            "flowVersion": flow_version,
        },
    )
    return result


@eel.expose
def list_daily_checklist_submissions(limit: int = 30) -> List[Dict[str, Any]]:
    limit = max(1, min(int(limit or 30), 200))
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, created_at, checklist_id, flow_version, local_date, answers_json
            FROM submissions
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    out: List[Dict[str, Any]] = []
    for r in rows:
        try:
            answers = json.loads(r["answers_json"])
        except (json.JSONDecodeError, TypeError):
            answers = {}
        out.append(
            {
                "id": r["id"],
                "created_at": r["created_at"],
                "checklist_id": r["checklist_id"],
                "flow_version": r["flow_version"],
                "local_date": r["local_date"],
                "answers": answers,
            }
        )
    return out
