"""
Push journal entries into Cluny's storage after local save.

Configure from Settings → Cluny, or with environment variables (env wins):

  CLUNY_SQLITE_PATH — Path to Cluny's SQLite database file. Entries are inserted
      into table CLUNY_JOURNAL_TABLE (default: cluny_journal_entries), created if missing.

  CLUNY_INGEST_URL — HTTP endpoint that accepts POST JSON (same shape as the entry dict).
      Optional: CLUNY_API_KEY sent as Authorization: Bearer <key>.
      HTTPS, or HTTP on localhost.

Checklist submissions sync to CLUNY_CHECKLIST_TABLE (default: cluny_checklist_entries)
when a SQLite path is set, or to CLUNY_CHECKLIST_INGEST_URL / CLUNY_INGEST_URL.

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

import eel

from db import sqlite_connect
from paths import data_directory

_FILE_DEFAULTS: Dict[str, Any] = {
    "sqlite_path": "",
    "ingest_url": "",
    "api_key": "",
    "journal_enabled": True,
    "checklist_enabled": True,
}


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


def _settings_path() -> Path:
    return data_directory() / "cluny_settings.json"


def _read_file_settings() -> Dict[str, Any]:
    path = _settings_path()
    if not path.exists():
        return dict(_FILE_DEFAULTS)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return dict(_FILE_DEFAULTS)
    if not isinstance(raw, dict):
        return dict(_FILE_DEFAULTS)
    try:
        return _sanitize_file_settings(raw)
    except ValueError:
        return {
            "sqlite_path": str(raw.get("sqlite_path") or "").strip(),
            "ingest_url": str(raw.get("ingest_url") or "").strip(),
            "api_key": str(raw.get("api_key") or "").strip()[:200],
            "journal_enabled": raw.get("journal_enabled") is not False,
            "checklist_enabled": raw.get("checklist_enabled") is not False,
        }


def _sanitize_file_settings(raw: Dict[str, Any]) -> Dict[str, Any]:
    sqlite_path = str(raw.get("sqlite_path") or "").strip()
    ingest_url = str(raw.get("ingest_url") or "").strip()
    api_key = str(raw.get("api_key") or "").strip()
    if sqlite_path:
        sqlite_path = _validate_sqlite_path(sqlite_path)
    if ingest_url:
        ingest_url = _validate_ingest_url(ingest_url)
    return {
        "sqlite_path": sqlite_path,
        "ingest_url": ingest_url[:500],
        "api_key": api_key[:200],
        "journal_enabled": raw.get("journal_enabled") is not False,
        "checklist_enabled": raw.get("checklist_enabled") is not False,
    }


def _write_file_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    packed = _sanitize_file_settings(settings)
    path = _settings_path()
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(packed, handle, indent=2)
    os.replace(tmp, path)
    return packed


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


def _validate_ingest_url(raw: str) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""
    parsed = urlparse(text)
    host = (parsed.hostname or "").lower()
    loopback = host in ("127.0.0.1", "localhost", "::1")
    if parsed.scheme == "https":
        return text
    if parsed.scheme == "http" and loopback:
        return text
    raise ValueError("Ingest URL must be https, or http on localhost")


def effective_cluny_config() -> Dict[str, Any]:
    """Env vars override the Settings file. Empty file + empty env means off."""
    stored = _read_file_settings()
    env_sqlite = (os.environ.get("CLUNY_SQLITE_PATH") or os.environ.get("CLUNY_DATABASE_PATH") or "").strip()
    env_ingest = (os.environ.get("CLUNY_INGEST_URL") or "").strip()
    env_checklist = (os.environ.get("CLUNY_CHECKLIST_INGEST_URL") or "").strip()
    env_key = (os.environ.get("CLUNY_API_KEY") or "").strip()
    sqlite_path = env_sqlite or stored["sqlite_path"]
    ingest_url = env_ingest or stored["ingest_url"]
    checklist_url = env_checklist or env_ingest or stored["ingest_url"]
    api_key = env_key or stored["api_key"]
    return {
        "sqlite_path": sqlite_path,
        "ingest_url": ingest_url,
        "checklist_ingest_url": checklist_url,
        "api_key": api_key,
        "journal_enabled": stored["journal_enabled"],
        "checklist_enabled": stored["checklist_enabled"],
        "env_overrides": {
            "sqlite_path": bool(env_sqlite),
            "ingest_url": bool(env_ingest),
            "api_key": bool(env_key),
        },
    }


def public_cluny_settings() -> Dict[str, Any]:
    cfg = effective_cluny_config()
    has_sink = bool(cfg["sqlite_path"] or cfg["ingest_url"])
    bits = []
    if cfg["sqlite_path"]:
        bits.append("SQLite")
    if cfg["ingest_url"]:
        bits.append("ingest URL")
    if has_sink and cfg["journal_enabled"]:
        journal = "Journal copies after save"
    elif has_sink:
        journal = "Journal push is off"
    else:
        journal = "Not configured"
    if has_sink and cfg["checklist_enabled"]:
        check = "check-in copies after save"
    elif has_sink:
        check = "check-in push is off"
    else:
        check = "not configured"
    env_bits = [name for name, on in cfg["env_overrides"].items() if on]
    env_note = ""
    if env_bits:
        env_note = "Environment variables override Settings for: " + ", ".join(
            {"sqlite_path": "SQLite path", "ingest_url": "ingest URL", "api_key": "API key"}[name]
            for name in env_bits
        )
    return {
        "sqlite_path": cfg["sqlite_path"],
        "ingest_url": cfg["ingest_url"],
        "api_key": cfg["api_key"],
        "journal_enabled": cfg["journal_enabled"],
        "checklist_enabled": cfg["checklist_enabled"],
        "env_overrides": cfg["env_overrides"],
        "status_note": f"{journal}. {check[0].upper() + check[1:]}." if has_sink else "Off until you set a SQLite path or ingest URL.",
        "env_note": env_note,
        "configured": has_sink,
    }


@eel.expose
def get_cluny_settings() -> Dict[str, Any]:
    return public_cluny_settings()


@eel.expose
def save_cluny_settings(raw: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("Invalid Cluny settings")
    stored = _read_file_settings()
    incoming = dict(stored)
    if "sqlite_path" in raw:
        incoming["sqlite_path"] = str(raw.get("sqlite_path") or "").strip()
    if "ingest_url" in raw:
        incoming["ingest_url"] = str(raw.get("ingest_url") or "").strip()
    if "api_key" in raw:
        incoming["api_key"] = str(raw.get("api_key") or "").strip()
    if "journal_enabled" in raw:
        incoming["journal_enabled"] = bool(raw.get("journal_enabled"))
    if "checklist_enabled" in raw:
        incoming["checklist_enabled"] = bool(raw.get("checklist_enabled"))
    _write_file_settings(incoming)
    return public_cluny_settings()


def _sync_sqlite(entry: Dict[str, Any]) -> None:
    path = effective_cluny_config()["sqlite_path"]
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


def _post_json(url: str, payload: Dict[str, Any], api_key: str) -> None:
    url = _validate_ingest_url(url)
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    if api_key:
        req.add_header("Authorization", f"Bearer {api_key}")
    with _http_opener().open(req, timeout=60) as resp:
        resp.read()


def _sync_http(entry: Dict[str, Any]) -> None:
    cfg = effective_cluny_config()
    url = cfg["ingest_url"]
    if not url:
        return
    _post_json(url, entry, cfg["api_key"])


def _checklist_table_name() -> str:
    raw = os.environ.get("CLUNY_CHECKLIST_TABLE", "cluny_checklist_entries")
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", raw or ""):
        return raw
    return "cluny_checklist_entries"


def _sync_checklist_sqlite(submission: Dict[str, Any]) -> None:
    path = effective_cluny_config()["sqlite_path"]
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
    cfg = effective_cluny_config()
    url = cfg["checklist_ingest_url"]
    if not url:
        return
    payload = {
        "type": "checklist_submission",
        **submission,
    }
    _post_json(url, payload, cfg["api_key"])


def sync_checklist_submission_to_cluny(submission: Dict[str, Any]) -> None:
    cfg = effective_cluny_config()
    if not cfg["checklist_enabled"]:
        return
    if cfg["sqlite_path"]:
        _sync_checklist_sqlite(submission)
    if cfg["checklist_ingest_url"]:
        _sync_checklist_http(submission)


def sync_checklist_submission_safe(submission: Dict[str, Any]) -> None:
    try:
        cfg = effective_cluny_config()
        if not cfg["checklist_enabled"]:
            return
        if not (cfg["sqlite_path"] or cfg["checklist_ingest_url"]):
            return
        sync_checklist_submission_to_cluny(submission)
    except (OSError, sqlite3.Error, urllib.error.URLError, ValueError) as e:
        print(f"[Cluny sync] Checklist failed (still saved locally): {e}")


def sync_journal_entry_to_cluny(entry: Dict[str, Any]) -> None:
    """Best-effort sync to Cluny. Raises only from HTTP/SQLite if you need strict mode."""
    cfg = effective_cluny_config()
    if not cfg["journal_enabled"]:
        return
    if cfg["sqlite_path"]:
        _sync_sqlite(entry)
    if cfg["ingest_url"]:
        _sync_http(entry)


def sync_journal_entry_safe(entry: Dict[str, Any]) -> None:
    """Never raises; prints errors for debugging."""
    try:
        cfg = effective_cluny_config()
        if not cfg["journal_enabled"]:
            return
        if not (cfg["sqlite_path"] or cfg["ingest_url"]):
            return
        sync_journal_entry_to_cluny(entry)
    except (OSError, sqlite3.Error, urllib.error.URLError, ValueError) as e:
        print(f"[Cluny sync] Failed (entry still saved locally): {e}")
