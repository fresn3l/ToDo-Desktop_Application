"""
Export checklist and journal data to CSV or JSON.
"""

from __future__ import annotations

import csv
import json
from datetime import date, datetime, timedelta
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


def _journal_date(entry: Dict[str, Any]) -> date | None:
    raw = entry.get("date") or entry.get("created_at") or ""
    try:
        return datetime.fromisoformat(str(raw)).date()
    except (ValueError, TypeError):
        return None


@eel.expose
def export_week_markdown(days: int = 7) -> Dict[str, Any]:
    """Write the last N days of checklist + journal into a markdown file."""
    days = max(1, min(int(days or 7), 90))
    end = date.today()
    start = end - timedelta(days=days - 1)

    submissions = daily_checklist.fetch_submissions(
        start_date=start.isoformat(),
        end_date=end.isoformat(),
        decorate=True,
    )
    by_date_subs: Dict[str, List[Dict[str, Any]]] = {}
    for row in submissions:
        iso = row.get("local_date")
        if iso:
            by_date_subs.setdefault(iso, []).append(row)

    by_date_journal: Dict[str, List[Dict[str, Any]]] = {}
    span = max(days + 1, 14)
    for entry in journal.get_recent_entries(days=span):
        ed = _journal_date(entry)
        if ed and start <= ed <= end:
            by_date_journal.setdefault(ed.isoformat(), []).append(entry)

    lines = [
        f"# Kosistenz week {start.isoformat()} – {end.isoformat()}",
        "",
    ]
    recorded_days = 0
    cursor = start
    while cursor <= end:
        iso = cursor.isoformat()
        weekday = cursor.strftime("%A")
        lines.append(f"## {weekday}, {iso}")
        lines.append("")

        day_subs = list(reversed(by_date_subs.get(iso, [])))
        day_journals = list(reversed(by_date_journal.get(iso, [])))
        if not day_subs and not day_journals:
            lines.append("_Nothing recorded._")
            lines.append("")
        else:
            recorded_days += 1
            for sub in day_subs:
                title = sub.get("title") or sub.get("checklist_id") or "Checklist"
                lines.append(f"### {title}")
                lines.append("")
                formatted = sub.get("answers_formatted") or []
                if formatted:
                    for qa in formatted:
                        label = qa.get("label") or qa.get("key") or "Item"
                        value = str(qa.get("value") or "").replace("\n", " ").strip()
                        lines.append(f"- **{label}:** {value}")
                else:
                    lines.append("_No answers stored._")
                lines.append("")
            for entry in day_journals:
                lines.append("### Journal")
                lines.append("")
                content = str(entry.get("content") or "").strip() or "_Empty entry._"
                lines.append(content)
                lines.append("")
        cursor += timedelta(days=1)

    path = _exports_dir() / f"week_{start.isoformat()}_{end.isoformat()}_{_stamp()}.md"
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {
        "path": str(path.resolve()),
        "count": recorded_days,
        "days": days,
        "format": "markdown",
        "start": start.isoformat(),
        "end": end.isoformat(),
    }
