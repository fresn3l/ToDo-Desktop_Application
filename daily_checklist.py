"""
Daily Checklist (Kosistenz) — branching questionnaire with local SQLite storage.

Checklist flow JSON: see checklists/default.json
Database: Application Support/ToDo/daily_checklist.sqlite (macOS; legacy path preserved for existing data)
"""

from __future__ import annotations

import eel
import json
import os
import re
import sqlite3
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import checkin_github


def _resource_base() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


_CHECKLIST_STEM_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


def _checklists_dir() -> Path:
    return _resource_base() / "checklists"


def get_selected_checklist_stem() -> str:
    pref = get_data_directory() / "checklist_selected_stem.txt"
    if pref.exists():
        try:
            stem = pref.read_text(encoding="utf-8").strip()
        except OSError:
            stem = ""
        if stem and _CHECKLIST_STEM_PATTERN.fullmatch(stem):
            candidate = _checklists_dir() / f"{stem}.json"
            if candidate.exists():
                return stem
    return "default"


def set_selected_checklist_stem(stem: str) -> None:
    stem = (stem or "").strip()
    if not _CHECKLIST_STEM_PATTERN.fullmatch(stem):
        raise ValueError("Invalid checklist template id")
    path = _checklists_dir() / f"{stem}.json"
    if not path.exists():
        raise ValueError("Checklist template not found")
    pref = get_data_directory() / "checklist_selected_stem.txt"
    get_data_directory().mkdir(parents=True, exist_ok=True)
    pref.write_text(stem, encoding="utf-8")


def get_checklist_definition_path() -> Path:
    return _checklists_dir() / f"{get_selected_checklist_stem()}.json"


def _is_valid_bundle_dict(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    if not isinstance(data.get("nodes"), dict):
        return False
    start = data.get("start")
    if not start or not isinstance(start, str):
        return False
    return True


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


def get_custom_items_path() -> Path:
    return get_data_directory() / "checklist_custom_items.json"


def _load_custom_items_raw() -> List[Dict[str, Any]]:
    path = get_custom_items_path()
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return []
    except (json.JSONDecodeError, OSError):
        return []


def _save_custom_items(items: List[Dict[str, Any]]) -> None:
    path = get_custom_items_path()
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def _slug_option(label: str, idx: int) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", label.strip().lower()).strip("_")
    return s or f"option_{idx}"


@eel.expose
def get_custom_checklist_items() -> List[Dict[str, Any]]:
    """User-defined extra questions (yes/no or choice), stored locally."""
    return _load_custom_items_raw()


@eel.expose
def add_custom_checklist_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Append a validated item. choice.options must be a list of non-empty strings (min 2).
    """
    t = (item.get("type") or "").strip()
    q = (item.get("question") or "").strip()
    if not q:
        raise ValueError("Question is required")
    if t not in ("yes_no", "choice"):
        raise ValueError("Type must be yes_no or choice")

    cid = "c_" + uuid.uuid4().hex[:12]
    if t == "yes_no":
        row: Dict[str, Any] = {"id": cid, "type": "yes_no", "question": q}
    else:
        raw_opts = item.get("options") or []
        if not isinstance(raw_opts, list):
            raise ValueError("Options must be a list")
        labels = [str(x).strip() for x in raw_opts if str(x).strip()]
        if len(labels) < 2:
            raise ValueError("Add at least two options")
        options = []
        seen = set()
        for i, lab in enumerate(labels):
            val = _slug_option(lab, i)
            if val in seen:
                val = f"{val}_{i}"
            seen.add(val)
            options.append({"label": lab, "value": val, "next": "end"})
        row = {
            "id": cid,
            "type": "choice",
            "question": q,
            "options": options,
            "allowOther": bool(item.get("allowOther")),
            "otherNext": "end",
        }

    row["trackDuration"] = bool(item.get("trackDuration"))

    items = _load_custom_items_raw()
    items.append(row)
    _save_custom_items(items)
    return row


@eel.expose
def remove_custom_checklist_item(item_id: str) -> bool:
    item_id = (item_id or "").strip()
    if not item_id:
        return False
    items = _load_custom_items_raw()
    new_items = [x for x in items if x.get("id") != item_id]
    if len(new_items) == len(items):
        return False
    _save_custom_items(new_items)
    return True


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
def list_bundled_checklists() -> List[Dict[str, str]]:
    """JSON files in the bundled checklists/ folder (valid flow definitions only)."""
    out: List[Dict[str, str]] = []
    d = _checklists_dir()
    if not d.is_dir():
        return out
    for path in sorted(d.glob("*.json")):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        if not _is_valid_bundle_dict(data):
            continue
        stem = path.stem
        title = str(data.get("title") or stem).strip() or stem
        out.append({"id": stem, "title": title})
    return out


@eel.expose
def get_active_checklist_stem() -> str:
    return get_selected_checklist_stem()


@eel.expose
def set_active_checklist_stem(stem: str) -> None:
    set_selected_checklist_stem(stem)


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
