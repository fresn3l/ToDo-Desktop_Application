"""Ask Cluny, work proposals, and a local accept/dismiss inbox.

Cluny never places clock times. Accepting a proposal creates an All Work item.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import eel

import cluny_client
import cluny_sync
from paths import data_directory

PROPOSAL_SOURCE = "cluny_proposal"
PROPOSAL_CALENDAR = "cluny"
ASK_INSTRUCTION = (
    "You are Cluny, the local brain. Kosistenz owns the list and the clock. "
    "Answer from this context. When asked what is on today, list todos_today, "
    "events_today, and overdue items. When asked about free time, recommend "
    "open to-dos by title using estimates and free_minutes as capacity. "
    "Never pick a clock time or say to do something at HH:MM. "
    "The user still picks the day; Fill week places the gap."
)


def _inbox_path():
    return data_directory() / "cluny_inbox.json"


def _empty_inbox() -> Dict[str, Any]:
    return {"pending": [], "closed": []}


def _load_inbox() -> Dict[str, Any]:
    path = _inbox_path()
    if not path.exists():
        return _empty_inbox()
    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return _empty_inbox()
    if not isinstance(raw, dict):
        return _empty_inbox()
    pending = raw.get("pending") if isinstance(raw.get("pending"), list) else []
    closed = raw.get("closed") if isinstance(raw.get("closed"), list) else []
    return {
        "pending": [row for row in pending if isinstance(row, dict)],
        "closed": [row for row in closed if isinstance(row, dict)],
    }


def _save_inbox(inbox: Dict[str, Any]) -> Dict[str, Any]:
    packed = {
        "pending": inbox.get("pending") or [],
        "closed": inbox.get("closed") or [],
    }
    path = _inbox_path()
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(packed, handle, indent=2)
    os.replace(tmp, path)
    return packed


def proposal_uid(row: Dict[str, Any]) -> str:
    given = str(row.get("id") or row.get("source_uid") or "").strip()
    if given:
        return given
    title = str(row.get("title") or "").strip().lower()
    due = str(row.get("due") or "").strip()
    kws = "|".join(str(k).strip().lower() for k in (row.get("keywords") or []) if str(k).strip())
    digest = hashlib.sha256(f"{title}|{due}|{kws}".encode("utf-8")).hexdigest()[:16]
    return f"cluny-{digest}"


def _hhmm(raw: Any) -> Optional[str]:
    text = str(raw or "").strip()
    if not text:
        return None
    if "T" in text:
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00")[:32])
            return parsed.strftime("%H:%M")
        except ValueError:
            pass
    if len(text) >= 5 and text[2] == ":":
        return text[:5]
    return text[:16]


def _minutes(hhmm: Optional[str]) -> Optional[int]:
    text = str(hhmm or "").strip()
    if len(text) < 5 or text[2] != ":":
        return None
    try:
        return int(text[:2]) * 60 + int(text[3:5])
    except ValueError:
        return None


def _work_row(item: Dict[str, Any]) -> Dict[str, Any]:
    due = str(item.get("due_at") or "").strip()
    return {
        "title": item.get("title") or "",
        "due": due[:10] or None,
        "estimate_minutes": item.get("estimate_minutes"),
        "status": item.get("status") or "open",
    }


def free_minutes(events: List[Dict[str, Any]], day_start: str, day_end: str) -> int:
    start = _minutes(day_start) or 7 * 60
    end = _minutes(day_end) or 22 * 60
    if end <= start:
        return 0
    busy_raw: List[tuple[int, int]] = []
    for event in events:
        begin = _minutes(event.get("start"))
        finish = _minutes(event.get("end"))
        if begin is None or finish is None:
            continue
        begin = max(start, begin)
        finish = min(end, finish)
        if finish <= begin:
            continue
        busy_raw.append((begin, finish))
    busy_raw.sort()
    busy: List[List[int]] = []
    for begin, finish in busy_raw:
        if busy and begin <= busy[-1][1]:
            busy[-1][1] = max(busy[-1][1], finish)
        else:
            busy.append([begin, finish])
    used = sum(finish - begin for begin, finish in busy)
    return max(0, end - start - used)


def build_context() -> Dict[str, Any]:
    import calclock
    import day_brief
    import goals
    import work

    today = date.today().isoformat()
    todos_today: List[Dict[str, Any]] = []
    overdue: List[Dict[str, Any]] = []
    backlog: List[Dict[str, Any]] = []
    deadline_todos: List[Dict[str, Any]] = []
    try:
        board = work.get_work_board(today)
        todos_today = [_work_row(item) for item in board.get("today") or []][:40]
        overdue = [_work_row(item) for item in board.get("overdue") or [] if item.get("status") != "done"][:20]
        backlog = [_work_row(item) for item in board.get("backlog") or []][:20]
        deadline_todos = [
            {"title": item.get("title") or "", "due": str(item.get("due") or item.get("due_at") or "")[:10]}
            for item in todos_today + overdue + backlog
            if item.get("due")
        ][:40]
    except Exception:
        todos_today, overdue, backlog, deadline_todos = [], [], [], []
    events_today: List[Dict[str, Any]] = []
    unplaced: List[str] = []
    day_start, day_end = "07:00", "22:00"
    try:
        agenda = calclock.get_day_agenda(today)
        settings = agenda.get("settings") or {}
        day_start = str(settings.get("day_start") or day_start)
        day_end = str(settings.get("day_end") or day_end)
        for item in agenda.get("items") or []:
            events_today.append(
                {
                    "title": item.get("title") or "",
                    "kind": item.get("kind") or "",
                    "start": _hhmm(item.get("start_at")),
                    "end": _hhmm(item.get("end_at")),
                }
            )
        unplaced = [
            str(item.get("title") or "").strip()
            for item in (agenda.get("unplaced") or [])
            if str(item.get("title") or "").strip()
        ][:20]
    except Exception:
        events_today, unplaced = [], []
    weekly_goals: List[str] = []
    try:
        for goal in goals.list_goals():
            if goal.get("horizon") == "week" and not goal.get("archived"):
                title = str(goal.get("title") or "").strip()
                if title:
                    weekly_goals.append(title)
    except Exception:
        weekly_goals = []
    notes = None
    try:
        brief = day_brief.get_brief(today, "morning") or {}
        text = str(brief.get("intention_text") or "").strip()
        notes = text or None
    except Exception:
        notes = None
    return {
        "date": today,
        "instruction": ASK_INSTRUCTION,
        "todos_today": todos_today,
        "overdue": overdue,
        "backlog": backlog,
        "deadline_todos": deadline_todos[:40],
        "events_today": events_today[:40],
        "unplaced": unplaced,
        "free_minutes": free_minutes(events_today, day_start, day_end),
        "weekly_goals": weekly_goals[:20],
        "notes": notes,
    }


@eel.expose
def get_cluny_health() -> Dict[str, Any]:
    probe = cluny_client.health()
    settings = cluny_sync.public_cluny_settings()
    return {
        **settings,
        "ok": probe.get("ok"),
        "brain_ready": probe.get("brain_ready"),
        "ollama_ok": probe.get("ollama_ok"),
        "health_status": probe.get("status"),
        "health_message": probe.get("message"),
        "offline_copy": "Cluny is off. Journal, to-dos, and the clock still work.",
    }


@eel.expose
def probe_cluny_connection() -> Dict[str, Any]:
    return get_cluny_health()


def _closed_ids(inbox: Dict[str, Any]) -> set[str]:
    return {proposal_uid(row) for row in inbox.get("closed") or []}


@eel.expose
def get_cluny_inbox() -> Dict[str, Any]:
    inbox = _load_inbox()
    pending = inbox.get("pending") or []
    return {
        "pending": pending,
        "pending_count": len(pending),
        "closed": inbox.get("closed") or [],
    }


@eel.expose
def ask_cluny(question: str) -> Dict[str, Any]:
    text = str(question or "").strip()
    if not text:
        raise ValueError("Ask a question first")
    return cluny_client.chat(text, context_json=build_context())


@eel.expose
def suggest_cluny_work(question: str = "") -> Dict[str, Any]:
    inbox = _load_inbox()
    closed = _closed_ids(inbox)
    pending_ids = {proposal_uid(row) for row in inbox.get("pending") or []}
    proposals = cluny_client.propose(question or "What should I tackle next?", context_json=build_context())
    added = 0
    for row in proposals:
        uid = proposal_uid(row)
        if uid in closed or uid in pending_ids:
            continue
        packed = {
            "id": uid,
            "title": row["title"],
            "estimate_minutes": row.get("estimate_minutes"),
            "due": row.get("due"),
            "keywords": row.get("keywords") or [],
            "status": "pending",
        }
        inbox["pending"].append(packed)
        pending_ids.add(uid)
        added += 1
    _save_inbox(inbox)
    return {**get_cluny_inbox(), "added": added}


@eel.expose
def accept_cluny_proposal(proposal_id: str) -> Dict[str, Any]:
    import work

    uid = str(proposal_id or "").strip()
    inbox = _load_inbox()
    match = next((row for row in inbox["pending"] if proposal_uid(row) == uid), None)
    if match is None:
        closed = next((row for row in inbox["closed"] if proposal_uid(row) == uid), None)
        if closed and closed.get("work_item_id"):
            return {"ok": True, "duplicate": True, "item": None, "inbox": get_cluny_inbox()}
        raise ValueError("That suggestion is gone")
    item = work.create_work_item(
        match["title"],
        scheduled_date=None,
        source=PROPOSAL_SOURCE,
        due_at=match.get("due"),
        estimate_minutes=match.get("estimate_minutes"),
        source_uid=uid,
        source_calendar=PROPOSAL_CALENDAR,
    )
    inbox["pending"] = [row for row in inbox["pending"] if proposal_uid(row) != uid]
    inbox["closed"].append(
        {
            **match,
            "status": "accepted",
            "work_item_id": item.get("id"),
        }
    )
    _save_inbox(inbox)
    return {"ok": True, "duplicate": False, "item": item, "inbox": get_cluny_inbox()}


@eel.expose
def dismiss_cluny_proposal(proposal_id: str) -> Dict[str, Any]:
    uid = str(proposal_id or "").strip()
    inbox = _load_inbox()
    match = next((row for row in inbox["pending"] if proposal_uid(row) == uid), None)
    inbox["pending"] = [row for row in inbox["pending"] if proposal_uid(row) != uid]
    if match:
        inbox["closed"].append({**match, "status": "dismissed"})
    _save_inbox(inbox)
    return get_cluny_inbox()
