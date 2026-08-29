"""
JSON pack for the iPhone companion.

SQLite stays on the Mac. Both apps read/write JSON files in iCloud Drive
(or a local fallback folder) so one Apple ID can keep Today in sync.
"""

from __future__ import annotations

import json
import os
import socket
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import eel

import appearance
import journal
import work
import workouts
from paths import data_directory

SCHEMA = 1
SETTINGS_NAME = "icloud_sync.json"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def default_sync_dir() -> Path:
    if os.environ.get("KOSISTENZ_DATA_DIR"):
        return data_directory() / "iCloudPack"
    icloud = Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "Kosistenz"
    if icloud.parent.is_dir():
        return icloud
    return data_directory() / "iCloudPack"


def _settings_path() -> Path:
    return data_directory() / SETTINGS_NAME


def load_settings() -> Dict[str, Any]:
    path = _settings_path()
    raw: Dict[str, Any] = {}
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                raw = loaded
        except (OSError, json.JSONDecodeError):
            raw = {}
    folder = str(raw.get("folder") or default_sync_dir())
    return {
        "folder": folder,
        "auto": bool(raw.get("auto")) if "auto" in raw else False,
        "using_icloud_drive": "com~apple~CloudDocs" in folder.replace("\\", "/"),
    }


def save_settings(partial: Dict[str, Any]) -> Dict[str, Any]:
    current = load_settings()
    folder = partial.get("folder")
    if isinstance(folder, str) and folder.strip():
        current["folder"] = str(Path(folder.strip()).expanduser())
    if "auto" in partial:
        current["auto"] = bool(partial["auto"])
    path = _settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump({"folder": current["folder"], "auto": current["auto"]}, handle, indent=2)
    os.replace(tmp, path)
    return load_settings()


def sync_dir() -> Path:
    path = Path(load_settings()["folder"]).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def _read_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback
    return data


def _newer(incoming: Optional[str], existing: Optional[str]) -> bool:
    left = str(incoming or "")
    right = str(existing or "")
    if not left:
        return False
    if not right:
        return True
    return left > right


def _dump_work() -> Dict[str, Any]:
    items = work.list_all_work_items()
    slim = []
    for item in items:
        slim.append(
            {
                "id": item["id"],
                "title": item["title"],
                "notes": item.get("notes") or "",
                "scheduled_date": item.get("scheduled_date"),
                "status": item["status"],
                "active_started_at": item.get("active_started_at"),
                "finished_at": item.get("finished_at"),
                "duration_seconds": item.get("stored_duration_seconds") or 0,
                "sort_order": item.get("sort_order") or 0,
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
                "source": item.get("source") or "manual",
                "series_id": item.get("series_id"),
                "occurrence_date": item.get("occurrence_date"),
            }
        )
    with work._connect() as conn:
        series = [dict(row) for row in conn.execute("SELECT * FROM work_series")]
        exceptions = [dict(row) for row in conn.execute("SELECT * FROM work_exceptions")]
    return {"items": slim, "series": series, "exceptions": exceptions}


def _dump_workouts() -> Dict[str, Any]:
    with workouts._connect() as conn:
        days = [dict(row) for row in conn.execute("SELECT * FROM workout_days ORDER BY local_date")]
        sessions = [dict(row) for row in conn.execute("SELECT * FROM workout_sessions ORDER BY created_at")]
    return {
        "days": days,
        "sessions": sessions,
        "template": workouts.load_week_template(),
    }


