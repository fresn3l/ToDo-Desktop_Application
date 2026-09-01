"""
Push journal entries into Cluny's storage after local save.

Configure one or both:

  CLUNY_SQLITE_PATH — Path to Cluny's SQLite database file. Entries are inserted
      into table CLUNY_JOURNAL_TABLE (default: cluny_journal_entries), created if missing.

  CLUNY_INGEST_URL — HTTP endpoint that accepts POST JSON (same shape as the entry dict).
      Optional: CLUNY_API_KEY sent as Authorization: Bearer <key>.

Checklist submissions sync to CLUNY_CHECKLIST_TABLE (default: cluny_checklist_entries)
when CLUNY_SQLITE_PATH is set, or to CLUNY_CHECKLIST_INGEST_URL / CLUNY_INGEST_URL.

Sync failures are logged; they do not block saving locally.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import urllib.error
import urllib.request
from typing import Any, Dict
from pathlib import Path
from urllib.parse import urlparse

from db import sqlite_connect


def _journal_table_name() -> str:
    raw = os.environ.get("CLUNY_JOURNAL_TABLE", "cluny_journal_entries")
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", raw or ""):
        return raw
    return "cluny_journal_entries"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ARG002
        return None


def _http_opener() -> urllib.request.OpenerDirector:
    return urllib.request.build_opener(_NoRedirect)


def _validate_sqlite_path(raw: str) -> str:
    path = Path(raw).expanduser()
    if ".." in path.parts:
        raise ValueError("CLUNY_SQLITE_PATH cannot contain ..")
    try:
        resolved = path.resolve()
    except OSError as exc:
        raise ValueError("Invalid CLUNY_SQLITE_PATH") from exc
    home = Path.home().resolve()
    try:
        resolved.relative_to(home)
    except ValueError as exc:
        raise ValueError("CLUNY_SQLITE_PATH must be inside your home folder") from exc
    return str(resolved)


def _sync_sqlite(entry: Dict[str, Any]) -> None:
    path = os.environ.get("CLUNY_SQLITE_PATH") or os.environ.get("CLUNY_DATABASE_PATH")
    if not path:
        return
    path = _validate_sqlite_path(path)
    table = _journal_table_name()
    raw = json.dumps(entry, ensure_ascii=False)
    with sqlite_connect(path) as conn:
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {table} (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                date TEXT,
                duration_seconds INTEGER,
                continued INTEGER,
                created_at TEXT,
                raw_json TEXT NOT NULL
            )
            """
        )
        # kind and brief ride in raw_json so existing Cluny DBs need no migration.
        conn.execute(
            f"""
            INSERT OR REPLACE INTO {table}
            (id, content, date, duration_seconds, continued, created_at, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry.get("id"),
                entry.get("content", ""),
                entry.get("date"),
                int(entry.get("duration_seconds") or 0),
                1 if entry.get("continued") else 0,
                entry.get("created_at"),
                raw,
            ),
        )


def _sync_http(entry: Dict[str, Any]) -> None:
    url = os.environ.get("CLUNY_INGEST_URL")
    if not url:
        return
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError("CLUNY_INGEST_URL must be https")
    body = json.dumps(entry, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    key = os.environ.get("CLUNY_API_KEY")
    if key:
        req.add_header("Authorization", f"Bearer {key}")
    with _http_opener().open(req, timeout=60) as resp:
        resp.read()


def _checklist_table_name() -> str:
    raw = os.environ.get("CLUNY_CHECKLIST_TABLE", "cluny_checklist_entries")
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", raw or ""):
        return raw
    return "cluny_checklist_entries"


def _sync_checklist_sqlite(submission: Dict[str, Any]) -> None:
    path = os.environ.get("CLUNY_SQLITE_PATH") or os.environ.get("CLUNY_DATABASE_PATH")
    if not path:
        return
    path = _validate_sqlite_path(path)
    table = _checklist_table_name()
    raw = json.dumps(submission, ensure_ascii=False)
    with sqlite_connect(path) as conn:
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {table} (
                id INTEGER PRIMARY KEY,
                checklist_id TEXT NOT NULL,
                local_date TEXT NOT NULL,
                created_at TEXT NOT NULL,
                flow_version INTEGER,
                answers_json TEXT NOT NULL,
                raw_json TEXT NOT NULL
            )
            """
        )
        conn.execute(
            f"""
            INSERT OR REPLACE INTO {table}
            (id, checklist_id, local_date, created_at, flow_version, answers_json, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                submission.get("id"),
                submission.get("checklist_id", ""),
                submission.get("local_date", ""),
                submission.get("created_at", ""),
                int(submission.get("flow_version") or 0),
                json.dumps(submission.get("answers") or {}, ensure_ascii=False),
                raw,
            ),
        )


def _sync_checklist_http(submission: Dict[str, Any]) -> None:
    url = os.environ.get("CLUNY_CHECKLIST_INGEST_URL") or os.environ.get("CLUNY_INGEST_URL")
    if not url:
        return
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError("Cluny ingest URL must be https")
    payload = {
        "type": "checklist_submission",
        **submission,
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    key = os.environ.get("CLUNY_API_KEY")
    if key:
        req.add_header("Authorization", f"Bearer {key}")
    with _http_opener().open(req, timeout=60) as resp:
        resp.read()


def sync_checklist_submission_to_cluny(submission: Dict[str, Any]) -> None:
    if os.environ.get("CLUNY_SQLITE_PATH") or os.environ.get("CLUNY_DATABASE_PATH"):
        _sync_checklist_sqlite(submission)
    if os.environ.get("CLUNY_CHECKLIST_INGEST_URL") or os.environ.get("CLUNY_INGEST_URL"):
        _sync_checklist_http(submission)


def sync_checklist_submission_safe(submission: Dict[str, Any]) -> None:
    try:
        if not (
            os.environ.get("CLUNY_SQLITE_PATH")
            or os.environ.get("CLUNY_DATABASE_PATH")
            or os.environ.get("CLUNY_CHECKLIST_INGEST_URL")
            or os.environ.get("CLUNY_INGEST_URL")
        ):
            return
        sync_checklist_submission_to_cluny(submission)
    except (OSError, sqlite3.Error, urllib.error.URLError, ValueError) as e:
        print(f"[Cluny sync] Checklist failed (still saved locally): {e}")


def sync_journal_entry_to_cluny(entry: Dict[str, Any]) -> None:
    """Best-effort sync to Cluny. Raises only from HTTP/SQLite if you need strict mode."""
    if os.environ.get("CLUNY_SQLITE_PATH") or os.environ.get("CLUNY_DATABASE_PATH"):
        _sync_sqlite(entry)
    if os.environ.get("CLUNY_INGEST_URL"):
        _sync_http(entry)


def sync_journal_entry_safe(entry: Dict[str, Any]) -> None:
    """Never raises; prints errors for debugging."""
    try:
        if not (
            os.environ.get("CLUNY_SQLITE_PATH")
            or os.environ.get("CLUNY_DATABASE_PATH")
            or os.environ.get("CLUNY_INGEST_URL")
        ):
            return
        sync_journal_entry_to_cluny(entry)
    except (OSError, sqlite3.Error, urllib.error.URLError, ValueError) as e:
        print(f"[Cluny sync] Failed (entry still saved locally): {e}")
