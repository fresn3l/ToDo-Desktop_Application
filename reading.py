"""Currently reading — book, page, pages today, and a reading journal."""

from __future__ import annotations

import json
import os
from datetime import date
from typing import Any, Dict, Optional

import eel

import journal
from paths import data_directory

MAX_TITLE = 160
MAX_PAGE = 20_000


def _today() -> date:
    return date.today()


def _path():
    return data_directory() / "reading.json"


def _clip_title(raw: Any) -> str:
    return str(raw or "").strip()[:MAX_TITLE]


def _page(raw: Any) -> int:
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return 0
    return max(0, min(MAX_PAGE, n))


def _load() -> Dict[str, Any]:
    packed = {
        "title": "",
        "page": 0,
        "pages_today": 0,
        "pages_today_date": "",
    }
    path = _path()
    if not path.exists():
        return packed
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return packed
    if not isinstance(data, dict):
        return packed
    packed["title"] = _clip_title(data.get("title"))
    packed["page"] = _page(data.get("page"))
    packed["pages_today"] = _page(data.get("pages_today"))
    packed["pages_today_date"] = str(data.get("pages_today_date") or "")[:10]
    return packed


def _write(state: Dict[str, Any]) -> Dict[str, Any]:
    path = _path()
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2)
    os.replace(tmp, path)
    return _decorate(state)


def _decorate(state: Dict[str, Any], today: Optional[date] = None) -> Dict[str, Any]:
    today = today or _today()
    iso = today.isoformat()
    pages_today = int(state.get("pages_today") or 0)
    if str(state.get("pages_today_date") or "") != iso:
        pages_today = 0
    return {
        "title": state.get("title") or "",
        "page": int(state.get("page") or 0),
        "pages_today": pages_today,
        "pages_today_date": iso if pages_today else str(state.get("pages_today_date") or ""),
        "today": iso,
    }


@eel.expose
def get_reading() -> Dict[str, Any]:
    return _decorate(_load())


@eel.expose
def set_reading_book(title: str, page: Any = None) -> Dict[str, Any]:
    state = _load()
    state["title"] = _clip_title(title)
    if page is not None and str(page) != "":
        state["page"] = _page(page)
    return _write(state)


@eel.expose
def add_reading_pages(pages: Any = 1) -> Dict[str, Any]:
    n = _page(pages)
    if n <= 0:
        raise ValueError("Add at least one page")
    state = _load()
    if not state.get("title"):
        raise ValueError("Name the book first")
    today = _today().isoformat()
    if str(state.get("pages_today_date") or "") != today:
        state["pages_today"] = 0
        state["pages_today_date"] = today
    state["pages_today"] = _page(int(state.get("pages_today") or 0) + n)
    state["page"] = _page(int(state.get("page") or 0) + n)
    return _write(state)


@eel.expose
def save_reading_journal(content: str) -> Dict[str, Any]:
    text = str(content or "").strip()
    if not text:
        raise ValueError("Write what you learned")
    state = _decorate(_load())
    extra = {"book": state["title"], "page": state["page"], "pages_today": state["pages_today"]}
    entry = journal.save_journal_entry(text, 0, False, ["reading"], "reading", extra)
    return {"reading": state, "entry": entry}
