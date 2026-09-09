"""
Kosistenz calendar — hard events, deadline ingest, and the week clock.

SQLite lives next to the work database. Apple Calendar is a read-only feed.
Generated study blocks are never written back to EventKit.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import uuid
from collections import Counter
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import eel

import work
from db import sqlite_connect

SETTINGS_NAME = "calendar_feeds.json"
DEFAULT_ESTIMATE = 60
MAX_ICS_BYTES = 2 * 1024 * 1024
CHUNK_MIN = 50
CHUNK_MAX = 90
DAY_START = "05:30"
DAY_END = "21:30"
UNPLACED_UI_LIMIT = 80
BLOCK_STATUSES = ("proposed", "locked", "done", "skipped")
_last_purge_day: Optional[str] = None
_ICS_URL_RE = re.compile(r"(?:https?|webcal)://[^\s<>\"']+", re.I)
_ICS_FETCH_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Kosistenz/1.0",
    "Accept": "text/calendar, text/plain, application/calendar+xml, */*",
}
_BYDAY = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}
_COURSE_RE = re.compile(r"\[([A-Za-z]{2,10})\s*[-–]\s*(\d{2,4})")


def course_code_from_title(title: str) -> str:
    match = _COURSE_RE.search(str(title or ""))
    if not match:
        return ""
    return f"{match.group(1).upper()}-{match.group(2)}"


def course_hue(code: str) -> int:
    key = str(code or "").strip()
    if not key:
        return 32
    acc = 0
    for ch in key:
        acc = (acc * 31 + ord(ch)) & 0xFFFFFFFF
    return int(acc % 360)


def normalize_ics_url(raw: str, *, allow_empty: bool = False) -> str:
    """Turn a pasted calendar link into an http(s) ICS URL."""
    text = str(raw or "").replace("\ufeff", "").strip()
    if not text:
        if allow_empty:
            return ""
        raise ValueError("Paste a calendar URL")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    text = lines[0] if lines else text
    text = text.strip("<>").strip().strip("'\"").strip()
    match = _ICS_URL_RE.search(text)
    if match:
        text = match.group(0)
    text = text.rstrip(".,;)]}>\"'")
    lower = text.lower()
    if lower.startswith("webcal://"):
        text = "https://" + text[len("webcal://") :]
    parsed = urlparse(text)
    if parsed.scheme not in ("https", "http") or not parsed.netloc:
        raise ValueError("Calendar URL must be http or https")
    return text


def _feed_id_for_url(url: str) -> str:
    parsed = urlparse(url)
    raw = f"{parsed.netloc}{parsed.path}".rstrip("/")
    for feed in load_settings().get("feeds") or []:
        if str(feed.get("url") or "").rstrip("/") == url.rstrip("/"):
            key = str(feed.get("id") or "").strip()
            if key:
                return key
    if len(raw) <= 72:
        return "ics:" + raw
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]
    host = (parsed.netloc or "ics")[:40]
    return f"ics:{host}:{digest}"


def _now() -> datetime:
    return datetime.now().replace(microsecond=0)


def _db_path() -> Path:
    return work._data_dir() / "calendar.sqlite"


def _settings_path() -> Path:
    return work._data_dir() / SETTINGS_NAME


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    with sqlite_connect(_db_path()) as conn:
        _ensure_schema(conn)
        yield conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
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
    cols = {str(row[1]) for row in conn.execute("PRAGMA table_info(calendar_events)")}
    if "source_uid" not in cols:
        conn.execute("ALTER TABLE calendar_events ADD COLUMN source_uid TEXT")
    if "source_calendar" not in cols:
        conn.execute("ALTER TABLE calendar_events ADD COLUMN source_calendar TEXT")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_cal_events_source ON calendar_events(source_calendar)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_cal_events_start ON calendar_events(start_at)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_cal_events_end ON calendar_events(end_at)"
    )


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
        "feeds": _normalize_feeds(raw.get("feeds")),
    }


def _feed_enabled(item: Dict[str, Any]) -> bool:
    val = item.get("enabled", True)
    if val in (False, 0, "0", "false", "False", "off", "no"):
        return False
    return True


def _normalize_feeds(raw: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: List[Dict[str, Any]] = []
    seen = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        feed_id = str(item.get("id") or "").strip()
        if not feed_id or feed_id in seen:
            continue
        seen.add(feed_id)
        out.append(
            {
                "id": feed_id,
                "kind": str(item.get("kind") or "ics").strip() or "ics",
                "url": str(item.get("url") or "").strip(),
                "title": str(item.get("title") or "").strip() or feed_id,
                "enabled": _feed_enabled(item),
            }
        )
    return out


def _write_settings(current: Dict[str, Any]) -> Dict[str, Any]:
    payload = {
        "ics_url": str(current.get("ics_url") or ""),
        "day_start": str(current.get("day_start") or DAY_START),
        "day_end": str(current.get("day_end") or DAY_END),
        "default_estimate_minutes": int(current.get("default_estimate_minutes") or DEFAULT_ESTIMATE),
        "chunk_min": int(current.get("chunk_min") or CHUNK_MIN),
        "chunk_max": int(current.get("chunk_max") or CHUNK_MAX),
        "feeds": _normalize_feeds(current.get("feeds")),
    }
    path = _settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    os.replace(tmp, path)
    return load_settings()


def register_calendar_feed(
    feed_id: str,
    *,
    kind: str = "ics",
    title: str = "",
    url: str = "",
) -> Dict[str, Any]:
    key = str(feed_id or "").strip()
    if not key:
        return load_settings()
    current = load_settings()
    feeds = list(current.get("feeds") or [])
    found = False
    for feed in feeds:
        if feed["id"] != key:
            continue
        if title:
            feed["title"] = title
        if url:
            feed["url"] = url
        feed["kind"] = kind or feed.get("kind") or "ics"
        found = True
        break
    if not found:
        feeds.append(
            {
                "id": key,
                "kind": kind or "ics",
                "url": url,
                "title": title or key,
                "enabled": True,
            }
        )
    current["feeds"] = feeds
    return _write_settings(current)


def _disabled_feed_ids() -> set[str]:
    return {
        str(feed.get("id") or "")
        for feed in load_settings().get("feeds") or []
        if feed.get("id") and not _feed_enabled(feed)
    }


def _is_hidden_source(source_calendar: Any) -> bool:
    key = str(source_calendar or "").strip()
    return bool(key) and key in _disabled_feed_ids()


@eel.expose
def set_calendar_feed_enabled(feed_id: str = "", enabled: bool = True) -> Dict[str, Any]:
    key = str(feed_id or "").strip()
    if not key:
        return {"ok": False, "error": "Missing calendar.", **list_calendar_feeds()}
    current = load_settings()
    feeds = list(current.get("feeds") or [])
    found = False
    for feed in feeds:
        if feed.get("id") != key:
            continue
        feed["enabled"] = bool(enabled)
        found = True
        break
    if not found:
        feeds.append({"id": key, "kind": "ics", "url": "", "title": key, "enabled": bool(enabled)})
    current["feeds"] = feeds
    _write_settings(current)
    return {"ok": True, "feed_id": key, "enabled": bool(enabled), **list_calendar_feeds()}


@eel.expose
def get_calendar_settings() -> Dict[str, Any]:
    return load_settings()


@eel.expose
def save_calendar_settings(partial: Dict[str, Any]) -> Dict[str, Any]:
    current = load_settings()
    incoming = partial if isinstance(partial, dict) else {}
    if "ics_url" in incoming:
        url = str(incoming.get("ics_url") or "").strip()
        current["ics_url"] = normalize_ics_url(url, allow_empty=True) if url else ""
    if incoming.get("day_start"):
        current["day_start"] = _parse_hhmm(str(incoming["day_start"]))
    if incoming.get("day_end"):
        current["day_end"] = _parse_hhmm(str(incoming["day_end"]))
    if "default_estimate_minutes" in incoming:
        minutes = work._parse_estimate(incoming.get("default_estimate_minutes"))
        current["default_estimate_minutes"] = minutes or DEFAULT_ESTIMATE
    if "feeds" in incoming:
        current["feeds"] = _normalize_feeds(incoming.get("feeds"))
    return _write_settings(current)


def _parse_hhmm(raw: str) -> str:
    text = str(raw or "").strip().replace(".", ":").replace(" ", "")
    if re.fullmatch(r"\d{3,4}", text):
        text = text.zfill(4)
        text = f"{text[:2]}:{text[2:]}"
    match = re.fullmatch(r"(\d{1,2}):(\d{2})", text)
    if not match:
        raise ValueError("Time must be HH:MM or HHMM (24-hour, like 0530 or 2130)")
    hour = int(match.group(1))
    minute = int(match.group(2))
    if hour > 23 or minute > 59:
        raise ValueError("Time must be HH:MM or HHMM (24-hour, like 0530 or 2130)")
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
    keys = set(row.keys())
    return {
        "id": row["id"],
        "title": row["title"],
        "start_at": row["start_at"],
        "end_at": row["end_at"],
        "all_day": bool(row["all_day"]),
        "recurrence": recurrence,
        "source": row["source"],
        "source_uid": (row["source_uid"] if "source_uid" in keys else "") or "",
        "source_calendar": (row["source_calendar"] if "source_calendar" in keys else "") or "",
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


def _cal_today() -> date:
    return work._today()


def _ics_window(today: Optional[date] = None) -> Tuple[date, date]:
    day = today or _cal_today()
    return day, day + timedelta(days=120)


def _ics_calendar_title(text: str, fallback: str = "") -> str:
    unfolded = _unfold_ics(text)
    for key in ("X-WR-CALNAME", "NAME"):
        prefix = key + ":"
        for line in unfolded.splitlines():
            if line.upper().startswith(prefix):
                name = line.split(":", 1)[1].strip()
                if name:
                    return name[:80]
    return fallback


def _parse_ics_duration(raw: str) -> Optional[timedelta]:
    text = (raw or "").strip().upper()
    match = re.match(
        r"^P(?:(\d+)W)?(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?$",
        text,
    )
    if not match:
        return None
    weeks, days, hours, minutes, seconds = (int(part or 0) for part in match.groups())
    delta = timedelta(weeks=weeks, days=days, hours=hours, minutes=minutes, seconds=seconds)
    if delta.total_seconds() <= 0:
        return None
    return delta


def _parse_rrule(raw: str) -> Optional[Dict[str, Any]]:
    text = (raw or "").strip()
    if not text:
        return None
    parts: Dict[str, str] = {}
    for piece in text.split(";"):
        if "=" not in piece:
            continue
        key, val = piece.split("=", 1)
        parts[key.strip().upper()] = val.strip()
    freq = (parts.get("FREQ") or "").upper()
    if not freq:
        return None
    interval = 1
    try:
        interval = max(1, int(parts.get("INTERVAL") or "1"))
    except ValueError:
        interval = 1
    until: Optional[date] = None
    if parts.get("UNTIL"):
        try:
            parsed, _ = _parse_ics_datetime(parts["UNTIL"], "")
            until = parsed.date()
        except (ValueError, TypeError):
            until = None
    count = None
    if parts.get("COUNT"):
        try:
            count = max(1, int(parts["COUNT"]))
        except ValueError:
            count = None
    weekdays: List[int] = []
    for token in (parts.get("BYDAY") or "").split(","):
        token = token.strip().upper()
        if not token:
            continue
        code = token[-2:] if len(token) >= 2 else token
        if code in _BYDAY:
            weekdays.append(_BYDAY[code])
    return {
        "freq": freq,
        "interval": interval,
        "weekdays": sorted(set(weekdays)),
        "until": until,
        "count": count,
    }


def _parse_exdates(values: List[Tuple[str, str]]) -> set:
    out = set()
    for raw, extra in values:
        for piece in (raw or "").split(","):
            piece = piece.strip()
            if not piece:
                continue
            try:
                parsed, _ = _parse_ics_datetime(piece, extra)
            except (ValueError, TypeError):
                continue
            out.add(parsed.date())
    return out


def _shift_dt(stamp: datetime, day: date) -> datetime:
    return datetime.combine(day, stamp.time())


def _expand_rrule_dates(
    start: date,
    rrule: Dict[str, Any],
    exdates: set,
    window_start: date,
    window_end: date,
) -> List[date]:
    freq = rrule["freq"]
    interval = int(rrule.get("interval") or 1)
    until = rrule.get("until")
    hard_end = window_end
    if until and until < hard_end:
        hard_end = until
    if hard_end < start and freq != "YEARLY":
        # Series may still have later yearly instances; weekly/daily ended before DTSTART window.
        pass
    count = rrule.get("count")
    out: List[date] = []
    generated = 0

    def take(day: date) -> bool:
        nonlocal generated
        if count is not None and generated >= count:
            return False
        generated += 1
        if day in exdates:
            return True
        if window_start <= day <= hard_end:
            out.append(day)
        return True

    if freq == "DAILY":
        cur = start
        while cur <= hard_end:
            if not take(cur):
                break
            cur += timedelta(days=interval)
        return out

    if freq == "WEEKLY":
        weekdays = list(rrule.get("weekdays") or []) or [start.weekday()]
        allowed = set(weekdays)
        cur = start
        origin = start
        while cur <= hard_end:
            if cur.weekday() in allowed:
                weeks = (cur - origin).days // 7
                if weeks % interval == 0:
                    if not take(cur):
                        break
            cur += timedelta(days=1)
        return out

    if freq == "YEARLY":
        year = start.year
        last_year = hard_end.year
        while year <= last_year:
            try:
                occ = start.replace(year=year)
            except ValueError:
                year += interval
                continue
            if occ > hard_end and (count is None or generated >= (count or 0)):
                break
            if occ >= start:
                if not take(occ):
                    break
            year += interval
        return out

    if freq == "MONTHLY":
        year, month = start.year, start.month
        guard = 0
        while guard < 240:
            guard += 1
            try:
                occ = date(year, month, start.day)
            except ValueError:
                month += interval
                year += (month - 1) // 12
                month = (month - 1) % 12 + 1
                continue
            if occ > hard_end:
                break
            if occ >= start:
                if not take(occ):
                    break
            month += interval
            year += (month - 1) // 12
            month = (month - 1) % 12 + 1
        return out

    if window_start <= start <= hard_end and start not in exdates:
        return [start]
    return out


def parse_ics_events(text: str, *, today: Optional[date] = None) -> List[Dict[str, Any]]:
    """Parse VEVENT blocks. Weekly timed lectures keep a compact RRULE; other recurrences expand."""
    unfolded = _unfold_ics(text)
    window_start, window_end = _ics_window(today)
    blocks = re.split(r"BEGIN:VEVENT", unfolded, flags=re.IGNORECASE)[1:]
    events: List[Dict[str, Any]] = []
    for block in blocks:
        chunk = block.split("END:VEVENT", 1)[0]
        fields: Dict[str, str] = {}
        params: Dict[str, str] = {}
        exdate_raw: List[Tuple[str, str]] = []
        for line in chunk.splitlines():
            if ":" not in line:
                continue
            key, _, val = line.partition(":")
            name, _, extra = key.partition(";")
            name = name.strip().upper()
            value = val.strip()
            if name == "EXDATE":
                exdate_raw.append((value, extra))
                continue
            fields[name] = value
            params[name] = extra
        summary = (fields.get("SUMMARY") or "").strip()
        start_raw = fields.get("DTSTART")
        if not summary or not start_raw:
            continue
        try:
            start, all_day = _parse_ics_datetime(start_raw, params.get("DTSTART") or "")
        except (ValueError, TypeError):
            continue
        end: Optional[datetime] = None
        if fields.get("DTEND"):
            try:
                end, end_all_day = _parse_ics_datetime(fields["DTEND"], params.get("DTEND") or "")
                all_day = all_day or end_all_day
            except (ValueError, TypeError):
                end = None
        if end is None and fields.get("DURATION"):
            delta = _parse_ics_duration(fields["DURATION"])
            if delta:
                end = start + delta
        if end is None:
            end = start + (timedelta(days=1) if all_day else timedelta(minutes=50))
        elif not all_day and end <= start:
            end = start + timedelta(minutes=50)
        rrule = _parse_rrule(fields.get("RRULE") or "")
        exdates = _parse_exdates(exdate_raw)
        uid = (fields.get("UID") or uuid.uuid4().hex).strip()
        location = (fields.get("LOCATION") or "").strip()
        duration = end - start
        compact_weekly = bool(
            rrule
            and not all_day
            and rrule["freq"] == "WEEKLY"
            and int(rrule.get("interval") or 1) == 1
            and not rrule.get("count")
            and (rrule.get("weekdays") or [start.weekday()])
        )
        if compact_weekly and rrule:
            until = rrule.get("until")
            if until and until < window_start:
                continue
            weekdays = list(rrule.get("weekdays") or []) or [start.weekday()]
            events.append(
                {
                    "uid": uid,
                    "title": summary[:200],
                    "start_at": start,
                    "end_at": end,
                    "all_day": False,
                    "location": location,
                    "recurrence": {
                        "kind": "weekly",
                        "weekdays": weekdays,
                        "until": until.isoformat() if until else None,
                        "exdates": [day.isoformat() for day in sorted(exdates)],
                    },
                }
            )
            continue
        if rrule:
            days = _expand_rrule_dates(start.date(), rrule, exdates, window_start, window_end)
            if not days:
                continue
            for day in days:
                occ_start = _shift_dt(start, day)
                occ_end = occ_start + duration
                if all_day:
                    occ_end = occ_start + timedelta(days=1)
                events.append(
                    {
                        "uid": f"{uid}#{day.isoformat()}",
                        "title": summary[:200],
                        "start_at": occ_start,
                        "end_at": occ_end,
                        "all_day": all_day,
                        "location": location,
                        "recurrence": None,
                    }
                )
            continue
        # One-shot: drop anything already past. Recurring series stay for this week forward.
        if start.date() < window_start or start.date() > window_end:
            continue
        events.append(
            {
                "uid": uid,
                "title": summary[:200],
                "start_at": start,
                "end_at": end,
                "all_day": all_day,
                "location": location,
                "recurrence": None,
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
    skipped = 0
    rows: List[Dict[str, Any]] = []
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
        due_day = str(due or "")[:10]
        if not due_day or due_day < _cal_today().isoformat():
            skipped += 1
            continue
        rows.append(
            {
                "title": title,
                "due_at": due,
                "source_uid": uid,
                "source_calendar": calendar_id,
                "estimate_minutes": estimate,
                "notes": str(raw.get("location") or ""),
            }
        )
    counts = work.ingest_imported_work_batch(rows)
    created = int(counts.get("created") or 0)
    updated = int(counts.get("updated") or 0)
    return {"created": created, "updated": updated, "skipped": skipped, "total": len(events)}


def _busy_event_too_long(start: datetime, end: Optional[datetime]) -> bool:
    if not isinstance(end, datetime):
        return False
    return (end - start).total_seconds() > 12 * 3600


def replace_imported_hard_events(calendar_id: str, events: List[Dict[str, Any]]) -> int:
    """Replace timed ICS events for one feed. Leaves user-created lectures alone."""
    key = str(calendar_id or "").strip()
    if not key:
        return 0
    now = _now().isoformat()
    stored = 0
    with _connect() as conn:
        conn.execute("DELETE FROM calendar_events WHERE source_calendar = ?", (key,))
        for raw in events:
            title = str(raw.get("title") or "").strip()
            start = raw.get("start_at")
            end = raw.get("end_at")
            if isinstance(start, str):
                start = parse_datetime(start)
            if isinstance(end, str) and str(end).strip():
                end = parse_datetime(end)
            if not title or not isinstance(start, datetime):
                continue
            if not isinstance(end, datetime) or end <= start:
                end = start + timedelta(minutes=50)
            if _busy_event_too_long(start, end):
                continue
            rec = raw.get("recurrence") if isinstance(raw.get("recurrence"), dict) else None
            if not rec and end.date() < _cal_today():
                continue
            conn.execute(
                """
                INSERT INTO calendar_events (
                    id, title, start_at, end_at, all_day, recurrence_json, source,
                    created_at, updated_at, source_uid, source_calendar
                ) VALUES (?, ?, ?, ?, 0, ?, 'ics', ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    title[:200],
                    start.isoformat(timespec="seconds"),
                    end.isoformat(timespec="seconds"),
                    json.dumps(rec) if rec else None,
                    now,
                    now,
                    str(raw.get("uid") or "")[:200],
                    key,
                ),
            )
            stored += 1
        conn.commit()
    return stored


