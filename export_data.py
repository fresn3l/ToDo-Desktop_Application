"""
Export journal, workouts, and to dos to CSV, JSON, or markdown.
"""

from __future__ import annotations

import csv
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

import eel

import journal
import work
import workouts
from paths import data_directory


def _exports_dir() -> Path:
    d = data_directory() / "exports"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _write_json(name: str, payload: Any) -> Dict[str, Any]:
    path = _exports_dir() / f"{name}_{_stamp()}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    count = len(payload) if isinstance(payload, list) else 1
    return {"path": str(path.resolve()), "count": count, "format": "json"}


@eel.expose
def export_journal_json() -> Dict[str, Any]:
    return _write_json("journal", journal.get_all_entries())


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
def export_work_json() -> Dict[str, Any]:
    return _write_json("work", work.list_all_work_items())


@eel.expose
def export_work_csv() -> Dict[str, Any]:
    items = work.list_all_work_items()
    path = _exports_dir() / f"work_{_stamp()}.csv"
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "id",
                "title",
                "scheduled_date",
                "status",
                "duration_seconds",
                "series_id",
                "occurrence_date",
                "cadence_label",
            ]
        )
        for item in items:
            writer.writerow(
                [
                    item.get("id"),
                    item.get("title"),
                    item.get("scheduled_date") or "",
                    item.get("status"),
                    item.get("duration_seconds") or 0,
                    item.get("series_id") or "",
                    item.get("occurrence_date") or "",
                    item.get("cadence_label") or "",
                ]
            )
    return {"path": str(path.resolve()), "count": len(items), "format": "csv"}


@eel.expose
def export_workouts_json() -> Dict[str, Any]:
    return _write_json("workouts", workouts.list_all_workout_days())


@eel.expose
def export_workouts_csv() -> Dict[str, Any]:
    sessions = workouts.list_all_workout_sessions()
    path = _exports_dir() / f"workouts_{_stamp()}.csv"
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["id", "local_date", "kind", "label", "miles", "minutes"]
        )
        for session in sessions:
            writer.writerow(
                [
                    session.get("id"),
                    session.get("local_date"),
                    session.get("kind"),
                    session.get("label"),
                    session.get("miles") if session.get("miles") is not None else "",
                    session.get("minutes") if session.get("minutes") is not None else "",
                ]
            )
    return {"path": str(path.resolve()), "count": len(sessions), "format": "csv"}


@eel.expose
def get_exports_directory() -> str:
    return str(_exports_dir().resolve())


@eel.expose
def get_app_data_directory() -> str:
    return str(data_directory().resolve())


def _journal_date(entry: Dict[str, Any]) -> date | None:
    raw = entry.get("date") or entry.get("created_at") or ""
    try:
        return datetime.fromisoformat(str(raw)).date()
    except (ValueError, TypeError):
        return None


@eel.expose
def export_week_markdown(days: int = 7) -> Dict[str, Any]:
    """Write the last N days of journal, workouts, and to dos into markdown."""
    import daily_checklist

    days = max(1, min(int(days or 7), 90))
    end = date.today()
    start = end - timedelta(days=days - 1)

    by_date_journal: Dict[str, List[Dict[str, Any]]] = {}
    span = max(days + 1, 14)
    for entry in journal.get_recent_entries(days=span):
        ed = _journal_date(entry)
        if ed and start <= ed <= end:
            by_date_journal.setdefault(ed.isoformat(), []).append(entry)

    by_date_work: Dict[str, List[Dict[str, Any]]] = {}
    for item in work.list_all_work_items():
        iso = item.get("scheduled_date")
        if iso and start.isoformat() <= iso <= end.isoformat():
            by_date_work.setdefault(iso, []).append(item)

    by_date_workout: Dict[str, Dict[str, Any]] = {}
    for day in workouts.list_all_workout_days():
        iso = day.get("local_date")
        if iso and start.isoformat() <= iso <= end.isoformat():
            by_date_workout[iso] = day

    by_date_subs: Dict[str, List[Dict[str, Any]]] = {}
    try:
        submissions = daily_checklist.fetch_submissions(
            start_date=start.isoformat(),
            end_date=end.isoformat(),
            decorate=True,
        )
        for row in submissions:
            iso = row.get("local_date")
            if iso:
                by_date_subs.setdefault(iso, []).append(row)
    except Exception:
        pass

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

        day_journals = list(reversed(by_date_journal.get(iso, [])))
        day_work = by_date_work.get(iso, [])
        day_workout = by_date_workout.get(iso)
        day_subs = list(reversed(by_date_subs.get(iso, [])))
        if not day_journals and not day_work and not day_workout and not day_subs:
            lines.append("_Nothing recorded._")
            lines.append("")
        else:
            recorded_days += 1
            if day_workout:
                lines.append("### Workout")
                lines.append("")
                if day_workout.get("body_weight") is not None:
                    lines.append(f"- **Body weight:** {day_workout['body_weight']}")
                for session in day_workout.get("sessions") or []:
                    bits = [session.get("label") or session.get("kind")]
                    if session.get("miles") is not None:
                        bits.append(f"{session['miles']} mi")
                    if session.get("minutes") is not None:
                        bits.append(f"{session['minutes']} min")
                    lines.append(f"- {' · '.join(str(b) for b in bits if b)}")
                lines.append("")
            if day_work:
                lines.append("### To Do")
                lines.append("")
                for item in day_work:
                    status = item.get("status") or "open"
                    lines.append(f"- **{item.get('title')}** ({status})")
                lines.append("")
            for entry in day_journals:
                lines.append("### Journal")
                lines.append("")
                content = str(entry.get("content") or "").strip() or "_Empty entry._"
                lines.append(content)
                lines.append("")
            for sub in day_subs:
                title = sub.get("title") or sub.get("checklist_id") or "Earlier checklist"
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
