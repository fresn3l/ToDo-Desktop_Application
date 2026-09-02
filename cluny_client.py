"""HTTP client for `cluny serve` (localhost brain). Kosistenz does not embed Ollama."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional
from urllib.parse import quote, urljoin, urlparse

import cluny_sync

DEFAULT_BRAIN_URL = "http://127.0.0.1:8787"
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ARG002
        return None


def _opener() -> urllib.request.OpenerDirector:
    return urllib.request.build_opener(_NoRedirect)


def validate_brain_url(raw: str) -> str:
    text = str(raw or "").strip().rstrip("/")
    if not text:
        return DEFAULT_BRAIN_URL
    parsed = urlparse(text)
    host = (parsed.hostname or "").lower()
    loopback = host in LOOPBACK_HOSTS
    if parsed.scheme == "https":
        return text
    if parsed.scheme == "http" and loopback:
        return text
    raise ValueError("Brain URL must be https, or http on localhost")


def brain_url() -> str:
    cfg = cluny_sync.effective_cluny_config()
    return validate_brain_url(str(cfg.get("brain_url") or DEFAULT_BRAIN_URL))


def ingest_endpoint() -> str:
    cfg = cluny_sync.effective_cluny_config()
    custom = str(cfg.get("ingest_url") or "").strip()
    if custom:
        return cluny_sync._validate_ingest_url(custom)
    return urljoin(brain_url() + "/", "ingest/text")


def _token() -> str:
    return str(cluny_sync.effective_cluny_config().get("api_key") or "").strip()


def _headers(*, json_body: bool = True, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    headers = {"Accept": "application/json"}
    if json_body:
        headers["Content-Type"] = "application/json; charset=utf-8"
    if extra:
        headers.update(extra)
    token = _token()
    if token:
        headers["X-Cluny-Token"] = token
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _request(
    method: str,
    url: str,
    payload: Optional[Dict[str, Any]] = None,
    *,
    timeout: float = 30.0,
    raw_body: Optional[bytes] = None,
    headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    body = raw_body
    req_headers = headers or _headers(json_body=payload is not None and raw_body is None)
    if payload is not None and raw_body is None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, method=method, headers=req_headers)
    try:
        with _opener().open(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        raise ValueError(f"Cluny HTTP {exc.code}: {detail or exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise ValueError("Cluny is off or unreachable") from exc
    if not raw:
        return {}
    try:
        data = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("Cluny returned something that is not JSON") from exc
    return data if isinstance(data, dict) else {"value": data}


def _api_url(path: str) -> str:
    base = brain_url().rstrip("/") + "/"
    return urljoin(base, path.lstrip("/"))


def health() -> Dict[str, Any]:
    try:
        data = _request("GET", _api_url("health"), timeout=3.0)
    except ValueError as exc:
        return {
            "ok": False,
            "brain_ready": False,
            "ollama_ok": False,
            "status": "offline",
            "message": str(exc),
        }
    ready = bool(data.get("brain_ready", data.get("status") == "ok"))
    return {
        "ok": True,
        "brain_ready": ready,
        "ollama_ok": bool(data.get("ollama_ok", ready)),
        "status": str(data.get("status") or ("ok" if ready else "down")),
        "message": data.get("message"),
        "doc_count": data.get("doc_count"),
        "chunk_count": data.get("chunk_count"),
        "chat_model": data.get("chat_model"),
        "embed_model": data.get("embed_model"),
        "retrieval_k": data.get("retrieval_k"),
        "agent_mode": data.get("agent_mode"),
        "ask_collection": data.get("ask_collection"),
    }


def stats() -> Dict[str, Any]:
    return _request("GET", _api_url("stats"), timeout=5.0)


def ingest_text(
    text: str,
    *,
    title: str = "",
    source: str = "kosistenz-journal",
    collection: str = "journal",
) -> Dict[str, Any]:
    body = {
        "text": str(text or ""),
        "catalog": True,
        "source": source,
        "title": title or "journal",
        "collection": collection,
    }
    return _request("POST", ingest_endpoint(), body, timeout=60.0)


def journal_ingest_payload(entry: Dict[str, Any]) -> Dict[str, Any]:
    day = str(entry.get("date") or entry.get("created_at") or "")[:10]
    title = f"{day} journal" if day else "journal"
    return {
        "text": str(entry.get("content") or ""),
        "catalog": True,
        "source": "kosistenz-journal",
        "title": title,
        "collection": "journal",
    }


def chat(
    question: str,
    context_json: Optional[Dict[str, Any]] = None,
    *,
    session_id: Optional[str] = None,
    collection: Optional[str] = None,
    k: Optional[int] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"question": str(question or "").strip()}
    if context_json:
        payload["context_json"] = context_json
    if session_id:
        payload["session_id"] = session_id
    if collection:
        payload["collection"] = collection
    if k is not None:
        payload["k"] = k
    data = _request("POST", _api_url("chat"), payload, timeout=90.0)
    sources = data.get("sources") if isinstance(data.get("sources"), list) else []
    return {
        "answer": str(data.get("answer") or ""),
        "sources": sources,
        "session_id": data.get("session_id"),
        "route": data.get("route") or "ask",
        "tool_calls": data.get("tool_calls") or [],
    }


def chat_stream(
    question: str,
    context_json: Optional[Dict[str, Any]] = None,
    *,
    session_id: Optional[str] = None,
    collection: Optional[str] = None,
    k: Optional[int] = None,
    on_event: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    """Read SSE from /chat/stream; optionally invoke on_event for each JSON payload."""
    payload: Dict[str, Any] = {"question": str(question or "").strip()}
    if context_json:
        payload["context_json"] = context_json
    if session_id:
        payload["session_id"] = session_id
    if collection:
        payload["collection"] = collection
    if k is not None:
        payload["k"] = k
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        _api_url("chat/stream"),
        data=body,
        method="POST",
        headers={**_headers(), "Accept": "text/event-stream"},
    )
    route = "ask"
    sid = session_id
    sources: List[Any] = []
    tokens: List[str] = []
    try:
        with _opener().open(req, timeout=120.0) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                data_text = line[5:].strip()
                if data_text == "[DONE]":
                    break
                try:
                    event = json.loads(data_text)
                except json.JSONDecodeError:
                    continue
                if not isinstance(event, dict):
                    continue
                if on_event:
                    on_event(event)
                if "route" in event:
                    route = str(event.get("route") or route)
                if "session_id" in event:
                    sid = str(event.get("session_id") or sid)
                if "sources" in event and isinstance(event["sources"], list):
                    sources = event["sources"]
                if "token" in event:
                    tokens.append(str(event["token"]))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        raise ValueError(f"Cluny HTTP {exc.code}: {detail or exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise ValueError("Cluny is off or unreachable") from exc
    return {
        "answer": "".join(tokens),
        "sources": sources,
        "session_id": sid,
        "route": route,
    }


def propose(
    question: str,
    context_json: Optional[Dict[str, Any]] = None,
    *,
    collection: Optional[str] = None,
    k: Optional[int] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "question": str(question or "").strip() or "What should I tackle next?",
    }
    if context_json:
        payload["context_json"] = context_json
    if collection:
        payload["collection"] = collection
    if k is not None:
        payload["k"] = k
    data = _request("POST", _api_url("propose"), payload, timeout=90.0)
    items = data.get("proposals") if isinstance(data.get("proposals"), list) else []
    sources = data.get("sources") if isinstance(data.get("sources"), list) else []
    out: list[Dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        est = item.get("estimate_minutes")
        estimate = int(est) if isinstance(est, (int, float)) else None
        due = str(item.get("due") or "").strip() or None
        raw_kw = item.get("keywords") or []
        keywords = [str(k).strip() for k in raw_kw if str(k).strip()] if isinstance(raw_kw, list) else []
        given = str(item.get("id") or item.get("proposal_id") or "").strip()
        out.append(
            {
                "id": given,
                "title": title,
                "estimate_minutes": estimate,
                "due": due,
                "keywords": keywords,
            }
        )
    return {"proposals": out, "sources": sources}


def library_list(
    *,
    collection: Optional[str] = None,
    source: Optional[str] = None,
) -> Dict[str, Any]:
    url = _api_url("library")
    params = []
    if collection:
        params.append(f"collection={quote(collection)}")
    if source:
        params.append(f"source={quote(source)}")
    if params:
        url = url + "?" + "&".join(params)
    return _request("GET", url, timeout=15.0)


def library_collections() -> Dict[str, Any]:
    return _request("GET", _api_url("library/collections"), timeout=10.0)


def library_delete(doc_id: str) -> Dict[str, Any]:
    return _request("DELETE", _api_url(f"library/{doc_id}"), timeout=30.0)


def brain_config_get() -> Dict[str, Any]:
    return _request("GET", _api_url("brain/config"), timeout=10.0)


def brain_config_put(payload: Dict[str, Any]) -> Dict[str, Any]:
    return _request("PUT", _api_url("brain/config"), payload, timeout=15.0)


def brain_config_reset(payload: Dict[str, Any]) -> Dict[str, Any]:
    return _request("POST", _api_url("brain/config/reset"), payload, timeout=15.0)


def user_config_get() -> Dict[str, Any]:
    return _request("GET", _api_url("user/config"), timeout=10.0)


def user_config_put(payload: Dict[str, Any]) -> Dict[str, Any]:
    return _request("PUT", _api_url("user/config"), payload, timeout=15.0)


def sessions_list(*, limit: int = 50) -> Dict[str, Any]:
    return _request("GET", _api_url(f"sessions?limit={int(limit)}"), timeout=10.0)


def sessions_create(title: Optional[str] = None) -> Dict[str, Any]:
    body: Dict[str, Any] = {}
    if title:
        body["title"] = title
    return _request("POST", _api_url("sessions"), body, timeout=10.0)


def session_messages(session_id: str) -> Dict[str, Any]:
    return _request("GET", _api_url(f"sessions/{session_id}/messages"), timeout=15.0)


def ingest_file_bytes(
    filename: str,
    content: bytes,
    *,
    title: Optional[str] = None,
    collection: Optional[str] = None,
    copy_into_library: bool = False,
) -> Dict[str, Any]:
    import uuid

    boundary = uuid.uuid4().hex
    parts: List[bytes] = []
    fields = {
        "title": title or "",
        "copy_into_library": "true" if copy_into_library else "false",
    }
    if collection:
        fields["collection"] = collection
    for key, value in fields.items():
        parts.append(f"--{boundary}\r\n".encode())
        parts.append(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode())
        parts.append(f"{value}\r\n".encode())
    safe_name = Path(filename or "upload.txt").name
    parts.append(f"--{boundary}\r\n".encode())
    parts.append(
        f'Content-Disposition: form-data; name="file"; filename="{safe_name}"\r\n'.encode()
    )
    parts.append(b"Content-Type: application/octet-stream\r\n\r\n")
    parts.append(content)
    parts.append(b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    body = b"".join(parts)
    headers = _headers(json_body=False, extra={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    return _request(
        "POST",
        _api_url("ingest/file"),
        raw_body=body,
        headers=headers,
        timeout=120.0,
    )


def sync_task(
    *,
    external_id: str,
    title: str,
    status: str = "open",
    due_at: Optional[str] = None,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    payload = {
        "external_id": external_id,
        "title": title,
        "status": status,
        "due_at": due_at,
        "notes": notes,
    }
    return _request("POST", _api_url("tasks/sync"), payload, timeout=15.0)


def delete_synced_task(external_id: str) -> Dict[str, Any]:
    return _request("DELETE", _api_url(f"tasks/sync/{external_id}"), timeout=15.0)


def ensure_serve_running() -> Dict[str, Any]:
    """Start Cluny serve if auto-start is enabled (delegates to cluny_brain)."""
    import cluny_brain

    return cluny_brain.ensure_running(wait=True)