def delete_past_imported_one_shots() -> int:
    """Drop timed feed events that already ended and are not a recurring series."""
    today = _cal_today().isoformat()
    with _connect() as conn:
        cur = conn.execute(
            """
            DELETE FROM calendar_events
            WHERE source != 'kosistenz'
              AND (recurrence_json IS NULL OR TRIM(recurrence_json) IN ('', '{}', 'null'))
              AND substr(end_at, 1, 10) < ?
            """,
            (today,),
        )
        conn.commit()
        return int(cur.rowcount or 0)


def reset_purge_cache() -> None:
    global _last_purge_day
    _last_purge_day = None


def purge_stale_imports() -> Dict[str, Any]:
    global _last_purge_day
    result = work.delete_stale_imported_work()
    delete_blocks_for_work_items(result.get("ids") or [])
    events_deleted = delete_past_imported_one_shots()
    _last_purge_day = work._today().isoformat()
    return {
        "ok": True,
        "deleted": int(result.get("deleted") or 0),
        "ids": result.get("ids") or [],
        "events_deleted": events_deleted,
    }


def maybe_purge_stale_imports() -> Dict[str, Any]:
    """Drop past imports at most once per local day on read paths."""
    today = work._today().isoformat()
    if _last_purge_day == today:
        return {"ok": True, "deleted": 0, "ids": [], "events_deleted": 0, "skipped": True}
    return purge_stale_imports()


