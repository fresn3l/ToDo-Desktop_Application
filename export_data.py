"""
Export checklist and journal data to CSV or JSON.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import eel

import daily_checklist
import journal


def _exports_dir() -> Path:
    d = daily_checklist.get_data_directory() / "exports"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _flatten_answer(val: Any) -> str:
    if val is True:
        return "yes"
    if val is False:
        return "no"
    if val is None:
        return ""
    if isinstance(val, (int, float, str)):
        return str(val)
    if isinstance(val, dict):
        duration = val.get("durationMinutes")
        if "answer" in val:
            base = _flatten_answer(val["answer"])
        elif val.get("value") == "other":
            base = f"other:{val.get('otherText', '')}"
        elif "value" in val:
            base = str(val.get("value", ""))
        else:
            base = ""
        if duration is not None:
            extra = f"duration_min={duration}"
            return f"{base}|{extra}" if base else extra
        return base or json.dumps(val, ensure_ascii=False)
    return json.dumps(val, ensure_ascii=False)


@eel.expose
def export_checklist_json() -> Dict[str, Any]:
    rows = daily_checklist.fetch_submissions(decorate=True)
    path = _exports_dir() / f"checklist_{_stamp()}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
    return {"path": str(path.resolve()), "count": len(rows), "format": "json"}


@eel.expose
def export_checklist_csv() -> Dict[str, Any]:
    rows = daily_checklist.fetch_submissions(decorate=False)
    path = _exports_dir() / f"checklist_{_stamp()}.csv"
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["submission_id", "local_date", "created_at", "checklist_id", "question_key", "answer"]
        )
        for row in rows:
            answers = row.get("answers") or {}
            if not answers:
                writer.writerow(
                    [row["id"], row["local_date"], row["created_at"], row.get("checklist_id"), "", ""]
                )
                continue
            for key, val in answers.items():
                writer.writerow(
                    [
                        row["id"],
                        row["local_date"],
                        row["created_at"],
                        row.get("checklist_id"),
                        key,
                        _flatten_answer(val),
                    ]
                )
    return {"path": str(path.resolve()), "count": len(rows), "format": "csv"}


@eel.expose
def export_journal_json() -> Dict[str, Any]:
    entries = journal.get_all_entries()
    path = _exports_dir() / f"journal_{_stamp()}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
    return {"path": str(path.resolve()), "count": len(entries), "format": "json"}


@eel.expose
def export_journal_csv() -> Dict[str, Any]:
    entries = journal.get_all_entries()
    path = _exports_dir() / f"journal_{_stamp()}.csv"
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["id", "date", "content", "duration_seconds", "continued", "tags"]
        )
        for e in entries:
            tags = e.get("tags") or []
            writer.writerow(
                [
                    e.get("id"),
                    e.get("date") or e.get("created_at"),
                    e.get("content", ""),
                    e.get("duration_seconds", 0),
                    1 if e.get("continued") else 0,
                    ",".join(tags) if isinstance(tags, list) else "",
                ]
            )
    return {"path": str(path.resolve()), "count": len(entries), "format": "csv"}


@eel.expose
def get_exports_directory() -> str:
    return str(_exports_dir().resolve())