def _apply_work(payload: Dict[str, Any]) -> Dict[str, int]:
    items = payload.get("items") if isinstance(payload, dict) else None
    series = payload.get("series") if isinstance(payload, dict) else None
    exceptions = payload.get("exceptions") if isinstance(payload, dict) else None
    applied = 0
    with work._connect() as conn:
        for row in series or []:
            if not isinstance(row, dict) or not row.get("id"):
                continue
            existing = conn.execute("SELECT updated_at FROM work_series WHERE id = ?", (row["id"],)).fetchone()
            if existing and not _newer(row.get("updated_at"), existing["updated_at"]):
                continue
            conn.execute(
                """
                INSERT INTO work_series (id, title, notes, cadence_json, start_date, end_date, created_at, updated_at, archived)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    notes = excluded.notes,
                    cadence_json = excluded.cadence_json,
                    start_date = excluded.start_date,
                    end_date = excluded.end_date,
                    updated_at = excluded.updated_at,
                    archived = excluded.archived
                """,
                (
                    row["id"],
                    row.get("title") or "",
                    row.get("notes") or "",
                    row.get("cadence_json") or "{}",
                    row.get("start_date") or datetime.now().date().isoformat(),
                    row.get("end_date"),
                    row.get("created_at") or _now(),
                    row.get("updated_at") or _now(),
                    int(row.get("archived") or 0),
                ),
            )
            applied += 1
        for row in items or []:
            if not isinstance(row, dict) or not row.get("id"):
                continue
            existing = conn.execute("SELECT updated_at FROM work_items WHERE id = ?", (row["id"],)).fetchone()
            if existing and not _newer(row.get("updated_at"), existing["updated_at"]):
                continue
            conn.execute(
                """
                INSERT INTO work_items (
                    id, title, notes, scheduled_date, status, active_started_at, finished_at,
                    duration_seconds, sort_order, created_at, updated_at, source, series_id, occurrence_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    notes = excluded.notes,
                    scheduled_date = excluded.scheduled_date,
                    status = excluded.status,
                    active_started_at = excluded.active_started_at,
                    finished_at = excluded.finished_at,
                    duration_seconds = excluded.duration_seconds,
                    sort_order = excluded.sort_order,
                    updated_at = excluded.updated_at,
                    source = excluded.source,
                    series_id = excluded.series_id,
                    occurrence_date = excluded.occurrence_date
                """,
                (
                    row["id"],
                    row.get("title") or "",
                    row.get("notes") or "",
                    row.get("scheduled_date"),
                    row.get("status") or "open",
                    row.get("active_started_at"),
                    row.get("finished_at"),
                    int(row.get("duration_seconds") or 0),
                    int(row.get("sort_order") or 0),
                    row.get("created_at") or _now(),
                    row.get("updated_at") or _now(),
                    row.get("source") or "manual",
                    row.get("series_id"),
                    row.get("occurrence_date"),
                ),
            )
            applied += 1
        for row in exceptions or []:
            if not isinstance(row, dict) or not row.get("series_id") or not row.get("occurrence_date"):
                continue
            conn.execute(
                """
                INSERT INTO work_exceptions (series_id, occurrence_date, action, title)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(series_id, occurrence_date) DO UPDATE SET
                    action = excluded.action,
                    title = excluded.title
                """,
                (
                    row["series_id"],
                    row["occurrence_date"],
                    row.get("action") or "skip",
                    row.get("title"),
                ),
            )
            applied += 1
        conn.commit()
    return {"work": applied}