def delete_imported_hard_events(calendar_id: str) -> int:
    key = str(calendar_id or "").strip()
    if not key:
        return 0
    with _connect() as conn:
        cur = conn.execute("DELETE FROM calendar_events WHERE source_calendar = ?", (key,))
        conn.commit()
        return int(cur.rowcount or 0)


def import_ics_text(
    text: str,
    calendar_id: str = "ics",
    *,
    url: str = "",
    title: str = "",
    role: str = "auto",
) -> Dict[str, Any]:
    blob = str(text or "")
    if "BEGIN:VCALENDAR" not in blob.upper():
        raise ValueError("That file is not a calendar (missing BEGIN:VCALENDAR).")
    events = parse_ics_events(blob)
    dues: List[Dict[str, Any]] = []
    busy: List[Dict[str, Any]] = []
    for raw in events:
        start = raw.get("start_at")
        end = raw.get("end_at")
        if not isinstance(start, datetime):
            continue
        if is_deadline_event(
            all_day=bool(raw.get("all_day")),
            start_at=start,
            end_at=end if isinstance(end, datetime) else None,
            role=role,
        ):
            dues.append(raw)
        else:
            busy.append(raw)
    due_counts = ingest_events(dues, calendar_id=calendar_id, role="deadlines")
    busy_uids: List[str] = []
    for raw in busy:
        uid = str(raw.get("uid") or "").strip()
        if not uid:
            continue
        busy_uids.append(uid)
        busy_uids.append(uid.split("#", 1)[0])
    dropped = work.delete_open_imported_uids(calendar_id, busy_uids)
    delete_blocks_for_work_items(dropped.get("ids") or [])
    events_created = replace_imported_hard_events(calendar_id, busy)
    label = title or _ics_calendar_title(blob, calendar_id)
    register_calendar_feed(
        calendar_id,
        kind="ics",
        url=url,
        title=label,
    )
    purge_stale_imports()
    return {
        "ok": True,
        "calendar_id": calendar_id,
        "created": due_counts["created"],
        "updated": due_counts["updated"],
        "skipped": due_counts["skipped"],
        "total": len(events),
        "events_created": events_created,
    }


