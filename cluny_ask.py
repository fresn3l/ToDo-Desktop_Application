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
import cluny_snapshot
import cluny_sync
from paths import data_directory

PROPOSAL_SOURCE = "cluny_proposal"
PROPOSAL_CALENDAR = "cluny"
ASK_INSTRUCTION = cluny_snapshot.ASK_INSTRUCTION


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
    return cluny_snapshot.free_minutes(events, day_start, day_end)


def build_context(focus: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    try:
        ctx = cluny_snapshot.build_life_snapshot()
    except Exception:
        ctx = {
            "date": date.today().isoformat(),
            "instruction": ASK_INSTRUCTION,
            "todos_today": [],
            "overdue": [],
            "backlog": [],
            "deadline_todos": [],
            "events_today": [],
            "unplaced": [],
            "free_minutes": 0,
            "weekly_goals": [],
            "notes": None,
            "analytics": {},
            "journal": [],
            "work": {},
            "calendar": {},
            "workouts": [],
            "goals": [],
            "briefs": [],
        }
    ctx["instruction"] = ASK_INSTRUCTION
    if focus:
        ctx["focus"] = focus
    return ctx


@eel.expose
def get_cluny_health() -> Dict[str, Any]:
    import cluny_brain

    probe = cluny_brain.supervisor_status()
    settings = cluny_sync.public_cluny_settings()
    managed = "Kosistenz is keeping Cluny running." if probe.get("managed") else ""
    auto = (
        "Auto-start is on."
        if probe.get("auto_start")
        else "Auto-start is off — start Cluny manually or enable it in Settings."
    )
    offline = "Cluny is off. Journal, to-dos, and the clock still work."
    if not probe.get("brain_ready"):
        detail = str(probe.get("message") or "").strip()
        if detail and detail not in offline:
            offline = f"{detail} Journal, to-dos, and the clock still work."
        elif probe.get("ok") and probe.get("ollama_ok") is False:
            offline = (
                "Cluny is up; Ollama is not ready. Open Ollama and pull a chat model. "
                "Journal, to-dos, and the clock still work."
            )
    return {
        **settings,
        **probe,
        "ok": probe.get("ok"),
        "brain_ready": probe.get("brain_ready"),
        "ollama_ok": probe.get("ollama_ok"),
        "health_status": probe.get("status"),
        "health_message": probe.get("message"),
        "offline_copy": offline if not probe.get("brain_ready") else f"{managed} {auto}".strip(),
    }


@eel.expose
def probe_cluny_connection() -> Dict[str, Any]:
    import cluny_brain

    try:
        cluny_brain.ensure_running(wait=True)
    except Exception:
        pass
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
def ask_cluny(question: str, focus: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    text = str(question or "").strip()
    if not text:
        raise ValueError("Ask a question first")
    packed = focus if isinstance(focus, dict) else None
    return cluny_client.chat(text, context_json=build_context(packed))


@eel.expose
def suggest_cluny_work(question: str = "") -> Dict[str, Any]:
    inbox = _load_inbox()
    closed = _closed_ids(inbox)
    pending_ids = {proposal_uid(row) for row in inbox.get("pending") or []}
    proposals = cluny_client.propose(question or "What should I tackle next?", context_json=build_context())
    rows = proposals.get("proposals") if isinstance(proposals, dict) else proposals
    added = 0
    for row in rows:
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
    kosistenz_id = f"kosistenz:{item.get('id')}"
    inbox["closed"].append(
        {
            **match,
            "status": "accepted",
            "work_item_id": item.get("id"),
            "kosistenz_id": kosistenz_id,
        }
    )
    _save_inbox(inbox)
    try:
        cluny_sync.sync_task_mirror_safe({**item, "id": kosistenz_id})
    except Exception:
        pass
    return {"ok": True, "duplicate": False, "item": item, "inbox": get_cluny_inbox(), "kosistenz_id": kosistenz_id}


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
