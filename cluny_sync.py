"""
Push journal entries into Cluny's storage after local save.

Configure from Settings → Cluny, or with environment variables (env wins):

  CLUNY_BRAIN_URL — Base URL for `cluny serve` (default http://127.0.0.1:8787).
      HTTPS, or HTTP on localhost. Ask, propose, and journal ingest use this.

  CLUNY_SQLITE_PATH — Optional sidecar copy into Cluny's SQLite file. Not the RAG path.
      Entries go into CLUNY_JOURNAL_TABLE (default: cluny_journal_entries).

  CLUNY_INGEST_URL — Optional override for POST /ingest/text. Default is {brain}/ingest/text.
      Body is { text, catalog, source, title, collection }. HTTPS, or HTTP on localhost.
      Optional: CLUNY_API_KEY as X-Cluny-Token and Authorization: Bearer.

Checklist submissions sync to CLUNY_CHECKLIST_TABLE when a SQLite path is set,
or to CLUNY_CHECKLIST_INGEST_URL / CLUNY_INGEST_URL.

Sync failures are logged; they do not block saving locally. The app stays usable
if Cluny is quit.
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
    "brain_url": "",
    "api_key": "",
    "journal_enabled": True,
    "checklist_enabled": True,
    "auto_start_brain": True,
    "cluny_binary_path": "",
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
            "brain_url": str(raw.get("brain_url") or "").strip(),
            "api_key": str(raw.get("api_key") or "").strip()[:200],
            "journal_enabled": raw.get("journal_enabled") is not False,
            "checklist_enabled": raw.get("checklist_enabled") is not False,
            "auto_start_brain": raw.get("auto_start_brain") is not False,
            "cluny_binary_path": str(raw.get("cluny_binary_path") or "").strip(),
        }


def _sanitize_file_settings(raw: Dict[str, Any]) -> Dict[str, Any]:
    sqlite_path = str(raw.get("sqlite_path") or "").strip()
    ingest_url = str(raw.get("ingest_url") or "").strip()
    brain_url = str(raw.get("brain_url") or "").strip()
    api_key = str(raw.get("api_key") or "").strip()
    if sqlite_path:
        sqlite_path = _validate_sqlite_path(sqlite_path)
    if ingest_url:
        ingest_url = _validate_ingest_url(ingest_url)
    if brain_url:
        import cluny_client

        brain_url = cluny_client.validate_brain_url(brain_url)
    return {
        "sqlite_path": sqlite_path,
        "ingest_url": ingest_url[:500],
        "brain_url": brain_url[:500],
        "api_key": api_key[:200],
        "journal_enabled": raw.get("journal_enabled") is not False,
        "checklist_enabled": raw.get("checklist_enabled") is not False,
        "auto_start_brain": raw.get("auto_start_brain") is not False,
        "cluny_binary_path": str(raw.get("cluny_binary_path") or "").strip()[:500],
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
    env_brain = (os.environ.get("CLUNY_BRAIN_URL") or "").strip()
    env_checklist = (os.environ.get("CLUNY_CHECKLIST_INGEST_URL") or "").strip()
    env_key = (os.environ.get("CLUNY_API_KEY") or "").strip()
    sqlite_path = env_sqlite or stored["sqlite_path"]
    ingest_url = env_ingest or stored["ingest_url"]
    brain_url = env_brain or stored["brain_url"] or "http://127.0.0.1:8787"
    checklist_url = env_checklist or env_ingest or stored["ingest_url"]
    api_key = env_key or stored["api_key"]
    return {
        "sqlite_path": sqlite_path,
        "ingest_url": ingest_url,
        "brain_url": brain_url,
        "checklist_ingest_url": checklist_url,
        "api_key": api_key,
        "journal_enabled": stored["journal_enabled"],
        "checklist_enabled": stored["checklist_enabled"],
        "env_overrides": {
            "sqlite_path": bool(env_sqlite),
            "ingest_url": bool(env_ingest),
            "brain_url": bool(env_brain),
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
    labels = {
        "sqlite_path": "SQLite path",
        "ingest_url": "ingest URL",
        "brain_url": "brain URL",
        "api_key": "API key",
    }
    if env_bits:
        env_note = "Environment variables override Settings for: " + ", ".join(
            labels[name] for name in env_bits
        )
    return {
        "sqlite_path": cfg["sqlite_path"],
        "ingest_url": cfg["ingest_url"],
        "brain_url": cfg["brain_url"],
        "api_key": cfg["api_key"],
        "journal_enabled": cfg["journal_enabled"],
        "checklist_enabled": cfg["checklist_enabled"],
        "auto_start_brain": _read_file_settings().get("auto_start_brain", True),
        "cluny_binary_path": _read_file_settings().get("cluny_binary_path", ""),
        "env_overrides": cfg["env_overrides"],
        "status_note": f"{journal}. {check[0].upper() + check[1:]}." if has_sink else "Ask uses http://127.0.0.1:8787 when Cluny is running. SQLite copy is optional.",
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
    if "brain_url" in raw:
        incoming["brain_url"] = str(raw.get("brain_url") or "").strip()
    if "api_key" in raw:
        incoming["api_key"] = str(raw.get("api_key") or "").strip()
    if "journal_enabled" in raw:
        incoming["journal_enabled"] = bool(raw.get("journal_enabled"))
    if "checklist_enabled" in raw:
        incoming["checklist_enabled"] = bool(raw.get("checklist_enabled"))
    if "auto_start_brain" in raw:
        incoming["auto_start_brain"] = bool(raw.get("auto_start_brain"))
    if "cluny_binary_path" in raw:
        incoming["cluny_binary_path"] = str(raw.get("cluny_binary_path") or "").strip()
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
    import cluny_client

    payload = cluny_client.journal_ingest_payload(entry)
    if not str(payload.get("text") or "").strip():
        return
    cluny_client.ingest_text(
        payload["text"],
        title=str(payload.get("title") or ""),
        source=str(payload.get("source") or "kosistenz-journal"),
        collection=str(payload.get("collection") or "journal"),
    )


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
    _sync_http(entry)


def sync_journal_entry_safe(entry: Dict[str, Any]) -> None:
    """Never raises; prints errors for debugging."""
    try:
        cfg = effective_cluny_config()
        if not cfg["journal_enabled"]:
            return
        sync_journal_entry_to_cluny(entry)
    except (OSError, sqlite3.Error, urllib.error.URLError, ValueError) as e:
        print(f"[Cluny sync] Failed (entry still saved locally): {e}")


def _analytics_sync_path() -> Path:
    return data_directory() / "cluny_analytics_sync.json"


def _load_analytics_sync_state() -> Dict[str, Any]:
    path = _analytics_sync_path()
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
        return raw if isinstance(raw, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save_analytics_sync_state(state: Dict[str, Any]) -> None:
    path = _analytics_sync_path()
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2)
    os.replace(tmp, path)


def sync_analytics_rollup_safe() -> Dict[str, Any]:
    """Weekly analytics rollup into Cluny library (collection: analytics)."""
    import cluny_client
    import insights

    try:
        data = insights.get_analytics(7)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    week_key = str(data.get("week_key") or "")
    if not week_key:
        return {"ok": False, "error": "missing week_key"}
    state = _load_analytics_sync_state()
    if state.get("week_key") == week_key:
        return {"ok": True, "skipped": True, "week_key": week_key}
    work_stats = data.get("work") or {}
    journal = data.get("journal") or {}
    lines = [
        f"Weekly analytics {week_key}",
        f"Period: {data.get('period_start')} – {data.get('period_end')}",
        f"Journal entries: {journal.get('entries', 0)}",
        f"Journal streak: {journal.get('streak', 0)} days",
        f"Writing minutes: {journal.get('minutes', 0)}",
        f"Dated tasks done: {work_stats.get('dated_done', 0)}",
        f"Repeat missed: {work_stats.get('repeat_missed', 0)}",
        f"Show-up streak: {data.get('show_up_streak', 0)}",
    ]
    text = "\n".join(str(line) for line in lines if line)
    try:
        cluny_client.ingest_text(
            text,
            title=f"analytics-{week_key}",
            source="kosistenz-analytics",
            collection="analytics",
        )
    except ValueError as exc:
        return {"ok": False, "error": str(exc), "week_key": week_key}
    _save_analytics_sync_state({"week_key": week_key, "synced_at": data.get("period_end")})
    return {"ok": True, "synced": True, "week_key": week_key}


def sync_task_mirror_safe(item: Dict[str, Any]) -> None:
    """Mirror a Kosistenz todo to Cluny /tasks/sync (best-effort)."""
    import cluny_client

    item_id = str(item.get("id") or "").strip()
    title = str(item.get("title") or "").strip()
    if not item_id or not title:
        return
    status = str(item.get("status") or "open")
    mirror_status = "done" if status == "done" else "open"
    due = item.get("due_at") or item.get("due")
    due_at = str(due)[:19] if due else None
    notes = str(item.get("notes") or "").strip() or None
    try:
        if not cluny_client.health().get("brain_ready"):
            return
        cluny_client.sync_task(
            external_id=item_id,
            title=title,
            status=mirror_status,
            due_at=due_at,
            notes=notes,
        )
    except ValueError as exc:
        print(f"[Cluny sync] Task mirror failed: {exc}")


def delete_task_mirror_safe(external_id: str) -> None:
    import cluny_client

    item_id = str(external_id or "").strip()
    if not item_id:
        return
    try:
        if not cluny_client.health().get("brain_ready"):
            return
        cluny_client.delete_synced_task(item_id)
    except ValueError as exc:
        print(f"[Cluny sync] Task delete mirror failed: {exc}")