@eel.expose
def import_ics_url(url: str = "") -> Dict[str, Any]:
    settings = load_settings()
    target = normalize_ics_url(url or settings.get("ics_url") or "")
    if url:
        save_calendar_settings({"ics_url": target})
    req = Request(target, headers=dict(_ICS_FETCH_HEADERS))
    try:
        with urlopen(req, timeout=45) as resp:
            data = resp.read(MAX_ICS_BYTES + 1)
    except HTTPError as exc:
        raise ValueError(
            f"Calendar server returned HTTP {exc.code}. Use a public iCloud or class calendar link."
        ) from exc
    except URLError as exc:
        raise ValueError("Could not reach that calendar URL. Check the link and your network.") from exc
    if len(data) > MAX_ICS_BYTES:
        raise ValueError("Calendar file is too large")
    text = data.decode("utf-8", errors="replace")
    if "BEGIN:VCALENDAR" not in text.upper():
        raise ValueError("That URL did not return a calendar. iCloud links should start with webcal:// or https://.")
    calendar_id = _feed_id_for_url(target)
    parsed = urlparse(target)
    label = _ics_calendar_title(text, parsed.netloc or "Class calendar")
    return import_ics_text(text, calendar_id=calendar_id, url=target, title=label)


@eel.expose
def import_pasted_calendar(raw: str = "") -> Dict[str, Any]:
    """ICS URL or a pasted BEGIN:VCALENDAR blob from the Due dates box."""
    text = str(raw or "").replace("\ufeff", "").strip()
    if "BEGIN:VCALENDAR" in text.upper():
        if len(text.encode("utf-8")) > MAX_ICS_BYTES:
            raise ValueError("Calendar file is too large")
        return import_ics_text(text, calendar_id="paste")
    return import_ics_url(text)


@eel.expose
def ingest_calendar_events(payload: Dict[str, Any]) -> Dict[str, Any]:
    """EventKit / tests: JSON events from a named Apple calendar (deadlines)."""
    body = payload if isinstance(payload, dict) else {}
    calendar_id = str(body.get("calendar_id") or "eventkit").strip() or "eventkit"
    role = str(body.get("role") or "deadlines")
    events = body.get("events") if isinstance(body.get("events"), list) else []
    counts = ingest_events(events, calendar_id=calendar_id, role=role)
    register_calendar_feed(
        calendar_id,
        kind="apple",
        title=str(body.get("calendar_title") or calendar_id),
    )
    purged = purge_stale_imports()
    return {"ok": True, "calendar_id": calendar_id, **counts, "purged": purged["deleted"]}


def delete_blocks_for_work_items(item_ids: List[str]) -> int:
    ids = [str(item) for item in item_ids if str(item or "").strip()]
    if not ids:
        return 0
    placeholders = ",".join("?" * len(ids))
    with _connect() as conn:
        cur = conn.execute(
            f"DELETE FROM schedule_blocks WHERE work_item_id IN ({placeholders})",
            ids,
        )
        return int(cur.rowcount or 0)


