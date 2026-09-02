"""Brain tab — full Cluny GUI over HTTP (sidebar, chat stream, library, config)."""

from __future__ import annotations

import base64
import json
from typing import Any, Dict, List, Optional

import eel

import cluny_ask
import cluny_client
import cluny_sync

_brain_session_id: Optional[str] = None


def _context() -> Dict[str, Any]:
    return cluny_ask.build_context()


def _set_session(session_id: Optional[str]) -> None:
    global _brain_session_id  # noqa: PLW0603
    _brain_session_id = str(session_id).strip() if session_id else None


@eel.expose
def brain_ensure_serve() -> Dict[str, Any]:
    return cluny_client.ensure_serve_running()


@eel.expose
def brain_health() -> Dict[str, Any]:
    probe = cluny_client.health()
    settings = cluny_sync.public_cluny_settings()
    return {
        **settings,
        **probe,
        "offline_copy": "Cluny is off. Journal, to-dos, and the clock still work.",
    }


@eel.expose
def brain_stats() -> Dict[str, Any]:
    try:
        return cluny_client.stats()
    except ValueError as exc:
        return {"error": str(exc)}


@eel.expose
def brain_library(
    collection: str = "",
    source: str = "",
) -> Dict[str, Any]:
    return cluny_client.library_list(
        collection=collection or None,
        source=source or None,
    )


@eel.expose
def brain_library_filters() -> Dict[str, Any]:
    return cluny_client.library_collections()


@eel.expose
def brain_delete_doc(doc_id: str) -> Dict[str, Any]:
    return cluny_client.library_delete(str(doc_id or "").strip())


@eel.expose
def brain_ingest_file_b64(
    filename: str,
    content_b64: str,
    title: str = "",
    collection: str = "",
) -> Dict[str, Any]:
    raw = base64.b64decode(content_b64 or "")
    return cluny_client.ingest_file_bytes(
        filename,
        raw,
        title=title or None,
        collection=collection or None,
    )


@eel.expose
def brain_new_session(title: str = "") -> Dict[str, Any]:
    created = cluny_client.sessions_create(title or None)
    sid = created.get("session_id")
    _set_session(str(sid) if sid else None)
    return created


@eel.expose
def brain_list_sessions(limit: int = 50) -> Dict[str, Any]:
    return cluny_client.sessions_list(limit=limit)


@eel.expose
def brain_load_session(session_id: str) -> Dict[str, Any]:
    sid = str(session_id or "").strip()
    _set_session(sid)
    return cluny_client.session_messages(sid)


@eel.expose
def brain_get_session_id() -> Optional[str]:
    return _brain_session_id


@eel.expose
def brain_chat(question: str, collection: str = "") -> Dict[str, Any]:
    text = str(question or "").strip()
    if not text:
        raise ValueError("Ask a question first")
    result = cluny_client.chat(
        text,
        context_json=_context(),
        session_id=_brain_session_id,
        collection=collection or None,
    )
    if result.get("session_id"):
        _set_session(str(result["session_id"]))
    return result


@eel.expose
def brain_chat_stream(question: str, collection: str = "") -> Dict[str, Any]:
    """Stream chat; pushes token events to JS via eel.brain_push_stream_event."""
    text = str(question or "").strip()
    if not text:
        raise ValueError("Ask a question first")
    events: List[Dict[str, Any]] = []

    def on_event(event: Dict[str, Any]) -> None:
        events.append(event)
        try:
            eel.brain_push_stream_event(event)()
        except Exception:
            pass

    result = cluny_client.chat_stream(
        text,
        context_json=_context(),
        session_id=_brain_session_id,
        collection=collection or None,
        on_event=on_event,
    )
    if result.get("session_id"):
        _set_session(str(result["session_id"]))
    return result


@eel.expose
def brain_propose(question: str = "", collection: str = "") -> Dict[str, Any]:
    staged = cluny_ask.suggest_cluny_work(question or "What should I tackle next?")
    raw = cluny_client.propose(
        question or "What should I tackle next?",
        context_json=_context(),
        collection=collection or None,
    )
    return {
        "proposals": staged.get("pending") or raw.get("proposals") or [],
        "sources": raw.get("sources") or [],
        "added": staged.get("added", 0),
        "inbox": staged,
    }


@eel.expose
def brain_config_get() -> Dict[str, Any]:
    return cluny_client.brain_config_get()


@eel.expose
def brain_config_save(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Invalid brain config")
    return cluny_client.brain_config_put(payload)


@eel.expose
def brain_config_reset(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        payload = {"reset_all": True}
    return cluny_client.brain_config_reset(payload)


@eel.expose
def brain_user_config_get() -> Dict[str, Any]:
    return cluny_client.user_config_get()


@eel.expose
def brain_user_config_save(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Invalid user config")
    return cluny_client.user_config_put(payload)


@eel.expose
def brain_export_config() -> str:
    return json.dumps(cluny_client.brain_config_get(), indent=2)


@eel.expose
def brain_import_config(raw_json: str) -> Dict[str, Any]:
    data = json.loads(raw_json or "{}")
    if not isinstance(data, dict):
        raise ValueError("Brain config must be a JSON object")
    return cluny_client.brain_config_put(data)


@eel.expose
def brain_sync_analytics() -> Dict[str, Any]:
    return cluny_sync.sync_analytics_rollup_safe()


@eel.expose
def brain_accept_proposal(proposal_id: str) -> Dict[str, Any]:
    return cluny_ask.accept_cluny_proposal(proposal_id)


@eel.expose
def brain_context_preview() -> Dict[str, Any]:
    return _context()
