"""
Kosistenz calendar — hard events, deadline ingest, and the week clock.

SQLite lives next to the work database. Apple Calendar is a read-only feed.
Generated study blocks are never written back to EventKit.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import eel

import work

SETTINGS_NAME = "calendar_feeds.json"
DEFAULT_ESTIMATE = 60
MAX_ICS_BYTES = 2 * 1024 * 1024
CHUNK_MIN = 50
CHUNK_MAX = 90
DAY_START = "07:00"
DAY_END = "22:00"
BLOCK_STATUSES = ("proposed", "locked", "done", "skipped")


def _now() -> datetime:
    return datetime.now().replace(microsecond=0)


def _db_path() -> Path:
    return work._data_dir() / "calendar.sqlite"


def _settings_path() -> Path:
    return work._data_dir() / SETTINGS_NAME


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS calendar_events (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            start_at TEXT NOT NULL,
            end_at TEXT NOT NULL,
            all_day INTEGER NOT NULL DEFAULT 0,
            recurrence_json TEXT,
            source TEXT NOT NULL DEFAULT 'kosistenz',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schedule_blocks (
            id TEXT PRIMARY KEY,
            work_item_id TEXT,
            title TEXT NOT NULL,
            local_date TEXT NOT NULL,
            start_at TEXT NOT NULL,
            end_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'proposed',
            kind TEXT NOT NULL DEFAULT 'work',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_blocks_date ON schedule_blocks(local_date)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_blocks_work ON schedule_blocks(work_item_id)"
    )
    return conn


def load_settings() -> Dict[str, Any]:
    raw: Dict[str, Any] = {}
    path = _settings_path()
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                raw = loaded
        except (OSError, json.JSONDecodeError):
            raw = {}
    return {
        "ics_url": str(raw.get("ics_url") or ""),
        "day_start": str(raw.get("day_start") or DAY_START),
        "day_end": str(raw.get("day_end") or DAY_END),
        "default_estimate_minutes": int(raw.get("default_estimate_minutes") or DEFAULT_ESTIMATE),
        "chunk_min": int(raw.get("chunk_min") or CHUNK_MIN),
        "chunk_max": int(raw.get("chunk_max") or CHUNK_MAX),
    }


@eel.expose
def get_calendar_settings() -> Dict[str, Any]:
    return load_settings()


@eel.expose
def save_calendar_settings(partial: Dict[str, Any]) -> Dict[str, Any]:
    current = load_settings()
    incoming = partial if isinstance(partial, dict) else {}
    if "ics_url" in incoming:
        url = str(incoming.get("ics_url") or "").strip()
        if url:
            parsed = urlparse(url)
            if parsed.scheme not in ("https", "webcal"):
                raise ValueError("Calendar URL must be https")
        current["ics_url"] = url.replace("webcal://", "https://", 1) if url else ""
    if incoming.get("day_start"):
        current["day_start"] = _parse_hhmm(str(incoming["day_start"]))
    if incoming.get("day_end"):
        current["day_end"] = _parse_hhmm(str(incoming["day_end"]))
    if "default_estimate_minutes" in incoming:
        minutes = work._parse_estimate(incoming.get("default_estimate_minutes"))
        current["default_estimate_minutes"] = minutes or DEFAULT_ESTIMATE
    path = _settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(current, handle, indent=2)
    os.replace(tmp, path)
    return load_settings()


def _parse_hhmm(raw: str) -> str:
    text = str(raw or "").strip()
    match = re.fullmatch(r"(\d{1,2}):(\d{2})", text)
    if not match:
        raise ValueError("Time must be HH:MM")
    hour = int(match.group(1))
    minute = int(match.group(2))
    if hour > 23 or minute > 59:
        raise ValueError("Time must be HH:MM")
    return f"{hour:02d}:{minute:02d}"


def parse_clock(raw: str) -> Tuple[int, int]:
    stamp = _parse_hhmm(raw)
    return int(stamp[:2]), int(stamp[3:5])


def monday_of(day: date) -> date:
    return day - timedelta(days=day.weekday())


def parse_datetime(raw: Optional[str]) -> datetime:
    text = str(raw or "").strip()
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00")[:32])
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)
    return parsed.replace(microsecond=0)


def _row_event(row: sqlite3.Row) -> Dict[str, Any]:
    recurrence = None
    raw = row["recurrence_json"]
    if raw:
        try:
            loaded = json.loads(raw)
            if isinstance(loaded, dict):
                recurrence = loaded
        except json.JSONDecodeError:
            recurrence = None
    return {
        "id": row["id"],
        "title": row["title"],
        "start_at": row["start_at"],
        "end_at": row["end_at"],
        "all_day": bool(row["all_day"]),
        "recurrence": recurrence,
        "source": row["source"],
        "kind": "hard",
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _row_block(row: sqlite3.Row) -> Dict[str, Any]:
    start = parse_datetime(row["start_at"])
    end = parse_datetime(row["end_at"])
    return {
        "id": row["id"],
        "work_item_id": row["work_item_id"],
        "title": row["title"],
        "local_date": row["local_date"],
        "start_at": row["start_at"],
        "end_at": row["end_at"],
        "status": row["status"],
        "kind": row["kind"],
        "minutes": max(1, int((end - start).total_seconds() // 60)),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def is_deadline_event(
    *,
    all_day: bool,
    start_at: datetime,
    end_at: Optional[datetime],
    role: str = "deadlines",
) -> bool:
    """Class due-date feeds: all-day titles and 11:59 stubs are dues, not busy."""
    if (role or "deadlines").strip().lower() in ("deadlines", "deadline", "due"):
        return True
    if all_day:
        return True
    end = end_at or start_at
    minutes = max(0, int((end - start_at).total_seconds() // 60))
    if minutes <= 15 and (start_at.minute == 59 or start_at.hour == 23):
        return True
    if start_at.hour == 23 and start_at.minute >= 50:
        return True
    return False


def due_at_for_imported(
    *,
    all_day: bool,
    start_at: datetime,
    end_at: Optional[datetime],
) -> str:
    if all_day:
        day = start_at.date()
        if end_at and end_at.date() > start_at.date() and end_at.hour == 0 and end_at.minute == 0:
            day = (end_at.date() - timedelta(days=1))
        return datetime.combine(day, datetime.min.time()).replace(hour=23, minute=59).isoformat(timespec="seconds")
    return start_at.replace(microsecond=0).isoformat(timespec="seconds")


def _unfold_ics(text: str) -> str:
    lines = text.replace("\r\n", "\n").split("\n")
    out: List[str] = []
    for line in lines:
        if line.startswith((" ", "\t")) and out:
            out[-1] += line.strip()
        else:
            out.append(line)
    return "\n".join(out)


def _parse_ics_datetime(value: str, params: str) -> Tuple[datetime, bool]:
    raw = (value or "").strip()
    if "VALUE=DATE" in params.upper() or (len(raw) == 8 and raw.isdigit()):
        day = date(int(raw[:4]), int(raw[4:6]), int(raw[6:8]))
        return datetime.combine(day, datetime.min.time()), True
    stamp = raw.replace("-", "")
    if stamp.endswith("Z"):
        parsed = datetime.strptime(stamp[:15], "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
        return parsed.astimezone().replace(tzinfo=None), False
    compact = stamp.replace(":", "")
    if "T" in compact:
        body = compact.split("T")[0] + "T" + compact.split("T")[1][:6]
        parsed = datetime.strptime(body[:15], "%Y%m%dT%H%M%S")
        return parsed, False
    day = date(int(raw[:4]), int(raw[4:6]), int(raw[6:8]))
    return datetime.combine(day, datetime.min.time()), True


def parse_ics_events(text: str) -> List[Dict[str, Any]]:
    unfolded = _unfold_ics(text)
    blocks = re.split(r"BEGIN:VEVENT", unfolded, flags=re.IGNORECASE)[1:]
    events: List[Dict[str, Any]] = []
    for block in blocks:
        chunk = block.split("END:VEVENT", 1)[0]
        fields: Dict[str, str] = {}
        params: Dict[str, str] = {}
        for line in chunk.splitlines():
            if ":" not in line:
                continue
            key, _, val = line.partition(":")
            name, _, extra = key.partition(";")
            name = name.strip().upper()
            fields[name] = val.strip()
            params[name] = extra
        summary = (fields.get("SUMMARY") or "").strip()
        start_raw = fields.get("DTSTART")
        if not summary or not start_raw:
            continue
        start, all_day = _parse_ics_datetime(start_raw, params.get("DTSTART") or "")
        end: Optional[datetime] = None
        if fields.get("DTEND"):
            end, end_all_day = _parse_ics_datetime(fields["DTEND"], params.get("DTEND") or "")
            all_day = all_day or end_all_day
        events.append(
            {
                "uid": (fields.get("UID") or uuid.uuid4().hex).strip(),
                "title": summary[:200],
                "start_at": start,
                "end_at": end,
                "all_day": all_day,
                "location": (fields.get("LOCATION") or "").strip(),
            }
        )
    return events


def ingest_events(
    events: List[Dict[str, Any]],
    *,
    calendar_id: str,
    role: str = "deadlines",
    default_estimate: Optional[int] = None,
) -> Dict[str, int]:
    settings = load_settings()
    estimate = default_estimate or settings["default_estimate_minutes"]
    created = 0
    updated = 0
    skipped = 0
    for raw in events:
        title = str(raw.get("title") or raw.get("summary") or "").strip()
        uid = str(raw.get("uid") or "").strip()
        if not title or not uid:
            skipped += 1
            continue
        start = raw.get("start_at")
        if isinstance(start, str):
            start = parse_datetime(start)
        if not isinstance(start, datetime):
            skipped += 1
            continue
        end = raw.get("end_at")
        if isinstance(end, str) and end.strip():
            end = parse_datetime(end)
        elif not isinstance(end, datetime):
            end = None
        all_day = bool(raw.get("all_day"))
        if not is_deadline_event(all_day=all_day, start_at=start, end_at=end, role=role):
            skipped += 1
            continue
        due = due_at_for_imported(all_day=all_day, start_at=start, end_at=end)
        before = None
        with work._connect() as conn:
            before = conn.execute(
                "SELECT id FROM work_items WHERE source_calendar = ? AND source_uid = ?",
                (calendar_id, uid),
            ).fetchone()
        item = work.upsert_imported_work(
            title=title,
            due_at=due,
            source_uid=uid,
            source_calendar=calendar_id,
            estimate_minutes=estimate,
            notes=str(raw.get("location") or ""),
        )
        if before:
            updated += 1
        else:
            created += 1
        _ = item
    return {"created": created, "updated": updated, "skipped": skipped, "total": len(events)}


def import_ics_text(text: str, calendar_id: str = "ics") -> Dict[str, Any]:
    events = parse_ics_events(text)
    counts = ingest_events(events, calendar_id=calendar_id, role="deadlines")
    return {"ok": True, "calendar_id": calendar_id, **counts}


@eel.expose
def import_ics_url(url: str = "") -> Dict[str, Any]:
    settings = load_settings()
    target = (url or settings.get("ics_url") or "").strip()
    if target.startswith("webcal://"):
        target = "https://" + target[len("webcal://") :]
    parsed = urlparse(target)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("Calendar URL must be https")
    if url:
        save_calendar_settings({"ics_url": target})
    req = Request(target, headers={"User-Agent": "Kosistenz/1.0"})
    with urlopen(req, timeout=20) as resp:
        data = resp.read(MAX_ICS_BYTES + 1)
    if len(data) > MAX_ICS_BYTES:
        raise ValueError("Calendar file is too large")
    text = data.decode("utf-8", errors="replace")
    return import_ics_text(text, calendar_id="ics:" + (parsed.netloc + parsed.path)[:80])


@eel.expose
def ingest_calendar_events(payload: Dict[str, Any]) -> Dict[str, Any]:
    """EventKit / tests: JSON events from a named Apple calendar (deadlines)."""
    body = payload if isinstance(payload, dict) else {}
    calendar_id = str(body.get("calendar_id") or "eventkit").strip() or "eventkit"
    role = str(body.get("role") or "deadlines")
    events = body.get("events") if isinstance(body.get("events"), list) else []
    counts = ingest_events(events, calendar_id=calendar_id, role=role)
    return {"ok": True, "calendar_id": calendar_id, **counts}


def _normalize_weekdays(raw: Any) -> List[int]:
    if not raw:
        return []
    out: List[int] = []
    for item in raw:
        try:
            day = int(item)
        except (TypeError, ValueError):
            continue
        if 0 <= day <= 6 and day not in out:
            out.append(day)
    return sorted(out)


@eel.expose
def create_calendar_event(
    title: str,
    start_at: str,
    end_at: str,
    weekdays: Any = None,
) -> Dict[str, Any]:
    clean = (title or "").strip()
    if not clean:
        raise ValueError("Name the event (lecture, lab, shift)")
    start = parse_datetime(start_at)
    end = parse_datetime(end_at)
    if end <= start:
        raise ValueError("End must be after start")
    if (end - start).total_seconds() > 12 * 3600:
        raise ValueError("Events longer than 12 hours are not lectures — check the times")
    days = _normalize_weekdays(weekdays)
    recurrence = {"kind": "weekly", "weekdays": days} if days else None
    now = _now().isoformat()
    event_id = str(uuid.uuid4())
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO calendar_events (
                id, title, start_at, end_at, all_day, recurrence_json, source, created_at, updated_at
            ) VALUES (?, ?, ?, ?, 0, ?, 'kosistenz', ?, ?)
            """,
            (
                event_id,
                clean[:200],
                start.isoformat(timespec="seconds"),
                end.isoformat(timespec="seconds"),
                json.dumps(recurrence) if recurrence else None,
                now,
                now,
            ),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM calendar_events WHERE id = ?", (event_id,)).fetchone()
    assert row is not None
    return _row_event(row)