@eel.expose
def list_calendar_feeds() -> Dict[str, Any]:
    settings = load_settings()
    stored = {feed["id"]: dict(feed) for feed in settings.get("feeds") or []}
    sources = work.list_imported_calendar_sources()
    feeds: List[Dict[str, Any]] = []
    seen = set()
    for source in sources:
        feed_id = source["id"]
        seen.add(feed_id)
        meta = stored.get(feed_id) or {}
        feeds.append(
            {
                "id": feed_id,
                "kind": meta.get("kind") or ("apple" if not str(feed_id).startswith("ics:") else "ics"),
                "url": meta.get("url") or "",
                "title": meta.get("title") or feed_id,
                "enabled": _feed_enabled(meta) if meta else True,
                "open_count": source["open_count"],
                "undated_count": source["undated_count"],
                "total": source["total"],
            }
        )
    for feed_id, meta in stored.items():
        if feed_id in seen:
            continue
        feeds.append(
            {
                "id": feed_id,
                "kind": meta.get("kind") or "ics",
                "url": meta.get("url") or "",
                "title": meta.get("title") or feed_id,
                "enabled": _feed_enabled(meta),
                "open_count": 0,
                "undated_count": 0,
                "total": 0,
            }
        )
    ics_url = str(settings.get("ics_url") or "")
    if ics_url and not any(feed.get("url") == ics_url for feed in feeds):
        feeds.append(
            {
                "id": "",
                "kind": "ics",
                "url": ics_url,
                "title": ics_url,
                "enabled": True,
                "open_count": 0,
                "undated_count": 0,
                "total": 0,
            }
        )
    undated = work.count_undated_imported_work()
    return {
        "ok": True,
        "feeds": feeds,
        "ics_url": ics_url,
        "undated_imported": undated,
    }


@eel.expose
def unsubscribe_calendar_feed(feed_id: str = "", url: str = "") -> Dict[str, Any]:
    settings = load_settings()
    key = str(feed_id or "").strip()
    link = str(url or "").strip()
    feeds = list(settings.get("feeds") or [])
    if not key and link:
        for feed in feeds:
            if feed.get("url") == link:
                key = feed["id"]
                break
    matched = next((feed for feed in feeds if feed.get("id") == key), None)
    deleted = work.delete_open_imported_work(key) if key else {"deleted": 0, "ids": []}
    delete_blocks_for_work_items(deleted.get("ids") or [])
    if key:
        delete_imported_hard_events(key)
    next_feeds = [feed for feed in feeds if feed.get("id") != key]
    if link:
        next_feeds = [feed for feed in next_feeds if feed.get("url") != link]
    settings["feeds"] = next_feeds
    current_url = str(settings.get("ics_url") or "")
    drop_url = False
    if matched and matched.get("url") and matched.get("url") == current_url:
        drop_url = True
    if link and link == current_url:
        drop_url = True
    if current_url:
        parsed = urlparse(current_url)
        if key and key == "ics:" + (parsed.netloc + parsed.path)[:80]:
            drop_url = True
        try:
            if key and key == _feed_id_for_url(current_url):
                drop_url = True
        except ValueError:
            pass
    if drop_url:
        settings["ics_url"] = ""
    _write_settings(settings)
    return {
        "ok": True,
        "deleted": int(deleted.get("deleted") or 0),
        "feed_id": key,
        **list_calendar_feeds(),
    }


@eel.expose
def delete_undated_imported_assignments() -> Dict[str, Any]:
    result = purge_stale_imports()
    return {
        "ok": True,
        "deleted": int(result.get("deleted") or 0),
        **list_calendar_feeds(),
    }


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
        raise ValueError("Name the event")
    start = parse_datetime(start_at)
    end = parse_datetime(end_at)
    if end <= start:
        raise ValueError("End must be after start")
    if (end - start).total_seconds() > 12 * 3600:
        raise ValueError("Events longer than 12 hours need to be split")
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


def _load_event(event_id: str) -> Dict[str, Any]:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM calendar_events WHERE id = ?", (event_id,)).fetchone()
    if row is None:
        raise ValueError("Event not found")
    return _row_event(row)


def _load_block(block_id: str) -> Dict[str, Any]:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM schedule_blocks WHERE id = ?", (block_id,)).fetchone()
    if row is None:
        raise ValueError("Block not found")
    return _row_block(row)


def _work_item(item_id: str) -> Dict[str, Any]:
    items = work.get_work_items_by_ids([item_id])
    if not items:
        raise ValueError("Work item not found")
    return items[0]


def _validate_span(start: datetime, end: datetime, *, hard: bool) -> None:
    if end <= start:
        raise ValueError("End must be after start")
    hours = (end - start).total_seconds() / 3600
    if hard and hours > 12:
        raise ValueError("Events longer than 12 hours need to be split")
    if not hard and hours > 12:
        raise ValueError("Blocks longer than 12 hours need to be split")


@eel.expose
def update_calendar_event(
    event_id: str,
    title: str = "",
    start_at: str = "",
    end_at: str = "",
    weekdays: Any = None,
    occurrence_date: str = "",
) -> Dict[str, Any]:
    """Rename or move a timed event. Recurring series keep weekdays unless you pass new ones
    or drag an occurrence onto another weekday."""
    event = _load_event(event_id)
    clean = (title or "").strip() or event["title"]
    start = parse_datetime(start_at) if start_at else parse_datetime(event["start_at"])
    end = parse_datetime(end_at) if end_at else parse_datetime(event["end_at"])
    duration = end - start
    rec = event.get("recurrence") if isinstance(event.get("recurrence"), dict) else None
    if weekdays is not None:
        days = _normalize_weekdays(weekdays)
        rec = {"kind": "weekly", "weekdays": days} if days else None
    elif rec and occurrence_date:
        try:
            old_day = date.fromisoformat(str(occurrence_date)[:10]).weekday()
        except ValueError:
            old_day = None
        new_day = start.date().weekday()
        days = _normalize_weekdays((rec or {}).get("weekdays"))
        if old_day is not None and days and old_day != new_day:
            days = sorted({new_day if d == old_day else d for d in days})
            rec = {"kind": "weekly", "weekdays": days}
        # Series template keeps its original date; only the clock time moves.
        template = parse_datetime(event["start_at"])
        start = datetime.combine(template.date(), start.time())
        end = start + duration
    _validate_span(start, end, hard=True)
    now = _now().isoformat()
    with _connect() as conn:
        conn.execute(
            """
            UPDATE calendar_events
            SET title = ?, start_at = ?, end_at = ?, recurrence_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                clean[:200],
                start.isoformat(timespec="seconds"),
                end.isoformat(timespec="seconds"),
                json.dumps(rec) if rec else None,
                now,
                event_id,
            ),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM calendar_events WHERE id = ?", (event_id,)).fetchone()
    assert row is not None
    return _row_event(row)


def _recurrence_until(recurrence: Any) -> Optional[date]:
    if not isinstance(recurrence, dict):
        return None
    raw = recurrence.get("until")
    if not raw:
        return None
    try:
        return datetime.strptime(str(raw)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _recurrence_exdates(recurrence: Any) -> set:
    if not isinstance(recurrence, dict):
        return set()
    out = set()
    for item in recurrence.get("exdates") or []:
        text = str(item or "")[:10]
        if len(text) == 10:
            out.add(text)
    return out


def expand_hard_events(start: date, end: date) -> List[Dict[str, Any]]:
    """Timed busy occurrences in [start, end] inclusive."""
    out: List[Dict[str, Any]] = []
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM calendar_events
            WHERE (
                recurrence_json IS NOT NULL
                AND TRIM(recurrence_json) NOT IN ('', '{}', 'null')
            )
            OR (
                substr(COALESCE(NULLIF(TRIM(end_at), ''), start_at), 1, 10) >= ?
                AND substr(start_at, 1, 10) <= ?
            )
            """,
            (start.isoformat(), end.isoformat()),
        ).fetchall()
    for row in rows:
        event = _row_event(row)
        if _is_hidden_source(event.get("source_calendar")):
            continue
        event_start = parse_datetime(event["start_at"])
        event_end = parse_datetime(event["end_at"])
        duration = event_end - event_start
        recurrence = event.get("recurrence") or {}
        weekdays = recurrence.get("weekdays") if isinstance(recurrence, dict) else None
        until = _recurrence_until(recurrence)
        exdates = _recurrence_exdates(recurrence)
        if weekdays:
            allowed = {int(day) for day in weekdays}
            cursor = max(start, event_start.date())
            last = end if until is None else min(end, until)
            while cursor <= last:
                if cursor.weekday() in allowed and cursor.isoformat() not in exdates:
                    occ_start = datetime.combine(cursor, event_start.time())
                    out.append(
                        {
                            **event,
                            "occurrence_date": cursor.isoformat(),
                            "start_at": occ_start.isoformat(timespec="seconds"),
                            "end_at": (occ_start + duration).isoformat(timespec="seconds"),
                            "kind": "hard",
                            "status": "locked",
                        }
                    )
                cursor += timedelta(days=1)
            continue
        last_day = event_end.date()
        if event_end.time() == datetime.min.time() and last_day > event_start.date():
            last_day -= timedelta(days=1)
        cursor = max(start, event_start.date())
        last = min(end, last_day)
        while cursor <= last:
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
    until = _recurrence_until(recurrence)
    if until and day > until:
        return None
    if day.isoformat() in _recurrence_exdates(recurrence):
        return None
    if weekdays:
        if day.weekday() not in set(int(d) for d in weekdays):
            return None
        if day < start.date():
            return None
        occ_start = datetime.combine(day, start.time())
        occ_end = occ_start + duration
    else:
        last_day = end.date()
        if end.time() == datetime.min.time() and last_day > start.date():
            last_day -= timedelta(days=1)
        if day < start.date() or day > last_day:
            return None
        occ_start = start if day == start.date() else datetime.combine(day, datetime.min.time())
        if day < last_day:
            occ_end = datetime.combine(day + timedelta(days=1), datetime.min.time())
        else:
            occ_end = end
        if occ_end <= occ_start:
            return None
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