def _apply_workouts(payload: Dict[str, Any]) -> Dict[str, int]:
    applied = 0
    days = payload.get("days") if isinstance(payload, dict) else None
    sessions = payload.get("sessions") if isinstance(payload, dict) else None
    template = payload.get("template") if isinstance(payload, dict) else None
    with workouts._connect() as conn:
        for row in days or []:
            if not isinstance(row, dict) or not row.get("local_date"):
                continue
            existing = conn.execute(
                "SELECT updated_at FROM workout_days WHERE local_date = ?",
                (row["local_date"],),
            ).fetchone()
            if existing and not _newer(row.get("updated_at"), existing["updated_at"]):
                continue
            conn.execute(
                """
                INSERT INTO workout_days (local_date, body_weight, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(local_date) DO UPDATE SET
                    body_weight = excluded.body_weight,
                    notes = excluded.notes,
                    updated_at = excluded.updated_at
                """,
                (
                    row["local_date"],
                    row.get("body_weight"),
                    row.get("notes") or "",
                    row.get("created_at") or _now(),
                    row.get("updated_at") or _now(),
                ),
            )
            applied += 1
        for row in sessions or []:
            if not isinstance(row, dict) or not row.get("id"):
                continue
            exists = conn.execute("SELECT 1 FROM workout_sessions WHERE id = ?", (row["id"],)).fetchone()
            if exists:
                continue
            conn.execute(
                """
                INSERT INTO workout_sessions (id, local_date, kind, other_label, miles, minutes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["id"],
                    row.get("local_date") or datetime.now().date().isoformat(),
                    row.get("kind") or "other",
                    row.get("other_label") or "",
                    row.get("miles"),
                    row.get("minutes"),
                    row.get("created_at") or _now(),
                ),
            )
            applied += 1
        conn.commit()
    if isinstance(template, dict) and template:
        workouts.save_week_template(template)
        applied += 1
    return {"workouts": applied}


def _apply_journal(entries: List[Any]) -> Dict[str, int]:
    existing_ids = {entry.get("id") for entry in journal.get_all_entries()}
    applied = 0
    for entry in entries or []:
        if not isinstance(entry, dict) or not entry.get("content"):
            continue
        entry_id = entry.get("id")
        if entry_id and entry_id in existing_ids:
            continue
        if journal.import_journal_entry(entry):
            applied += 1
    return {"journal": applied}


def build_pack() -> Dict[str, Any]:
    return {
        "manifest": {
            "schema": SCHEMA,
            "exported_at": _now(),
            "device": socket.gethostname(),
        },
        "work": _dump_work(),
        "workouts": _dump_workouts(),
        "journal": journal.get_all_entries(),
        "appearance": appearance.get_appearance_settings(),
    }


def write_pack(folder: Optional[Path] = None) -> Dict[str, Any]:
    dest = Path(folder) if folder else sync_dir()
    dest.mkdir(parents=True, exist_ok=True)
    pack = build_pack()
    _write_json(dest / "manifest.json", pack["manifest"])
    _write_json(dest / "work.json", pack["work"])
    _write_json(dest / "workouts.json", pack["workouts"])
    _write_json(dest / "journal.json", pack["journal"])
    _write_json(dest / "appearance.json", pack["appearance"])
    if not _settings_path().exists():
        save_settings({"folder": str(dest), "auto": True})
    return {"ok": True, "folder": str(dest), "exported_at": pack["manifest"]["exported_at"]}


def read_pack(folder: Optional[Path] = None) -> Dict[str, Any]:
    src = Path(folder) if folder else sync_dir()
    return {
        "manifest": _read_json(src / "manifest.json", {}),
        "work": _read_json(src / "work.json", {"items": [], "series": [], "exceptions": []}),
        "workouts": _read_json(src / "workouts.json", {"days": [], "sessions": [], "template": {}}),
        "journal": _read_json(src / "journal.json", []),
        "appearance": _read_json(src / "appearance.json", {}),
        "folder": str(src),
    }


def apply_pack(folder: Optional[Path] = None) -> Dict[str, Any]:
    global _exporting
    pack = read_pack(folder)
    _exporting = True
    try:
        counts = {}
        counts.update(_apply_work(pack.get("work") or {}))
        counts.update(_apply_workouts(pack.get("workouts") or {}))
        journal_list = pack.get("journal")
        counts.update(_apply_journal(journal_list if isinstance(journal_list, list) else []))
        incoming_appearance = pack.get("appearance")
        if isinstance(incoming_appearance, dict) and incoming_appearance:
            appearance.save_appearance_settings(incoming_appearance)
            counts["appearance"] = 1
        try:
            work.refresh_widget_snapshot()
        except Exception:
            pass
        result = {"ok": True, "folder": pack.get("folder"), "applied": counts}
    finally:
        _exporting = False
    try:
        write_pack(Path(result["folder"]) if result.get("folder") else None)
    except (OSError, TypeError, NameError):
        pass
    return result


_exporting = False


def export_if_enabled() -> None:
    global _exporting
    if _exporting:
        return
    if not _settings_path().exists() or not load_settings().get("auto"):
        return
    _exporting = True
    try:
        write_pack()
    except OSError:
        pass
    finally:
        _exporting = False


@eel.expose
def get_icloud_sync_status() -> Dict[str, Any]:
    settings = load_settings()
    folder = Path(settings["folder"])
    manifest = _read_json(folder / "manifest.json", {})
    return {
        **settings,
        "folder_exists": folder.is_dir(),
        "last_export": manifest.get("exported_at") if isinstance(manifest, dict) else None,
        "last_device": manifest.get("device") if isinstance(manifest, dict) else None,
        "default_folder": str(default_sync_dir()),
    }


@eel.expose
def save_icloud_sync_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    saved = save_settings(settings if isinstance(settings, dict) else {})
    status = get_icloud_sync_status()
    status.update(saved)
    return status


@eel.expose
def push_icloud_pack() -> Dict[str, Any]:
    return write_pack()


@eel.expose
def pull_icloud_pack() -> Dict[str, Any]:
    return apply_pack()