@eel.expose
def delete_calendar_event(event_id: str) -> Dict[str, Any]:
    with _connect() as conn:
        cur = conn.execute("DELETE FROM calendar_events WHERE id = ?", (event_id,))
        conn.commit()
        if cur.rowcount < 1:
            raise ValueError("Event not found")
    return {"ok": True, "id": event_id}


def expand_hard_events(start: date, end: date) -> List[Dict[str, Any]]:
    """Timed busy occurrences in [start, end] inclusive."""
    out: List[Dict[str, Any]] = []
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM calendar_events").fetchall()
    cursor = start
    while cursor <= end:
        for row in rows:
            event = _row_event(row)
            occ = _occurrence_on(event, cursor)
            if occ:
                out.append(occ)
        cursor += timedelta(days=1)
    out.sort(key=lambda item: item["start_at"])
    return out


def _occurrence_on(event: Dict[str, Any], day: date) -> Optional[Dict[str, Any]]:
    start = parse_datetime(event["start_at"])
    end = parse_datetime(event["end_at"])
    duration = end - start
    recurrence = event.get("recurrence") or {}
    weekdays = recurrence.get("weekdays") if isinstance(recurrence, dict) else None
    if weekdays:
        if day.weekday() not in set(int(d) for d in weekdays):
            return None
        if day < start.date():
            return None
        occ_start = datetime.combine(day, start.time())
    else:
        if start.date() != day:
            return None
        occ_start = start
    occ_end = occ_start + duration
    return {
        **event,
        "occurrence_date": day.isoformat(),
        "start_at": occ_start.isoformat(timespec="seconds"),
        "end_at": occ_end.isoformat(timespec="seconds"),
        "kind": "hard",
        "status": "locked",
    }


