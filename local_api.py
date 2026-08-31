"""
Loopback HTTP API for the Mac menu bar, widget, and Services.

Eel serves the WebView on its own port. This server binds 127.0.0.1:18741
(or the next free port through 18750) so WidgetKit and the status item can
call Python without going through JavaScript.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qs, urlparse

import work
import workouts

API_PORT_START = 18741
API_PORT_END = 18750
MAX_BODY_BYTES = 64 * 1024
MAX_CALENDAR_BODY_BYTES = 2 * 1024 * 1024
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}

_bound_port: Optional[int] = None
_server: Optional[ThreadingHTTPServer] = None


def bound_port() -> Optional[int]:
    return _bound_port


def _hostname(host_header: str) -> str:
    raw = (host_header or "").strip().lower()
    if raw.startswith("["):
        end = raw.find("]")
        if end != -1:
            return raw[1:end]
    return raw.split("/")[0].split(":")[0]


def is_loopback_host(host_header: str) -> bool:
    return _hostname(host_header) in LOOPBACK_HOSTS


def origin_allowed(origin: str) -> bool:
    """Native clients omit Origin. Browser CSRF sends a non-loopback Origin."""
    raw = (origin or "").strip()
    if not raw:
        return True
    if raw.lower() == "null":
        return False
    parsed = urlparse(raw)
    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.hostname or "").lower()
    if host not in LOOPBACK_HOSTS:
        return False
    ui_port = os.environ.get("KOSISTENZ_UI_PORT")
    if not ui_port:
        return True
    try:
        want = int(ui_port)
    except ValueError:
        return True
    port = parsed.port
    if port is None:
        port = 443 if parsed.scheme == "https" else 80
    return port == want


def client_allowed(headers: Any) -> bool:
    """DNS-rebinding (Host) and website CSRF (Origin) gates for the loopback API."""
    getter = headers.get if hasattr(headers, "get") else lambda _key, default="": default
    host = str(getter("Host") or getter("host") or "")
    origin = str(getter("Origin") or getter("origin") or "")
    if host and not is_loopback_host(host):
        return False
    if not origin_allowed(origin):
        return False
    return True


def _today() -> date:
    return date.today()


def widget_payload() -> Dict[str, Any]:
    """Live Notification Center / Lock Screen payload (and JSON snapshot)."""
    payload = dict(work.refresh_widget_snapshot())
    payload["api_port"] = _bound_port
    return payload


def menu_status() -> Dict[str, Any]:
    today_iso = _today().isoformat()
    board = work.get_work_board(today_iso)
    today_items = list(board.get("today") or [])
    active = next((item for item in today_items if item.get("status") == "active"), None)
    first_open = next((item for item in today_items if item.get("status") == "open"), None)
    payload = widget_payload()
    return {
        "date": today_iso,
        "summary": payload.get("summary") or "Today is empty",
        "today_empty": bool(payload.get("today_empty")),
        "open_count": int(payload.get("open_count") or 0),
        "done_count": int(payload.get("done_count") or 0),
        "workout_logged": bool(payload.get("workout_logged")),
        "journal_today": bool(payload.get("journal_today")),
        "journal_streak": int(payload.get("journal_streak") or 0),
        "active_id": None if active is None else active.get("id"),
        "active_title": None if active is None else active.get("title"),
        "first_open_id": None if first_open is None else first_open.get("id"),
        "first_open_title": None if first_open is None else first_open.get("title"),
        "api_port": _bound_port,
    }


def start_today_todo() -> Dict[str, Any]:
    board = work.get_work_board()
    for item in board.get("today") or []:
        if item.get("status") == "active":
            return {"ok": True, "already": True, "item": item}
    for item in board.get("today") or []:
        if item.get("status") == "open":
            started = work.start_work_item(item["id"])
            return {"ok": True, "already": False, "item": started}
    raise ValueError("No open to do today")


def finish_today_todo() -> Dict[str, Any]:
    board = work.get_work_board()
    for item in board.get("today") or []:
        if item.get("status") == "active":
            finished = work.finish_work_item(item["id"])
            return {"ok": True, "item": finished}
    raise ValueError("Nothing is active")


def log_session(
    kind: str,
    miles: Any = None,
    minutes: Any = None,
    other_label: str = "",
) -> Dict[str, Any]:
    key = str(kind or "").strip().lower()
    if key == "running" and miles is None:
        miles = 0
    day = workouts.add_workout_session(
        _today().isoformat(),
        key,
        other_label=other_label,
        miles=miles,
        minutes=minutes,
    )
    return {"ok": True, "day": day}


def park_in_all_work(title: str) -> Dict[str, Any]:
    clean = (title or "").strip()
    if not clean:
        raise ValueError("Title is required")
    item = work.create_work_item(clean, scheduled_date=None, source="service")
    return {"ok": True, "item": item}


def handle_request(method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Tuple[int, Dict[str, Any]]:
    """Pure router used by the HTTP server and tests."""
    method = (method or "GET").upper()
    parsed = urlparse(path)
    route = parsed.path.rstrip("/") or "/"
    payload = body if isinstance(body, dict) else {}
    query = parse_qs(parsed.query)

    try:
        if method == "GET" and route in ("/api/widget", "/api/snapshot"):
            return 200, widget_payload()
        if method == "GET" and route == "/api/status":
            return 200, menu_status()
        if method == "GET" and route in ("/api/health", "/api/ok"):
            return 200, {"ok": True, "port": _bound_port}
        if method == "POST" and route == "/api/todo/start":
            return 200, start_today_todo()
        if method == "POST" and route == "/api/todo/finish":
            return 200, finish_today_todo()
        if method == "POST" and route == "/api/workout/log":
            kind = payload.get("kind") or (query.get("kind") or [""])[0]
            return 200, log_session(
                str(kind),
                miles=payload.get("miles"),
                minutes=payload.get("minutes"),
                other_label=str(payload.get("other_label") or ""),
            )
        if method == "POST" and route == "/api/work/park":
            title = payload.get("title") or (query.get("title") or [""])[0]
            return 200, park_in_all_work(str(title))
        if method == "POST" and route == "/api/calendar/ingest":
            import calclock

            return 200, calclock.ingest_calendar_events(payload)
    except ValueError as exc:
        return 400, {"ok": False, "error": str(exc)}
    except Exception:
        return 500, {"ok": False, "error": "Server error"}
    return 404, {"ok": False, "error": "Not found"}


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        self._dispatch("GET")

    def do_POST(self) -> None:  # noqa: N802
        self._dispatch("POST")

    def do_OPTIONS(self) -> None:  # noqa: N802
        if not client_allowed(self.headers):
            self._write(403, {"ok": False, "error": "Forbidden"})
            return
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return

    def _dispatch(self, method: str) -> None:
        if not client_allowed(self.headers):
            self._write(403, {"ok": False, "error": "Forbidden"})
            return
        body: Dict[str, Any] = {}
        if method == "POST":
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except (TypeError, ValueError):
                self._write(400, {"ok": False, "error": "Invalid Content-Length"})
                return
            if length < 0:
                self._write(400, {"ok": False, "error": "Invalid Content-Length"})
                return
            route = urlparse(self.path).path.rstrip("/") or "/"
            limit = MAX_CALENDAR_BODY_BYTES if route == "/api/calendar/ingest" else MAX_BODY_BYTES
            if length > limit:
                self._write(413, {"ok": False, "error": "Request too large"})
                return
            raw = self.rfile.read(length) if length else b""
            if raw:
                try:
                    parsed = json.loads(raw.decode("utf-8"))
                    if isinstance(parsed, dict):
                        body = parsed
                except (json.JSONDecodeError, UnicodeDecodeError):
                    self._write(400, {"ok": False, "error": "Invalid JSON"})
                    return
        status, payload = handle_request(method, self.path, body)
        self._write(status, payload)

    def _write(self, status: int, payload: Dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)


def start_background_server(preferred: Optional[int] = None) -> int:
    """Bind 127.0.0.1 and serve in a daemon thread. Safe to call once."""
    global _bound_port, _server
    if _server is not None and _bound_port:
        return _bound_port
    env_port = os.environ.get("KOSISTENZ_API_PORT")
    start = int(preferred or env_port or API_PORT_START)
    last_error: Optional[Exception] = None
    for port in range(start, API_PORT_END + 1):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
            server.daemon_threads = True
            thread = threading.Thread(target=server.serve_forever, name="kosistenz-api", daemon=True)
            thread.start()
            _server = server
            _bound_port = port
            os.environ["KOSISTENZ_API_PORT"] = str(port)
            return port
        except OSError as exc:
            last_error = exc
            continue
    raise RuntimeError(f"Could not bind local API on {start}-{API_PORT_END}: {last_error}")
