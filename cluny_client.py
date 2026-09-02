"""HTTP client for `cluny serve` (localhost brain). Kosistenz does not embed Ollama."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, Optional
from urllib.parse import urljoin, urlparse

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


def _request(
    method: str,
    url: str,
    payload: Optional[Dict[str, Any]] = None,
    *,
    timeout: float = 30.0,
) -> Dict[str, Any]:
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    token = _token()
    if token:
        headers["X-Cluny-Token"] = token
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
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


def health() -> Dict[str, Any]:
    try:
        data = _request("GET", urljoin(brain_url() + "/", "health"), timeout=3.0)
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
    }


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


def chat(question: str, context_json: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"question": str(question or "").strip()}
    if context_json:
        payload["context_json"] = context_json
    data = _request("POST", urljoin(brain_url() + "/", "chat"), payload, timeout=90.0)
    sources = data.get("sources") if isinstance(data.get("sources"), list) else []
    return {
        "answer": str(data.get("answer") or ""),
        "sources": sources,
        "session_id": data.get("session_id"),
        "route": data.get("route") or "ask",
    }


def propose(question: str, context_json: Optional[Dict[str, Any]] = None) -> list[Dict[str, Any]]:
    payload: Dict[str, Any] = {
        "question": str(question or "").strip() or "What should I tackle next?",
    }
    if context_json:
        payload["context_json"] = context_json
    data = _request("POST", urljoin(brain_url() + "/", "propose"), payload, timeout=90.0)
    items = data.get("proposals") if isinstance(data.get("proposals"), list) else []
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
    return out