def list_blocks(start: date, end: date) -> List[Dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM schedule_blocks
            WHERE local_date >= ? AND local_date <= ?
            ORDER BY start_at ASC
            """,
            (start.isoformat(), end.isoformat()),
        ).fetchall()
    return [_row_block(row) for row in rows]


def blocks_for_item(item_id: str) -> List[Dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM schedule_blocks
            WHERE work_item_id = ?
            ORDER BY start_at ASC
            """,
            (item_id,),
        ).fetchall()
    return [_row_block(row) for row in rows]


def placed_minutes(item_id: str) -> int:
    total = 0
    for block in blocks_for_item(item_id):
        if block["status"] in ("skipped",):
            continue
        total += int(block["minutes"])
    return total


def remaining_minutes(item: Dict[str, Any]) -> int:
    estimate = int(item.get("estimate_minutes") or 0)
    if estimate <= 0:
        return 0
    if item.get("status") == "done":
        return 0
    return max(0, estimate - placed_minutes(item["id"]))


def unplaced_work() -> List[Dict[str, Any]]:
    items = []
    for item in work.list_all_work_items():
        leftover = remaining_minutes(item)
        if leftover <= 0:
            continue
        packed = dict(item)
        packed["remaining_minutes"] = leftover
        items.append(packed)
    items.sort(key=lambda row: (row.get("due_at") or "9999", row.get("created_at") or ""))
    return items