def _span_minutes(start_at: str, end_at: str) -> int:
    start = parse_datetime(start_at)
    end = parse_datetime(end_at)
    return max(1, int((end - start).total_seconds() // 60))


def _placed_minutes_map() -> Dict[str, int]:
    """One pass over schedule_blocks instead of a query per to-do."""
    totals: Dict[str, int] = {}
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT work_item_id, start_at, end_at, status
            FROM schedule_blocks
            WHERE work_item_id IS NOT NULL
            """
        ).fetchall()
    for row in rows:
        if row["status"] == "skipped":
            continue
        item_id = row["work_item_id"]
        if not item_id:
            continue
        totals[item_id] = totals.get(item_id, 0) + _span_minutes(row["start_at"], row["end_at"])
    return totals


def placed_minutes(item_id: str) -> int:
    total = 0
    for block in blocks_for_item(item_id):
        if block["status"] == "skipped":
            continue
        total += int(block["minutes"])
    return total


def remaining_minutes(item: Dict[str, Any], placed: Optional[int] = None) -> int:
    estimate = int(item.get("estimate_minutes") or 0)
    if estimate <= 0:
        return 0
    if item.get("status") == "done":
        return 0
    used = placed if placed is not None else placed_minutes(item["id"])
    return max(0, estimate - used)


def unplaced_work() -> List[Dict[str, Any]]:
    placed = _placed_minutes_map()
    items = []
    now = work._now()
    with work._connect() as conn:
        rows = conn.execute(
            work._ITEM_SELECT
            + """
            WHERE work_items.status != 'done'
              AND IFNULL(work_items.source, '') != 'calendar'
              AND work_items.estimate_minutes IS NOT NULL
              AND work_items.estimate_minutes > 0
            """
        ).fetchall()
    for row in rows:
        item = work._row_to_dict(row, now)
        leftover = remaining_minutes(item, placed.get(item["id"], 0))
        if leftover <= 0:
            continue
        packed = dict(item)
        packed["remaining_minutes"] = leftover
        items.append(packed)
    items.sort(key=lambda row: (row.get("due_at") or "9999", row.get("created_at") or ""))
    return items


def _slim_unplaced(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": item.get("id"),
        "title": item.get("title") or "",
        "due_at": item.get("due_at"),
        "scheduled_date": item.get("scheduled_date"),
        "estimate_minutes": item.get("estimate_minutes"),
        "remaining_minutes": item.get("remaining_minutes"),
    }


def _unplaced_ui(rows: Optional[List[Dict[str, Any]]] = None) -> Tuple[List[Dict[str, Any]], int]:
    items = rows if rows is not None else unplaced_work()
    return [_slim_unplaced(item) for item in items[:UNPLACED_UI_LIMIT]], len(items)


def _slim_clock_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Fields the week clock paints. Recurrence keeps weekdays only."""
    out: Dict[str, Any] = {
        "id": item.get("id"),
        "title": item.get("title") or "",
        "start_at": item.get("start_at"),
        "end_at": item.get("end_at"),
        "kind": item.get("kind") or "work",
        "status": item.get("status") or "",
    }
    if item.get("work_item_id"):
        out["work_item_id"] = item["work_item_id"]
    if item.get("occurrence_date"):
        out["occurrence_date"] = item["occurrence_date"]
    if item.get("local_date"):
        out["local_date"] = item["local_date"]
    if item.get("minutes"):
        out["minutes"] = item["minutes"]
    rec = item.get("recurrence")
    if isinstance(rec, dict) and rec.get("weekdays"):
        out["recurrence"] = {"weekdays": rec.get("weekdays")}
    return out


def _slim_feed(feed: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": feed.get("id"),
        "title": feed.get("title") or feed.get("id") or "",
        "url": feed.get("url") or "",
        "enabled": feed.get("enabled") is not False,
    }


@eel.expose
def get_week(week_start: str = "", include_unplaced: bool = True) -> Dict[str, Any]:
    maybe_purge_stale_imports()
    settings = load_settings()
    start = date.fromisoformat(week_start) if week_start else monday_of(_cal_today())
    start = monday_of(start)
    end = start + timedelta(days=6)
    hard = expand_hard_events(start, end)
    blocks = list_blocks(start, end)
    dues = _dues_by_day(start, end)
    days = []
    today_iso = _cal_today().isoformat()
    for offset in range(7):
        day = start + timedelta(days=offset)
        iso = day.isoformat()
        days.append(
            {
                "date": iso,
                "weekday": day.strftime("%a"),
                "is_today": iso == today_iso,
                "events": [
                    _slim_clock_item(item)
                    for item in hard
                    if item["occurrence_date"] == iso
                ],
                "blocks": [
                    _slim_clock_item(item)
                    for item in blocks
                    if item["local_date"] == iso
                ],
                "dues": dues.get(iso, []),
            }
        )
    rows = unplaced_work() if include_unplaced else []
    shown, total = _unplaced_ui(rows)
    slim_settings = {
        "day_start": settings.get("day_start") or DAY_START,
        "day_end": settings.get("day_end") or DAY_END,
        "ics_url": settings.get("ics_url") or "",
        "default_estimate_minutes": settings.get("default_estimate_minutes")
        or DEFAULT_ESTIMATE,
    }
    return {
        "week_start": start.isoformat(),
        "week_end": end.isoformat(),
        "settings": slim_settings,
        "days": days,
        "today": _today_from_days(days, slim_settings),
        "feeds": [_slim_feed(feed) for feed in (list_calendar_feeds().get("feeds") or [])],
        "unplaced": shown,
        "unplaced_total": total,
    }


def _today_from_days(days: List[Dict[str, Any]], settings: Dict[str, Any]) -> Dict[str, Any]:
    today = _cal_today()
    iso = today.isoformat()
    match = next((row for row in days if row.get("date") == iso), None)
    if match is None:
        return _today_column()
    items = list(match.get("events") or []) + list(match.get("blocks") or [])
    items.sort(key=lambda row: str(row.get("start_at") or ""))
    overdue = [
        _slim_due(item, is_overdue=True)
        for item in work.list_overdue_work()
        if not _is_hidden_source(item.get("source_calendar"))
    ]
    return {
        "date": iso,
        "weekday": today.strftime("%a"),
        "label": f"{today.strftime('%A')}, {today.strftime('%b')} {today.day}",
        "day_start": settings.get("day_start") or DAY_START,
        "day_end": settings.get("day_end") or DAY_END,
        "overdue": overdue,
        "dues": list(match.get("dues") or []),
        "items": items,
    }


def _slim_due(item: Dict[str, Any], *, is_overdue: bool = False) -> Dict[str, Any]:
    title = item.get("title") or ""
    course = course_code_from_title(title)
    return {
        "id": item.get("id"),
        "title": title,
        "status": item.get("status") or "open",
        "due_at": item.get("due_at"),
        "estimate_minutes": int(item.get("estimate_minutes") or DEFAULT_ESTIMATE),
        "source_calendar": item.get("source_calendar") or "",
        "course": course,
        "hue": course_hue(course),
        "is_overdue": bool(is_overdue or item.get("is_overdue")),
    }


def _today_column() -> Dict[str, Any]:
    settings = load_settings()
    today = _cal_today()
    iso = today.isoformat()
    hard = expand_hard_events(today, today)
    blocks = list_blocks(today, today)
    items = list(hard) + list(blocks)
    items.sort(key=lambda row: str(row.get("start_at") or ""))
    overdue = [
        _slim_due(item, is_overdue=True)
        for item in work.list_overdue_work()
        if not _is_hidden_source(item.get("source_calendar"))
    ]
    return {
        "date": iso,
        "weekday": today.strftime("%a"),
        "label": f"{today.strftime('%A')}, {today.strftime('%b')} {today.day}",
        "day_start": settings.get("day_start") or DAY_START,
        "day_end": settings.get("day_end") or DAY_END,
        "overdue": overdue,
        "dues": _dues_by_day(today, today).get(iso, []),
        "items": items,
    }


def _dues_by_day(start: date, end: date) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    now = work._now()
    hidden = _disabled_feed_ids()
    with work._connect() as conn:
        rows = conn.execute(
            work._ITEM_SELECT
            + """
            WHERE work_items.due_at IS NOT NULL
              AND TRIM(work_items.due_at) != ''
              AND substr(work_items.due_at, 1, 10) >= ?
              AND substr(work_items.due_at, 1, 10) <= ?
            ORDER BY work_items.due_at ASC, work_items.sort_order ASC
            """,
            (start.isoformat(), end.isoformat()),
        ).fetchall()
    for row in rows:
        item = work._row_to_dict(row, now)
        src = str(item.get("source_calendar") or "")
        if src and src in hidden:
            continue
        day = str(item.get("due_at") or "")[:10]
        if len(day) != 10:
            continue
        grouped.setdefault(day, []).append(_slim_due(item))
    return grouped


def _due_counts() -> Dict[str, int]:
    counts: Counter[str] = Counter()
    hidden = _disabled_feed_ids()
    with work._connect() as conn:
        rows = conn.execute(
            "SELECT due_at, scheduled_date, status, source_calendar FROM work_items WHERE status != 'done'"
        ).fetchall()
    for row in rows:
        src = str(row["source_calendar"] or "")
        if src and src in hidden:
            continue
        due = str(row["due_at"] or "")[:10]
        if len(due) == 10:
            counts[due] += 1
            continue
        sched = str(row["scheduled_date"] or "")[:10]
        if len(sched) == 10:
            counts[sched] += 1
    return dict(counts)


def _month_weeks(
    year: int,
    month: int,
    hard: List[Dict[str, Any]],
    blocks: List[Dict[str, Any]],
    due_counts: Dict[str, int],
) -> List[List[Dict[str, Any]]]:
    first = date(year, month, 1)
    cursor = monday_of(first)
    weeks: List[List[Dict[str, Any]]] = []
    today = _cal_today().isoformat()
    events_by_day: Dict[str, int] = Counter()
    for item in hard:
        iso = item.get("occurrence_date")
        if iso:
            events_by_day[iso] += 1
    blocks_by_day: Dict[str, int] = Counter()
    for item in blocks:
        iso = item.get("local_date")
        if iso:
            blocks_by_day[iso] += 1
    for _ in range(6):
        week: List[Dict[str, Any]] = []
        for _day in range(7):
            iso = cursor.isoformat()
            event_count = int(events_by_day.get(iso, 0))
            block_count = int(blocks_by_day.get(iso, 0))
            dues = int(due_counts.get(iso, 0))
            week.append(
                {
                    "date": iso,
                    "day": cursor.day,
                    "in_month": cursor.month == month,
                    "is_today": iso == today,
                    "event_count": event_count,
                    "block_count": block_count,
                    "due_count": dues,
                    "has_items": bool(event_count or block_count or dues),
                }
            )
            cursor += timedelta(days=1)
        weeks.append(week)
    return weeks


def _clamp_year_month(year: Any, month: Any) -> Tuple[int, int]:
    today = _cal_today()
    try:
        y = int(year) if year else today.year
    except (TypeError, ValueError):
        y = today.year
    try:
        m = int(month) if month else today.month
    except (TypeError, ValueError):
        m = today.month
    if y < 1970 or y > 2100:
        y = today.year
    if m < 1 or m > 12:
        m = today.month
    return y, m


@eel.expose
def get_month(year: int = 0, month: int = 0) -> Dict[str, Any]:
    maybe_purge_stale_imports()
    y, m = _clamp_year_month(year, month)
    first = date(y, m, 1)
    grid_start = monday_of(first)
    grid_end = grid_start + timedelta(days=41)
    hard = expand_hard_events(grid_start, grid_end)
    blocks = list_blocks(grid_start, grid_end)
    shown, total = _unplaced_ui()
    return {
        "year": y,
        "month": m,
        "label": first.strftime("%B %Y"),
        "weeks": _month_weeks(y, m, hard, blocks, _due_counts()),
        "settings": load_settings(),
        "unplaced": shown,
        "unplaced_total": total,
        "feeds": list_calendar_feeds().get("feeds") or [],
    }


@eel.expose
def get_year(year: int = 0) -> Dict[str, Any]:
    maybe_purge_stale_imports()
    y, _ = _clamp_year_month(year, 1)
    start = date(y, 1, 1)
    grid_start = monday_of(start)
    grid_end = monday_of(date(y, 12, 1)) + timedelta(days=41)
    hard = expand_hard_events(grid_start, grid_end)
    blocks = list_blocks(grid_start, grid_end)
    due_counts = _due_counts()
    shown, total = _unplaced_ui()
    months = []
    for month in range(1, 13):
        first = date(y, month, 1)
        months.append(
            {
                "year": y,
                "month": month,
                "label": first.strftime("%b"),
                "weeks": _month_weeks(y, month, hard, blocks, due_counts),
            }
        )
    return {
        "year": y,
        "label": str(y),
        "months": months,
        "settings": load_settings(),
        "unplaced": shown,
        "unplaced_total": total,
        "feeds": list_calendar_feeds().get("feeds") or [],
    }


@eel.expose
def get_day_agenda(local_date: str = "") -> Dict[str, Any]:
    maybe_purge_stale_imports()
    iso = work._parse_date(local_date) or _cal_today().isoformat()
    day = date.fromisoformat(iso)
    settings = load_settings()
    items = list(expand_hard_events(day, day)) + list(list_blocks(day, day))
    items.sort(key=lambda row: str(row.get("start_at") or ""))
    overdue = []
    if iso == _cal_today().isoformat():
        overdue = [
            _slim_due(item, is_overdue=True)
            for item in work.list_overdue_work()
            if not _is_hidden_source(item.get("source_calendar"))
        ]
    return {
        "local_date": iso,
        "items": items,
        "dues": _dues_by_day(day, day).get(iso, []),
        "overdue": overdue,
        "unplaced": [],
        "settings": settings,
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
def delete_schedule_block(block_id: str, force: bool = False) -> Dict[str, Any]:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM schedule_blocks WHERE id = ?", (block_id,)).fetchone()
        if row is None:
            raise ValueError("Block not found")
        if row["status"] == "locked" and not force:
            raise ValueError("Locked blocks stay until you unlock them")
        conn.execute("DELETE FROM schedule_blocks WHERE id = ?", (block_id,))
        conn.commit()
    return {"ok": True, "id": block_id}


@eel.expose
def update_schedule_block(
    block_id: str,
    title: str = "",
    start_at: str = "",
    end_at: str = "",
    status: str = "",
) -> Dict[str, Any]:
    """Rename or move a work/workout block. Locked blocks can be moved by you."""
    block = _load_block(block_id)
    clean = (title or "").strip() or block["title"]
    start = parse_datetime(start_at) if start_at else parse_datetime(block["start_at"])
    end = parse_datetime(end_at) if end_at else parse_datetime(block["end_at"])
    _validate_span(start, end, hard=False)
    key = str(status or "").strip().lower()
    next_status = key if key in BLOCK_STATUSES else block["status"]
    now = _now().isoformat()
    with _connect() as conn:
        conn.execute(
            """
            UPDATE schedule_blocks
            SET title = ?, local_date = ?, start_at = ?, end_at = ?, status = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                clean[:200],
                start.date().isoformat(),
                start.isoformat(timespec="seconds"),
                end.isoformat(timespec="seconds"),
                next_status,
                now,
                block_id,
            ),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM schedule_blocks WHERE id = ?", (block_id,)).fetchone()
    if block.get("work_item_id") and clean != block["title"]:
        work.update_work_item(block["work_item_id"], clean)
    if block.get("work_item_id") and start.date().isoformat() != block.get("local_date"):
        work.assign_work_item(block["work_item_id"], start.date().isoformat())
    assert row is not None
    return _row_block(row)


@eel.expose
def park_schedule_block(block_id: str) -> Dict[str, Any]:
    """Save for later: take it off the clock into All Work."""
    block = _load_block(block_id)
    work_item_id = block.get("work_item_id")
    with _connect() as conn:
        if work_item_id:
            conn.execute("DELETE FROM schedule_blocks WHERE work_item_id = ?", (work_item_id,))
        else:
            conn.execute("DELETE FROM schedule_blocks WHERE id = ?", (block_id,))
        conn.commit()
    parked = None
    if work_item_id:
        parked = work.assign_work_item(work_item_id, "")
    return {"ok": True, "id": block_id, "parked": parked}


@eel.expose
def schedule_work_at(item_id: str, start_at: str, end_at: str = "") -> Dict[str, Any]:
    """Place an unplaced work item at an exact time."""
    item = _work_item(item_id)
    start = parse_datetime(start_at)
    if end_at:
        end = parse_datetime(end_at)
    else:
        leftover = remaining_minutes(item) or int(load_settings().get("default_estimate_minutes") or DEFAULT_ESTIMATE)
        end = start + timedelta(minutes=max(15, min(int(leftover), CHUNK_MAX)))
    _validate_span(start, end, hard=False)
    if str(item.get("source") or "") != "calendar":
        work.assign_work_item(item_id, start.date().isoformat())
    block = add_block(
        title=item["title"],
        start=start,
        end=end,
        work_item_id=item_id,
        kind="work",
        status="proposed",
    )
    return {"ok": True, "block": block, "item": _work_item(item_id)}


@eel.expose
def place_work_after_lecture(item_id: str, local_date: str = "") -> Dict[str, Any]:
    """Drop optional work time after that day's first timed event, or at wake-up."""
    item = _work_item(item_id)
    iso = work._parse_date(local_date) or str(item.get("due_at") or "")[:10] or _cal_today().isoformat()
    day = date.fromisoformat(iso)
    week = get_week(monday_of(day).isoformat(), include_unplaced=False)
    match = next((row for row in week["days"] if row["date"] == iso), None)
    lectures = sorted(match["events"] if match else [], key=lambda row: str(row.get("start_at") or ""))
    leftover = remaining_minutes(item) or int(load_settings().get("default_estimate_minutes") or DEFAULT_ESTIMATE)
    duration = max(15, min(int(leftover), CHUNK_MAX))
    if lectures:
        start = parse_datetime(lectures[0]["end_at"])
    else:
        hour, minute = parse_clock(str(load_settings().get("day_start") or DAY_START))
        start = datetime(day.year, day.month, day.day, hour, minute, 0)
    end = start + timedelta(minutes=duration)
    return schedule_work_at(item_id, start.isoformat(timespec="seconds"), end.isoformat(timespec="seconds"))
