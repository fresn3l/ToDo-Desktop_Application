"""
Daily Checklist (Kosistenz) — branching questionnaire with local SQLite storage.

Checklist flow JSON: see checklists/default.json
Database: Application Support/ToDo/daily_checklist.sqlite (macOS; legacy path preserved for existing data)
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

import eel
from db import sqlite_connect
from paths import data_directory


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
    return data_directory()


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
    if t not in ("yes_no", "choice", "text", "scale", "number"):
        raise ValueError("Type must be yes_no, choice, text, scale, or number")

    cid = "c_" + uuid.uuid4().hex[:12]
    if t == "yes_no":
        row: Dict[str, Any] = {"id": cid, "type": "yes_no", "question": q}
    elif t == "text":
        row = {"id": cid, "type": "text", "question": q, "optional": bool(item.get("optional"))}
    elif t == "scale":
        row = {
            "id": cid,
            "type": "scale",
            "question": q,
            "min": int(item.get("min") or 1),
            "max": int(item.get("max") or 5),
        }
    elif t == "number":
        row = {
            "id": cid,
            "type": "number",
            "question": q,
            "min": float(item.get("min") or 0),
            "max": float(item.get("max") or 999),
            "step": float(item.get("step") or 1),
            "optional": bool(item.get("optional")),
        }
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

    row["trackDuration"] = bool(item.get("trackDuration")) if t in ("yes_no", "choice") else False

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
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_submissions_local_date ON submissions (local_date)"
    )


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    with sqlite_connect(get_daily_checklist_db_path()) as conn:
        _init_db(conn)
        yield conn


@eel.expose
def get_daily_checklist() -> Dict[str, Any]:
    """Return the active checklist flow definition, with today’s word filled in."""
    path = get_checklist_definition_path()
    if not path.exists():
        raise FileNotFoundError(f"Missing checklist definition: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    try:
        import word_of_the_day

        return word_of_the_day.decorate_flow(data)
    except Exception:
        return data


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


def _humanize_key(key: str) -> str:
    return str(key or "").replace("_", " ").replace("-", " ").strip().title() or "Item"


def _defs_by_id() -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    d = _checklists_dir()
    if not d.is_dir():
        return out
    for path in d.glob("*.json"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        if not _is_valid_bundle_dict(data):
            continue
        out[path.stem] = data
        cid = data.get("id")
        if cid:
            out[str(cid)] = data
    return out


def _format_answer_value(node: Any, val: Any) -> str:
    if val is True:
        base = "Yes"
    elif val is False:
        base = "No"
    elif val is None:
        base = "—"
    elif isinstance(val, (int, float)) and not isinstance(val, bool):
        base = str(val)
    elif isinstance(val, str):
        base = val
    elif isinstance(val, dict):
        duration = val.get("durationMinutes")
        if "answer" in val:
            base = _format_answer_value(node, val["answer"])
        elif val.get("value") == "other":
            base = f"Other: {val.get('otherText', '')}"
        elif "value" in val:
            raw = val.get("value")
            base = raw
            if isinstance(node, dict):
                for opt in node.get("options") or []:
                    if opt.get("value") == raw:
                        base = str(opt.get("label") or raw)
                        break
            else:
                base = str(raw)
        elif duration is not None:
            return f"{duration} min"
        elif "created_titles" in val or "assign_ids" in val:
            titles = [str(t).strip() for t in (val.get("created_titles") or []) if str(t).strip()]
            assigned = [x for x in (val.get("assign_ids") or []) if x]
            n = len(titles) + len(assigned)
            if not n:
                return "No tasks planned"
            sample = ", ".join(titles[:2])
            if sample:
                return f"{n} for tomorrow: {sample}"
            return f"{n} task{'s' if n != 1 else ''} for tomorrow"
        else:
            base = str(val)
        if duration is not None:
            return f"{base} ({duration} min)"
        return str(base)
    else:
        base = str(val)

    if isinstance(node, dict) and node.get("type") == "choice" and not isinstance(val, dict):
        for opt in node.get("options") or []:
            if opt.get("value") == val:
                return str(opt.get("label") or val)
    return str(base)


def _node_for_key(
    checklist_id: str,
    key: str,
    defs: Dict[str, Dict[str, Any]] | None = None,
    custom_items: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    defs = defs if defs is not None else _defs_by_id()
    defn = defs.get(checklist_id) or {}
    node = (defn.get("nodes") or {}).get(key)
    if isinstance(node, dict):
        return node
    items = custom_items if custom_items is not None else _load_custom_items_raw()
    for item in items:
        if item.get("id") == key:
            return item
    for data in defs.values():
        node = (data.get("nodes") or {}).get(key)
        if isinstance(node, dict):
            return node
    return {}


def format_submission_answers(
    checklist_id: str,
    answers: Dict[str, Any],
    defs: Dict[str, Dict[str, Any]] | None = None,
    custom_items: List[Dict[str, Any]] | None = None,
) -> List[Dict[str, str]]:
    """Turn stored answer keys into question/answer rows for the UI."""
    formatted: List[Dict[str, str]] = []
    if not isinstance(answers, dict):
        return formatted
    defs = defs if defs is not None else _defs_by_id()
    custom_items = custom_items if custom_items is not None else _load_custom_items_raw()
    for key, val in answers.items():
        node = _node_for_key(checklist_id, key, defs=defs, custom_items=custom_items)
        label = str(node.get("history_label") or node.get("question") or _humanize_key(key))
        formatted.append(
            {
                "key": str(key),
                "label": label,
                "value": _format_answer_value(node, val),
            }
        )
    return formatted


def summarize_formatted_answers(formatted: List[Dict[str, str]], limit: int = 3) -> str:
    parts: List[str] = []
    for row in formatted[:limit]:
        val = row.get("value") or ""
        if len(val) > 42:
            val = val[:39] + "…"
        parts.append(f"{row.get('label')}: {val}")
    extra = len(formatted) - limit
    if extra > 0:
        parts.append(f"+{extra} more")
    return " · ".join(parts)


def decorate_submission(
    row: Dict[str, Any],
    defs: Dict[str, Dict[str, Any]] | None = None,
    custom_items: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    answers = row.get("answers") or {}
    cid = row.get("checklist_id") or ""
    defs = defs if defs is not None else _defs_by_id()
    custom_items = custom_items if custom_items is not None else _load_custom_items_raw()
    formatted = format_submission_answers(cid, answers, defs=defs, custom_items=custom_items)
    out = dict(row)
    data = defs.get(cid) or {}
    out["title"] = str(data.get("title") or cid or "Checklist")
    out["answers_formatted"] = formatted
    out["summary"] = summarize_formatted_answers(formatted)
    return out


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
        "flow_version": flow_version,
        "answers": answers,
    }
    try:
        import work

        work.apply_evening_plan(answers)
    except Exception:
        pass
    try:
        import cluny_sync

        cluny_sync.sync_checklist_submission_safe(result)
    except Exception:
        pass
    return result


def _submission_from_row(r: sqlite3.Row) -> Dict[str, Any]:
    try:
        answers = json.loads(r["answers_json"])
    except (json.JSONDecodeError, TypeError):
        answers = {}
    return {
        "id": r["id"],
        "created_at": r["created_at"],
        "checklist_id": r["checklist_id"],
        "flow_version": r["flow_version"],
        "local_date": r["local_date"],
        "answers": answers,
    }


def fetch_submissions(
    *,
    limit: Optional[int] = None,
    local_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    decorate: bool = True,
) -> List[Dict[str, Any]]:
    """Load submissions from SQLite. No default row cap — filter by date instead."""
    clauses: List[str] = []
    params: List[Any] = []
    if local_date:
        clauses.append("local_date = ?")
        params.append(local_date)
    if start_date:
        clauses.append("local_date >= ?")
        params.append(start_date)
    if end_date:
        clauses.append("local_date <= ?")
        params.append(end_date)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"""
        SELECT id, created_at, checklist_id, flow_version, local_date, answers_json
        FROM submissions
        {where}
        ORDER BY created_at DESC
    """
    if limit is not None:
        sql += " LIMIT ?"
        params.append(max(1, int(limit)))
    with _connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    defs = _defs_by_id() if decorate else None
    custom_items = _load_custom_items_raw() if decorate else None
    out: List[Dict[str, Any]] = []
    for r in rows:
        row = _submission_from_row(r)
        if decorate:
            row = decorate_submission(row, defs=defs, custom_items=custom_items)
        out.append(row)
    return out


def list_submission_dates() -> List[str]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT DISTINCT local_date FROM submissions ORDER BY local_date DESC"
        ).fetchall()
    return [r["local_date"] for r in rows if r["local_date"]]


@eel.expose
def list_daily_checklist_submissions(limit: int = 30) -> List[Dict[str, Any]]:
    """Recent submissions for the checklist history panel only."""
    limit = max(1, min(int(limit or 30), 100))
    return fetch_submissions(limit=limit, decorate=True)