@eel.expose
def get_week(week_start: str = "") -> Dict[str, Any]:
    settings = load_settings()
    start = date.fromisoformat(week_start) if week_start else monday_of(date.today())
    start = monday_of(start)
    end = start + timedelta(days=6)
    hard = expand_hard_events(start, end)
    blocks = list_blocks(start, end)
    days = []
    for offset in range(7):
        day = start + timedelta(days=offset)
        iso = day.isoformat()
        days.append(
            {
                "date": iso,
                "weekday": day.strftime("%a"),
                "is_today": iso == date.today().isoformat(),
                "events": [item for item in hard if item["occurrence_date"] == iso],
                "blocks": [item for item in blocks if item["local_date"] == iso],
            }
        )
    unplaced = unplaced_work()
    return {
        "week_start": start.isoformat(),
        "week_end": end.isoformat(),
        "settings": settings,
        "days": days,
        "unplaced": unplaced,
        "at_risk": [
            item
            for item in unplaced
            if item.get("due_at") and item["due_at"][:10] <= end.isoformat()
        ],
    }


@eel.expose
def get_day_agenda(local_date: str = "") -> Dict[str, Any]:
    iso = work._parse_date(local_date) or date.today().isoformat()
    day = date.fromisoformat(iso)
    week = get_week(monday_of(day).isoformat())
    match = next((row for row in week["days"] if row["date"] == iso), None)
    items = []
    if match:
        items.extend(match["events"])
        items.extend(match["blocks"])
        items.sort(key=lambda row: row["start_at"])
    return {
        "local_date": iso,
        "items": items,
        "unplaced": week["unplaced"],
        "settings": week["settings"],
    }


def add_block(
    *,
    title: str,
    start: datetime,
    end: datetime,
    work_item_id: Optional[str] = None,
    kind: str = "work",
    status: str = "proposed",
) -> Dict[str, Any]:
    block_id = str(uuid.uuid4())
    now = _now().isoformat()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO schedule_blocks (
                id, work_item_id, title, local_date, start_at, end_at, status, kind, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                block_id,
                work_item_id,
                title[:200],
                start.date().isoformat(),
                start.isoformat(timespec="seconds"),
                end.isoformat(timespec="seconds"),
                status if status in BLOCK_STATUSES else "proposed",
                kind,
                now,
                now,
            ),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM schedule_blocks WHERE id = ?", (block_id,)).fetchone()
    assert row is not None
    return _row_block(row)


@eel.expose
def set_block_status(block_id: str, status: str) -> Dict[str, Any]:
    key = str(status or "").strip().lower()
    if key not in BLOCK_STATUSES:
        raise ValueError("Unknown block status")
    now = _now().isoformat()
    with _connect() as conn:
        row = conn.execute("SELECT * FROM schedule_blocks WHERE id = ?", (block_id,)).fetchone()
        if row is None:
            raise ValueError("Block not found")
        conn.execute(
            "UPDATE schedule_blocks SET status = ?, updated_at = ? WHERE id = ?",
            (key, now, block_id),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM schedule_blocks WHERE id = ?", (block_id,)).fetchone()
    assert row is not None
    return _row_block(row)


@eel.expose
def delete_schedule_block(block_id: str) -> Dict[str, Any]:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM schedule_blocks WHERE id = ?", (block_id,)).fetchone()
        if row is None:
            raise ValueError("Block not found")
        if row["status"] == "locked":
            raise ValueError("Locked blocks stay until you unlock them")
        conn.execute("DELETE FROM schedule_blocks WHERE id = ?", (block_id,))
        conn.commit()
    return {"ok": True, "id": block_id}
